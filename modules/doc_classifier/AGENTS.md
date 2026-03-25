# Локальная политика агента модуля doc_classifier

## Назначение
Модуль отвечает за распознавание и классификацию документов.

## Что модуль делает
- получает документы из реестра или подготовленного источника;
- извлекает текст и признаки;
- определяет тип документа;
- сохраняет результаты классификации;
- показывает результат обработки и статус.

## Что модуль не делает
- не импортирует файлы из внешних источников;
- не ведет первичный реестр файлов;
- не формирует проекты и связи между документами.

## Особые требования
- Результат распознавания должен быть отделен от результата классификации.
- Нужно хранить исходный статус, статус распознавания и статус классификации.
- Нужно уметь повторно прогонять документ без поломки данных.
- UI должен позволять видеть, что было распознано и как классифицировано.

## Особые запреты
- Не реализовывать функции импорта и синхронизации.
- Не реализовывать проектные связи и аналитические выводы о нехватке документов.

## Команда task
По команде `task` агент этого модуля обязан:
- сначала смотреть SQL-реестр задач как источник правды;
- затем смотреть Google Sheets только как дашборд;
- искать записи по `module_name=doc_classifier`, своему `target_agent` или нужному `task_id`;
- при начале работы добавлять новую запись со статусом `in_progress`;
- при завершении, handoff, блокере или ошибке добавлять новую запись и не менять старые.

Где смотреть:
- `shared/task_registry.sql`
- `shared/task_registry.md`
- `.env` для `GOOGLE_SHEETS_DASHBOARD_ID` и `GOOGLE_SHEETS_DASHBOARD_URL`

Куда записывать:
- в SQL-таблицу `task_registry` через `./task add ...`;
- в Google Sheets только через `./task add ... --sync`;
- руками в таблицу агент doc_classifier ничего не пишет.

Команды:
- смотреть задачи: `./task list --module-name doc_classifier --limit 20`
- завершать запись: `./task add ... --module-name doc_classifier --sync`
- запускать модуль: `./modulectl start doc_classifier`
- смотреть статус: `./modulectl status doc_classifier`
- проверять доступность: `./modulectl health doc_classifier`
- останавливать модуль: `./modulectl stop doc_classifier`

Обязательное правило:
- перед работой читать задачи через `./task list --module-name doc_classifier --limit 20`;
- запускать локальный UI только через `./modulectl`, а не через прямой `python main.py`;
- после результата, handoff, blocker или ошибки выполнять `./task add ... --module-name doc_classifier --sync`;
- не завершать работу без записи в реестр задач.

Шаблоны:
- start:
  `./task add --task-id <task_id> --source-agent doc_classifier --target-agent doc_classifier --module-name doc_classifier --action-type start --summary "<что начато>" --status in_progress --artifacts "<paths>" --sync`
- handoff:
  `./task add --task-id <task_id> --source-agent doc_classifier --target-agent <reviewer_or_next_module> --module-name doc_classifier --action-type handoff --summary "<что готово>" --status done --artifacts "<paths>" --sync`
