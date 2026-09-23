const entries = {
brand:['Distingt','Distingt','Distingt'], product:['Анализ структуры и функций','Құрылым мен функцияларды талдау','Structure & responsibility analysis'], workspace:['Рабочее пространство','Жұмыс кеңістігі','Workspace'], newAnalysis:['Новый анализ','Жаңа талдау','New analysis'], results:['Результаты','Нәтижелер','Results'], report:['Заключение','Қорытынды','Conclusion'], settings:['Подключение модели','Модельді қосу','Model connection'], localWorkspace:['Локальное рабочее место','Жергілікті жұмыс орны','Local workspace'], localHint:['Документы и оценки хранятся только в текущем сеансе.','Құжаттар мен бағалар тек ағымдағы сеанста сақталады.','Documents and reviews stay in this session only.'], navLabel:['Основная навигация','Негізгі навигация','Main navigation'], menu:['Открыть навигацию','Навигацияны ашу','Open navigation'], closeNav:['Закрыть навигацию','Навигацияны жабу','Close navigation'], language:['Язык интерфейса','Интерфейс тілі','Interface language'], theme:['Оформление','Безендіру','Appearance'], system:['Системная','Жүйелік','System'], light:['Светлая','Ашық','Light'], dark:['Тёмная','Қараңғы','Dark'], track:['ТРЕК КАЗАХТЕЛЕКОМА','ҚАЗАҚТЕЛЕКОМ ТРЕГІ','KAZAKHTELECOM TRACK'], title:['Анализ организационных изменений','Ұйымдық өзгерістерді талдау','Review organizational changes'], intro:['Сопоставьте структуру и обязанности до и после реорганизации. Проверьте каждый вывод по документам.','Қайта ұйымдастыруға дейінгі және кейінгі құрылым мен міндеттерді салыстырыңыз. Әр тұжырымды құжаттармен тексеріңіз.','Compare structures and responsibilities before and after reorganization. Verify every finding against its source.'], evidenceFirst:['От изменения — к источнику','Өзгерістен — дереккөзге','Every finding, connected to its source'], evidenceHint:['Подразделения, функции и потенциальные риски в одном рабочем пространстве.','Бөлімшелер, функциялар және ықтимал тәуекелдер бір жұмыс кеңістігінде.','Departments, functions and potential risks in one workspace.'], uploadStep:['Загрузите документы','Құжаттарды жүктеңіз','Add documents'], compareStep:['Сопоставьте изменения','Өзгерістерді салыстырыңыз','Compare changes'], reviewStep:['Проверьте заключение','Қорытындыны тексеріңіз','Review the conclusion'], documents:['Документы','Құжаттар','Documents'], before:['До реорганизации','Қайта ұйымдастыруға дейін','Before reorganization'], after:['После реорганизации','Қайта ұйымдастырудан кейін','After reorganization'], beforeShort:['До','Дейін','Before'], afterShort:['После','Кейін','After'], version:['Редакция','Редакция','Version'], originalVersion:['Исходная редакция','Бастапқы редакция','Original version'], newVersion:['Новая редакция','Жаңа редакция','Updated version'], dropTitle:['Перетащите документ сюда','Құжатты осында сүйреп әкеліңіз','Drop a document here'], orSelect:['или выберите файл','немесе файлды таңдаңыз','or choose a file'], fileLimit:['Один DOCX · до 10 МБ','Бір DOCX · 10 МБ дейін','One DOCX · up to 10 MB'], backendLimit:['Текущий анализатор принимает по одному DOCX с каждой стороны. Комплекты из нескольких файлов, PDF и Excel пока не поддерживаются.','Ағымдағы талдағыш әр тараптан бір DOCX қабылдайды. Бірнеше файлдан тұратын жинақтар, PDF және Excel әзірге қолдау көрсетілмейді.','The current analyzer accepts one DOCX per side. Multiple-file sets, PDF and Excel are not supported yet.'], ready:['Готов к анализу','Талдауға дайын','Ready for analysis'], removeFile:['Удалить файл {name}','{name} файлын жою','Remove {name}'], replaceFile:['Заменить документ','Құжатты ауыстыру','Replace document'], start:['Начать анализ','Талдауды бастау','Start analysis'], retry:['Повторить анализ','Талдауды қайталау','Retry analysis'], example:['Загрузить пример: редакции 8 и 9','Үлгіні жүктеу: 8 және 9 редакциялар','Load example: versions 8 and 9'], exampleLoaded:['Загружены реальные документы. Нажмите «Начать анализ».','Нақты құжаттар жүктелді. «Талдауды бастау» батырмасын басыңыз.','Real documents loaded. Select Start analysis.'], needFiles:['Добавьте документ «до» и документ «после», чтобы начать.','Бастау үшін «дейін» және «кейін» құжаттарын қосыңыз.','Add a before document and an after document to begin.'], aiToggle:['Использовать ИИ','ЖИ пайдалану','Use AI'], rulesHint:['Без ИИ: локальный поиск кандидатов по текстовым правилам.','ЖИ жоқ: мәтіндік ережелер бойынша жергілікті іздеу.','Without AI: local candidate search using text rules.'], aiHint:['Тексты будут отправлены модели {model} через {base}.','Мәтіндер {base} арқылы {model} моделіне жіберіледі.','Texts will be sent to {model} via {base}.'], aiAdvice:['Для поиска смысловых изменений подключите модель.','Мағыналық өзгерістерді іздеу үшін модельді қосыңыз.','Connect a model to identify semantic changes.'], progressTitle:['Анализ выполняется','Талдау орындалуда','Analysis in progress'], reading:['Читаем выбранные файлы…','Таңдалған файлдар оқылуда…','Reading selected files…'], processing:['Сервер обрабатывает документы и сопоставляет тексты…','Сервер құжаттарды өңдеп, мәтіндерді салыстыруда…','The server is processing documents and comparing text…'], processingAI:['Ожидаем анализ сервера и ответ модели…','Сервер талдауы мен модель жауабы күтілуде…','Waiting for server analysis and the model response…'], progressHint:['API не передаёт промежуточные этапы. При работе с ИИ ожидание может занять до двух минут.','API аралық кезеңдерді жібермейді. ЖИ пайдаланғанда күту екі минутқа дейін созылуы мүмкін.','The API does not report intermediate stages. AI analysis may take up to two minutes.'], errorTitle:['Не удалось завершить анализ','Талдауды аяқтау мүмкін болмады','Analysis could not be completed'], genericError:['Проверьте файлы и подключение, затем повторите попытку.','Файлдар мен қосылымды тексеріп, қайталап көріңіз.','Check your files and connection, then try again.'], serverUnavailable:['Сервер недоступен. Запустите локальный сервер и повторите попытку.','Сервер қолжетімсіз. Жергілікті серверді іске қосып, қайталаңыз.','Server unavailable. Start the local server and try again.'], timeout:['Время ожидания истекло. Повторите без ИИ или проверьте настройки модели.','Күту уақыты аяқталды. ЖИ-сіз қайталаңыз немесе модель параметрлерін тексеріңіз.','The request timed out. Retry without AI or check the model settings.'], fileTypeError:['Поддерживается только DOCX. PDF и Excel пока недоступны.','Тек DOCX қолдау көрсетіледі. PDF және Excel әзірге қолжетімсіз.','Only DOCX is supported. PDF and Excel are not available yet.'], fileSizeError:['Размер файла должен быть больше нуля и не превышать 10 МБ.','Файл өлшемі нөлден үлкен және 10 МБ-тан аспауы тиіс.','Files must be non-empty and no larger than 10 MB.'], fileCountError:['Можно выбрать только один DOCX с каждой стороны. Ни один файл из этого набора не добавлен.','Әр тарапқа тек бір DOCX таңдауға болады. Бұл жинақтан ешбір файл қосылмады.','Choose one DOCX per side. No files from this selection were added.'], readError:['Не удалось прочитать файл. Выберите его заново.','Файлды оқу мүмкін болмады. Оны қайта таңдаңыз.','The file could not be read. Select it again.'], exampleError:['Документы примера недоступны. Загрузите собственную пару DOCX.','Үлгі құжаттары қолжетімсіз. Өз DOCX жұбыңызды жүктеңіз.','Example documents are unavailable. Upload your own DOCX pair.'], technicalDetails:['Технические сведения сервера','Сервердің техникалық мәліметтері','Server diagnostics'], complete:['Анализ завершён','Талдау аяқталды','Analysis complete'], partial:['Частичный результат','Ішінара нәтиже','Partial result'], completedAt:['{date} · {seconds} с','{date} · {seconds} с','{date} · {seconds} s'], rulesMode:['Текстовые правила · без ИИ','Мәтіндік ережелер · ЖИ жоқ','Text rules · no AI'], aiMode:['ИИ и текстовые правила','ЖИ және мәтіндік ережелер','AI and text rules'], fallbackMode:['ИИ недоступен · результаты по правилам','ЖИ қолжетімсіз · ережелер нәтижесі','AI unavailable · rule-based results'], resultIntro:['Кандидаты изменений требуют проверки по источникам.','Өзгеріс нұсқаларын дереккөздер бойынша тексеру қажет.','Candidate changes require source verification.'], export:['Скачать заключение','Қорытындыны жүктеп алу','Download conclusion'], candidates:['Кандидаты изменений','Өзгеріс нұсқалары','Candidate changes'], departments:['Подразделения','Бөлімшелер','Departments'], functions:['Функции','Функциялар','Functions'], risks:['Риски','Тәуекелдер','Risks'], reviewed:['Проверено аналитиком','Талдаушы тексерді','Reviewed by analyst'], summaryNote:['Количество кандидатов не равно количеству нарушений.','Нұсқалар саны бұзушылықтар санына тең емес.','Candidate counts are not violation counts.'], tabLabel:['Разделы результатов','Нәтиже бөлімдері','Result sections'], search:['Поиск по изменениям и источникам','Өзгерістер мен дереккөздерден іздеу','Search changes and sources'], searchPlaceholder:['Найти подразделение или функцию…','Бөлімшені не функцияны іздеу…','Find a department or function…'], allTypes:['Все изменения','Барлық өзгерістер','All changes'], typeFilter:['Тип изменения','Өзгеріс түрі','Change type'], departmentFilter:['Подразделение','Бөлімше','Department'], allDepartments:['Все подразделения','Барлық бөлімшелер','All departments'], unassigned:['Подразделение не определено','Бөлімше анықталмаған','Department not identified'], unreviewed:['Только непроверенные','Тек тексерілмегендер','Unreviewed only'], shown:['Показано {count} из {total}','{total} ішінен {count} көрсетілді','Showing {count} of {total}'], emptyResults:['Кандидатов по этим условиям нет','Бұл шарттар бойынша нұсқалар жоқ','No matching candidates'], emptyResultsHint:['Измените фильтры. Отсутствие находок не доказывает отсутствие рисков.','Сүзгілерді өзгертіңіз. Табылымдардың болмауы тәуекелдердің жоқтығын дәлелдемейді.','Try other filters. No findings does not prove there are no risks.'], clearFilters:['Сбросить фильтры','Сүзгілерді тазарту','Clear filters'], change:['Изменение','Өзгеріс','Change'], function:['Функция / формулировка','Функция / тұжырым','Function / wording'], beforeDept:['Подразделение до','Бұрынғы бөлімше','Department before'], afterDept:['Подразделение после','Кейінгі бөлімше','Department after'], sources:['Источники','Дереккөздер','Sources'], showSources:['Показать источники','Дереккөздерді көрсету','Show sources'], evidenceTitle:['Проверка источников','Дереккөздерді тексеру','Source review'], ruleMethod:['Текстовое правило','Мәтіндік ереже','Text rule'], modelMethod:['Предложение модели','Модель ұсынысы','Model proposal'], notReviewed:['Не проверено','Тексерілмеген','Not reviewed'], reviewLabel:['Решение аналитика','Талдаушы шешімі','Analyst decision'], chooseReview:['Дать оценку','Бағалау','Give a decision'], noteLabel:['Комментарий к решению','Шешімге түсініктеме','Review note'], notePlaceholder:['Что проверено и что нужно уточнить…','Не тексерілді және нені нақтылау қажет…','What was verified and what needs clarification…'], savedSession:['Включено в заключение · до перезагрузки','Қорытындыға енгізілді · бет жаңартылғанға дейін','Included in report · until reload'], advisory:['Выводы ИИ носят рекомендательный характер и требуют проверки ответственным сотрудником.','ЖИ тұжырымдары ұсынымдық сипатта және жауапты қызметкердің тексеруін қажет етеді.','AI findings are advisory and require verification by a responsible employee.'], limitations:['Ограничения анализа','Талдау шектеулері','Analysis limitations'], limitsText:['Полнота обнаружения потерь, дублирования и конфликтов не гарантируется. Ссылка на абзац подтверждает происхождение, но не обоснованность вывода.','Функциялардың жоғалуын, қайталануын және қайшылықтарды толық анықтауға кепілдік берілмейді. Абзацқа сілтеме тұжырымның негізділігін емес, шығу тегін растайды.','Detection of losses, duplication and conflicts is not guaranteed to be complete. A paragraph reference establishes provenance, not validity.'], reportTitle:['Предварительное аналитическое заключение','Алдын ала талдамалық қорытынды','Preliminary analytical conclusion'], reportPair:['Сопоставлены документы «{before}» и «{after}».','«{before}» және «{after}» құжаттары салыстырылды.','Compared “{before}” and “{after}”.'], reportCounts:['Кандидатов: {total}. Проверено: {reviewed}. Подтверждено аналитиком: {confirmed}.','Нұсқалар: {total}. Тексерілгені: {reviewed}. Талдаушы растағаны: {confirmed}.','Candidates: {total}. Reviewed: {reviewed}. Confirmed by analyst: {confirmed}.'], questions:['Вопросы для проверки','Тексерілетін сұрақтар','Items for review'], recommendations:['Рекомендации','Ұсынымдар','Recommendations'], recommendationText:['Сверьте каждый кандидат с обеими редакциями, проверьте полномочия и исключения, зафиксируйте решение. История сохраняется в этом браузере; скачайте заключение для передачи сотруднику.','Әр нұсқаны екі редакциямен салыстырып, өкілеттіктер мен ерекшеліктерді тексеріңіз және шешімді тіркеңіз. Тарих осы браузерде сақталады; қызметкерге беру үшін қорытындыны жүктеңіз.','Check each candidate against both versions, verify responsibilities and exceptions, and record a decision. History is saved in this browser; export the conclusion to share with a reviewer.'], close:['Закрыть','Жабу','Close'], sourceLeft:['Документ и редакция слева','Сол жақ құжат пен редакция','Left document and version'], sourceRight:['Документ и редакция справа','Оң жақ құжат пен редакция','Right document and version'], leftPanel:['Левая панель','Сол жақ панель','Left panel'], rightPanel:['Правая панель','Оң жақ панель','Right panel'], swap:['Поменять панели местами','Панельдерді ауыстыру','Swap panels'], relatedOnly:['Только связанные пункты','Тек байланысты тармақтар','Related paragraphs only'], allText:['Показать полный текст','Толық мәтінді көрсету','Show full text'], noSource:['Источник не указан. Вывод с этой стороны не подтверждён; отсутствие функции не доказано.','Дереккөз көрсетілмеген. Бұл тарапта тұжырым расталмаған; функцияның жоқтығы дәлелденбеген.','No source was cited. This side does not substantiate the finding; absence of a function is not proven.'], linkedCount:['Связанных абзацев: {count}','Байланысты абзацтар: {count}','Linked paragraphs: {count}'], paragraph:['Пункт {section} · {id}','{section} тармақ · {id}','Section {section} · {id}'], noNumber:['без номера','нөмірсіз','unnumbered'], paragraphCount:['Абзацев: {count}','Абзацтар: {count}','Paragraphs: {count}'], downloadOriginal:['Скачать оригинал DOCX','DOCX түпнұсқасын жүктеу','Download original DOCX'], sourceText:['Текст документа','Құжат мәтіні','Document text'], paneWidth:['Ширина панелей источников','Дереккөз панельдерінің ені','Source panel width'], noEvidenceText:['Для проверки откройте полный текст.','Тексеру үшін толық мәтінді ашыңыз.','Open the full text to investigate.'], previous:['Предыдущее замечание','Алдыңғы ескерту','Previous finding'], next:['Следующее замечание','Келесі ескерту','Next finding'], of:['{index} из {total}','{total} ішінен {index}','{index} of {total}'], provider:['Провайдер','Провайдер','Provider'], localModel:['Локальная модель','Жергілікті модель','Local model'], compatible:['OpenAI / совместимый API','OpenAI / үйлесімді API','OpenAI / compatible API'], baseUrl:['Базовый адрес API','API негізгі мекенжайы','API base URL'], model:['Модель','Модель','Model'], modelPlaceholder:['Имя модели у провайдера','Провайдердегі модель атауы','Provider model identifier'], key:['API-ключ','API кілті','API key'], keyPlaceholder:['Только для этого сеанса','Тек осы сеанс үшін','This session only'], keyHint:['Ключ не сохраняется на диск. При ИИ-анализе текст документов отправляется выбранному провайдеру.','Кілт дискіге сақталмайды. ЖИ талдауы кезінде құжат мәтіні таңдалған провайдерге жіберіледі.','The key is not saved to disk. AI analysis sends document text to the selected provider.'], serverKey:['Ключ настроен на сервере. Пустое поле использует его только для настроенного провайдера.','Кілт серверде бапталған. Бос өріс оны тек бапталған провайдер үшін пайдаланады.','A server key is configured. An empty field uses it only for the configured provider.'], apply:['Применить','Қолдану','Apply'], sessionOnly:['Сеанс без сохранения','Сақталмайтын сеанс','Session only'], skip:['Перейти к содержимому','Мазмұнға өту','Skip to content'], dataLanguage:['Текст ответа сервера сохранён на исходном языке. Цитаты не переводятся.','Сервер жауабы бастапқы тілінде сақталды. Дәйексөздер аударылмайды.','Server-generated content remains in its original language. Source quotations are not translated.'], sameFiles:['Загружены одинаковые файлы. Внутренние пересечения всё ещё возможны.','Бірдей файлдар жүктелді. Ішкі қайталанулар болуы мүмкін.','The same file was uploaded on both sides. Internal overlaps may still exist.'], rejected:['Отброшено выводов с некорректными ссылками: {count}.','Қате сілтемелері бар тұжырымдар алынып тасталды: {count}.','Findings with invalid references rejected: {count}.'], noModelFindings:['Модель не вернула допустимых находок. Это не доказывает отсутствие рисков.','Модель жарамды табылымдар қайтармады. Бұл тәуекелдердің жоқтығын дәлелдемейді.','The model returned no valid findings. This does not prove there are no risks.'], fallbackWarning:['ИИ-анализ не завершён. Доступны только кандидаты по текстовым правилам.','ЖИ талдауы аяқталмады. Тек мәтіндік ережелер нұсқалары қолжетімді.','AI analysis did not complete. Only text-rule candidates are available.'], notice:['Обратите внимание','Назар аударыңыз','Please note'], availableAfter:['Раздел появится после анализа','Бөлім талдаудан кейін ашылады','Available after analysis'], sourceCount:['Фрагментов: {count}','Үзінділер: {count}','Excerpts: {count}'], unknownOwner:['Владелец не указан','Иесі көрсетілмеген','Owner not specified'], unitFilterHint:['Фильтр использует явные названия из находок по подразделениям и совпадения в источниках; это не назначение владельца функции.','Сүзгі бөлімше табылымдарындағы нақты атауларды және дереккөз сәйкестіктерін пайдаланады; бұл функция иесін тағайындау емес.','This filter uses explicit department names and source matches; it does not assign ownership of a function.'], fileReadyNote:['Файл выбран локально; на сервер отправится при запуске анализа.','Файл жергілікті таңдалды; талдау басталғанда серверге жіберіледі.','Selected locally; sent to the server when analysis starts.'], exportDone:['Файл заключения подготовлен для скачивания.','Қорытынды файлы жүктеп алуға дайын.','Conclusion file prepared for download.'], modelSettingsSaved:['Настройки модели применены.','Модель параметрлері қолданылды.','Model settings applied.'], loadingExample:['Загружаем документы примера…','Үлгі құжаттары жүктелуде…','Loading example documents…'], workflow:['Как проходит проверка','Тексеру қалай өтеді','Review workflow'], unsupported:['Ограничения текущей версии','Ағымдағы нұсқа шектеулері','Current version limits'], noFindings:['Анализ завершён без кандидатов. Это не подтверждает отсутствие рисков.','Талдау нұсқаларсыз аяқталды. Бұл тәуекелдердің жоқтығын растамайды.','Analysis completed with no candidates. This does not establish that there are no risks.'], all:['Все','Барлығы','All'], status:['Статус','Мәртебе','Status'], note:['Комментарий аналитика','Талдаушы түсініктемесі','Analyst note'], method:['Метод','Әдіс','Method'], warning:['Ограничение','Шектеу','Limitation'], reportLanguage:['Язык интерфейса и заголовков отчёта меняется; язык ответа модели задан сервером.','Интерфейс пен есеп тақырыптарының тілі өзгереді; модель жауабының тілін сервер белгілейді.','Interface and report headings are localized; the server controls the model response language.'], candidate:['Кандидат','Нұсқа','Candidate'], noReport:['Сначала выполните анализ документов.','Алдымен құжаттарды талдаңыз.','Analyze documents first.']
};
entries.settingsInvalid=['Укажите адрес HTTP(S) и имя модели.','HTTP(S) мекенжайы мен модель атауын көрсетіңіз.','Enter an HTTP(S) address and a model name.'];
Object.assign(entries,{
example:['Загрузить пример: 8 документов','Үлгіні жүктеу: 8 құжат','Load example: 8 documents'],
exampleLoaded:['Загружен учебный пакет: 8 вымышленных документов. Нажмите «Начать анализ» для реальной обработки.','Оқу пакеті жүктелді: 8 ойдан шығарылған құжат. Нақты өңдеу үшін талдауды бастаңыз.','Example packet loaded: 8 fictional documents. Start analysis to process them.'],
brand:['Distingt','Distingt','Distingt'],
otherDocumentSource:['Цитаты этого вывода находятся в другом документе. Выберите его в списке.','Бұл тұжырымның дәйексөздері басқа құжатта. Оны тізімнен таңдаңыз.','This finding cites another document. Select it from the list.'],
heroKicker:['ЯСНОСТЬ В ИЗМЕНЕНИЯХ','ӨЗГЕРІСТЕРДІҢ АЙҚЫНДЫҒЫ','CLARITY THROUGH CHANGE'],
heroTitle1:['Изменения в структуре.','Құрылым өзгереді.','Structures change.'],
heroTitle2:['Ясность в каждой функции.','Әр функция айқын.','Every function, clear.'],
heroDescription:['Сравните документы до и после реорганизации. Найдите потерянные функции, дублирование и пересечения ответственности.','Қайта ұйымдастыруға дейінгі және кейінгі құжаттарды салыстырыңыз. Жоғалған функцияларды, қайталануды және жауапкершілік қиылысын табыңыз.','Compare documents before and after reorganization. Find lost functions, duplication and overlapping responsibilities.'],
viewExample:['Посмотреть пример','Үлгіні көру','View example'],
heroFootnote:['Каждый вывод — с проверяемым источником','Әр тұжырымның тексерілетін дереккөзі бар','Every finding linked to a verifiable source'],
heroSignature:['От документов к обоснованному решению','Құжаттан негізді шешімге','From documents to informed decisions'],
analysisExample:['Пример анализа','Талдау үлгісі','Example analysis'],
mockOrg:['Организационная структура','Ұйымдық құрылым','Organizational structure'],
mockFunctional:['Функции и ответственность','Функциялар мен жауапкершілік','Functions & responsibilities'],
mockFunction:['Подготовка сводного отчёта','Жиынтық есепті дайындау','Consolidated reporting'],
mockDeptA:['Отдел планирования','Жоспарлау бөлімі','Planning department'],
mockDeptB:['Отдел аналитики','Талдау бөлімі','Analytics department'],
mockTransfer:['Функция передана','Функция берілді','Function transferred'],
mockCitation:['Источник: пункт 5.3','Дереккөз: 5.3 тармақ','Source: section 5.3'],
previewTitle:['Изменение видно. Основание — рядом.','Өзгеріс көрінеді. Негізі — қасында.','See the change. Inspect the evidence.'],
previewBefore:['Отдел планирования готовит сводный отчёт.','Жоспарлау бөлімі жиынтық есеп дайындайды.','The Planning department prepares the consolidated report.'],
previewAfter:['Отдел аналитики готовит сводный отчёт.','Талдау бөлімі жиынтық есеп дайындайды.','The Analytics department prepares the consolidated report.'],
previewExplanation:['Условный пример: формулировка функции сохранена, указан другой исполнитель. В рабочем анализе здесь открываются точные цитаты из загруженных документов; вывод требует проверки аналитиком.','Шартты мысал: функция тұжырымы сақталған, орындаушы өзгерген. Нақты талдауда жүктелген құжаттардың дәл дәйексөздері ашылады; тұжырымды талдаушы тексеруі керек.','Illustrative example: the function wording is retained with a different owner. In a real analysis, exact uploaded source passages open here; an analyst must verify the finding.'],
timelineUpload:['Загрузите документы','Құжаттарды жүктеңіз','Upload documents'],
timelineUploadHint:['Все положения и редакции — одним пакетом.','Барлық ережелер мен нұсқалар — бір пакетте.','All policies and versions in one packet.'],
timelineMatch:['Сопоставьте версии','Нұсқаларды салыстырыңыз','Match versions'],
timelineMatchHint:['Автоопределение редакций. Уточнение спорных случаев.','Нұсқаларды автоматты анықтау. Күмәнді жағдайларды нақтылау.','Automatic version detection. Clarify ambiguous cases.'],
timelineReview:['Проверьте источники','Дереккөздерді тексеріңіз','Review sources'],
timelineReviewHint:['Два документа рядом, связанные пункты выделены.','Екі құжат қатар, байланысты тармақтар белгіленген.','Two documents side by side, linked passages highlighted.'],
timelineReport:['Получите заключение','Қорытынды алыңыз','Export the conclusion'],
timelineReportHint:['Ваши решения, комментарии и основания.','Шешімдеріңіз, түсініктемелеріңіз және негіздері.','Your decisions, notes and supporting evidence.'],
packetTitle:['Весь контекст. Один пакет.','Толық контекст. Бір пакет.','The full context. One packet.'],
packetIntro:['Добавьте организационные и функциональные документы вместе — обе редакции. Редакции определяются по названиям и номерам версий; с включённым ИИ — также по содержимому. Неопределённые случаи появятся для уточнения.','Ұйымдық және функционалдық құжаттардың екі нұсқасын бірге қосыңыз. Нұсқалар атаулар мен нөмірлерден, ЖИ қосылса — мазмұннан да анықталады. Анықталмаған жағдайлар нақтылауға ұсынылады.','Add organizational and functional documents together, including both versions. Versions are detected from names and numbers, and from content when AI is enabled. Unresolved cases are flagged for clarification.'],
packetDrop:['Перетащите все документы сюда','Барлық құжаттарды осында сүйреңіз','Drop all your documents here'],
packetLimits:['2–20 DOCX · до 10 МБ каждый · до 20 МБ вместе','2–20 DOCX · әрқайсысы 10 МБ дейін · барлығы 20 МБ дейін','2–20 DOCX · up to 10 MB each · 20 MB total'],
packetCount:['Файлов в пакете: {count}','Пакеттегі файлдар: {count}','Files in packet: {count}'],
packetReady:['Готово к обработке: {count} файлов. Редакции определятся на сервере.','Өңдеуге дайын: {count} файл. Нұсқалар серверде анықталады.','Ready to process: {count} files. Versions will be identified on the server.'],
needFiles:['Добавьте как минимум два документа.','Кемінде екі құжат қосыңыз.','Add at least two documents.'],
packetCountError:['В одном пакете может быть до 20 файлов.','Бір пакетте 20 файлға дейін болады.','A packet can contain up to 20 files.'],
packetSizeError:['Общий размер пакета превышает 20 МБ.','Пакеттің жалпы көлемі 20 МБ-тан асты.','The packet exceeds 20 MB in total.'],
automatic:['Автоматически','Автоматты','Automatic'],
awaitingClassification:['Редакция определится при анализе','Нұсқа талдау кезінде анықталады','Version identified during analysis'],
versionFor:['Редакция: {name}','Нұсқа: {name}','Version: {name}'],
classificationReview:['Нужно уточнение: назначьте «До» или «После» файлам с неопределённой редакцией. В пакете должны быть обе стороны. Затем запустите анализ ещё раз.','Нақтылау қажет: нұсқасы анықталмаған файлдарға «Дейін» немесе «Кейін» белгілеңіз. Пакетте екі кезең де болуы керек. Содан кейін талдауды қайта бастаңыз.','Clarification needed: assign Before or After to unresolved files. Both sides must be present. Then run the analysis again.'],
classificationModelError:['Модель не смогла определить все редакции. Уточните их в списке файлов.','Модель барлық нұсқаларды анықтай алмады. Оларды файлдар тізімінде нақтылаңыз.','The model could not identify all versions. Clarify them in the file list.'],
class_model:['Предложено ИИ · проверьте основание','ЖИ ұсынды · негізін тексеріңіз','AI assignment · review the evidence'],
orSelect:['или выберите файлы','немесе файлдарды таңдаңыз','or select files'],
class_manual:['Редакция выбрана вами','Нұсқаны сіз таңдадыңыз','Version selected by you'],
class_filename:['Определено по названию','Атауынан анықталды','Detected from filename'],
class_version:['Определено по номеру версии / году','Нұсқа нөмірінен / жылдан анықталды','Detected from version number / year'],
class_unresolved:['Редакция не определена','Нұсқа анықталмады','Version unresolved'],
backendLimit:['Поддерживаются DOCX. PDF, сканы и Excel пока не разбираются. Лимит анализа: 1 500 абзацев и 250 000 символов на каждую сторону; превышение не обрезается молча.','DOCX қолданылады. PDF, скан және Excel әзірге өңделмейді. Әр кезеңге 1 500 абзац және 250 000 таңба шегі бар; артық мәтін үнсіз қиылмайды.','DOCX supported. PDF, scans and Excel are not parsed yet. Analysis limit: 1,500 paragraphs and 250,000 characters per side; excess content is never silently truncated.'],
agentTrace:['Ход анализа и состав пакета','Талдау барысы және пакет құрамы','Analysis trace & packet manifest'],
completedRun:['ЗАВЕРШЁННЫЙ ЗАПУСК','АЯҚТАЛҒАН ІСКЕ ҚОСУ','COMPLETED RUN'],
traceExtract:['Извлечён текст документов: {count}','Құжат мәтіндері алынды: {count}','Documents extracted: {count}'],
traceClassify:['Определены редакции: {count}','Нұсқалар анықталды: {count}','Versions assigned: {count}'],
traceRules:['Кандидатов по текстовым правилам: {count}','Мәтіндік ереже нұсқалары: {count}','Text-rule candidates: {count}'],
traceModel:['Приняты предложения модели: {count}','Модель ұсыныстары қабылданды: {count}','Model proposals accepted: {count}'],
traceSources:['Ссылок на существующие абзацы: {count}','Бар абзацтарға сілтемелер: {count}','References to existing paragraphs: {count}']
});
Object.assign(entries,{
 "home": [
  "Главная",
  "Басты бет",
  "Home"
 ],
 "guide": [
  "Как работать",
  "Нұсқаулық",
  "Guide"
 ],
 "about": [
  "О проекте",
  "Жоба туралы",
  "About"
 ],
 "dataPolicy": [
  "О данных",
  "Деректер туралы",
  "Data policy"
 ],
 "capabilities": [
  "Возможности",
  "Мүмкіндіктер",
  "Capabilities"
 ],
 "openWorkspace": [
  "Рабочая область",
  "Жұмыс кеңістігі",
  "Workspace"
 ],
 "emptyWorkspace": [
  "Здесь начнётся ваш анализ",
  "Талдауыңыз осы жерден басталады",
  "Your analysis starts here"
 ],
 "emptyWorkspaceText": [
  "Добавьте два комплекта документов или изучите учебный пример.",
  "Құжаттардың екі жинағын қосыңыз немесе оқу мысалын қараңыз.",
  "Add two document sets or explore the example."
 ],
 "viewExample": [
  "Посмотреть пример",
  "Мысалды көру",
  "View example"
 ],
 "versionContents": [
  "Структуры, положения, инструкции, приказы и приложения",
  "Құрылымдар, ережелер, нұсқаулықтар, бұйрықтар мен қосымшалар",
  "Structures, regulations, job descriptions, orders and appendices"
 ],
 "mixedDrop": [
  "Или добавьте обе версии вместе — определим автоматически",
  "Немесе екі нұсқаны бірге қосыңыз — автоматты түрде анықтаймыз",
  "Or add both versions together — assign automatically"
 ],
 "demoLabel": [
  "Учебный пример",
  "Оқу мысалы",
  "Synthetic example"
 ],
 "demoDisclosure": [
  "Синтетические документы. Это демонстрация, а не результат анализа ваших файлов. Выводы требуют проверки аналитиком.",
  "Синтетикалық құжаттар. Бұл сіздің файлдарыңызды талдау нәтижесі емес, көрсету мысалы. Қорытындыларды талдаушы тексеруі керек.",
  "Synthetic documents. This is a demonstration, not an analysis of your files. Findings require analyst review."
 ],
 "analyzeOwn": [
  "Загрузить свои документы",
  "Өз құжаттарыңызды жүктеу",
  "Upload your documents"
 ],
 "overview": [
  "Обзор",
  "Шолу",
  "Overview"
 ],
 "teamTrack": [
  "Проект команды freax для трека Казахтелекома",
  "Қазақтелеком бағытына арналған freax командасының жобасы",
  "A freax team project for the Kazakhtelecom track"
 ],
 "footerNav": [
  "Навигация в футере",
  "Төменгі навигация",
  "Footer navigation"
 ],
 "openOriginal": [
  "Открыть исходный файл",
  "Бастапқы файлды ашу",
  "Open original file"
 ],
 "editorialKicker": [
  "Анализ структуры и функций",
  "Құрылым мен функцияларды талдау",
  "Structure & responsibility analysis"
 ],
 "editorialTitle": [
  "Структура меняется.",
  "Құрылым өзгереді.",
  "Structures change."
 ],
 "editorialTitleAccent": [
  "А ответственность?",
  "Ал жауапкершілік ше?",
  "What about responsibility?"
 ],
 "editorialIntro": [
  "Сопоставьте документы до и после реорганизации. Найдите изменения функций — и проверьте каждое по первоисточнику.",
  "Қайта ұйымдастыруға дейінгі және кейінгі құжаттарды салыстырыңыз. Функция өзгерістерін тауып, әрқайсысын дереккөзден тексеріңіз.",
  "Compare documents before and after reorganization. Find changes in responsibilities, then check the original evidence."
 ],
 "previewDocument": [
  "Функции подразделений",
  "Бөлімшелердің функциялары",
  "Department responsibilities"
 ],
 "pageOne": [
  "стр. 1",
  "1-бет",
  "page 1"
 ],
 "originalQuote": [
  "Дословная цитата · исходный язык",
  "Дәл дәйексөз · түпнұсқа тілі",
  "Exact quotation · original language"
 ],
 "preliminary": [
  "Предварительный вывод",
  "Алдын ала қорытынды",
  "Preliminary finding"
 ],
 "previewTransfer": [
  "Функция сохранена. Ответственный изменился.",
  "Функция сақталған. Жауапты бөлімше өзгерген.",
  "The function remains. Its owner has changed."
 ],
 "previewTransferText": [
  "Закупочные решения перешли от отдела закупок к внутреннему аудиту. Следующий шаг — проверить совместимость полномочий.",
  "Сатып алу шешімдері сатып алу бөлімінен ішкі аудитке берілген. Келесі қадам — өкілеттіктердің үйлесімділігін тексеру.",
  "Purchasing decisions moved from Procurement to Internal Audit. Next, check whether the responsibilities are compatible."
 ],
 "reviewExample": [
  "Проверить пример",
  "Мысалды тексеру",
  "Inspect example"
 ],
 "previewDisclosure": [
  "Пример C010 из синтетического набора. Ссылки ведут к учебным документам; наличие цитаты не подтверждает вывод.",
  "Синтетикалық жинақтағы C010 мысалы. Сілтемелер оқу құжаттарына апарады; дәйексөздің болуы қорытындыны растамайды.",
  "C010 from the synthetic dataset. Links lead to training documents; a citation does not establish a conclusion."
 ],
 "studyTitle": [
  "Одна передача. Два несовместимых полномочия?",
  "Бір функция берілді. Өкілеттіктер үйлесе ме?",
  "One transfer. Two incompatible responsibilities?"
 ],
 "studyIntro": [
  "Название отдела — только начало. Важно увидеть, кто выполняет действие и кто затем проверяет его результат.",
  "Бөлім атауы — бастамасы ғана. Әрекетті кім орындайтынын және оның нәтижесін кім тексеретінін көру маңызды.",
  "The department name is only a starting point. See who performs an action and who later checks its outcome."
 ],
 "studyVerdict": [
  "Возможный конфликт интересов",
  "Ықтимал мүдделер қақтығысы",
  "Potential conflict of interest"
 ],
 "studyVerdictText": [
  "В примере одна служба выбирает поставщиков и проверяет закупки. Для решения нужны контекст и оценка сотрудника.",
  "Мысалда бір қызмет жеткізушіні таңдайды әрі сатып алуды тексереді. Шешім үшін контекст пен қызметкер бағасы қажет.",
  "In this example, one service selects vendors and audits purchases. Context and human judgment are needed."
 ],
 "studySource": [
  "Учебный пример · C010_after_functions · стр. 1, пп. 2.4–2.5",
  "Оқу мысалы · C010_after_functions · 1-бет, 2.4–2.5 тармақтар",
  "Synthetic example · C010_after_functions · page 1, clauses 2.4–2.5"
 ],
 "changesTitle": [
  "Не просто разница в тексте.",
  "Тек мәтін айырмасы емес.",
  "Beyond changed wording."
 ],
 "changesIntro": [
  "Distingt группирует предварительные выводы, чтобы вы могли проверить смысл изменений.",
  "Distingt өзгерістердің мағынасын тексеру үшін алдын ала қорытындыларды топтайды.",
  "Distingt groups preliminary findings so you can examine what changed in practice."
 ],
 "changeUnits": [
  "Создание, сохранение и преобразование подразделений — с привязкой к упоминаниям в документах.",
  "Бөлімшелердің құрылуы, сақталуы мен өзгеруі — құжаттағы деректерге сілтемемен.",
  "Created, retained and reorganized units, linked to their mentions in documents."
 ],
 "changeTransfer": [
  "Сопоставление обязанностей между версиями. Изменение названия не обязательно означает потерю функции.",
  "Нұсқалар арасындағы міндеттерді салыстыру. Атаудың өзгеруі функцияның жоғалғанын білдірмейді.",
  "Compare duties across versions. A renamed unit does not necessarily mean a lost function."
 ],
 "changeRisks": [
  "Потенциальные потери, дублирование и конфликты. Каждый кандидат остаётся открытым до проверки.",
  "Ықтимал жоғалу, қайталану және қайшылықтар. Әр болжам тексерілгенше ашық қалады.",
  "Potential losses, duplication and conflicts. Every candidate remains open until reviewed."
 ],
 "journeyTitle": [
  "От двух комплектов — к проверяемому заключению.",
  "Екі жинақтан тексерілетін қорытындыға.",
  "From two document sets to a reviewable conclusion."
 ],
 "journeyUpload": [
  "Добавьте комплекты «До» и «После». В каждом могут быть структуры, положения, инструкции и приложения. Либо загрузите всё вместе и проверьте назначенные версии.",
  "«Дейін» және «Кейін» жинақтарын қосыңыз. Әрқайсысында құрылымдар, ережелер, нұсқаулықтар мен қосымшалар болуы мүмкін. Немесе бәрін бірге жүктеп, белгіленген нұсқаларды тексеріңіз.",
  "Add Before and After sets, each with structures, regulations, job descriptions and appendices. Or upload them together and check assigned versions."
 ],
 "journeyCompare": [
  "Запустите доступный режим. Реальные этапы и состав обработанного пакета появятся в результате.",
  "Қолжетімді режимді іске қосыңыз. Нақты кезеңдер мен өңделген жинақ құрамы нәтижеде көрсетіледі.",
  "Run the available mode. Actual processing steps and the packet manifest appear with the result."
 ],
 "journeyReview": [
  "Откройте источник рядом с выводом. Проверьте цитату и контекст, затем укажите своё решение и комментарий.",
  "Қорытындының жанынан дереккөзді ашыңыз. Дәйексөз бен контексті тексеріп, шешім мен түсініктеме қосыңыз.",
  "Open the source beside the finding. Check the quote and context, then record your decision and note."
 ],
 "journeyReport": [
  "Скачайте Markdown с выводами, источниками и вашими отметками проверки.",
  "Қорытындылар, дереккөздер және тексеру белгілері бар Markdown жүктеп алыңыз.",
  "Download Markdown with findings, sources and your review decisions."
 ],
 "boundaries": [
  "Границы анализа",
  "Талдау шектері",
  "Analysis boundaries"
 ],
 "faqTitle": [
  "Перед началом работы.",
  "Жұмысты бастамас бұрын.",
  "Before you begin."
 ],
 "faqIntro": [
  "Полнота исходных данных и проверка сотрудником важнее красивого отчёта.",
  "Бастапқы деректердің толықтығы мен қызметкердің тексеруі әдемі есептен маңыздырақ.",
  "Complete source material and human review matter more than a polished report."
 ],
 "faqFiles": [
  "Какие файлы можно загрузить?",
  "Қандай файлдарды жүктеуге болады?",
  "Which files can I upload?"
 ],
 "faqFilesAnswer": [
  "Рабочий экран принимает 2–20 DOCX, до 10 МБ каждый и 20 МБ суммарно. PDF доступен в отдельном серверном исследовательском API, но ещё не подключён к этой форме. OCR и Excel не поддерживаются.",
  "Жұмыс экраны 2–20 DOCX қабылдайды: әрқайсысы 10 МБ, барлығы 20 МБ дейін. PDF бөлек серверлік зерттеу API-де бар, бірақ бұл формаға қосылмаған. OCR және Excel қолдау таппайды.",
  "The workspace accepts 2–20 DOCX, up to 10 MB each and 20 MB total. PDF reading exists in the separate research API but is not connected to this form. OCR and Excel are unsupported."
 ],
 "faqLoss": [
  "Отсутствие совпадения означает потерю функции?",
  "Сәйкестіктің болмауы функция жоғалды деген сөз бе?",
  "Does a missing match prove a lost function?"
 ],
 "faqLossAnswer": [
  "Нет. Это повод проверить область поиска, приложения, переформулировки и правопреемство. Вывод относится к предоставленному комплекту, а не ко всей организации.",
  "Жоқ. Іздеу аясын, қосымшаларды, өзгерген тұжырымдарды және құқықтық мирасқорлықты тексеру қажет. Қорытынды бүкіл ұйымға емес, берілген жинаққа қатысты.",
  "No. Check the search scope, appendices, rewording and succession. The finding concerns the supplied packet, not the entire organization."
 ],
 "faqData": [
  "Куда отправляются документы?",
  "Құжаттар қайда жіберіледі?",
  "Where do documents go?"
 ],
 "faqDataAnswer": [
  "Файлы отправляются серверу Distingt. При включённом ИИ текст передаётся настроенному провайдеру; материалы AI-запуска сохраняются на диске сервера. Подробнее — на странице о данных.",
  "Файлдар Distingt серверіне жіберіледі. ЖИ қосылғанда мәтін бапталған провайдерге беріледі; ЖИ сеансының материалдары сервер дискісінде сақталады. Толығырақ — деректер бетінде.",
  "Files go to the Distingt server. When AI is enabled, text goes to the configured provider; AI run materials are saved on the server disk. See the data policy."
 ],
 "faqDecision": [
  "Кто принимает окончательное решение?",
  "Соңғы шешімді кім қабылдайды?",
  "Who makes the final decision?"
 ],
 "faqDecisionAnswer": [
  "Ответственный сотрудник. Система предлагает кандидатов, а не юридическое или кадровое решение. Цитата подтверждает происхождение текста, но не правильность интерпретации.",
  "Жауапты қызметкер. Жүйе құқықтық не кадрлық шешім емес, болжамдар ұсынады. Дәйексөз мәтіннің шығу тегін көрсетеді, бірақ түсіндірудің дұрыстығын растамайды.",
  "The responsible employee. The system proposes candidates, not legal or staffing decisions. A citation verifies the origin of text, not its interpretation."
 ],
 "finalTitle": [
  "Начните с документов.",
  "Құжаттардан бастаңыз.",
  "Start with the documents."
 ],
 "finalText": [
  "Две версии. Полный контекст. Решение — за вами.",
  "Екі нұсқа. Толық контекст. Шешім — сізде.",
  "Two versions. Full context. You make the decision."
 ],
 "guidePrepare": [
  "Подготовьте комплекты",
  "Жинақтарды дайындаңыз",
  "Prepare both sets"
 ],
 "guideRun": [
  "Запустите обработку",
  "Өңдеуді бастаңыз",
  "Run the analysis"
 ],
 "guideRunText": [
  "Без ИИ работают текстовые правила. С ИИ запрос идёт настроенной модели. При ошибке модели интерфейс явно показывает резервный режим. Анимация означает ожидание, а не процент готовности.",
  "ЖИ жоқ кезде мәтін ережелері жұмыс істейді. ЖИ қосылғанда сұрау бапталған модельге жіберіледі. Модель қатесі болса, интерфейс резервтік режимді көрсетеді. Анимация дайындық пайызын емес, күтуді білдіреді.",
  "Without AI, text rules run. With AI, the configured model receives the request. Model failures are explicitly labeled as fallback mode. Animation indicates waiting, not completion percentage."
 ],
 "guideExportText": [
  "Отметки и комментарии хранятся в памяти вкладки: выгрузите Markdown до обновления страницы. Ссылки на исходные пункты и пометка деморежима сохраняются в заключении.",
  "Белгілер мен түсініктемелер қойынды жадында сақталады: бетті жаңартпас бұрын Markdown жүктеңіз. Түпнұсқа тармақ сілтемелері мен демо белгісі қорытындыда сақталады.",
  "Reviews and notes live in tab memory: export Markdown before refreshing. Source references and the demo label remain in the conclusion."
 ],
 "aboutText": [
  "Distingt — рабочее место для сопоставления организационной структуры и функций до и после реорганизации. Команда freax соединяет анализ документов с проверкой по первоисточнику.",
  "Distingt — қайта ұйымдастыруға дейінгі және кейінгі құрылым мен функцияларды салыстыруға арналған жұмыс орны. freax командасы құжат талдауын түпнұсқадан тексерумен біріктіреді.",
  "Distingt is a workspace for comparing organizational structure and responsibilities before and after reorganization. The freax team connects document analysis with source review."
 ],
 "aboutLimits": [
  "Это хакатонный продукт. Качество смыслового анализа ещё требует проверки; полнота обнаружения изменений не гарантируется. Агентное исследование доступно через отдельный API и ещё не встроено в рабочий экран.",
  "Бұл — хакатон өнімі. Мағыналық талдау сапасы әлі тексеруді қажет етеді; барлық өзгерістерді табуға кепілдік жоқ. Агенттік зерттеу бөлек API арқылы қолжетімді, жұмыс экранына әлі қосылмаған.",
  "This is a hackathon product. Semantic analysis still needs validation; complete detection is not guaranteed. Agentic research is available through a separate API and is not integrated into this workspace."
 ],
 "dataUpload": [
  "Передача файлов",
  "Файлдарды жіберу",
  "File transmission"
 ],
 "dataUploadText": [
  "После запуска файлы DOCX передаются серверу Distingt через /api/analyze. В режиме правил сервер извлекает текст и сравнивает его без обращения к модели.",
  "Іске қосылғаннан кейін DOCX файлдары /api/analyze арқылы Distingt серверіне жіберіледі. Ереже режимінде сервер мәтінді шығарып, модельсіз салыстырады.",
  "On submission, DOCX files are sent to the Distingt server through /api/analyze. Rules mode extracts and compares text without calling a model."
 ],
 "dataProvider": [
  "Обращение к модели",
  "Модельге сұрау",
  "Model requests"
 ],
 "dataProviderText": [
  "Если включён ИИ, текст документов отправляется по указанному Base URL. Адрес и модель видны в настройках. Условия обработки зависят от выбранного провайдера.",
  "ЖИ қосылса, құжат мәтіні көрсетілген Base URL мекенжайына жіберіледі. Мекенжай мен модель баптауларда көрінеді. Өңдеу шарттары таңдалған провайдерге байланысты.",
  "With AI enabled, document text is sent to the configured Base URL. The address and model are visible in settings. Processing terms depend on that provider."
 ],
 "dataStorage": [
  "Сохранение на сервере",
  "Серверде сақтау",
  "Server storage"
 ],
 "dataStorageText": [
  "Материалы AI-сравнения — документы, запросы и ответы — сохраняются в output/runs. Отдельное исследовательское API сохраняет пакеты и состояние в output/research. Автоматическое удаление и управление сроками хранения в интерфейсе не реализованы.",
  "ЖИ салыстыру материалдары — құжаттар, сұраулар мен жауаптар — output/runs ішінде сақталады. Бөлек зерттеу API жинақтар мен күйді output/research ішінде сақтайды. Интерфейсте автоматты жою мен сақтау мерзімін басқару іске асырылмаған.",
  "AI comparison documents, requests and responses are saved in output/runs. The separate research API saves packets and state in output/research. Automatic deletion and retention controls are not implemented in the UI."
 ],
 "dataReview": [
  "Ваши настройки и решения",
  "Баптаулар мен шешімдеріңіз",
  "Your preferences and decisions"
 ],
 "dataReviewText": [
  "Язык и тема сохраняются в браузере. Ключ из формы, решения аналитика и комментарии остаются в памяти вкладки; после обновления они теряются. Экспорт сохраняет решения в скачиваемый Markdown.",
  "Тіл мен тақырып браузерде сақталады. Формадағы кілт, талдаушы шешімдері мен түсініктемелер қойынды жадында қалады; жаңартқанда жоғалады. Экспорт шешімдерді Markdown файлына сақтайды.",
  "Language and theme persist in your browser. A form-entered API key, analyst decisions and notes remain in tab memory and are lost on refresh. Export includes decisions in the downloaded Markdown."
 ],
 "demoPolicyText": [
  "C010 загружается из статического синтетического набора, без запуска модели. Его PDF — учебные исходники. Демо не использует выбранные вами файлы и не выдаётся за их анализ.",
  "C010 модельсіз статикалық синтетикалық жинақтан жүктеледі. PDF файлдары — оқу дереккөздері. Демо таңдаған файлдарыңызды пайдаланбайды және оларды талдау ретінде көрсетілмейді.",
  "C010 loads from a static synthetic dataset without calling a model. Its PDFs are training sources. The demo does not use or analyze your selected files."
 ],
 "class_demo": [
  "Учебный источник",
  "Оқу дереккөзі",
  "Training source"
 ],
 "demoMode": [
  "Подготовленное демо C010",
  "Дайын C010 демосы",
  "Prepared C010 demo"
 ],
 "demoMethod": [
  "Синтетический пример",
  "Синтетикалық мысал",
  "Synthetic example"
 ],
 "staticExample": [
  "C010 · подготовленный пример, без запуска backend",
  "C010 · backend іске қосылмайтын дайын мысал",
  "C010 · prepared example, no backend run"
 ],
 "searchScope": [
  "Область сравнения «После»",
  "«Кейін» салыстыру аясы",
  "After comparison scope"
 ],
 "lossCaution": [
  "Совпадение не найдено в доступных документах. Это не доказательство утраты функции во всей организации.",
  "Қолжетімді құжаттарда сәйкестік табылмады. Бұл бүкіл ұйымдағы функция жоғалғанының дәлелі емес.",
  "No match was found in the available documents. This does not prove the function was lost across the organization."
 ],
 "pageNumber": [
  "Страница {page}",
  "{page}-бет",
  "Page {page}"
 ],
 "pageUnavailable": [
  "Страница не определена парсером",
  "Бет нөмірін талдағыш анықтамады",
  "Page not supplied by parser"
 ],
 "overviewTitle": [
  "Сначала проверьте контекст.",
  "Алдымен контексті тексеріңіз.",
  "Check the context first."
 ],
 "overviewText": [
  "Ниже — состав сравнения и предварительные выводы. Откройте источник, чтобы подтвердить или отклонить интерпретацию.",
  "Төменде салыстыру құрамы мен алдын ала қорытындылар бар. Түсіндіруді растау не қабылдамау үшін дереккөзді ашыңыз.",
  "Below are the comparison scope and preliminary findings. Open a source to confirm or reject the interpretation."
 ],
 "localHint": [
  "Файлы обрабатывает сервер. С ИИ текст передаётся провайдеру; материалы запуска сохраняются на сервере.",
  "Файлдарды сервер өңдейді. ЖИ қосылса, мәтін провайдерге беріледі; сеанс материалдары серверде сақталады.",
  "Files are processed by the server. With AI, text goes to the provider and run materials are saved on the server."
 ],
 "backendLimit": [
  "Эта форма принимает DOCX. PDF доступен только в отдельном исследовательском API. OCR и Excel не подключены. Лимит: 1 500 абзацев и 250 000 символов на сторону.",
  "Бұл форма DOCX қабылдайды. PDF тек бөлек зерттеу API-де бар. OCR және Excel қосылмаған. Шек: әр кезеңге 1 500 абзац және 250 000 таңба.",
  "This form accepts DOCX. PDF is available only in the separate research API. OCR and Excel are not connected. Limit: 1,500 paragraphs and 250,000 characters per side."
 ]
});
Object.assign(entries,{fileTypeError:['Эта форма принимает только DOCX.','Бұл форма тек DOCX қабылдайды.','This form accepts DOCX only.']});
Object.assign(entries,{
 "cases": [
  "Дела",
  "Істер",
  "Cases"
 ],
 "collapseNav": [
  "Свернуть навигацию",
  "Навигацияны жинау",
  "Collapse navigation"
 ],
 "caseName": [
  "Название дела",
  "Іс атауы",
  "Case name"
 ],
 "caseNamePlaceholder": [
  "Например, реорганизация технического блока",
  "Мысалы, техникалық блокты қайта ұйымдастыру",
  "For example, technical division reorganization"
 ],
 "caseDefault": [
  "Проверка документов",
  "Құжаттарды тексеру",
  "Document review"
 ],
 "demoCaseName": [
  "Реорганизация технического блока · C010",
  "Техникалық блокты қайта ұйымдастыру · C010",
  "Technical division reorganization · C010"
 ],
 "caseSections": [
  "Разделы дела",
  "Іс бөлімдері",
  "Case sections"
 ],
 "agent": [
  "Агент",
  "Агент",
  "Agent"
 ],
 "localCaseStorage": [
  "История этого браузера · документы и решения сохраняются локально",
  "Осы браузер тарихы · құжаттар мен шешімдер жергілікті сақталады",
  "Browser history · documents and decisions saved locally"
 ],
 "savedAnalysis": [
  "Сохранённый анализ",
  "Сақталған талдау",
  "Saved analysis"
 ],
 "caseSummary": [
  "Документов: {documents} · кандидатов: {findings}",
  "Құжаттар: {documents} · болжамдар: {findings}",
  "Documents: {documents} · findings: {findings}"
 ],
 "noCases": [
  "Пока нет сохранённых дел",
  "Сақталған істер жоқ",
  "No saved cases yet"
 ],
 "caseMissing": [
  "Дело не найдено в этом браузере",
  "Іс бұл браузерде табылмады",
  "Case not found in this browser"
 ],
 "caseMissingText": [
  "Локальная ссылка не предоставляет доступ на другом устройстве. Серверное хранение дел ещё не подключено.",
  "Жергілікті сілтеме басқа құрылғыға қолжетімділік бермейді. Істерді серверде сақтау әлі қосылмаған.",
  "A local link does not grant access on another device. Server case storage is not connected yet."
 ],
 "analysisVersion": [
  "Версия анализа {version}",
  "Талдау нұсқасы {version}",
  "Analysis version {version}"
 ],
 "conversation": [
  "Разговор по делу",
  "Іс бойынша әңгіме",
  "Case conversation"
 ],
 "agentQuestion": [
  "Вопрос по документам",
  "Құжаттар туралы сұрақ",
  "Question about the documents"
 ],
 "agentPlaceholder": [
  "Задайте вопрос или добавьте фрагмент из источника…",
  "Сұрақ қойыңыз немесе дереккөзден үзінді қосыңыз…",
  "Ask a question or add a source fragment…"
 ],
 "send": [
  "Отправить",
  "Жіберу",
  "Send"
 ],
 "stop": [
  "Остановить",
  "Тоқтату",
  "Stop"
 ],
 "stopping": [
  "Останавливаем…",
  "Тоқтатылуда…",
  "Stopping…"
 ],
 "newAnswer": [
  "Новый ответ ↓",
  "Жаңа жауап ↓",
  "New response ↓"
 ],
 "demoOperation": [
  "Демо-действие",
  "Демо әрекеті",
  "Demo action"
 ],
 "searchDocuments": [
  "Поиск по документам",
  "Құжаттардан іздеу",
  "Search documents"
 ],
 "recheckFinding": [
  "Проверить выбранный вывод",
  "Таңдалған қорытындыны тексеру",
  "Recheck selected finding"
 ],
 "readFixture": [
  "Читаю учебный комплект C010",
  "C010 оқу жинағын оқу",
  "Read C010 training packet"
 ],
 "readFragments": [
  "Читаю исходные фрагменты",
  "Бастапқы үзінділерді оқу",
  "Read original fragments"
 ],
 "compareFragments": [
  "Сопоставляю формулировки",
  "Тұжырымдарды салыстыру",
  "Compare wording"
 ],
 "draftConclusion": [
  "Подготовить заключение",
  "Қорытынды дайындау",
  "Draft conclusion"
 ],
 "toolAction": [
  "Действие",
  "Әрекет",
  "Action"
 ],
 "tool_running": [
  "Выполняется",
  "Орындалуда",
  "Running"
 ],
 "tool_completed": [
  "Выполнено",
  "Орындалды",
  "Completed"
 ],
 "tool_failed": [
  "Ошибка",
  "Қате",
  "Failed"
 ],
 "tool_cancelled": [
  "Отменено",
  "Бас тартылды",
  "Cancelled"
 ],
 "tool_pending": [
  "Ожидает запуска",
  "Іске қосуды күтуде",
  "Pending"
 ],
 "toolItems": [
  "Элементов в результате: {count}",
  "Нәтижедегі элементтер: {count}",
  "Result items: {count}"
 ],
 "localDemoExecution": [
  "Локальное действие демонстрационного адаптера. Модель и серверный агент не вызываются.",
  "Демо адаптердің жергілікті әрекеті. Модель мен сервер агенті шақырылмайды.",
  "Local demo adapter operation. No model or server agent is called."
 ],
 "demoAgentDisclosure": [
  "ДЕМО C010 · Локальный адаптер читает учебные данные. Это демонстрация интерфейса, не работа серверного агента.",
  "C010 ДЕМО · Жергілікті адаптер оқу деректерін оқиды. Бұл сервер агентінің жұмысы емес, интерфейс көрсетілімі.",
  "C010 DEMO · A local adapter reads training data. This demonstrates the interface, not a server agent."
 ],
 "agentUnavailable": [
  "Чат с серверным агентом пока не подключён. Результаты, документы, проверка и экспорт доступны.",
  "Сервер агентімен чат әлі қосылмаған. Нәтижелер, құжаттар, тексеру және экспорт қолжетімді.",
  "Server agent chat is not connected yet. Results, documents, review and export remain available."
 ],
 "openDemoAgent": [
  "Открыть демо чата",
  "Чат демосын ашу",
  "Open chat demo"
 ],
 "liveComposerHint": [
  "Черновик сохраняется. Отправка станет доступна после подключения API разговоров и гостевой изоляции.",
  "Нобай сақталады. Жіберу әңгіме API-і мен қонақ оқшаулауы қосылғаннан кейін қолжетімді болады.",
  "Draft saved. Sending requires the conversation API and guest isolation."
 ],
 "demoComposerHint": [
  "Enter — отправить · Shift+Enter — новая строка. Действие выбрано явно; свободный текст используется для буквального поиска.",
  "Enter — жіберу · Shift+Enter — жаңа жол. Әрекет нақты таңдалады; еркін мәтін сөзбе-сөз іздеуге қолданылады.",
  "Enter to send · Shift+Enter for a new line. Choose an action explicitly; free text uses literal search."
 ],
 "savedSummary": [
  "Сводка сохранённого результата",
  "Сақталған нәтиже түйіні",
  "Saved result summary"
 ],
 "agentWelcome": [
  "Разберём изменения по источникам.",
  "Өзгерістерді дереккөздермен тексерейік.",
  "Review changes against the evidence."
 ],
 "summaryCounts": [
  "Обработано документов: {documents}. Кандидатов изменений: {findings}, из них потенциальных рисков: {risks}.",
  "Өңделген құжаттар: {documents}. Өзгеріс болжамдары: {findings}, оның ішінде ықтимал тәуекелдер: {risks}.",
  "Documents processed: {documents}. Candidate changes: {findings}, including {risks} potential risks."
 ],
 "summaryCaution": [
  "Откройте вывод, сопоставьте цитаты и зафиксируйте своё решение. Наличие источника не означает подтверждение аналитиком.",
  "Қорытындыны ашып, дәйексөздерді салыстырыңыз және шешіміңізді белгілеңіз. Дереккөздің болуы талдаушы растағанын білдірмейді.",
  "Open a finding, compare quotations and record your decision. A source does not mean an analyst has confirmed the finding."
 ],
 "noRisksScoped": [
  "По обработанным документам потенциальные отклонения не найдены. Это не гарантия отсутствия риска за пределами доступного комплекта.",
  "Өңделген құжаттарда ықтимал ауытқулар табылмады. Бұл қолжетімді жинақтан тыс тәуекел жоқ деген кепілдік емес.",
  "No potential deviations were found in the processed documents. This does not establish absence of risk beyond the available packet."
 ],
 "partialAgent": [
  "Результат неполный: проверьте предупреждения анализа во вкладке «Результаты».",
  "Нәтиже толық емес: «Нәтижелер» бөліміндегі ескертулерді тексеріңіз.",
  "Partial result: check the analysis warnings under Results."
 ],
 "you": [
  "Вы",
  "Сіз",
  "You"
 ],
 "userClarification": [
  "Пояснение пользователя, не факт из документа",
  "Пайдаланушы түсіндірмесі, құжаттағы факт емес",
  "User statement, not a documented fact"
 ],
 "demoAdapter": [
  "Демо-адаптер · без модели",
  "Демо адаптер · модельсіз",
  "Demo adapter · no model"
 ],
 "riskContext": [
  "Вывод",
  "Қорытынды",
  "Finding"
 ],
 "removeContext": [
  "Убрать контекст",
  "Контексті алып тастау",
  "Remove context"
 ],
 "discussAgent": [
  "Обсудить с агентом",
  "Агентпен талқылау",
  "Discuss with agent"
 ],
 "askFragment": [
  "Спросить о фрагменте",
  "Үзінді туралы сұрау",
  "Ask about fragment"
 ],
 "sourceTitle": [
  "Первоисточник",
  "Бастапқы дереккөз",
  "Original source"
 ],
 "surroundingContext": [
  "Соседние пункты",
  "Көршілес тармақтар",
  "Surrounding clauses"
 ],
 "documentsContext": [
  "Исходные тексты текущей версии. Откройте пункт или добавьте его в контекст разговора.",
  "Ағымдағы нұсқаның бастапқы мәтіндері. Тармақты ашыңыз немесе әңгіме контекстіне қосыңыз.",
  "Original texts for this analysis version. Open a clause or add it to the conversation context."
 ],
 "questionFinding": [
  "Проверь вывод «{type}» по исходным документам.",
  "«{type}» қорытындысын бастапқы құжаттардан тексер.",
  "Check the “{type}” finding against the original documents."
 ],
 "draftQuestion": [
  "Подготовь заключение по текущей версии анализа.",
  "Ағымдағы талдау нұсқасы бойынша қорытынды дайында.",
  "Draft a conclusion for this analysis version."
 ],
 "commonWording": [
  "Совпадающая формулировка в двух цитатах",
  "Екі дәйексөздегі ортақ тұжырым",
  "Shared wording in both quotations"
 ],
 "demoInterpretation": [
  "Показана предварительная интерпретация учебного набора. Распределение ролей может уточняться в других документах. Пояснение пользователя само по себе не подтверждает изменение обязанности.",
  "Оқу жинағының алдын ала түсіндіруі көрсетілген. Рөлдер басқа құжаттарда нақтылануы мүмкін. Пайдаланушы түсіндірмесі міндет өзгергенін өздігінен растамайды.",
  "This is the training dataset’s preliminary interpretation. Other documents may clarify the roles. A user statement alone does not establish a changed duty."
 ],
 "demoFragmentRead": [
  "Показан точный фрагмент учебного документа. Свободный вопрос сохранён, но модель для ответа на него не вызывалась.",
  "Оқу құжатының дәл үзіндісі көрсетілді. Еркін сұрақ сақталды, бірақ жауап беру үшін модель шақырылған жоқ.",
  "The exact training-document fragment is shown. Your question was saved, but no model was called to answer it."
 ],
 "demoSearchResults": [
  "Совпадения буквального поиска в учебном комплекте. Это найденные фрагменты, а не вывод модели.",
  "Оқу жинағындағы сөзбе-сөз іздеу сәйкестіктері. Бұлар модель қорытындысы емес, табылған үзінділер.",
  "Literal search matches in the training packet. These are retrieved fragments, not model conclusions."
 ],
 "demoNoMatches": [
  "Буквальный поиск в C010 не нашёл совпадений. Измените запрос или выберите конкретный вывод. Отсутствие совпадений не доказывает потерю функции.",
  "C010 бойынша сөзбе-сөз іздеу сәйкестік таппады. Сұрауды өзгертіңіз немесе нақты қорытындыны таңдаңыз. Сәйкестіктің болмауы функция жоғалғанын дәлелдемейді.",
  "Literal search found no C010 matches. Change the query or select a finding. Missing matches do not prove a lost function."
 ],
 "demoCancelled": [
  "Локальное демо-действие остановлено. Завершённые действия сохранены. Серверная отмена не выполнялась.",
  "Жергілікті демо әрекеті тоқтатылды. Аяқталған әрекеттер сақталды. Серверлік тоқтату орындалған жоқ.",
  "Local demo action stopped. Completed actions were retained. No server cancellation was performed."
 ],
 "demoConnection": [
  "Не удалось прочитать учебные данные. Частичные результаты сохранены; повторите нужное действие.",
  "Оқу деректерін оқу мүмкін болмады. Ішінара нәтижелер сақталды; қажетті әрекетті қайталаңыз.",
  "Could not read the training data. Partial results were retained; retry the needed action."
 ],
 "run_completed": [
  "Действие завершено",
  "Әрекет аяқталды",
  "Action completed"
 ],
 "run_failed": [
  "Действие не завершено. Уже полученные данные сохранены.",
  "Әрекет аяқталмады. Алынған деректер сақталды.",
  "The action did not complete. Available data was retained."
 ],
 "run_cancelled": [
  "Действие отменено",
  "Әрекет тоқтатылды",
  "Action cancelled"
 ],
 "run_interrupted": [
  "Сеанс прерван при закрытии или обновлении страницы. Автоматического повторного запуска не было.",
  "Сеанс бет жабылғанда не жаңартылғанда үзілді. Автоматты қайта іске қосу болған жоқ.",
  "The session was interrupted by closing or reloading the page. It was not automatically restarted."
 ],
 "retryOperation": [
  "Вернуть запрос в черновик",
  "Сұрауды нобайға қайтару",
  "Restore request to draft"
 ],
 "runActive": [
  "Дождитесь завершения или остановки текущего демо-действия.",
  "Ағымдағы демо әрекетінің аяқталуын не тоқтауын күтіңіз.",
  "Wait for the current demo action to finish or stop."
 ],
 "emptyMessage": [
  "Введите вопрос перед отправкой.",
  "Жібермес бұрын сұрақ енгізіңіз.",
  "Enter a question before sending."
 ],
 "staleContext": [
  "Контекст относится к другой версии или изменился. Выберите источник заново.",
  "Контекст басқа нұсқаға қатысты немесе өзгерген. Дереккөзді қайта таңдаңыз.",
  "The context belongs to another version or has changed. Select the source again."
 ],
 "sourceUnavailable": [
  "Источник недоступен в этой версии дела.",
  "Дереккөз бұл іс нұсқасында қолжетімсіз.",
  "Source unavailable in this case version."
 ],
 "originalUnavailable": [
  "Исходный файл отсутствует в локальной истории. Извлечённый текст доступен.",
  "Бастапқы файл жергілікті тарихта жоқ. Алынған мәтін қолжетімді.",
  "The original file is missing from local history. Extracted text remains available."
 ],
 "caseConflict": [
  "Дело изменилось в другой вкладке. Обновите страницу; текущие изменения не перезаписали сохранённую версию.",
  "Іс басқа қойындыда өзгерді. Бетті жаңартыңыз; ағымдағы өзгерістер сақталған нұсқаны қайта жазған жоқ.",
  "The case changed in another tab. Reload; current edits did not overwrite the saved version."
 ],
 "storageUnavailable": [
  "История браузера недоступна. Текущий результат останется только до обновления страницы — экспортируйте заключение.",
  "Браузер тарихы қолжетімсіз. Ағымдағы нәтиже бет жаңартылғанша ғана сақталады — қорытындыны экспорттаңыз.",
  "Browser storage is unavailable. The current result lasts only until reload — export the conclusion."
 ],
 "eventGap": [
  "Не хватает событий. Нужна синхронизация состояния разговора.",
  "Оқиғалар жетіспейді. Әңгіме күйін синхрондау қажет.",
  "Events are missing. Conversation state needs synchronization."
 ],
 "analysisReady": [
  "Анализ готов — открыть дело",
  "Талдау дайын — істі ашу",
  "Analysis ready — open case"
 ],
 "answerReady": [
  "Демо-ответ готов — открыть дело",
  "Демо жауап дайын — істі ашу",
  "Demo response ready — open case"
 ],
 "artifactVersions": [
  "Подготовленные версии заключения",
  "Дайын қорытынды нұсқалары",
  "Prepared conclusion versions"
 ],
 "artifactReady": [
  "Готовый файл",
  "Дайын файл",
  "File ready"
 ],
 "artifactOutdated": [
  "Оценки изменились после подготовки",
  "Бағалар дайындалғаннан кейін өзгерді",
  "Reviews changed after preparation"
 ],
 "artifactMissing": [
  "Эта версия материала недоступна.",
  "Материалдың бұл нұсқасы қолжетімсіз.",
  "This artifact version is unavailable."
 ],
 "downloadVersion": [
  "Скачать V{version}",
  "V{version} жүктеу",
  "Download V{version}"
 ],
 "localHint": [
  "Дела сохраняются в этом браузере. ИИ-запросы отправляют текст провайдеру. Серверный чат ещё не подключён.",
  "Істер осы браузерде сақталады. ЖИ сұраулары мәтінді провайдерге жібереді. Серверлік чат әлі қосылмаған.",
  "Cases are saved in this browser. AI requests send text to the provider. Server chat is not connected yet."
 ],
 "dataReviewText": [
  "Язык и тема сохраняются в браузере. Дела, исходные файлы, извлечённые тексты, результаты, решения и демопереписка хранятся в IndexedDB этого браузера. Ключ модели туда не записывается. Это локальное хранение, а не защищённый многопользовательский сервис; очистка данных сайта удалит историю.",
  "Тіл мен тақырып браузерде сақталады. Істер, бастапқы файлдар, алынған мәтіндер, нәтижелер, шешімдер мен демо әңгімелер осы браузердің IndexedDB ішінде сақталады. Модель кілті сақталмайды. Бұл қорғалған көп пайдаланушы қызметі емес, жергілікті сақтау; сайт деректерін тазалау тарихты жояды.",
  "Language and theme persist in your browser. Cases, original files, extracted text, results, reviews and demo conversations are stored in this browser’s IndexedDB. Model keys are never stored there. This is local storage, not a secure multi-user service; clearing site data removes the history."
 ],
 "guideExportText": [
  "История дела сохраняется в этом браузере. Заключение можно скачать в Markdown; отдельные демоверсии содержат номер, источники и демометку. Старые материалы не переписываются при изменении оценки — они получают отметку об устаревании.",
  "Іс тарихы осы браузерде сақталады. Қорытынды Markdown форматында жүктеледі; демо нұсқаларда нөмір, дереккөздер мен демо белгісі бар. Баға өзгергенде ескі материалдар қайта жазылмай, ескірген деп белгіленеді.",
  "Case history is saved in this browser. Export Markdown; demo artifact versions include their number, sources and demo label. Review changes mark old artifacts outdated without rewriting them."
 ],
 "savedSession": [
  "Сохранено в локальном деле",
  "Жергілікті істе сақталды",
  "Saved in local case"
 ]
});
Object.assign(entries,{expandSource:['Развернуть источник','Дереккөзді кеңейту','Expand source'],restoreChat:['Вернуться к разговору','Әңгімеге оралу','Return to conversation']});
Object.assign(entries,{packetTitle:['Начнём с документов.','Құжаттардан бастайық.','Start with your documents.'],packetIntro:['Два комплекта. Одна полная картина изменений.','Екі жинақ. Өзгерістердің толық көрінісі.','Two sets. One complete view of the changes.']});
Object.assign(entries,{documentEditingUnavailable:['Предложения правок и создание рабочих версий документов ещё не подключены. Исходники доступны для чтения; отметки аналитика сохраняются локально.','Құжат түзетулерін ұсыну және жұмыс нұсқаларын жасау әлі қосылмаған. Түпнұсқалар оқуға қолжетімді; талдаушы белгілері жергілікті сақталады.','Document change proposals and working versions are not connected yet. Originals remain readable; analyst decisions are saved locally.']});
Object.assign(entries,{previewArtifact:['Посмотреть эту версию','Осы нұсқаны көру','Preview this version']});
Object.assign(entries,{sampleProcessed:['Учебные DOCX обработаны настоящим backend. Это синтетический комплект для проверки, а не подготовленный результат C010.','Оқу DOCX файлдарын нақты backend өңдеді. Бұл C010 дайын нәтижесі емес, тексеруге арналған синтетикалық жинақ.','Sample DOCX files were processed by the real backend. This is a synthetic test set, not the prepared C010 result.']});
Object.assign(entries,{
 "tabTitle": [
  "Distingt — анализ документов",
  "Distingt — құжаттарды талдау",
  "Distingt — document analysis"
 ],
 "findingsBadge": [
  "Замечания · {count}",
  "Ескертулер · {count}",
  "Findings · {count}"
 ],
 "expandNav": [
  "Открыть боковую панель",
  "Бүйірлік панельді ашу",
  "Open sidebar"
 ],
 "collapseNav": [
  "Свернуть боковую панель",
  "Бүйірлік панельді жию",
  "Collapse sidebar"
 ],
 "newAnswer": [
  "К новым сообщениям",
  "Жаңа хабарламаларға",
  "New messages"
 ],
 "agentTrace": [
  "Действия",
  "Әрекеттер",
  "Actions"
 ],
 "demoOperation": [
  "Действие",
  "Әрекет",
  "Action"
 ],
 "settings": [
  "Настройки обработки",
  "Өңдеу параметрлері",
  "Processing settings"
 ],
 "semanticAnalysis": [
  "Искать смысловые изменения",
  "Мағыналық өзгерістерді іздеу",
  "Find changes in meaning"
 ],
 "analysisAvailable": [
  "Готово к сравнению документов.",
  "Құжаттарды салыстыруға дайын.",
  "Ready to compare your documents."
 ],
 "textComparisonAvailable": [
  "Доступно сравнение формулировок. Смысловые изменения требуют дополнительной проверки.",
  "Тұжырымдарды салыстыру қолжетімді. Мағыналық өзгерістерді қосымша тексеру қажет.",
  "Wording comparison is available. Changes in meaning need additional review."
 ],
 "reading": [
  "Подготавливаем документы…",
  "Құжаттарды дайындаудамыз…",
  "Preparing documents…"
 ],
 "processing": [
  "Сравниваем документы…",
  "Құжаттарды салыстырудамыз…",
  "Comparing documents…"
 ],
 "processingAI": [
  "Сравниваем функции…",
  "Функцияларды салыстырудамыз…",
  "Comparing responsibilities…"
 ],
 "progressHint": [
  "Дождитесь результата. Обработка может занять несколько минут; промежуточные этапы пока недоступны.",
  "Нәтижені күтіңіз. Өңдеу бірнеше минутқа созылуы мүмкін; аралық кезеңдер әзірге қолжетімсіз.",
  "Please wait for the result. Processing can take several minutes; intermediate stages are not available yet."
 ],
 "complete": [
  "Готово",
  "Дайын",
  "Ready"
 ],
 "timeout": [
  "Не удалось дождаться результата. Повторите попытку или попробуйте меньший комплект документов.",
  "Нәтижені күту уақыты аяқталды. Қайталаңыз немесе құжаттар санын азайтыңыз.",
  "The result took too long. Retry or try a smaller set of documents."
 ],
 "technicalDetails": [
  "Подробности ошибки",
  "Қате туралы мәлімет",
  "Error details"
 ],
 "localWorkspace": [
  "Сохранено в браузере",
  "Браузерде сақталған",
  "Saved in this browser"
 ],
 "localHint": [
  "Дела и история доступны в этом браузере. Подробнее — в разделе «Обработка данных».",
  "Істер мен тарих осы браузерде қолжетімді. Толығырақ — «Деректерді өңдеу» бөлімінде.",
  "Cases and history stay available in this browser. See Data processing for details."
 ],
 "dataPolicy": [
  "Обработка данных",
  "Деректерді өңдеу",
  "Data processing"
 ],
 "guideRunText": [
  "Нажмите «Начать анализ». Сервис использует настроенный способ обработки. Если смысловой анализ недоступен, вы увидите сравнение формулировок и его ограничения. Результаты проверяйте по источникам.",
  "«Талдауды бастау» батырмасын басыңыз. Қызмет бапталған өңдеу тәсілін қолданады. Мағыналық талдау қолжетімсіз болса, тұжырымдарды салыстыру және оның шектеулері көрсетіледі. Нәтижелерді дереккөздермен тексеріңіз.",
  "Select Start analysis. The service uses its configured processing method. If semantic analysis is unavailable, you will see wording comparisons and their limitations. Check results against their sources."
 ],
 "dataProviderText": [
  "При настроенном смысловом анализе текст документов отправляется выбранному поставщику ИИ. Если он не подключён или не ответил, доступны только текстовые сравнения с явной отметкой об ограничениях. Администратор может проверить и изменить подключение ниже. Условия обработки зависят от поставщика.",
  "Мағыналық талдау бапталғанда, құжат мәтіні таңдалған ЖИ жеткізушісіне жіберіледі. Ол қосылмаса немесе жауап бермесе, шектеулері белгіленген мәтіндік салыстыру ғана қолжетімді. Әкімші қосылымды төменде тексеріп, өзгерте алады. Өңдеу шарттары жеткізушіге байланысты.",
  "When semantic analysis is configured, document text is sent to the selected AI provider. If it is not connected or fails to respond, only wording comparisons are available, with a clear limitation notice. An administrator can inspect or change the connection below. Processing terms depend on the provider."
 ],
 "modelSettingsSaved": [
  "Настройки обработки применены.",
  "Өңдеу параметрлері қолданылды.",
  "Processing settings applied."
 ],
 "sampleProcessed": [
  "Учебные документы обработаны сервисом. Это вымышленный комплект для проверки, а не готовый результат демонстрации.",
  "Оқу құжаттарын қызмет өңдеді. Бұл дайын демо нәтижесі емес, тексеруге арналған ойдан шығарылған жинақ.",
  "The service processed these sample documents. This is a fictional test set, not a prepared demo result."
 ]
});
Object.assign(entries,{checkingAvailability:['Проверяем доступность обработки…','Өңдеу қолжетімділігін тексерудеміз…','Checking processing availability…']});
Object.assign(entries,{"demoAdapter": ["Демонстрация", "Көрсетілім", "Demonstration"], "demoAgentDisclosure": ["Демонстрационный пример C010. Действия выполняются на учебных документах без обращения к ИИ.", "C010 көрсетілім мысалы. Әрекеттер оқу құжаттарымен ЖИ-ге жүгінбей орындалады.", "C010 demonstration. Actions use sample documents without contacting an AI model."], "localDemoExecution": ["Проверяем учебный пример в этом браузере. Внешние сервисы не используются.", "Оқу мысалы осы браузерде тексеріледі. Сыртқы қызметтер қолданылмайды.", "The sample is checked in this browser. No external service is used."], "agentUnavailable": ["Разговор по загруженным документам пока недоступен. Можно изучить результаты, проверить источники и скачать заключение.", "Жүктелген құжаттар бойынша әңгіме әзірге қолжетімсіз. Нәтижелерді зерттеп, дереккөздерді тексеріп, қорытындыны жүктей аласыз.", "Chat about uploaded documents is not available yet. You can review results, check sources and download a conclusion."], "liveComposerHint": ["Вопрос сохраняется как черновик. Отправка пока недоступна.", "Сұрақ нобай ретінде сақталады. Жіберу әзірге қолжетімсіз.", "Your question is saved as a draft. Sending is not available yet."], "demoComposerHint": ["Enter — отправить · Shift+Enter — новая строка. В примере доступны поиск по словам, проверка замечания и заключение.", "Enter — жіберу · Shift+Enter — жаңа жол. Мысалда сөзбен іздеу, ескертуді тексеру және қорытынды қолжетімді.", "Enter to send · Shift+Enter for a new line. The demo supports word search, finding review and conclusions."], "candidateChanges": ["Замечания", "Ескертулер", "Findings"]});
Object.assign(entries,{
 "candidates": [
  "Замечания",
  "Ескертулер",
  "Findings"
 ],
 "riskContext": [
  "Замечание",
  "Ескерту",
  "Finding"
 ],
 "dataUploadText": [
  "После нажатия «Начать анализ» файлы DOCX передаются серверу Distingt. Он извлекает текст и сравнивает документы. Для сравнения формулировок внешний сервис не требуется.",
  "«Талдауды бастау» батырмасын басқан соң DOCX файлдары Distingt серверіне жіберіледі. Ол мәтінді шығарып, құжаттарды салыстырады. Тұжырымдарды салыстыру үшін сыртқы қызмет қажет емес.",
  "After you select Start analysis, DOCX files are sent to the Distingt server. It extracts text and compares documents. Wording comparison does not require an external service."
 ],
 "dataStorageText": [
  "Материалы смыслового анализа — документы, запросы и ответы — сохраняются на компьютере, где запущен сервер. Отдельный исследовательский режим также сохраняет документы и ход работы. Автоматическое удаление и управление сроками хранения в интерфейсе пока недоступны.",
  "Мағыналық талдау материалдары — құжаттар, сұраулар мен жауаптар — сервер іске қосылған компьютерде сақталады. Бөлек зерттеу режимі де құжаттар мен жұмыс барысын сақтайды. Интерфейсте автоматты жою және сақтау мерзімдерін басқару әзірге қолжетімсіз.",
  "Semantic analysis documents, requests and responses are saved on the computer running the server. The separate research mode also saves documents and work progress. Automatic deletion and retention controls are not available in the interface yet."
 ],
 "dataReviewText": [
  "Язык и тема, дела, исходные файлы, результаты, решения и переписка сохраняются в этом браузере. Ключ подключения туда не записывается. Сохранённые дела не переносятся автоматически на другие устройства. Очистка данных сайта удалит историю.",
  "Тіл мен тақырып, істер, бастапқы файлдар, нәтижелер, шешімдер мен әңгімелер осы браузерде сақталады. Қосылым кілті сақталмайды. Сақталған істер басқа құрылғыларға автоматты түрде көшірілмейді. Сайт деректерін тазалау тарихты жояды.",
  "Language, theme, cases, original files, results, decisions and conversations are saved in this browser. Connection keys are not stored there. Saved cases do not automatically transfer to other devices. Clearing site data deletes the history."
 ],
 "aboutLimits": [
  "Это хакатонный продукт. Качество смыслового анализа ещё требует проверки; полнота обнаружения изменений не гарантируется. Разговор по вашим документам и применение правок пока недоступны. Отдельный демочат работает только с учебным примером.",
  "Бұл — хакатон өнімі. Мағыналық талдау сапасы әлі тексеруді қажет етеді; барлық өзгерістерді табуға кепілдік жоқ. Өз құжаттарыңыз бойынша әңгіме және түзетулер енгізу әзірге қолжетімсіз. Бөлек демочат тек оқу мысалымен жұмыс істейді.",
  "This is a hackathon product. Semantic analysis still needs validation; complete detection is not guaranteed. Chat about your documents and applying edits are not available yet. The separate demo chat works only with a sample case."
 ]
});
Object.assign(entries,{
 dataUploadText:['После нажатия «Начать анализ» документы передаются локальному серверу. Обычный режим читает DOCX; исследовательский — DOCX и текстовые PDF. Сравнение по правилам не обращается к внешнему провайдеру.','«Талдауды бастау» басылғанда құжаттар жергілікті серверге жіберіледі. Әдеттегі режим DOCX, зерттеу режимі DOCX және мәтіндік PDF оқиды. Ережелік салыстыру сыртқы провайдерге жүгінбейді.','Starting analysis sends documents to the local server. Standard mode reads DOCX; research reads DOCX and text PDF. Rules comparison does not contact an external provider.'],
 dataStorageText:['Сервер сохраняет снимки анализов всех режимов и историю живого чата в output/analyses. Исследования и журналы модели также хранятся в output. Эти данные содержат текст документов. Автоматическое удаление и настройка сроков хранения пока недоступны.','Сервер барлық режимдердің талдау көшірмелері мен чат тарихын output/analyses ішінде сақтайды. Зерттеулер мен модель журналдары да output ішінде. Олар құжат мәтінін қамтиды. Автоматты жою және сақтау мерзімін баптау әзірге жоқ.','The server saves all analysis snapshots and live chat history in output/analyses. Research and model logs also reside in output and contain document text. Automatic deletion and retention controls are unavailable.'],
 dataReviewText:['Дела, исходные файлы, результаты и оценки аналитика сохраняются в этом браузере; живой чат — на локальном сервере. Черновик вопроса хранится в сеансе браузера. Ключи подключения не сохраняются в истории. Очистка данных сайта удаляет браузерные дела, но не серверные снимки.','Істер, түпнұсқалар, нәтижелер және талдаушы бағалары браузерде, чат жергілікті серверде сақталады. Сұрақ жобасы браузер сеансында. Қосылу кілттері тарихта сақталмайды. Сайт деректерін тазалау браузер істерін жояды, сервер көшірмелерін жоймайды.','Cases, original files, results and analyst reviews are saved in this browser; live chat is saved on the local server. Question drafts stay in browser session storage. Keys are not stored in history. Clearing site data removes browser cases, not server snapshots.'],
 aboutLimits:['Это хакатонный продукт. Качество смыслового анализа требует проверки; полнота обнаружения изменений не гарантируется. Чат по выполненному анализу использует источники и требует модели. Применение правок к документам пока недоступно. C010 — отдельный учебный пример.','Бұл хакатон өнімі. Семантикалық талдау сапасын тексеру қажет; өзгерістердің толық анықталуына кепілдік жоқ. Аяқталған талдау чаты дереккөздер мен модельді пайдаланады. Құжаттарға түзету енгізу әзірге жоқ. C010 — бөлек оқу үлгісі.','This is a hackathon product. Semantic quality needs review and complete detection is not guaranteed. Chat on a saved analysis uses sources and requires a model. Applying document edits is unavailable. C010 is a separate educational example.'],
 common:['Общий документ','Ортақ құжат','Shared document'],
 backendLimit:['DOCX: обычный анализ. Для текстового PDF включите исследовательского агента и укажите версии. OCR и Excel не подключены.','DOCX: әдеттегі талдау. Мәтіндік PDF үшін зерттеу агентін қосып, нұсқаларды таңдаңыз. OCR және Excel қосылмаған.','DOCX: standard analysis. For text PDF, enable research and assign versions. OCR and Excel are unavailable.'],
 packetLimits:['2–20 документов · до 10 МБ каждый · до 20 МБ вместе','2–20 құжат · әрқайсысы 10 МБ дейін · барлығы 20 МБ дейін','2–20 documents · up to 10 MB each · up to 20 MB total'],
 researchMode:['Исследовательский агент','Зерттеу агенті','Research agent'],
 researchChoice:['Исследовать функции с поиском источников','Дереккөздерді іздеп функцияларды зерттеу','Investigate functions with source search'],
 researchHint:['Экспериментальный режим: DOCX и текстовый PDF, до 20 МБ на комплект. Укажите «До» и «После». Текст передаётся модели и сервису эмбеддингов; качество требует проверки аналитиком.','Эксперимент: DOCX және мәтіндік PDF, жинаққа 20 МБ дейін. «Дейін» және «Кейін» таңдаңыз. Мәтін модельге және эмбеддинг сервисіне жіберіледі; нәтижені талдаушы тексереді.','Experimental: DOCX and text PDF, up to 20 MB per set. Assign Before and After. Text is sent to the model and embedding provider; results need analyst review.'],
 researchTask:['Задача исследования','Зерттеу тапсырмасы','Research task'],
 researchDefault:['Сопоставь функции и подразделения до и после изменений. Найди существенные изменения, возможные потери, дублирование и конфликт интересов. Проверь подтверждающие и опровергающие источники; явно укажи непроверенные области.','Өзгерістерге дейінгі және кейінгі функциялар мен бөлімдерді салыстыр. Өзгерістерді, ықтимал жоғалуды, қайталануды және мүдделер қақтығысын зертте. Растайтын және теріске шығаратын деректерді тексер; тексерілмеген аймақтарды көрсет.','Compare functions and departments before and after changes. Investigate material changes, potential losses, duplication and conflicts of interest. Check supporting and counter evidence; state unexamined areas.'],
 researchPrepare:['Подготовка поискового индекса…','Іздеу индексі дайындалуда…','Preparing the search index…'],
 researchProgress:['Исследование: {calls} действий, {seconds} с','Зерттеу: {calls} әрекет, {seconds} с','Research: {calls} actions, {seconds} s'],
 researchSaved:['Открыть сохранённое исследование','Сақталған зерттеуді ашу','Open saved research'],
 researchNoConclusion:['Проверка не завершена. По этому запуску нельзя судить об отсутствии рисков.','Тексеру аяқталмады. Бұл іске қосу тәуекелдердің жоқтығын растамайды.','The review is incomplete. This run cannot establish the absence of risks.'],
 researchPartial:['Исследование завершено частично. Проверьте ограничения и непроверенные области.','Зерттеу ішінара аяқталды. Шектеулер мен тексерілмеген аймақтарды қараңыз.','Research is partial. Review limitations and unexamined areas.'],
 researchWarning:['Ограничение исследования','Зерттеу шектеуі','Research limitation'],
 researchPdf:['PDF доступен в режиме исследовательского агента.','PDF зерттеу агенті режимінде қолжетімді.','PDF is available in research agent mode.'],
 function_preserved:['Функция сохранена','Функция сақталған','Function preserved'],function_reworded:['Изменена формулировка','Тұжырым өзгерген','Wording changed'],function_changed:['Функция изменена','Функция өзгерген','Function changed'],function_unmatched:['Соответствие не найдено','Сәйкестік табылмады','No match established'],structure_unresolved:['Структура требует уточнения','Құрылымды нақтылау қажет','Structure unresolved'],risk_insufficient:['Недостаточно данных для риска','Тәуекелді бағалауға дерек жеткіліксіз','Insufficient evidence for risk'],commonShort:['Общий документ','Ортақ құжат','Shared document'],
 chatContextPartial:['Показана часть контекста. Для полного документа откройте вкладку «Документы».','Мәтінмәннің бір бөлігі көрсетілген. Толық құжатты «Құжаттар» бөлімінен ашыңыз.','Only part of the context is shown. Open Documents to read the full document.'],
 chatAskFragment:['Объясни фрагмент из «{name}» и проверь его по исходным документам: {quote}','«{name}» үзіндісін түсіндіріп, түпнұсқалармен тексер: {quote}','Explain this excerpt from «{name}» and verify it against the original documents: {quote}'],
 chatTitle:['Обсудить этот анализ','Осы талдауды талқылау','Discuss this analysis'],chatQuestion:['Вопрос по документам и выводам','Құжаттар мен қорытындылар туралы сұрақ','Question about documents and findings'],chatSend:['Отправить вопрос','Сұрақ жіберу','Send question'],chatAnswer:['Ответ агента','Агент жауабы','Agent answer'],
 chatSnapshotNote:['Агент видит исходный серверный анализ. Ваши локальные оценки и комментарии аналитика не передаются ему автоматически. Ответы требуют проверки.','Агент бастапқы серверлік талдауды көреді. Талдаушының жергілікті бағалары мен пікірлері автоматты түрде берілмейді. Жауаптарды тексеріңіз.','The agent sees the original server analysis. Local analyst reviews and notes are not automatically shared with it. Review its answers.'],
 chatProviderNote:['Вопрос и текст источников отправляются выбранному провайдеру. История сохраняется на локальном сервере.','Сұрақ пен дереккөз мәтіні таңдалған провайдерге жіберіледі. Тарих жергілікті серверде сақталады.','Your question and source text are sent to the selected provider. History is saved on the local server.'],
 chatNoSnapshot:['Для этого результата серверный чат недоступен. Выполните новый анализ; для частичного исследования сначала проверьте ограничения.','Бұл нәтиже үшін серверлік чат қолжетімсіз. Жаңа талдау жасаңыз; ішінара зерттеудің шектеулерін тексеріңіз.','Server chat is unavailable for this result. Run a new analysis; review limitations of partial research.'],
 chatRefresh:['Обновить историю','Тарихты жаңарту','Refresh history'],chatLoading:['Загрузка истории…','Тарих жүктелуде…','Loading history…'],chatMissing:['Серверный анализ не найден. Проверьте, что запущен тот же сервер, или выполните новый анализ.','Серверлік талдау табылмады. Сол серверді іске қосыңыз немесе жаңа талдау жасаңыз.','Server analysis was not found. Start the same server or run a new analysis.'],
 chatRetryRequest:['Повторить доставку вопроса','Сұрақты жеткізуді қайталау','Retry question delivery'],chatDisconnected:['Связь с сервером прервалась. Обновите историю; повторная доставка того же вопроса не создаёт второй запрос к модели.','Сервермен байланыс үзілді. Тарихты жаңартыңыз; сол сұрақты қайта жеткізу модельге екінші сұрау жасамайды.','Connection was interrupted. Refresh history; redelivering the same question does not create a second model request.'],chatConflict:['История изменилась. Проверьте новые сообщения и отправьте вопрос снова.','Тарих өзгерді. Жаңа хабарларды тексеріп, сұрақты қайта жіберіңіз.','History changed. Review new messages and send your question again.'],
 chatStatus_queued:['Вопрос принят','Сұрақ қабылданды','Question accepted'],chatStatus_preparing:['Подготовка поиска по источникам…','Дереккөздерді іздеу дайындалуда…','Preparing source search…'],chatStatus_answering:['Агент проверяет источники…','Агент дереккөздерді тексеруде…','The agent is checking sources…'],
 chatOutcome_answered:['Ответ с проверяемыми основаниями','Тексерілетін негіздері бар жауап','Answer with verifiable evidence'],chatOutcome_insufficient_data:['Недостаточно данных','Деректер жеткіліксіз','Insufficient data'],chatOutcome_needs_clarification:['Нужно уточнение','Нақтылау қажет','Clarification needed'],
 chatBasis_source:['Документ','Құжат','Document'],chatBasis_analysis:['Исходный анализ','Бастапқы талдау','Original analysis'],chatBasis_user:['Слова пользователя','Пайдаланушы сөзі','User statement'],chatBasis_conversation:['История разговора','Әңгіме тарихы','Conversation history']
});
Object.assign(entries,{backToCase:['Вернуться к проверке','Тексеруге оралу','Back to review'],findingMissing:['Замечание не найдено в этой проверке.','Бұл тексеруде ескерту табылмады.','This finding was not found in this review.']});
const enumEntries={
'department_added':['Добавлено в перечень','Тізімге қосылды','Added to the list'], 'department_removed':['Убрано из перечня','Тізімнен алынды','Removed from the list'], 'department_retained':['Сохранено в перечне','Тізімде сақталды','Retained in the list'], 'reorganization':['Преобразование','Қайта ұйымдастыру','Reorganization'], 'function_loss':['Потенциальная потеря','Ықтимал жоғалу','Potential loss'], 'function_transfer':['Передача функции','Функцияны беру','Function transfer'], 'duplication':['Возможное дублирование','Ықтимал қайталану','Potential duplication'], 'conflict':['Конфликт интересов','Мүдделер қақтығысы','Conflict of interest'], 'contradiction':['Противоречие формулировок','Тұжырымдар қайшылығы','Conflicting wording'], 'unknown':['Недостаточно данных','Деректер жеткіліксіз','Insufficient information'], 'risk':['Возможный риск','Ықтимал тәуекел','Potential risk'], 'confirmed':['Подтверждено аналитиком','Талдаушы растады','Confirmed by analyst'], 'dismissed':['Отклонено аналитиком','Талдаушы қабылдамады','Dismissed by analyst']};
Object.assign(entries,enumEntries);
export const dictionaries=Object.fromEntries(['ru','kk','en'].map((lang,i)=>[lang,Object.fromEntries(Object.entries(entries).map(([key,values])=>[key,values[i]]))]));
export let language=['ru','kk','en'].includes(document.documentElement.lang)?document.documentElement.lang:'ru';
export function t(key,params={}){return (dictionaries[language][key]??dictionaries.ru[key]??key).replace(/\{(\w+)\}/g,(_,name)=>String(params[name]??''));}
export function setLanguage(value){if(!dictionaries[value])return;language=value;document.documentElement.lang=value;try{localStorage.setItem('osnovanie.language',value);}catch{};translate();}
export function translate(root=document){
 root.querySelectorAll('[data-i18n]').forEach(el=>{el.textContent=t(el.dataset.i18n);});
 for(const attr of ['placeholder','aria-label','title'])root.querySelectorAll(`[data-i18n-${attr}]`).forEach(el=>el.setAttribute(attr,t(el.getAttribute(`data-i18n-${attr}`))));
 document.title=t('tabTitle');
}
export const number=value=>new Intl.NumberFormat(language==='kk'?'kk-KZ':language==='ru'?'ru-RU':'en-GB').format(value);
export const date=value=>new Intl.DateTimeFormat(language==='kk'?'kk-KZ':language==='ru'?'ru-RU':'en-GB',{dateStyle:'medium',timeStyle:'short'}).format(new Date(value));
