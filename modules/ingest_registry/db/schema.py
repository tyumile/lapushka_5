SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cabinet_id TEXT NOT NULL DEFAULT 'default',
    source_type TEXT NOT NULL,
    title TEXT NOT NULL,
    source_url TEXT NOT NULL DEFAULT '',
    added_at TEXT NOT NULL,
    last_sync_at TEXT,
    sync_status TEXT NOT NULL DEFAULT 'idle',
    sync_message TEXT NOT NULL DEFAULT '',
    last_total_files INTEGER NOT NULL DEFAULT 0,
    last_added_files INTEGER NOT NULL DEFAULT 0,
    last_changed_files INTEGER NOT NULL DEFAULT 0,
    last_deleted_files INTEGER NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_type_url
ON sources (cabinet_id, source_type, source_url);

CREATE TABLE IF NOT EXISTS file_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cabinet_id TEXT NOT NULL DEFAULT 'default',
    source_id INTEGER,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT '',
    external_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_date TEXT NOT NULL,
    created_at_remote TEXT,
    modified_at_remote TEXT,
    page_count INTEGER,
    status TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    first_seen_at TEXT,
    last_seen_at TEXT,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_file_registry_source_external
ON file_registry (cabinet_id, source_id, external_id);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cabinet_id TEXT NOT NULL DEFAULT 'default',
    action_type TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    artifacts TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
