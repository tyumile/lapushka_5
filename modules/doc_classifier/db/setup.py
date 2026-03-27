import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cabinet_id TEXT NOT NULL DEFAULT 'default',
    external_ref TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source_status TEXT NOT NULL,
    recognition_status TEXT NOT NULL,
    classification_status TEXT NOT NULL,
    source_payload TEXT NOT NULL,
    recognized_text TEXT,
    extracted_features TEXT,
    classification_label TEXT,
    classification_reason TEXT,
    classification_confidence REAL,
    error_message TEXT,
    source_module TEXT NOT NULL DEFAULT '',
    source_file_path TEXT NOT NULL DEFAULT '',
    source_file_name TEXT NOT NULL DEFAULT '',
    source_file_size INTEGER NOT NULL DEFAULT 0,
    source_file_date TEXT NOT NULL DEFAULT '',
    source_modified_at TEXT NOT NULL DEFAULT '',
    page_count INTEGER NOT NULL DEFAULT 0,
    source_signature TEXT NOT NULL DEFAULT '',
    structured_data TEXT NOT NULL DEFAULT '',
    processing_notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS module_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cabinet_id TEXT NOT NULL DEFAULT 'default',
    event_type TEXT NOT NULL,
    details TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


DOCUMENT_COLUMNS = {
    "cabinet_id": "TEXT NOT NULL DEFAULT 'default'",
    "source_module": "TEXT NOT NULL DEFAULT ''",
    "source_file_path": "TEXT NOT NULL DEFAULT ''",
    "source_file_name": "TEXT NOT NULL DEFAULT ''",
    "source_file_size": "INTEGER NOT NULL DEFAULT 0",
    "source_file_date": "TEXT NOT NULL DEFAULT ''",
    "source_modified_at": "TEXT NOT NULL DEFAULT ''",
    "page_count": "INTEGER NOT NULL DEFAULT 0",
    "source_signature": "TEXT NOT NULL DEFAULT ''",
    "structured_data": "TEXT NOT NULL DEFAULT ''",
    "processing_notes": "TEXT NOT NULL DEFAULT ''",
}


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(SCHEMA)
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(documents)").fetchall()
        }
        for column_name, definition in DOCUMENT_COLUMNS.items():
            if column_name in columns:
                continue
            connection.execute(f"ALTER TABLE documents ADD COLUMN {column_name} {definition}")
        event_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(module_events)").fetchall()
        }
        if "cabinet_id" not in event_columns:
            connection.execute("ALTER TABLE module_events ADD COLUMN cabinet_id TEXT NOT NULL DEFAULT 'default'")
        connection.commit()
