import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from db.schema import SCHEMA


class RegistryRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def ensure_sources(self, items: list[dict[str, str]]) -> None:
        now = self._now()
        with self._connect() as connection:
            for item in items:
                connection.execute(
                    """
                    INSERT INTO source_status (
                        source_name, status, message, last_sync_at, updated_at
                    )
                    VALUES (?, ?, ?, NULL, ?)
                    ON CONFLICT(source_name) DO UPDATE SET
                        status = excluded.status,
                        message = excluded.message,
                        updated_at = excluded.updated_at
                    """,
                    (item["source_name"], item["status"], item["message"], now),
                )
            connection.commit()

    def list_sources(self) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT source_name, status, message, last_sync_at, updated_at
                FROM source_status
                ORDER BY source_name
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def update_source_status(self, source_name: str, status: str, message: str) -> None:
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE source_status
                SET status = ?, message = ?, last_sync_at = ?, updated_at = ?
                WHERE source_name = ?
                """,
                (status, message, now, now, source_name),
            )
            connection.commit()

    def upsert_file(self, item: dict[str, str | int]) -> None:
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO file_registry (
                    source_name, external_id, file_path, file_name, file_date,
                    status, file_size, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_name, external_id) DO UPDATE SET
                    file_path = excluded.file_path,
                    file_name = excluded.file_name,
                    file_date = excluded.file_date,
                    status = excluded.status,
                    file_size = excluded.file_size,
                    updated_at = excluded.updated_at
                """,
                (
                    item["source_name"],
                    item["external_id"],
                    item["file_path"],
                    item["file_name"],
                    item["file_date"],
                    item["status"],
                    item["file_size"],
                    now,
                    now,
                ),
            )
            connection.commit()

    def list_files(self) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    source_name,
                    external_id,
                    file_path,
                    file_name,
                    file_date,
                    status,
                    file_size,
                    created_at,
                    updated_at
                FROM file_registry
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def add_event(self, action_type: str, status: str, summary: str, artifacts: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO activity_log (action_type, status, summary, artifacts, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (action_type, status, summary, artifacts, self._now()),
            )
            connection.commit()

    def list_events(self, limit: int = 10) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT action_type, status, summary, artifacts, created_at
                FROM activity_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat()
