# API: чат по анализу

Статус: реализован в ayqyn/api/chat.py и ayqyn/chat/. Проверен в автоматических тестах и на живой модели с точными цитатами. Полная смысловая оценка неизвестных комплектов отдельно не завершена.
База кода: c287a1e, ветка codex/backend-research-snapshot, 2026-09-23. План реализации: [analysis-chat-backend.md](../plans/analysis-chat-backend.md).

## Общие правила

Один неизменяемый серверный снимок анализа и один диалог на снимок. ID непрозрачны: a-<uuid> для анализа, t-<uuid> для ответа, m-<uuid> для сообщения. Фронтенд не собирает пути и ID документов по именам.

Версия новых ответов: schema_version = 1. Источники всегда из текущего снимка. Существующие поля /api/analyze сохраняются; клиентский отчёт не используется для создания достоверного серверного анализа.

## Маршруты MVP

| Метод и путь | Назначение |
|---|---|
| POST /api/analyze | Существующий анализ; дополнительно возвращает analysis_id и chat |
| GET /api/analyses/{analysis_id} | Снимок: исходный result с документами, режим, ограничения и доступность чата |
| GET /api/analyses/{analysis_id}/chat | История сообщений, версия диалога, активный turn и доступность |
| POST /api/analyses/{analysis_id}/chat/messages | Принять вопрос и запустить ограниченный ход агента; HTTP 202 |
| GET /api/analyses/{analysis_id}/chat/turns/{turn_id} | Статус и итог ответа; HTTP 200, включая терминальную ошибку |
| GET /api/analyses/{analysis_id}/source?fragment_id=...&offset=0 | Проверенный исходный фрагмент и контекст для открытия цитаты |

Отдельный адаптер завершённого /api/research возвращает стабильный analysis_id в публичном результате, не изменяя исходные findings и журнал исследования. ID определяется содержимым снимка; снимок хранит research_id. Универсального POST для импорта присланного браузером анализа в MVP нет.

## Завершённый анализ

Добавление к прежнему ответу /api/analyze:

~~~json
{
  "analysis_id": "a-<uuid>",
  "chat": {
    "state": "available",
    "reason_code": null,
    "review_context": "server_snapshot_only"
  }
}
~~~

chat.state: available, requires_model или unavailable. available означает, что заданы необходимые настройки модели; поддержка инструментов/доступность провайдера проверяются реальным вызовом, успех заранее не обещается. При requires_model клиент может передать config в запросе сообщения. Сохранение снимка не вызывает embeddings.

При needs_review или статическом демо чат недоступен. При ошибке сохранения вернуть прежний результат плюс analysis_id: null, chat.state: unavailable, reason_code: snapshot_failed и предупреждение. GET снимка возвращает schema_version, analysis_id, created_at, source_kind (analyze/research), analysis_mode (ai/rules/fallback/agent), synthetic, limitations, result и chat. Сырые служебные промпты, секреты и внутренний журнал инструментов в этот публичный ответ не входят.

## Отправка вопроса

~~~json
{
  "client_message_id": "uuid-generated-by-client",
  "expected_version": 0,
  "text": "Почему эта функция отмечена как потерянная?",
  "finding_ids": ["f2"],
  "config": {
    "model": "configured-model"
  }
}
~~~

text: непустая строка до 4000 символов. finding_ids: необязательный массив до пяти существующих находок текущего снимка; это контекст выбора пользователя, не доказательство. config необязателен; разрешённые поля key/base/model/reasoning_effort/embedding_model/embedding_dimensions проверяются сервером. Без config используется окружение сервера. Ключи из поля config не сохраняются. config.model либо OPENAI_MODEL обязателен; локальная модель на localhost может работать без ключа.

Ответ HTTP 202:

~~~json
{
  "schema_version": 1,
  "analysis_id": "a-<uuid>",
  "turn_id": "t-<uuid>",
  "client_message_id": "uuid-generated-by-client",
  "status": "queued",
  "conversation_version": 1
}
~~~

