import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from db.schema import SCHEMA


class RegistryRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            self._rebuild_file_registry_if_needed(connection)
            connection.executescript(SCHEMA)
            self._ensure_columns(connection)
            self._migrate_legacy_rows(connection)
            connection.commit()
        self.ensure_local_source()

    def ensure_local_source(self, cabinet_id: str = "default") -> int:
        now = self._now()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id FROM sources
                WHERE cabinet_id = ? AND source_type = 'local_upload' AND source_url = ''
                """,
                (cabinet_id,),
            ).fetchone()
            if row:
                return int(row["id"])
            cursor = connection.execute(
                """
                INSERT INTO sources (
                    cabinet_id, source_type, title, source_url, added_at, sync_status, sync_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cabinet_id,
                    "local_upload",
                    "Локальное хранилище",
                    "",
                    now,
                    "ready",
                    "Локальные файлы готовы к просмотру и загрузке.",
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def add_source(self, source_type: str, source_url: str, title: str, cabinet_id: str = "default") -> int:
        now = self._now()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id FROM sources
                WHERE cabinet_id = ? AND source_type = ? AND source_url = ?
                """,
                (cabinet_id, source_type, source_url),
            ).fetchone()
            if row:
                connection.execute(
                    """
                    UPDATE sources
                    SET title = ?
                    WHERE id = ?
                    """,
                    (title, row["id"]),
                )
                connection.commit()
                return int(row["id"])
            cursor = connection.execute(
                """
                INSERT INTO sources (
                    cabinet_id, source_type, title, source_url, added_at, sync_status, sync_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (cabinet_id, source_type, title, source_url, now, "idle", "Источник добавлен, синхронизация еще не запускалась."),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def list_sources(self, cabinet_id: str = "default") -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    cabinet_id,
                    source_type,
                    title,
                    source_url,
                    added_at,
                    last_sync_at,
                    sync_status,
                    sync_message,
                    last_total_files,
                    last_added_files,
                    last_changed_files,
                    last_deleted_files
                FROM sources
                WHERE cabinet_id = ?
                ORDER BY CASE WHEN source_type = 'local_upload' THEN 0 ELSE 1 END, added_at DESC, id DESC
                """,
                (cabinet_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_source(self, source_id: int, cabinet_id: str = "default") -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    cabinet_id,
                    source_type,
                    title,
                    source_url,
                    added_at,
                    last_sync_at,
                    sync_status,
                    sync_message,
                    last_total_files,
                    last_added_files,
                    last_changed_files,
                    last_deleted_files
                FROM sources
                WHERE id = ? AND cabinet_id = ?
                """,
                (source_id, cabinet_id),
            ).fetchone()
        return dict(row) if row else None

    def mark_sync_failed(self, source_id: int, message: str, cabinet_id: str = "default") -> None:
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE sources
                SET sync_status = ?, sync_message = ?, last_sync_at = ?
                WHERE id = ? AND cabinet_id = ?
                """,
                ("failed", message, now, source_id, cabinet_id),
            )
            connection.commit()

    def update_source_sync_summary(
        self,
        source_id: int,
        sync_message: str,
        stats: dict[str, int],
        cabinet_id: str = "default",
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE sources
                SET
                    sync_message = ?,
                    last_total_files = ?,
                    last_added_files = ?,
                    last_changed_files = ?,
                    last_deleted_files = ?
                WHERE id = ? AND cabinet_id = ?
                """,
                (
                    sync_message,
                    stats["total"],
                    stats["added"],
                    stats["changed"],
                    stats["deleted"],
                    source_id,
                    cabinet_id,
                ),
            )
            connection.commit()

    def sync_files(
        self,
        source_id: int,
        source_type: str,
        title: str,
        source_url: str,
        files: list[dict[str, Any]],
        sync_message: str,
        cabinet_id: str = "default",
    ) -> dict[str, int]:
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE sources
                SET title = ?, source_url = ?
                WHERE id = ? AND cabinet_id = ?
                """,
                (title, source_url, source_id, cabinet_id),
            )
            existing_rows = connection.execute(
                """
                SELECT
                    id,
                    external_id,
                    file_path,
                    file_name,
                    file_size,
                    page_count,
                    created_at_remote,
                    modified_at_remote,
                    is_deleted,
                    first_seen_at
                FROM file_registry
                WHERE source_id = ? AND cabinet_id = ?
                """,
                (source_id, cabinet_id),
            ).fetchall()
            existing = {str(row["external_id"]): dict(row) for row in existing_rows}

            seen_ids: set[str] = set()
            added = 0
            changed = 0
            for item in files:
                external_id = str(item["external_id"])
                seen_ids.add(external_id)
                current = existing.get(external_id)
                file_size = int(item["file_size"] or 0)
                payload = (
                    cabinet_id,
                    source_id,
                    title,
                    source_type,
                    external_id,
                    str(item["file_path"]),
                    str(item["file_name"]),
                    str(item["created_at"] or item["modified_at"] or now),
                    item["created_at"],
                    item["modified_at"],
                    item["page_count"],
                    "ready",
                    file_size,
                    (current or {}).get("first_seen_at") or now,
                    now,
                    0,
                    now,
                    now,
                )
                connection.execute(
                    """
                    INSERT INTO file_registry (
                        cabinet_id,
                        source_id,
                        source_name,
                        source_type,
                        external_id,
                        file_path,
                        file_name,
                        file_date,
                        created_at_remote,
                        modified_at_remote,
                        page_count,
                        status,
                        file_size,
                        first_seen_at,
                        last_seen_at,
                        is_deleted,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(cabinet_id, source_id, external_id) DO UPDATE SET
                        source_name = excluded.source_name,
                        source_type = excluded.source_type,
                        file_path = excluded.file_path,
                        file_name = excluded.file_name,
                        file_date = excluded.file_date,
                        created_at_remote = excluded.created_at_remote,
                        modified_at_remote = excluded.modified_at_remote,
                        page_count = excluded.page_count,
                        status = excluded.status,
                        file_size = excluded.file_size,
                        last_seen_at = excluded.last_seen_at,
                        is_deleted = excluded.is_deleted,
                        updated_at = excluded.updated_at
                    """,
                    payload,
                )
                if not current:
                    added += 1
                    continue
                if self._file_changed(current, item):
                    changed += 1

            deleted = 0
            for external_id, row in existing.items():
                if external_id in seen_ids or int(row["is_deleted"] or 0) == 1:
                    continue
                connection.execute(
                    """
                    UPDATE file_registry
                    SET status = ?, is_deleted = 1, updated_at = ?
                    WHERE id = ? AND cabinet_id = ?
                    """,
                    ("deleted", now, row["id"], cabinet_id),
                )
                deleted += 1

            total = len(files)
            connection.execute(
                """
                UPDATE sources
                SET
                    title = ?,
                    source_url = ?,
                    last_sync_at = ?,
                    sync_status = ?,
                    sync_message = ?,
                    last_total_files = ?,
                    last_added_files = ?,
                    last_changed_files = ?,
                    last_deleted_files = ?
                WHERE id = ? AND cabinet_id = ?
                """,
                (
                    title,
                    source_url,
                    now,
                    "ready",
                    sync_message,
                    total,
                    added,
                    changed,
                    deleted,
                    source_id,
                    cabinet_id,
                ),
            )
            connection.commit()
        return {
            "total": total,
            "added": added,
            "changed": changed,
            "deleted": deleted,
        }

    def upsert_file(self, item: dict[str, Any]) -> None:
        now = self._now()
        source_id = int(item["source_id"])
        cabinet_id = str(item.get("cabinet_id") or "default")
        with self._connect() as connection:
            current = connection.execute(
                """
                SELECT first_seen_at
                FROM file_registry
                WHERE cabinet_id = ? AND source_id = ? AND external_id = ?
                """,
                (cabinet_id, source_id, item["external_id"]),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO file_registry (
                    cabinet_id,
                    source_id,
                    source_name,
                    source_type,
                    external_id,
                    file_path,
                    file_name,
                    file_date,
                    created_at_remote,
                    modified_at_remote,
                    page_count,
                    status,
                    file_size,
                    first_seen_at,
                    last_seen_at,
                    is_deleted,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cabinet_id, source_id, external_id) DO UPDATE SET
                    source_name = excluded.source_name,
                    source_type = excluded.source_type,
                    file_path = excluded.file_path,
                    file_name = excluded.file_name,
                    file_date = excluded.file_date,
                    created_at_remote = excluded.created_at_remote,
                    modified_at_remote = excluded.modified_at_remote,
                    page_count = excluded.page_count,
                    status = excluded.status,
                    file_size = excluded.file_size,
                    last_seen_at = excluded.last_seen_at,
                    is_deleted = excluded.is_deleted,
                    updated_at = excluded.updated_at
                """,
                (
                    cabinet_id,
                    source_id,
                    item["source_name"],
                    item["source_type"],
                    item["external_id"],
                    item["file_path"],
                    item["file_name"],
                    item["file_date"],
                    item.get("created_at_remote"),
                    item.get("modified_at_remote"),
                    item.get("page_count"),
                    item["status"],
                    item["file_size"],
                    current["first_seen_at"] if current else now,
                    now,
                    0,
                    now,
                    now,
                ),
            )
            connection.commit()

    def list_files(self, cabinet_id: str = "default") -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    file_registry.id,
                    file_registry.cabinet_id,
                    file_registry.source_id,
                    COALESCE(sources.title, file_registry.source_name) AS source_name,
                    file_registry.source_type,
                    file_registry.external_id,
                    file_registry.file_path,
                    file_registry.file_name,
                    file_registry.file_date,
                    file_registry.created_at_remote,
                    file_registry.modified_at_remote,
                    file_registry.page_count,
                    file_registry.status,
                    file_registry.file_size,
                    file_registry.created_at,
                    file_registry.updated_at,
                    sources.source_url
                FROM file_registry
                LEFT JOIN sources ON sources.id = file_registry.source_id
                WHERE file_registry.is_deleted = 0
                  AND file_registry.cabinet_id = ?
                ORDER BY file_registry.updated_at DESC, file_registry.id DESC
                """,
                (cabinet_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_event(self, action_type: str, status: str, summary: str, artifacts: str, cabinet_id: str = "default") -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO activity_log (cabinet_id, action_type, status, summary, artifacts, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (cabinet_id, action_type, status, summary, artifacts, self._now()),
            )
            connection.commit()

    def list_events(self, limit: int = 10, cabinet_id: str = "default") -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT cabinet_id, action_type, status, summary, artifacts, created_at
                FROM activity_log
                WHERE cabinet_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (cabinet_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_columns(self, connection: sqlite3.Connection) -> None:
        self._ensure_table_column(connection, "sources", "cabinet_id", "TEXT NOT NULL DEFAULT 'default'")
        self._ensure_table_column(connection, "sources", "source_type", "TEXT NOT NULL DEFAULT ''")
        self._ensure_table_column(connection, "sources", "title", "TEXT NOT NULL DEFAULT ''")
        self._ensure_table_column(connection, "sources", "source_url", "TEXT NOT NULL DEFAULT ''")
        self._ensure_table_column(connection, "sources", "added_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_table_column(connection, "sources", "last_sync_at", "TEXT")
        self._ensure_table_column(connection, "sources", "sync_status", "TEXT NOT NULL DEFAULT 'idle'")
        self._ensure_table_column(connection, "sources", "sync_message", "TEXT NOT NULL DEFAULT ''")
        self._ensure_table_column(connection, "sources", "last_total_files", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_table_column(connection, "sources", "last_added_files", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_table_column(connection, "sources", "last_changed_files", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_table_column(connection, "sources", "last_deleted_files", "INTEGER NOT NULL DEFAULT 0")

        self._ensure_table_column(connection, "file_registry", "cabinet_id", "TEXT NOT NULL DEFAULT 'default'")
        self._ensure_table_column(connection, "file_registry", "source_id", "INTEGER")
        self._ensure_table_column(connection, "file_registry", "source_type", "TEXT NOT NULL DEFAULT ''")
        self._ensure_table_column(connection, "file_registry", "created_at_remote", "TEXT")
        self._ensure_table_column(connection, "file_registry", "modified_at_remote", "TEXT")
        self._ensure_table_column(connection, "file_registry", "page_count", "INTEGER")
        self._ensure_table_column(connection, "file_registry", "first_seen_at", "TEXT")
        self._ensure_table_column(connection, "file_registry", "last_seen_at", "TEXT")
        self._ensure_table_column(connection, "file_registry", "is_deleted", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_table_column(connection, "activity_log", "cabinet_id", "TEXT NOT NULL DEFAULT 'default'")
        connection.execute("DROP INDEX IF EXISTS idx_sources_type_url")
        connection.execute("DROP INDEX IF EXISTS idx_file_registry_source_external")
        connection.execute("CREATE UNIQUE INDEX idx_sources_type_url ON sources (cabinet_id, source_type, source_url)")
        connection.execute("CREATE UNIQUE INDEX idx_file_registry_source_external ON file_registry (cabinet_id, source_id, external_id)")

    def _rebuild_file_registry_if_needed(self, connection: sqlite3.Connection) -> None:
        indexes = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='file_registry'"
            ).fetchall()
        }
        if "sqlite_autoindex_file_registry_1" not in indexes:
            return
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS file_registry_v2 (
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
            )
            """
        )
        connection.execute(
            """
            INSERT INTO file_registry_v2 (
                id,
                cabinet_id,
                source_id,
                source_name,
                source_type,
                external_id,
                file_path,
                file_name,
                file_date,
                created_at_remote,
                modified_at_remote,
                page_count,
                status,
                file_size,
                first_seen_at,
                last_seen_at,
                is_deleted,
                created_at,
                updated_at
            )
            SELECT
                id,
                'default',
                source_id,
                source_name,
                source_type,
                external_id,
                file_path,
                file_name,
                file_date,
                created_at_remote,
                modified_at_remote,
                page_count,
                status,
                file_size,
                first_seen_at,
                last_seen_at,
                is_deleted,
                created_at,
                updated_at
            FROM file_registry
            """
        )
        connection.execute("DROP TABLE file_registry")
        connection.execute("ALTER TABLE file_registry_v2 RENAME TO file_registry")

    def _migrate_legacy_rows(self, connection: sqlite3.Connection) -> None:
        connection.execute("DROP TABLE IF EXISTS source_status")
        connection.execute(
            """
            UPDATE file_registry
            SET is_deleted = 1, status = 'migrated_legacy', updated_at = ?
            WHERE source_id IS NULL
              AND source_name IN ('local_upload', 'google_drive', 'yandex_disk')
            """,
            (self._now(),),
        )
        connection.execute(
            """
            UPDATE file_registry
            SET source_name = COALESCE(
                (SELECT title FROM sources WHERE sources.id = file_registry.source_id),
                source_name
            )
            WHERE source_id IS NOT NULL
            """
        )
        connection.execute("UPDATE sources SET cabinet_id = COALESCE(NULLIF(cabinet_id, ''), 'default')")
        connection.execute("UPDATE file_registry SET cabinet_id = COALESCE(NULLIF(cabinet_id, ''), 'default')")
        connection.execute("UPDATE activity_log SET cabinet_id = COALESCE(NULLIF(cabinet_id, ''), 'default')")

    def _ensure_table_column(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        definition: str,
    ) -> None:
        columns = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name in columns:
            return
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    @staticmethod
    def _file_changed(current: dict[str, Any], item: dict[str, Any]) -> bool:
        return any(
            [
                current.get("file_path") != item["file_path"],
                current.get("file_name") != item["file_name"],
                int(current.get("file_size") or 0) != int(item["file_size"] or 0),
                current.get("page_count") != item.get("page_count"),
                current.get("created_at_remote") != item.get("created_at"),
                current.get("modified_at_remote") != item.get("modified_at"),
                int(current.get("is_deleted") or 0) == 1,
            ]
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat()
