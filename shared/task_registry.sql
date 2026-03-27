CREATE TABLE IF NOT EXISTS task_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL UNIQUE,
    cabinet_id TEXT NOT NULL DEFAULT 'default',
    module_name TEXT NOT NULL,
    title TEXT NOT NULL,
    created_by TEXT NOT NULL,
    assigned_agent TEXT NOT NULL,
    status TEXT NOT NULL,
    latest_summary TEXT NOT NULL DEFAULT '',
    latest_artifacts TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_assigned_agent
    ON tasks (assigned_agent);

CREATE INDEX IF NOT EXISTS idx_tasks_module_name
    ON tasks (module_name);

CREATE INDEX IF NOT EXISTS idx_tasks_status
    ON tasks (status);

CREATE INDEX IF NOT EXISTS idx_tasks_updated_at
    ON tasks (updated_at);

CREATE TABLE IF NOT EXISTS task_handoffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    cabinet_id TEXT NOT NULL DEFAULT 'default',
    module_name TEXT NOT NULL,
    source_agent TEXT NOT NULL,
    target_agent TEXT NOT NULL,
    review_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    implementation_report TEXT NOT NULL DEFAULT '',
    checks_required TEXT NOT NULL DEFAULT '',
    artifacts TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    claimed_at TEXT NOT NULL DEFAULT '',
    reviewed_at TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
);

CREATE INDEX IF NOT EXISTS idx_task_handoffs_task_id
    ON task_handoffs (task_id);

CREATE INDEX IF NOT EXISTS idx_task_handoffs_target_agent
    ON task_handoffs (target_agent, status);

CREATE INDEX IF NOT EXISTS idx_task_handoffs_created_at
    ON task_handoffs (created_at);

CREATE TABLE IF NOT EXISTS task_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    handoff_id INTEGER NOT NULL,
    cabinet_id TEXT NOT NULL DEFAULT 'default',
    module_name TEXT NOT NULL,
    reviewer_agent TEXT NOT NULL,
    review_type TEXT NOT NULL,
    result TEXT NOT NULL,
    summary TEXT NOT NULL,
    what_works TEXT NOT NULL DEFAULT '',
    what_fails TEXT NOT NULL DEFAULT '',
    policy_checks TEXT NOT NULL DEFAULT '',
    artifacts TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id),
    FOREIGN KEY(handoff_id) REFERENCES task_handoffs(id)
);

CREATE INDEX IF NOT EXISTS idx_task_reviews_task_id
    ON task_reviews (task_id);

CREATE INDEX IF NOT EXISTS idx_task_reviews_handoff_id
    ON task_reviews (handoff_id);

CREATE INDEX IF NOT EXISTS idx_task_reviews_reviewer_agent
    ON task_reviews (reviewer_agent);

CREATE TABLE IF NOT EXISTS task_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    cabinet_id TEXT NOT NULL DEFAULT 'default',
    module_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source_agent TEXT NOT NULL,
    target_agent TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    artifacts TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
);

CREATE INDEX IF NOT EXISTS idx_task_events_task_id
    ON task_events (task_id);

CREATE INDEX IF NOT EXISTS idx_task_events_target_agent
    ON task_events (target_agent);

CREATE INDEX IF NOT EXISTS idx_task_events_created_at
    ON task_events (created_at);

CREATE TABLE IF NOT EXISTS task_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    cabinet_id TEXT NOT NULL DEFAULT 'default',
    source_agent TEXT NOT NULL,
    target_agent TEXT NOT NULL,
    module_name TEXT NOT NULL,
    action_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    artifacts TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
