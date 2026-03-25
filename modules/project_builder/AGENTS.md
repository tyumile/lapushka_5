# Локальная политика агента модуля project_builder

## Назначение
Модуль отвечает за формирование проектов, сопоставление документов и определение нехватки материалов.

## Что модуль делает
- группирует документы в проекты;
- строит связи между документами;
- определяет полноту набора;
- показывает, чего не хватает;
- формирует результирующее представление по проекту.

## Что модуль не делает
- не импортирует файлы;
- не занимается первичным распознаванием;
- не выполняет первичную классификацию.

## Особые требования
- Логика сопоставления должна быть прозрачной.
- Нужно уметь объяснить, почему документ отнесен к проекту.
- Нужно отдельно хранить найденные связи и отдельно дефициты.
- UI должен показывать проект, связанные документы и нехватки.

## Особые запреты
- Не тащить в этот модуль логику импорта.
- Не тащить в этот модуль тяжелую распознавательную логику.

## Команда task
По команде `task` агент этого модуля обязан:
- сначала смотреть SQL-реестр задач как источник правды;
- затем смотреть Google Sheets только как дашборд;
- искать записи по `module_name=project_builder`, своему `target_agent` или нужному `task_id`;
- при начале работы добавлять новую запись со статусом `in_progress`;
- при завершении, handoff, блокере или ошибке добавлять новую запись и не менять старые.

Где смотреть:
- `shared/task_registry.sql`
- `shared/task_registry.md`
- `.env` для `GOOGLE_SHEETS_DASHBOARD_ID` и `GOOGLE_SHEETS_DASHBOARD_URL`

Куда записывать:
- в SQL-таблицу `task_registry` через `./task add ...`;
- в Google Sheets только через `./task add ... --sync`;
- руками в таблицу агент project_builder ничего не пишет.

Команды:
- смотреть задачи: `./task list --module-name project_builder --limit 20`
- завершать запись: `./task add ... --module-name project_builder --sync`
- запускать модуль: `./modulectl start project_builder`
- смотреть статус: `./modulectl status project_builder`
- проверять доступность: `./modulectl health project_builder`
- останавливать модуль: `./modulectl stop project_builder`

Обязательное правило:
- перед работой читать задачи через `./task list --module-name project_builder --limit 20`;
- запускать локальный UI только через `./modulectl`, а не через прямой `python main.py`;
- после результата, handoff, blocker или ошибки выполнять `./task add ... --module-name project_builder --sync`;
- не завершать работу без записи в реестр задач.

Шаблоны:
- start:
  `./task add --task-id <task_id> --source-agent project_builder --target-agent project_builder --module-name project_builder --action-type start --summary "<что начато>" --status in_progress --artifacts "<paths>" --sync`
- handoff:
  `./task add --task-id <task_id> --source-agent project_builder --target-agent <reviewer_or_next_module> --module-name project_builder --action-type handoff --summary "<что готово>" --status done --artifacts "<paths>" --sync`
