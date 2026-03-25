# Task Registry

## Источник правды
Источником правды по задачам является SQL-реестр задач.

## Назначение Google Sheets
Google Sheets используется только как дашборд для наблюдения пользователем за тем, что происходит в системе.

## Основной принцип
Агенты:
- могут добавлять только новые записи;
- не могут менять старые записи;
- не могут удалять старые записи.

## Что фиксируется новой записью
- начало работы;
- завершение работы;
- результат проверки;
- замечание reviewer;
- handoff между модулями;
- блокеры и ошибки.

## Минимальные поля записи
- task_id
- source_agent
- target_agent
- module_name
- action_type
- summary
- status
- artifacts
- created_at

## SQL-схема
Физическая схема таблицы хранится в `shared/task_registry.sql`.

Базовая таблица:
- `id` — внутренний числовой идентификатор записи;
- `task_id` — стабильный идентификатор задачи;
- `source_agent` — кто создал запись;
- `target_agent` — кому адресовано действие или handoff;
- `module_name` — имя модуля;
- `action_type` — тип действия;
- `summary` — короткое описание;
- `status` — текущий статус этой записи;
- `artifacts` — ссылки, пути, ids, json-строка или краткий список артефактов;
- `created_at` — время создания записи.

## Google Sheets dashboard
Google Sheets не заменяет SQL и не является источником правды.

Структура колонок для рабочего листа Google Sheets:
- `task_id`
- `source_agent`
- `target_agent`
- `module_name`
- `action_type`
- `summary`
- `status`
- `artifacts`
- `created_at`

Рекомендуемая первая строка листа:
`task_id | source_agent | target_agent | module_name | action_type | summary | status | artifacts | created_at`

Имя рабочего листа берется из `.env`:
- `GOOGLE_SHEETS_WORKSHEET_NAME`
- для текущего проекта настроен лист `Лист1`

## Команда task
По команде `task` агент должен:
1. Сначала прочитать SQL-реестр задач.
2. Найти последние записи по своему модулю, `task_id` или своему имени в `target_agent`.
3. Определить, есть ли активная работа, handoff, review или blocker.
4. После действия добавить новую запись, не меняя старые.
5. Использовать Google Sheets только как визуальный дашборд для пользователя.

Рекомендуемая CLI-команда проекта:
- `./task ensure-db`
- `./task list --limit 20`
- `./task list --module-name <module_name> --limit 20`
- `./task list --target-agent <agent_name> --limit 20`
- `./task add --task-id <task_id> --source-agent <source_agent> --target-agent <target_agent> --module-name <module_name> --action-type <action_type> --summary "<summary>" --status <status> --artifacts "<artifacts>" --sync`
- `./task sync`

Рекомендуемый режим работы:
- агент читает задачи через `./task list ...`;
- агент пишет новую запись через `./task add ... --sync`;
- отдельный постоянный демон не нужен, потому что append-only sync проще и надежнее поддерживать на текущем этапе.

Куда агент пишет запись:
- в SQL-таблицу `task_registry` через `./task add ...`;
- в Google Sheets запись попадает только через `./task add ... --sync` или `./task sync`;
- прямое ручное редактирование Google Sheets агентом не используется.

Как читать поля:
- `task_id` связывает все записи одной задачи;
- `source_agent` показывает, кто создал текущую запись;
- `target_agent` показывает, кому адресован следующий шаг;
- `module_name` определяет, к какому модулю относится запись;
- `action_type` описывает тип события;
- `summary` кратко объясняет событие;
- `status` фиксирует состояние именно этой записи;
- `artifacts` перечисляет полезные ссылки и файлы;
- `created_at` фиксирует время записи.

Шаблоны записей:
- start:
  `./task add --task-id <task_id> --source-agent <agent_name> --target-agent <agent_name> --module-name <module_name> --action-type start --summary "<work started>" --status in_progress --artifacts "<paths>" --sync`
- handoff:
  `./task add --task-id <task_id> --source-agent <agent_name> --target-agent <next_agent> --module-name <module_name> --action-type handoff --summary "<ready for next step>" --status done --artifacts "<paths>" --sync`
- review:
  `./task add --task-id <task_id> --source-agent <reviewer_name> --target-agent <module_name> --module-name <module_name> --action-type review --summary "<review result>" --status reviewed --artifacts "<paths>" --sync`
- blocked:
  `./task add --task-id <task_id> --source-agent <agent_name> --target-agent <agent_name> --module-name <module_name> --action-type blocked --summary "<blocker>" --status blocked --artifacts "<details>" --sync`

Типовые значения `action_type`:
- `start`
- `progress`
- `review`
- `handoff`
- `done`
- `blocked`
- `error`

Типовые значения `status`:
- `todo`
- `in_progress`
- `done`
- `blocked`
- `reviewed`
- `failed`
