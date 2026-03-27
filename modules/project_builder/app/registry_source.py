import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RegistryDocument:
    id: int
    cabinet_id: str
    source_id: int
    source_name: str
    source_title: str
    source_type: str
    source_url: str
    external_id: str
    file_path: str
    absolute_file_path: str
    file_name: str
    file_date: str
    created_at_remote: str
    modified_at_remote: str
    page_count: int | None
    status: str
    file_size: int

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


class IngestRegistryReader:
    def __init__(self, db_path: Path, base_dir: Path) -> None:
        self.db_path = db_path
        self.base_dir = base_dir

    def get_document(self, document_id: int, cabinet_id: str = "default") -> RegistryDocument | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    file_registry.id,
                    file_registry.cabinet_id,
                    file_registry.source_id,
                    file_registry.source_name,
                    COALESCE(sources.title, file_registry.source_name) AS source_title,
                    file_registry.source_type,
                    COALESCE(sources.source_url, '') AS source_url,
                    file_registry.external_id,
                    file_registry.file_path,
                    file_registry.file_name,
                    file_registry.file_date,
                    COALESCE(file_registry.created_at_remote, '') AS created_at_remote,
                    COALESCE(file_registry.modified_at_remote, '') AS modified_at_remote,
                    file_registry.page_count,
                    file_registry.status,
                    file_registry.file_size
                FROM file_registry
                LEFT JOIN sources ON sources.id = file_registry.source_id
                WHERE file_registry.id = ? AND file_registry.is_deleted = 0 AND file_registry.cabinet_id = ?
                """,
                (document_id, cabinet_id),
            ).fetchone()
        return self._row_to_document(row) if row else None

    def list_documents(
        self,
        cabinet_id: str = "default",
        source_ids: list[int] | None = None,
        document_ids: list[int] | None = None,
    ) -> list[RegistryDocument]:
        clauses = ["file_registry.is_deleted = 0", "file_registry.status = 'ready'", "file_registry.cabinet_id = ?"]
        params: list[object] = [cabinet_id]
        if source_ids:
            placeholders = ", ".join("?" for _ in source_ids)
            clauses.append(f"file_registry.source_id IN ({placeholders})")
            params.extend(source_ids)
        if document_ids:
            placeholders = ", ".join("?" for _ in document_ids)
            clauses.append(f"file_registry.id IN ({placeholders})")
            params.extend(document_ids)
        query = f"""
            SELECT
                file_registry.id,
                file_registry.cabinet_id,
                file_registry.source_id,
                file_registry.source_name,
                COALESCE(sources.title, file_registry.source_name) AS source_title,
                file_registry.source_type,
                COALESCE(sources.source_url, '') AS source_url,
                file_registry.external_id,
                file_registry.file_path,
                file_registry.file_name,
                file_registry.file_date,
                COALESCE(file_registry.created_at_remote, '') AS created_at_remote,
                COALESCE(file_registry.modified_at_remote, '') AS modified_at_remote,
                file_registry.page_count,
                file_registry.status,
                file_registry.file_size
            FROM file_registry
            LEFT JOIN sources ON sources.id = file_registry.source_id
            WHERE {' AND '.join(clauses)}
            ORDER BY file_registry.updated_at DESC, file_registry.id DESC
        """
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_document(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def _row_to_document(self, row: sqlite3.Row) -> RegistryDocument:
        absolute_path = Path(row["file_path"])
        if not absolute_path.is_absolute():
            absolute_path = self.base_dir / absolute_path
        return RegistryDocument(
            id=int(row["id"]),
            cabinet_id=str(row["cabinet_id"] or "default"),
            source_id=int(row["source_id"]),
            source_name=str(row["source_name"]),
            source_title=str(row["source_title"]),
            source_type=str(row["source_type"]),
            source_url=str(row["source_url"]),
            external_id=str(row["external_id"]),
            file_path=str(row["file_path"]),
            absolute_file_path=str(absolute_path.resolve()),
            file_name=str(row["file_name"]),
            file_date=str(row["file_date"]),
            created_at_remote=str(row["created_at_remote"]),
            modified_at_remote=str(row["modified_at_remote"]),
            page_count=int(row["page_count"]) if row["page_count"] is not None else None,
            status=str(row["status"]),
            file_size=int(row["file_size"] or 0),
        )