Версия диалога увеличивается при принятии пользовательского сообщения и при сохранении финального ответа/терминальной ошибки. GET истории является источником актуальной версии. Только один ход на анализ активен. Повтор того же client_message_id, текста, finding_ids и переданных несекретных настроек модели возвращает существующий turn (202 для активного, 200 для терминального), без новой модельной работы. Изменение этих полей под тем же ID даёт 409. Ключ не сохраняется и не входит в отпечаток повтора; передача нового ключа не перезапускает старый ход. Проверка повтора выполняется до проверки expected_version. Новая попытка после ошибки имеет новый client_message_id.

## Ход ответа и polling

Статусы: queued → preparing → answering → completed. Альтернативные терминальные статусы: failed, interrupted, budget_exhausted. Этап preparing включает подготовку/проверку индекса, answering — вызовы модели и инструментов. Нельзя публиковать выдуманные проценты.

GET turn возвращает analysis_id, turn_id, client_message_id, status, conversation_version, started_at, elapsed_ms, assistant_message либо null, error либо null. После completed у сообщения outcome: answered, insufficient_data или needs_clarification. Последние два — корректные ограниченные ответы, а не транспортный сбой.

При terminal error клиент получает код, понятный текст и retryable. История сохраняет вопрос и ошибку; они не подменяются успешным ответом. После рестарта queued/preparing/answering становятся interrupted и не перезапускаются автоматически. MVP использует polling раз в 1–2 секунды с остановкой при терминальном состоянии; SSE и токеновый стриминг — возможное расширение.

## Сообщение и источники

Пример формы ответа; текст и ID ниже иллюстрируют только контракт:

~~~json
{
  "id": "m-<uuid>",
  "role": "assistant",
  "turn_id": "t-<uuid>",
  "outcome": "insufficient_data",
  "blocks": [
    {
      "kind": "claim",
      "text": "В исходном анализе функция отмечена как кандидат потери.",
      "citation_ids": [],
      "finding_ids": ["f2"],
      "basis": "analysis"
    },
    {
      "kind": "claim",
      "text": "До изменений обязанность закреплена за отделом.",
      "citation_ids": ["c1"],
      "finding_ids": [],
      "basis": "source"
    },
    {
      "kind": "limitation",
      "text": "Без проверки оставшихся документов после изменений установить потерю нельзя.",
      "citation_ids": [],
      "finding_ids": [],
      "basis": "analysis"
    }
  ],
  "citations": [
    {
      "id": "c1",
      "fragment_id": "before:p12",
      "document_id": "before",
      "document_name": "Положение до.docx",
      "sha256": "<64 hex>",
      "side": "before",
      "section": "2.4",
      "page": null,
      "printed_page": null,
      "quote": "<дословная подстрока источника>",
      "source_locator": {
        "side": "before",
        "original_fragment_id": "p12"
      }
    }
  ],
  "analysis_relation": "not_determined",
  "limitations": ["Часть новой редакции ещё не проверена."],
  "human_review": "unreviewed"
}
~~~

blocks.kind: claim, explanation, limitation или question. basis: source, analysis, user или conversation — откуда взято утверждение. Фактические утверждения о документах требуют basis=source и проверенных citation_ids. Отсылка к старому выводу имеет basis=analysis и finding_ids, но не означает, что этот вывод верен. Метаданные цитаты формирует сервер из источника; модель передаёт только известный fragment_id и точную quote.

analysis_relation: supports, challenges либо not_determined. challenges требует объяснения и источников; исходная находка не изменяется. Для needs_clarification блок question содержит уточняющий вопрос. Для выводов о потере ограничения дополнительно содержат область проверенного after; ни пустой поиск, ни весь прочитанный предоставленный комплект не доказывают полноту документов организации.

DOCX не получает выдуманную страницу: page/printed_page остаются null. Для PDF page — физическая страница с 1; печатный номер отдельный, если известен. source_locator помогает фронтенду сопоставить ссылку с прежними панелями; открытие через GET source работает и после перезапуска.

Рекомендации/интерпретации оформляются как explanation с опорными ссылками и явно отделяются от фактов. Успешная валидация цитат не считается проверкой логической достаточности; human_review всегда unreviewed, пока нет отдельного подтверждения аналитика.

