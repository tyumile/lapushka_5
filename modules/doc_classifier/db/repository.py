import sqlite3
from pathlib import Path
from typing import Any

from app.models import DocumentRecord
from app.pipeline import classify_document, recognize_text


class DocumentRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def seed_demo_documents(self) -> None:
        with self._connect() as connection:
            existing = connection.execute("SELECT COUNT(*) AS count FROM documents").fetchone()["count"]
            if existing:
                return

            demo_documents = [
                {
                    "external_ref": "SRC-001",
                    "title": "Invoice 2026-03",
                    "source_payload": "Invoice 2026-03 Total payment due 1250 USD. Vendor: Northwind.",
                },
                {
                    "external_ref": "SRC-002",
                    "title": "Supplier Contract Draft",
                    "source_payload": "Draft contract between Alpha LLC and Beta LLC. Agreement terms and obligations.",
                },
                {
                    "external_ref": "SRC-003",
                    "title": "Passport Scan",
                    "source_payload": "Passport ID 4400 123456 Date of birth 1985-07-11 issued by state authority.",
                },
            ]
            for item in demo_documents:
                recognized_text, features = recognize_text(item["source_payload"])
                label, reason, confidence = classify_document(recognized_text)
                connection.execute(
                    """
                    INSERT INTO documents (
                        external_ref,
                        title,
                        source_status,
                        recognition_status,
                        classification_status,
                        source_payload,
                        recognized_text,
                        extracted_features,
                        classification_label,
                        classification_reason,
                        classification_confidence,
                        error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["external_ref"],
                        item["title"],
                        "received",
                        "done",
                        "done" if label != "unknown" else "needs_review",
                        item["source_payload"],
                        recognized_text,
                        features,
                        label,
                        reason,
                        confidence,
                        "",
                    ),
                )
            connection.execute(
                "INSERT INTO module_events (event_type, details) VALUES (?, ?)",
                ("seed_demo_documents", "Initial local documents inserted into the module database"),
            )
            connection.commit()

    def add_module_event(self, event_type: str, details: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO module_events (event_type, details) VALUES (?, ?)",
                (event_type, details),
            )
            connection.commit()

    def list_documents(self) -> list[DocumentRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM documents
                ORDER BY id DESC
                """
            ).fetchall()
        return [DocumentRecord.from_row(row) for row in rows]

    def get_document(self, document_id: int) -> DocumentRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM documents
                WHERE id = ?
                """,
                (document_id,),
            ).fetchone()
        return DocumentRecord.from_row(row) if row else None

    def update_processing_result(
        self,
        document_id: int,
        recognition_status: str,
        classification_status: str,
        recognized_text: str,
        extracted_features: str,
        classification_label: str,
        classification_reason: str,
        classification_confidence: float,
        error_message: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE documents
                SET recognition_status = ?,
                    classification_status = ?,
                    recognized_text = ?,
                    extracted_features = ?,
                    classification_label = ?,
                    classification_reason = ?,
                    classification_confidence = ?,
                    error_message = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    recognition_status,
                    classification_status,
                    recognized_text,
                    extracted_features,
                    classification_label,
                    classification_reason,
                    classification_confidence,
                    error_message,
                    document_id,
                ),
            )
            connection.commit()

    def get_status_counts(self) -> dict[str, Any]:
        with self._connect() as connection:
            total_documents = connection.execute(
                "SELECT COUNT(*) AS count FROM documents"
            ).fetchone()["count"]
            recognition_done = connection.execute(
                "SELECT COUNT(*) AS count FROM documents WHERE recognition_status = 'done'"
            ).fetchone()["count"]
            classification_done = connection.execute(
                "SELECT COUNT(*) AS count FROM documents WHERE classification_status = 'done'"
            ).fetchone()["count"]
            pending_review = connection.execute(
                "SELECT COUNT(*) AS count FROM documents WHERE classification_status = 'needs_review'"
            ).fetchone()["count"]
            last_event = connection.execute(
                """
                SELECT event_type, details, created_at
                FROM module_events
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        return {
            "total_documents": total_documents,
            "recognition_done": recognition_done,
            "classification_done": classification_done,
            "pending_review": pending_review,
            "last_event": dict(last_event) if last_event else None,
        }
