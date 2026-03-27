import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from app.connectors import (
    GoogleDrivePublicClient,
    LocalStorageClient,
    RemoteFile,
    SyncError,
    YandexDiskPublicClient,
    count_document_pages_from_path,
)
from db.repository import RegistryRepository


LOGGER = logging.getLogger(__name__)


class IngestRegistryService:
    def __init__(self, settings: Settings, repository: RegistryRepository) -> None:
        self.settings = settings
        self.repository = repository
        self.local_client = LocalStorageClient()
        self.google_client = GoogleDrivePublicClient()
        self.yandex_client = YandexDiskPublicClient()

    def bootstrap(self) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        self.settings.bootstrap_dir.mkdir(parents=True, exist_ok=True)
        self.repository.initialize()
        self._ensure_bootstrap_file()
        self._cabinet_upload_dir("default").mkdir(parents=True, exist_ok=True)
        self.sync_source(self.repository.ensure_local_source("default"), cabinet_id="default")

    def dashboard(self, source_filter: str = "all", cabinet_id: str = "default") -> dict[str, Any]:
        files = self._visible_files(self.repository.list_files(cabinet_id=cabinet_id), source_filter)
        sources = self.repository.list_sources(cabinet_id=cabinet_id)
        recent_logs = self.repository.list_events(limit=3, cabinet_id=cabinet_id)
        return {
            "cabinet_id": cabinet_id,
            "module_name": self.settings.module_name,
            "host": self.settings.host,
            "port": self.settings.port,
            "db_path": str(self.settings.db_path.relative_to(self.settings.base_dir)),
            "files": files,
            "sources": sources,
            "recent_logs": recent_logs,
            "source_filter": source_filter,
            "counts": {
                "files": len(files),
                "sources": len(sources),
            },
        }

    def add_source(self, source_type: str, source_url: str, cabinet_id: str = "default") -> int:
        source_type = source_type.strip()
        source_url = source_url.strip()
        if source_type not in {"google_drive", "yandex_disk"}:
            raise ValueError("Поддерживаются только google_drive и yandex_disk")
        if not source_url:
            raise ValueError("Нужно указать ссылку на папку")
        title = self._display_source_title(source_type, "")
        source_id = self.repository.add_source(source_type, source_url, title, cabinet_id=cabinet_id)
        self.repository.add_event(
            action_type="source_add",
            status="done",
            summary=f"Добавлен источник {source_type}",
            artifacts=source_url,
            cabinet_id=cabinet_id,
        )
        self.sync_source(source_id, cabinet_id=cabinet_id)
        return source_id

    def handle_upload(self, filename: str, payload: bytes, cabinet_id: str = "default") -> None:
        source_id = self.repository.ensure_local_source(cabinet_id)
        safe_name = Path(filename).name or "uploaded.bin"
        target = self._unique_upload_path(safe_name, cabinet_id)
        target.write_bytes(payload)
        stat = target.stat()
        self.repository.upsert_file(
            {
                "source_id": source_id,
                "cabinet_id": cabinet_id,
                "source_name": "Локальное хранилище",
                "source_type": "local_upload",
                "external_id": f"upload:{target.relative_to(self._cabinet_upload_dir(cabinet_id))}",
                "file_path": str(target.relative_to(self.settings.base_dir)),
                "file_name": target.name,
                "file_date": self._timestamp(datetime.fromtimestamp(stat.st_ctime, tz=UTC)),
                "created_at_remote": self._timestamp(datetime.fromtimestamp(stat.st_ctime, tz=UTC)),
                "modified_at_remote": self._timestamp(datetime.fromtimestamp(stat.st_mtime, tz=UTC)),
                "page_count": count_document_pages_from_path(target, stat.st_size),
                "status": "uploaded",
                "file_size": stat.st_size,
            }
        )
        self.repository.add_event(
            action_type="upload",
            status="done",
            summary=f"Сохранен локальный файл {target.name}",
            artifacts=str(target.relative_to(self.settings.base_dir)),
            cabinet_id=cabinet_id,
        )
        self.sync_source(source_id, cabinet_id=cabinet_id)
        LOGGER.info("Stored local upload %s", target)

    def sync_source(self, source_id: int, cabinet_id: str = "default") -> None:
        source = self.repository.get_source(source_id, cabinet_id=cabinet_id)
        if not source:
            raise ValueError("Источник не найден")
        try:
            remote_title, remote_files = self._load_source_files(source, cabinet_id)
            title = self._display_source_title(source["source_type"], remote_title)
            stats = self.repository.sync_files(
                source_id=source_id,
                source_type=source["source_type"],
                title=title,
                source_url=source["source_url"],
                files=[self._file_to_record(item) for item in remote_files],
                sync_message="Синхронизация завершена, статистика обновляется.",
                cabinet_id=cabinet_id,
            )
            message = self._build_sync_message(
                stats["total"], stats["added"], stats["changed"], stats["deleted"]
            )
            self.repository.update_source_sync_summary(source_id, message, stats, cabinet_id=cabinet_id)
            self.repository.add_event(
                action_type="sync",
                status="done",
                summary=f"Синхронизация завершена: {title}",
                artifacts=message,
                cabinet_id=cabinet_id,
            )
            LOGGER.info("Sync completed for source_id=%s type=%s", source_id, source["source_type"])
        except (SyncError, ValueError) as error:
            message = str(error)
            self.repository.mark_sync_failed(source_id, message, cabinet_id=cabinet_id)
            self.repository.add_event(
                action_type="sync",
                status="failed",
                summary=f"Синхронизация завершилась ошибкой: {source['title']}",
                artifacts=message,
                cabinet_id=cabinet_id,
            )
            LOGGER.exception("Sync failed for source_id=%s", source_id)

    def _ensure_bootstrap_file(self) -> None:
        bootstrap_file = self.settings.bootstrap_dir / "welcome.txt"
        if not bootstrap_file.exists():
            bootstrap_file.write_text(
                "ingest_registry bootstrap file\n"
                "This file proves the local registry is operational.\n",
                encoding="utf-8",
            )

    def _load_source_files(self, source: dict[str, Any], cabinet_id: str) -> tuple[str, list[RemoteFile]]:
        source_type = source["source_type"]
        if source_type == "local_upload":
            cabinet_dir = self._cabinet_upload_dir(cabinet_id)
            cabinet_dir.mkdir(parents=True, exist_ok=True)
            return self.local_client.list_files(cabinet_dir, self.settings.base_dir)
        if source_type == "google_drive":
            return self.google_client.list_files(source["source_url"])
        if source_type == "yandex_disk":
            return self.yandex_client.list_files(source["source_url"])
        raise ValueError(f"Неизвестный тип источника: {source_type}")

    def _unique_upload_path(self, filename: str, cabinet_id: str) -> Path:
        upload_dir = self._cabinet_upload_dir(cabinet_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        target = upload_dir / filename
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix
        counter = 1
        while True:
            candidate = upload_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def _cabinet_upload_dir(self, cabinet_id: str) -> Path:
        return self.settings.upload_dir / cabinet_id

    @staticmethod
    def _visible_files(files: list[dict[str, Any]], source_filter: str) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        for item in files:
            if source_filter != "all" and item["source_type"] != source_filter:
                continue
            if item["source_type"] == "local_upload":
                file_name = str(item["file_name"]).lower()
                file_path = str(item["file_path"]).lower()
                if "/bootstrap/" in file_path or file_path.startswith("data/storage/bootstrap/"):
                    continue
                if file_name.startswith("readme") and file_name.endswith(".md"):
                    continue
            filtered.append(item)
        return filtered

    @staticmethod
    def _file_to_record(item: RemoteFile) -> dict[str, Any]:
        return {
            "external_id": item.external_id,
            "file_path": item.file_path,
            "file_name": item.file_name,
            "file_size": item.file_size or 0,
            "page_count": item.page_count,
            "created_at": item.created_at,
            "modified_at": item.modified_at,
        }

    @staticmethod
    def _build_sync_message(total: int, added: int, changed: int, deleted: int) -> str:
        return (
            f"Файлов в источнике: {total}. "
            f"Добавлено: {added}. "
            f"Изменено: {changed}. "
            f"Удалено: {deleted}."
        )

    @staticmethod
    def _display_source_title(source_type: str, remote_title: str) -> str:
        if source_type == "google_drive":
            suffix = remote_title.strip() or "папка"
            return f"Google Drive: {suffix}"
        if source_type == "yandex_disk":
            suffix = remote_title.strip() or "папка"
            return f"Яндекс Диск: {suffix}"
        return "Локальное хранилище"

    @staticmethod
    def _timestamp(value: datetime) -> str:
        return value.astimezone(UTC).replace(microsecond=0).isoformat()