GET истории возвращает schema_version, analysis_id, conversation_version, messages, active_turn и chat. Пользовательские сообщения содержат id, role, text, finding_ids, client_message_id, created_at. Сообщения ассистента — структуру выше плюс created_at. Внутренние tool-сообщения и полный журнал провайдера не отдаются как видимая переписка.

## Ошибки

Все ошибки новых методов имеют форму error: {code, message, retryable}; при необходимости добавляются active_turn_id и conversation_version. Формат ошибок старого /api/analyze не ломается.

| HTTP | code | Смысл |
|---|---|---|
| 400 | invalid_request | Пустой/слишком длинный вопрос, неверная схема или ID находки |
| 403 | invalid_origin | Не разрешён Host/Origin |
| 404 | analysis_not_found / turn_not_found / source_not_found | Нет объекта в текущем анализе |
| 409 | turn_in_progress / version_conflict / idempotency_conflict | Другая работа, устаревшая история или изменённый повтор |
| 422 | model_required / chat_unavailable | Нет модели или готового снимка |
| 429 | capacity_exceeded | Достигнут лимит фоновых работ; вопрос не принят |
| 500 | storage_error | Не удалось сохранить состояние; нет успешного подтверждения приёма |
| 503 | capacity_exceeded | Сервер останавливается и не смог запустить принятую работу; попытка отмечается interrupted |

Сбои после HTTP 202 отражаются в error терминального turn: provider_error, index_error, invalid_evidence, storage_error, internal_error, interrupted либо budget_exhausted. Фронтенд не должен трактовать HTTP 200 polling как успешный ответ модели.

## Что нужно фронтенду

Сохранить analysis_id отдельно для каждого результата; статическое демо не использует реальный ID. Получить историю при открытии блока; отправлять expected_version и уникальный client_message_id; блокировать повторный новый вопрос во время активного ответа, но поддержать безопасный повтор сетевого запроса. Показывать статус и терминальные ошибки, открывать источники по каноническому ID и не смешивать локальные оценки аналитика с серверным снимком.

Расположение «анализ сверху, чат ниже при прокрутке» не требует нового серверного маршрута страницы. Бэкенд предоставляет данные; HTML/CSS/JS делает другой участник.

## Проверки и запуск

Запуск: python server.py --port 8765. Проверка чата: python -m unittest discover -s tests -p "test_chat*.py" -v. Все тесты используют существующие зависимости; tests/test_chat_http.py содержит полный HTTP-сценарий с настоящим циклом агента и scripted provider без внешних запросов.

Чат использует существующий llm.agent_turn и native tools. Для поиска нужен совместимый embeddings endpoint; индекс создаётся лениво, когда агент выбирает search. Простое чтение источника не строит индекс. Совместимый исследовательский кеш копируется в отдельный кеш чата, исходное исследование не меняется.

Серверный лимит — два активных ответа и один ответ на анализ, до 100 вопросов на анализ. На ход выделены 6 вызовов модели, 10 инструментов и 60 секунд вместе с поиском. При рестарте незавершённый ответ становится interrupted; автоматического повторного платного запроса нет. Один процесс API должен владеть своим каталогом output/analyses.

GET source дополнительно принимает offset для постраничного контекста и возвращает fragment, document, context; context.next_offset указывает непрочитанное продолжение. finish_answer — внутренний инструмент: claims_absence=true требует полного чтения предоставленного after и оговорок; это поле также присутствует в assistant_message.

Снимки и диалоги сохраняются только локально в output/analyses и не раздаются как статические файлы. Статическое C010 demo не получает реальный analysis_id. Внешний frontend подключается через same-origin proxy, существующие Host/Origin ограничения сохраняются.

Интеграционная сборка 2026-09-23 объединяет интерфейс и API на одном сервере. Публикация в main не меняет контракт чата. Лимиты загрузки legacy DOCX: 100 МБ на файл и 200 МБ на пакет; research сохраняет 10 МБ на файл и 40 МБ на комплект.
