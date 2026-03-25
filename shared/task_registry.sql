CREATE TABLE IF NOT EXISTS task_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    source_agent TEXT NOT NULL,
    target_agent TEXT NOT NULL,
    module_name TEXT NOT NULL,
    action_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    artifacts TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_task_registry_task_id
    ON task_registry (task_id);

CREATE INDEX IF NOT EXISTS idx_task_registry_target_agent
    ON task_registry (target_agent);

CREATE INDEX IF NOT EXISTS idx_task_registry_module_name
    ON task_registry (module_name);

CREATE INDEX IF NOT EXISTS idx_task_registry_created_at
    ON task_registry (created_at);
