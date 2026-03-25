# Локальная политика агента модуля ingest_registry

## Назначение
Модуль отвечает за импорт, загрузку и синхронизацию данных из Google Drive, Яндекс Диска и локальной загрузки, а также за ведение реестра файлов.

## Что модуль делает
- подключает источники данных;
- получает файлы и метаданные;
- сохраняет и обновляет реестр файлов;
- показывает статус загрузок и синхронизации;
- фиксирует происхождение файлов.

## Что модуль не делает
- не распознает содержимое документов;
- не классифицирует документы;
- не формирует проекты и связи между документами.

## Особые требования
- Любая синхронизация должна быть безопасной к повторному запуску.
- Реестр должен быть устойчив к дублям.
- Нужно сохранять источник, идентификатор, путь, имя, дату и статус файла.
- Локальная загрузка должна быть простой и проверяемой через UI.
- Ошибки по источникам должны логироваться отдельно и понятно.

## Особые запреты
- Не выполнять OCR, классификацию и проектную логику.
- Не добавлять в этот модуль чужие бизнес-правила.

## Команда task
По команде `task` агент этого модуля обязан:
- сначала смотреть SQL-реестр задач как источник правды;
- затем смотреть Google Sheets только как дашборд;
- искать записи по `module_name=ingest_registry`, своему `target_agent` или нужному `task_id`;
- при начале работы добавлять новую запись со статусом `in_progress`;
- при завершении, handoff, блокере или ошибке добавлять новую запись и не менять старые.

Где смотреть:
- `shared/task_registry.sql`
- `shared/task_registry.md`
- `.env` для `GOOGLE_SHEETS_DASHBOARD_ID` и `GOOGLE_SHEETS_DASHBOARD_URL`

Куда записывать:
- в SQL-таблицу `task_registry` через `./task add ...`;
- в Google Sheets только через `./task add ... --sync`;
- руками в таблицу агент ingest_registry ничего не пишет.

Команды:
- смотреть задачи: `./task list --module-name ingest_registry --limit 20`
- завершать запись: `./task add ... --module-name ingest_registry --sync`
- запускать модуль: `./modulectl start ingest_registry`
- смотреть статус: `./modulectl status ingest_registry`
- проверять доступность: `./modulectl health ingest_registry`
- останавливать модуль: `./modulectl stop ingest_registry`

Обязательное правило:
- перед работой читать задачи через `./task list --module-name ingest_registry --limit 20`;
- запускать локальный UI только через `./modulectl`, а не через прямой `python main.py`;
- после результата, handoff, blocker или ошибки выполнять `./task add ... --module-name ingest_registry --sync`;
- не завершать работу без записи в реестр задач.

Шаблоны:
- start:
  `./task add --task-id <task_id> --source-agent ingest_registry --target-agent ingest_registry --module-name ingest_registry --action-type start --summary "<что начато>" --status in_progress --artifacts "<paths>" --sync`
- handoff:
  `./task add --task-id <task_id> --source-agent ingest_registry --target-agent <reviewer_or_next_module> --module-name ingest_registry --action-type handoff --summary "<что готово>" --status done --artifacts "<paths>" --sync`
