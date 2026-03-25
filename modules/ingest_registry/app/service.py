import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from db.repository import RegistryRepository


LOGGER = logging.getLogger(__name__)


class IngestRegistryService:
    def __init__(self, settings: Settings, repository: RegistryRepository) -> None:
        self.settings = settings
        self.repository = repository

    def bootstrap(self) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        self.settings.bootstrap_dir.mkdir(parents=True, exist_ok=True)
        self.repository.initialize()
        self.repository.ensure_sources(
            [
                {
                    "source_name": "google_drive",
                    "status": "awaiting_setup",
                    "message": "OAuth and remote sync are not configured yet.",
                },
                {
                    "source_name": "yandex_disk",
                    "status": "awaiting_setup",
                    "message": "Token and remote sync are not configured yet.",
                },
                {
                    "source_name": "local_upload",
                    "status": "ready",
                    "message": "Local uploads are available via UI.",
                },
            ]
        )
        self._ensure_bootstrap_file()

    def _ensure_bootstrap_file(self) -> None:
        bootstrap_file = self.settings.bootstrap_dir / "welcome.txt"
        if not bootstrap_file.exists():
            bootstrap_file.write_text(
                "ingest_registry bootstrap file\n"
                "This file proves the local registry is operational.\n",
                encoding="utf-8",
            )
        self.repository.upsert_file(
            {
                "source_name": "local_upload",
                "external_id": "bootstrap:welcome.txt",
                "file_path": str(bootstrap_file.relative_to(self.settings.base_dir)),
                "file_name": bootstrap_file.name,
                "file_date": self._timestamp(datetime.fromtimestamp(bootstrap_file.stat().st_mtime, tz=UTC)),
                "status": "ready",
                "file_size": bootstrap_file.stat().st_size,
            }
        )

    def dashboard(self) -> dict[str, Any]:
        files = self.repository.list_files()
        sources = self.repository.list_sources()
        recent_logs = self.repository.list_events(limit=10)
        return {
            "module_name": self.settings.module_name,
            "host": self.settings.host,
            "port": self.settings.port,
            "db_path": str(self.settings.db_path.relative_to(self.settings.base_dir)),
            "files": files,
            "sources": sources,
            "recent_logs": recent_logs,
            "counts": {
                "files": len(files),
                "sources": len(sources),
                "ready_sources": len([item for item in sources if item["status"] == "ready"]),
            },
        }

    def handle_upload(self, filename: str, payload: bytes) -> None:
        safe_name = Path(filename).name or "uploaded.bin"
        target = self._unique_upload_path(safe_name)
        target.write_bytes(payload)
        stat = target.stat()
        now = self._timestamp(datetime.now(UTC))
        self.repository.upsert_file(
            {
                "source_name": "local_upload",
                "external_id": f"upload:{target.name}",
                "file_path": str(target.relative_to(self.settings.base_dir)),
                "file_name": target.name,
                "file_date": now,
                "status": "uploaded",
                "file_size": stat.st_size,
            }
        )
        self.repository.update_source_status(
            "local_upload",
            "ready",
            "Last upload stored successfully.",
        )
        self.repository.add_event(
            action_type="upload",
            status="done",
            summary=f"Stored local file {target.name}",
            artifacts=str(target.relative_to(self.settings.base_dir)),
        )
        LOGGER.info("Stored local upload %s", target)

    def run_sync_stub(self, source_name: str) -> None:
        now = self._timestamp(datetime.now(UTC))
        if source_name == "google_drive":
            status = "idle"
            message = f"Stub sync executed at {now}. Remote connector will be added later."
        elif source_name == "yandex_disk":
            status = "idle"
            message = f"Stub sync executed at {now}. Remote connector will be added later."
        else:
            status = "ready"
            message = f"Local source checked at {now}."
        self.repository.update_source_status(source_name, status, message)
        self.repository.add_event(
            action_type="sync_stub",
            status="done",
            summary=f"Executed stub sync for {source_name}",
            artifacts=source_name,
        )
        LOGGER.info("Executed sync stub for %s", source_name)

    def _unique_upload_path(self, filename: str) -> Path:
        target = self.settings.upload_dir / filename
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix
        counter = 1
        while True:
            candidate = self.settings.upload_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    @staticmethod
    def _timestamp(value: datetime) -> str:
        return value.astimezone(UTC).replace(microsecond=0).isoformat()
