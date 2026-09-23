# Передача внешнему ревьюеру

## Что проверять

Прототип по официальному кейсу HackAlem «Анализ организационной структуры и функционала». Основной экран: http://127.0.0.1:8765/ . Приоритет — анализ загружаемых документов. Практикум вынесен отдельно и не выдаётся за выполнение требований аналитического агента.

## Проверенные результаты

- 27 автоматических проверок прошли: чтение DOCX и таблиц, адресация пунктов, удалённые исправления, повреждённые файлы, размеры, сопоставление, существование ссылок модели, неполные/пустые ответы, HTTP-загрузка, резервный режим, ограничения доступа к файлам сервера и ключу.
- На реальных редакциях 8/9 браузерный сценарий подтвердил появление ДИТААД и ДОА в результатах, открытие пункта 3.4 с дословным текстом, изменение статуса аналитиком и скачивание заключения.
- На отдельном синтетическом DOCX-комплекте HTTP-проверка нашла добавленное подразделение, возможную потерю формулировки и дублирование. Ответы не привязаны к именам файлов редакций 8/9.
- Интерфейс проверен на 1440×1000 и 390×844; мобильное переполнение исправлено, ошибок JavaScript нет.
- Дополнительный практикум: ошибка → объяснение → повтор → ещё два задания; итог 2/3 с первой попытки, 1/3 после объяснения, 4 попытки. Счётчики получены из действий.
- Три замечания независимого ревью исправлены: наследование ключа только для настроенного адреса; атомарная загрузка пары примеров; явная оценка даже при согласии с исходным статусом.

## Двухминутный сценарий

1. Открыть редакции 8 и 9, нажать сравнение. Показать текущий режим обработки. Без подключённой модели это правила, не AI.
2. Отфильтровать подразделения. Открыть фрагмент ДИТААД/ДОА в пункте 3.4. Проверить название документа, текст и соседние абзацы.
3. Показать кандидаты потерь/дублирования и их ограничения. Отсутствие совпадения не доказывает потерю.
4. Дать оценку одному выводу. Скачать заключение и проверить соответствие статуса и источников.
5. Загрузить другие DOCX и убедиться, что результат вычисляется заново.

## Что ещё не доказано

Живой вызов API ещё не выполнен: пользователь выбрал OpenAI API, начальная модель — gpt-4.1-mini, ключ предстоит ввести в интерфейсе. Успех имитированных API-ответов подтверждает контракт и обработку ошибок, а не качество семантического анализа. Без этого оценка готовности к контрольному комплекту жюри остаётся Yellow.

PDF/Excel не реализованы. Полнота обнаружения реорганизации, потери функций, дублирования и конфликта интересов не гарантируется. Правила не устанавливают реорганизацию по смыслу; конфликт интересов поручен модели. Ссылки проверяются на существование, но не автоматически на логическое следование. Возможны дубли кандидатов модели и правил.

## Следующий обязательный шаг

Подключить выбранного провайдера и выполнить живой анализ редакций 8/9. Затем проверить отдельный контрольный комплект: для каждой ожидаемой находки зафиксировать найдено/пропущено, корректность источника, ложные срабатывания и время. Корректировать промпт по ошибкам этого прогона, не по одному удачному примеру.

Приоритет дальнейшей проверки — живой AI-прогон и контрольный комплект.

## Интерфейс проверки источников

Реализовано рабочее место с двумя независимыми панелями, списком замечаний, фильтрами и инспектором решения. Контракт `/api/analyze`, парсер и ML-модуль не менялись. Выбор документа в панели влияет только на просмотр. Поддерживаются два загруженных DOCX, не библиотека из четырёх документов «орг/функции × до/после».

Комментарий хранится в `finding.note` только на клиенте и включается в отчёт вместе с оценкой. Ссылки остаются исходными `before_ids` / `after_ids`. При отсутствии ссылки совпавший номер раздела служит лишь контекстом и не подсвечивается как доказательство. Анимации отключаются при prefers-reduced-motion.

27 Python-тестов пройдены. Через браузер проверены реальные DOCX, панели, фильтры, диалог цитаты, решение и комментарий, экспорт Markdown и ширина 390 px. Live AI по-прежнему не проверен.

## Корпоративный фронтенд и локализация

Новый frontend на том же vanilla JS/Python стеке: логотип Казахтелекома, light/dark/system, ru/kk/en, боковая навигация, четыре вкладки результатов, drawer источников, оценки и Markdown. Изменение backend ограничено явным списком публичных frontend-ресурсов в server.py; /api/analyze, парсер и модельный контракт сохранены.

Проверено: 29 Python-тестов, словари/настройки/контраст через scripts/check-frontend.cjs; браузерный реальный цикл и ошибки, fallback, 5 ширин в 2 темах, сохранение состояния при переключении языка. Обновлён scripts/check-ui.cjs; отдельно через CLI не запускался.

Оставшиеся ограничения интеграции: одна пара DOCX, нет PDF/Excel и комплектов, нет API-прогресса, нет структурированных владельцев функций, язык модельного ответа задаётся сервером. Клиент не выдумывает эти данные. Живой успешный AI-вызов и качество семантического анализа по-прежнему требуют отдельной проверки.


## AYQYN packet workspace — 2026-09-23

- Identity: AYQYN by freax; blue/cyan/navy/white hero with original CSS glass-document composition, comparison preview and four-step timeline. Sources studied: KazPunct, freax_ds, freaxlab; see docs/AYQYN_DESIGN.md. No framework/runtime dependency added. Kazakhtelecom SVG unchanged.
- Unified 2–20 DOCX upload, 10 MB/file and 20 MB/packet. Automatic explicit filename labels or two versions/years of the same filename family. Optional model classification uses bounded front matter, validates document ID and exact supporting quote, never overrides explicit assignments. Unknowns return a review manifest before analysis. Manual side overrides supported.
- Existing endpoint supports both legacy pair and new documents array. All documents are aggregated into before/after collections for cross-document analysis. Every paragraph retains document_id/document_name/original_id and globally unique dN:pM. Existing limits apply per side; no silent text truncation for analysis.
- Individual documents selectable in either evidence panel; original download and report source filenames map to the selected file. Report includes per-file hashes. Completed backend milestones are shown in an expandable AgentTrace; no fabricated progress stages.
- Eight fictional example DOCX are marked in filenames and first paragraphs; generated by scripts/generate-demo-packet.py. Real original editions 8/9 are retained. Example results are computed, not canned.
- Fixed concrete rule defect found with the packet: verbal sentences containing ведет/формирует/направляет/согласовывает no longer become department names. Existing rule and model limitations remain.
- Validation: 39 Python tests passed; dictionary/preferences/contrast check: 240 keys × 3 languages; JS syntax and diff whitespace checks passed. Browser: eight-document rules analysis (6 candidates), unknown versions -> manual clarification -> successful retry, independent file selectors, full-source context, note/review persistence, report generation, three locales, both themes and responsive widths. Model classifications and provider responses are mocked in tests; live paid/model quality has not been verified.
- Browser CLI script updated to the packet flow, syntax checked only; UI run used Codex browser tools. Screenshots are external task outputs, not repository assets.
