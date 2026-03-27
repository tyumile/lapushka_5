# Шаблон записи review в workflow-базу

- `task_id`: `<stable_task_id>`
- `source_agent`: `backend_reviewer`
- `target_agent`: `<module_name>`
- `module_name`: `<module_name>`
- `action_type`: `review`
- `summary`: `<короткий итог backend review>`
- `status`: `reviewed`
- `result`: `passed`, `passed_with_notes`, `failed` или `blocked`
- `what_works`: `<что подтверждено>`
- `what_fails`: `<что не работает>`
- `policy_checks`: `<что по backend-правилам прошло или нарушено>`
- `artifacts`: `<пути, id, заметки>`

Команда:

```bash
../../task add --task-id <stable_task_id> \
  --source-agent backend_reviewer \
  --target-agent <module_name> \
  --module-name <module_name> \
  --action-type review \
  --status reviewed \
  --result <passed|passed_with_notes|failed|blocked> \
  --summary "<короткий итог backend review>" \
  --what-works "<что подтверждено>" \
  --what-fails "<что не работает>" \
  --policy-checks "<структура, слои, точки входа, модульность>" \
  --artifacts "<пути, id, заметки>" \
  --sync
```
