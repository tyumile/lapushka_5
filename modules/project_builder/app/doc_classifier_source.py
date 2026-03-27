import json
import sqlite3
from pathlib import Path
from typing import Any


class DocClassifierReader:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def find_best_document_snapshot(self, file_name: str, cabinet_id: str = "default") -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    source_file_name,
                    source_file_path,
                    recognition_status,
                    classification_status,
                    recognized_text,
                    structured_data,
                    classification_label,
                    classification_reason,
                    classification_confidence,
                    processing_notes,
                    updated_at
                FROM documents
                WHERE source_file_name = ? AND cabinet_id = ?
                ORDER BY
                    CASE recognition_status
                        WHEN 'done' THEN 0
                        WHEN 'empty' THEN 1
                        ELSE 2
                    END,
                    CASE classification_status
                        WHEN 'done' THEN 0
                        ELSE 1
                    END,
                    LENGTH(COALESCE(recognized_text, '')) DESC,
                    updated_at DESC
                LIMIT 1
                """,
                (file_name, cabinet_id),
            ).fetchone()
        if not row:
            return None
        payload = dict(row)
        structured = payload.get("structured_data") or ""
        if structured:
            try:
                payload["structured_data"] = json.loads(structured)
            except json.JSONDecodeError:
                payload["structured_data"] = {}
        else:
            payload["structured_data"] = {}
        return payload

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection
