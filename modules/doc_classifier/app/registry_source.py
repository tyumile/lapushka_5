import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RegistryFileRecord:
    cabinet_id: str
    external_ref: str
    source_external_id: str
    title: str
    source_module: str
    source_name: str
    source_type: str
    source_url: str
    file_name: str
    relative_file_path: str
    absolute_file_path: Path
    file_size: int
    file_date: str
    modified_at: str
    page_count: int
    status: str
    source_signature: str


class IngestRegistryReader:
    def __init__(self, db_path: Path, base_dir: Path) -> None:
        self.db_path = db_path
        self.base_dir = base_dir

    def list_ready_files(self, cabinet_id: str = "default") -> list[RegistryFileRecord]:
        if not self.db_path.exists():
            return []
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT
                    file_registry.source_name,
                    file_registry.cabinet_id,
                    file_registry.source_type,
                    COALESCE(sources.source_url, '') AS source_url,
                    file_registry.external_id,
                    file_registry.file_name,
                    file_registry.file_path,
                    file_registry.file_date,
                    file_registry.modified_at_remote,
                    file_registry.page_count,
                    file_registry.status,
                    file_registry.file_size,
                    file_registry.updated_at
                FROM file_registry
                LEFT JOIN sources ON sources.id = file_registry.source_id
                WHERE file_registry.is_deleted = 0
                  AND file_registry.cabinet_id = ?
                ORDER BY file_registry.updated_at DESC, file_registry.id DESC
                """,
                (cabinet_id,),
            ).fetchall()
        result: list[RegistryFileRecord] = []
        for row in rows:
            relative_path = row["file_path"] or ""
            absolute_path = self.base_dir / relative_path
            file_size = int(row["file_size"] or 0)
            modified_at = row["modified_at_remote"] or row["updated_at"] or ""
            source_signature = f"{relative_path}|{file_size}|{modified_at}"
            result.append(
                RegistryFileRecord(
                    cabinet_id=row["cabinet_id"] or "default",
                    external_ref=f"ingest_registry:{row['cabinet_id'] or 'default'}:{row['source_name']}:{row['external_id']}",
                    source_external_id=row["external_id"] or "",
                    title=row["file_name"] or row["external_id"] or "Документ",
                    source_module="ingest_registry",
                    source_name=row["source_name"] or "",
                    source_type=row["source_type"] or "",
                    source_url=row["source_url"] or "",
                    file_name=row["file_name"] or "",
                    relative_file_path=relative_path,
                    absolute_file_path=absolute_path,
                    file_size=file_size,
                    file_date=row["file_date"] or "",
                    modified_at=modified_at,
                    page_count=int(row["page_count"] or 0),
                    status=row["status"] or "",
                    source_signature=source_signature,
                )
            )
        return result

    def get_file_by_external_ref(self, external_ref: str, cabinet_id: str = "default") -> RegistryFileRecord | None:
        for item in self.list_ready_files(cabinet_id=cabinet_id):
            if item.external_ref == external_ref:
                return item
        return None
