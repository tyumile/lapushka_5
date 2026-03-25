SCHEMA = """
CREATE TABLE IF NOT EXISTS source_status (
    source_name TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    last_sync_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS file_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    external_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_date TEXT NOT NULL,
    status TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_name, external_id)
);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    artifacts TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
