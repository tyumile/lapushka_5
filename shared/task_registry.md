# Task Workflow Registry

## Источник правды
Источником правды по задачам является SQL-база workflow задач.

## Назначение Google Sheets
Google Sheets используется только как пользовательский dashboard. Лист полностью перезаписывается из новой SQL-базы через `./task sync` или `./task add ... --sync`.

## Основной принцип
Агенты работают не с голым логом, а с четырьмя основными сущностями:
- `tasks` — карточка задачи и ее текущее состояние;
- `task_handoffs` — что сделал модульный агент и что reviewer должен проверить;
- `task_reviews` — verdict reviewer-а по handoff;
- `task_events` — история действий по задаче.

Append-only режим относится к `task_events`, `task_handoffs` и `task_reviews`. Таблица `tasks` является агрегированным текущим состоянием и может обновляться task-системой автоматически.

## Что хранится в SQL
`tasks`:
- `task_id` — стабильный id задачи;
- `module_name` — модуль, к которому относится задача;
- `title` — краткое название задачи;
- `created_by` — кто завел задачу;
- `assigned_agent` — кто отвечает за задачу со стороны модуля;
- `status` — `todo`, `in_progress`, `ready_for_review`, `reviewed`, `done`, `blocked`, `failed`;
- `latest_summary`, `latest_artifacts` — последнее краткое состояние;
- `created_at`, `updated_at`.

`task_handoffs`:
- `source_agent` — модульный агент, который передает задачу;
- `target_agent` — reviewer, который должен проверить;
- `review_type` — `frontend`, `backend`, `db`, `prompt`;
- `summary` — что сделано;
- `implementation_report` — как это устроено и где проверять;
- `checks_required` — что reviewer обязан проверить;
- `artifacts` — URL, файлы, порты, пути;
- `status` — `pending`, `claimed`, `reviewed`.

`task_reviews`:
- `reviewer_agent` — кто проверял;
- `result` — `passed`, `passed_with_notes`, `failed`, `blocked`;
- `summary` — краткий итог review;
- `what_works` — что подтверждено;
- `what_fails` — что не работает;
- `policy_checks` — проверка правил reviewer-а;
- `artifacts` — ссылки, пути, заметки.

## Как работает команда task
Модульный агент:
1. Смотрит свои активные задачи через `./task mine --agent <module_name>`.
2. Ведет задачу через `start`, `progress`, `ready_for_review`, `done`, `blocked`.
3. До финального `done` создает отдельный handoff для каждого reviewer-а через `./task add --action-type handoff ...`.
4. В handoff обязательно пишет:
   - что сделано;
   - где это проверять;
   - что именно reviewer должен проверить;
   - URL, файлы, порты и артефакты.

Reviewer:
1. По команде `task` смотрит свои непроверенные handoff через `./task mine --agent <reviewer_name>`.
2. Берет верхний `pending` handoff.
3. Проверяет handoff по описанию модульного агента и по своим постоянным правилам.
4. Пишет verdict через `./task add --action-type review ...`.

## Рекомендуемые команды
- `./task ensure-db`
- `./task mine --agent <agent_name> --limit 20`
- `./task show --task-id <task_id>`
- `./task list --task-id <task_id> --limit 20`
- `./task add --task-id <task_id> --source-agent <agent> --target-agent <agent> --module-name <module_name> --action-type start --summary "<что начато>" --status in_progress --artifacts "<paths>"`
- `./task add --task-id <task_id> --source-agent <module_agent> --target-agent <reviewer_agent> --module-name <module_name> --action-type handoff --status pending --summary "<что сделано>" --implementation-report "<где и как проверять>" --checks-required "<что reviewer обязан проверить>" --artifacts "<paths_or_urls>"`
- `./task add --task-id <task_id> --source-agent <reviewer_agent> --target-agent <module_name> --module-name <module_name> --action-type review --status reviewed --result <passed|passed_with_notes|failed|blocked> --summary "<итог review>" --what-works "<что работает>" --what-fails "<что не работает>" --policy-checks "<что по правилам прошло или нарушено>" --artifacts "<paths_or_urls>"`
- `./task add --task-id <task_id> --source-agent <module_agent> --target-agent <module_agent> --module-name <module_name> --action-type done --status done --summary "<что завершено>" --artifacts "<paths>"`
- `./task sync`

## Что идет в Google Sheets
Sheets получает dashboard-представление из новой базы:
- `task_id`
- `module_name`
- `task_status`
- `source_agent`
- `target_agent`
- `review_type`
- `handoff_status`
- `review_result`
- `summary`
- `implementation_report`
- `checks_required`
- `policy_checks`
- `artifacts`
- `updated_at`

## Обязательные правила
- агент не должен считать задачу переданной на review, пока не создал handoff в `task_handoffs`;
- reviewer не должен брать задачу из произвольного лога, он обязан брать только свои `pending` handoff;
- reviewer не должен писать общий комментарий вместо structured verdict;
- Google Sheets не редактируется вручную и полностью собирается из новой SQL-базы.
- `prompt_reviewer` является исключением: он не берет задачи из общей reviewer-очереди автоматически и работает только по прямой команде пользователя.
