import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS module_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    details TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(SCHEMA)
