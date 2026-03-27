import json
import sqlite3
from pathlib import Path
from typing import Any

from app.models import DocumentRecord
from app.registry_source import RegistryFileRecord


class DocumentRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def delete_legacy_demo_documents(self, cabinet_id: str = "default") -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM documents WHERE cabinet_id = ? AND external_ref LIKE 'SRC-%'",
                (cabinet_id,),
            )
            connection.commit()

    def sync_registry_documents(self, files: list[RegistryFileRecord], cabinet_id: str = "default") -> dict[str, int]:
        stats = {"added": 0, "updated": 0, "unchanged": 0, "deleted": 0}
        with self._connect() as connection:
            existing_rows = connection.execute(
                "SELECT id, external_ref, source_signature FROM documents WHERE cabinet_id = ?",
                (cabinet_id,),
            ).fetchall()
            existing = {row["external_ref"]: dict(row) for row in existing_rows}
            actual_refs = {item.external_ref for item in files}
            for external_ref in list(existing):
                if not external_ref.startswith("ingest_registry:"):
                    continue
                if external_ref in actual_refs:
                    continue
                connection.execute(
                    "DELETE FROM documents WHERE external_ref = ? AND cabinet_id = ?",
                    (external_ref, cabinet_id),
                )
                stats["deleted"] += 1
                existing.pop(external_ref, None)
            for item in files:
                current = existing.get(item.external_ref)
                source_payload = json.dumps(
                    {
                        "source_name": item.source_name,
                        "source_type": item.source_type,
                        "source_url": item.source_url,
                        "source_external_id": item.source_external_id,
                        "relative_file_path": item.relative_file_path,
                        "status": item.status,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                if current is None:
                    connection.execute(
                        """
                        INSERT INTO documents (
                            external_ref,
                            cabinet_id,
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
                            error_message,
                            source_module,
                            source_file_path,
                            source_file_name,
                            source_file_size,
                            source_file_date,
                            source_modified_at,
                            page_count,
                            source_signature,
                            structured_data,
                            processing_notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.external_ref,
                            cabinet_id,
                            item.title,
                            "received",
                            "queued",
                            "queued",
                            source_payload,
                            "",
                            "",
                            "",
                            "",
                            0.0,
                            "",
                            item.source_module,
                            item.relative_file_path,
                            item.file_name,
                            item.file_size,
                            item.file_date,
                            item.modified_at,
                            item.page_count,
                            item.source_signature,
                            "",
                            "",
                        ),
                    )
                    stats["added"] += 1
                    continue

                if current["source_signature"] == item.source_signature:
                    stats["unchanged"] += 1
                    continue

                connection.execute(
                    """
                    UPDATE documents
                    SET title = ?,
                        source_status = ?,
                        recognition_status = 'queued',
                        classification_status = 'queued',
                        source_payload = ?,
                        source_module = ?,
                        source_file_path = ?,
                        source_file_name = ?,
                        source_file_size = ?,
                        source_file_date = ?,
                        source_modified_at = ?,
                        page_count = ?,
                        source_signature = ?,
                        error_message = '',
                        processing_notes = '',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE external_ref = ? AND cabinet_id = ?
                    """,
                    (
                        item.title,
                        "updated",
                        source_payload,
                        item.source_module,
                        item.relative_file_path,
                        item.file_name,
                        item.file_size,
                        item.file_date,
                        item.modified_at,
                        item.page_count,
                        item.source_signature,
                        item.external_ref,
                        cabinet_id,
                    ),
                )
                stats["updated"] += 1
            connection.commit()
        return stats

    def list_documents(self, cabinet_id: str = "default") -> list[DocumentRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM documents
                WHERE cabinet_id = ?
                ORDER BY updated_at DESC, id DESC
                """,
                (cabinet_id,),
            ).fetchall()
        return [DocumentRecord.from_row(row) for row in rows]

    def get_document(self, document_id: int, cabinet_id: str = "default") -> DocumentRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM documents
                WHERE id = ? AND cabinet_id = ?
                """,
                (document_id, cabinet_id),
            ).fetchone()
        return DocumentRecord.from_row(row) if row else None

    def list_documents_for_processing(self, cabinet_id: str = "default") -> list[DocumentRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM documents
                WHERE cabinet_id = ?
                  AND (
                       recognition_status IN ('queued', 'failed', 'empty')
                   OR classification_status IN ('queued', 'failed', 'needs_review')
                  )
                ORDER BY id ASC
                """,
                (cabinet_id,),
            ).fetchall()
        return [DocumentRecord.from_row(row) for row in rows]

    def reset_processing_documents(self, cabinet_id: str = "default") -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE documents
                SET recognition_status = 'queued',
                    classification_status = 'queued',
                    updated_at = CURRENT_TIMESTAMP
                WHERE cabinet_id = ?
                  AND (recognition_status = 'processing'
                   OR classification_status = 'processing')
                """
                ,
                (cabinet_id,),
            )
            connection.commit()
        return int(cursor.rowcount or 0)

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
        structured_data: str,
        processing_notes: str,
        cabinet_id: str = "default",
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
                    structured_data = ?,
                    processing_notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND cabinet_id = ?
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
                    structured_data,
                    processing_notes,
                    document_id,
                    cabinet_id,
                ),
            )
            connection.commit()

    def mark_document_processing(self, document_id: int, cabinet_id: str = "default") -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE documents
                SET recognition_status = 'processing',
                    classification_status = 'processing',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND cabinet_id = ?
                """,
                (document_id, cabinet_id),
            )
            connection.commit()

    def add_module_event(self, event_type: str, details: str, cabinet_id: str = "default") -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO module_events (cabinet_id, event_type, details) VALUES (?, ?, ?)",
                (cabinet_id, event_type, details),
            )
            connection.commit()

    def get_status_counts(self, cabinet_id: str = "default") -> dict[str, Any]:
        with self._connect() as connection:
            total_documents = connection.execute(
                "SELECT COUNT(*) AS count FROM documents WHERE cabinet_id = ?",
                (cabinet_id,),
            ).fetchone()["count"]
            recognition_done = connection.execute(
                "SELECT COUNT(*) AS count FROM documents WHERE cabinet_id = ? AND recognition_status = 'done'",
                (cabinet_id,),
            ).fetchone()["count"]
            classification_done = connection.execute(
                "SELECT COUNT(*) AS count FROM documents WHERE cabinet_id = ? AND classification_status = 'done'",
                (cabinet_id,),
            ).fetchone()["count"]
            pending_review = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM documents
                WHERE cabinet_id = ?
                  AND (classification_status != 'done'
                   OR recognition_status NOT IN ('done', 'empty')
                  )
                """,
                (cabinet_id,),
            ).fetchone()["count"]
            last_event = connection.execute(
                """
                SELECT event_type, details, created_at
                FROM module_events
                WHERE cabinet_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (cabinet_id,),
            ).fetchone()
        return {
            "total_documents": total_documents,
            "recognition_done": recognition_done,
            "classification_done": classification_done,
            "pending_review": pending_review,
            "last_event": dict(last_event) if last_event else None,
        }

    def get_working_document_groups(self, cabinet_id: str = "default") -> list[dict[str, Any]]:
        groups: dict[str, dict[str, Any]] = {}
        for document in self.list_documents(cabinet_id=cabinet_id):
            label = document.classification_label or "other_working_document"
            title = _title_for_group(label)
            group = groups.setdefault(
                label,
                {"key": label, "title": title, "documents": []},
            )
            group["documents"].append(document)
        return list(groups.values())


def _title_for_group(label: str) -> str:
    mapping = {
        "quality_document": "Документы качества",
        "project_document": "Проектная документация",
        "estimate_document": "Сметная документация",
        "order_document": "Приказы",
        "work_log": "Журналы работ",
        "act_document": "Акты",
        "as_built_scheme": "Исполнительные схемы",
        "test_report": "Протоколы и отчеты испытаний",
        "permit_document": "Разрешительные документы",
        "other_working_document": "Прочая рабочая документация",
    }
    return mapping.get(label, "Прочая рабочая документация")
