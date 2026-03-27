import logging
import mimetypes
import threading
from pathlib import Path
from typing import Any

from app.pipeline import DocumentProcessingError, DocumentProcessor
from app.registry_source import IngestRegistryReader
from app.source_fetcher import SourceFileFetcher
from db.repository import DocumentRepository


logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        registry_reader: IngestRegistryReader,
        processor: DocumentProcessor,
        fetcher: SourceFileFetcher,
    ) -> None:
        self.repository = repository
        self.registry_reader = registry_reader
        self.processor = processor
        self.fetcher = fetcher
        self._sync_lock = threading.Lock()

    def bootstrap(self) -> None:
        self.repository.delete_legacy_demo_documents(cabinet_id="default")
        self.sync_registry_documents(cabinet_id="default")

    def get_dashboard(self, cabinet_id: str = "default") -> dict[str, Any]:
        return {
            "cabinet_id": cabinet_id,
            "status": self.repository.get_status_counts(cabinet_id=cabinet_id),
            "documents": self.repository.list_documents(cabinet_id=cabinet_id),
            "working_document_groups": self.repository.get_working_document_groups(cabinet_id=cabinet_id),
        }

    def list_documents(self, cabinet_id: str = "default") -> list[Any]:
        return self.repository.list_documents(cabinet_id=cabinet_id)

    def get_document(self, document_id: int, cabinet_id: str = "default") -> Any:
        return self.repository.get_document(document_id, cabinet_id=cabinet_id)

    def get_document_source_link(self, document_id: int, cabinet_id: str = "default") -> str | None:
        document = self.repository.get_document(document_id, cabinet_id=cabinet_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")
        registry_file = self.registry_reader.get_file_by_external_ref(document.external_ref, cabinet_id=cabinet_id)
        if registry_file is None:
            return None
        return self.fetcher.source_link(registry_file)

    def get_document_file(self, document_id: int, cabinet_id: str = "default") -> tuple[Path, str]:
        document = self.repository.get_document(document_id, cabinet_id=cabinet_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")
        registry_file = self.registry_reader.get_file_by_external_ref(document.external_ref, cabinet_id=cabinet_id)
        if registry_file is None and document.source_module == "ingest_registry":
            raise FileNotFoundError(f"Документ {document.external_ref} отсутствует в актуальном реестре")
        file_path = self.fetcher.resolve_file(registry_file) if registry_file else Path(
            self.registry_reader.base_dir / document.source_file_path
        )
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        return Path(file_path), content_type

    def rerun_document(self, document_id: int, cabinet_id: str = "default") -> None:
        document = self.repository.get_document(document_id, cabinet_id=cabinet_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")
        self._process_single_document(document, cabinet_id=cabinet_id)

    def sync_registry_documents(self, cabinet_id: str = "default") -> None:
        if not self._sync_lock.acquire(blocking=False):
            logger.info("Registry sync already running, skipping duplicate request")
            return
        try:
            reset_count = self.repository.reset_processing_documents(cabinet_id=cabinet_id)
            files = self.registry_reader.list_ready_files(cabinet_id=cabinet_id)
            stats = self.repository.sync_registry_documents(files, cabinet_id=cabinet_id)
            self.repository.add_module_event(
                event_type="registry_sync",
                details=(
                    "Реестр ingest_registry синхронизирован. "
                    f"Добавлено: {stats['added']}. Обновлено: {stats['updated']}. "
                    f"Удалено: {stats['deleted']}. Без изменений: {stats['unchanged']}. "
                    f"Сброшено зависших processing: {reset_count}."
                ),
                cabinet_id=cabinet_id,
            )
            for document in self.repository.list_documents_for_processing(cabinet_id=cabinet_id):
                try:
                    self._process_single_document(document, cabinet_id=cabinet_id)
                except Exception:
                    logger.exception("Unexpected sync failure for document_id=%s cabinet_id=%s", document.id, cabinet_id)
        finally:
            self._sync_lock.release()

    def _process_single_document(self, document: Any, cabinet_id: str = "default") -> None:
        self.repository.mark_document_processing(document.id, cabinet_id=cabinet_id)
        try:
            registry_file = self.registry_reader.get_file_by_external_ref(document.external_ref, cabinet_id=cabinet_id)
            if registry_file is None and document.source_module == "ingest_registry":
                raise DocumentProcessingError(f"Документ {document.external_ref} отсутствует в актуальном реестре")
            file_path = self.fetcher.resolve_file(registry_file) if registry_file else Path(
                self.registry_reader.base_dir / document.source_file_path
            )
            logger.info("Processing document_id=%s path=%s", document.id, file_path)
            result = self.processor.process_document(document, Path(file_path))
            self.repository.update_processing_result(document_id=document.id, cabinet_id=cabinet_id, **result)
            event_type = "document_processed"
            if result["classification_status"] == "needs_review":
                event_type = "document_processed_needs_review"
            self.repository.add_module_event(
                event_type=event_type,
                details=self._build_processing_event_details(document, result),
                cabinet_id=cabinet_id,
            )
        except Exception as error:
            if "Файл не найден" in str(error):
                result = self.processor.fallback_result_from_filename(document, Path(document.source_file_name or document.title))
                self.repository.update_processing_result(document_id=document.id, cabinet_id=cabinet_id, **result)
                self.repository.add_module_event(
                    event_type="document_processed_fallback",
                    details=f"Документ {document.source_file_name or document.title} классифицирован по имени файла.",
                    cabinet_id=cabinet_id,
                )
                return
            self.repository.update_processing_result(
                document_id=document.id,
                cabinet_id=cabinet_id,
                recognition_status="failed",
                classification_status="failed",
                recognized_text="",
                extracted_features="",
                classification_label="",
                classification_reason="",
                classification_confidence=0.0,
                error_message=str(error),
                structured_data="",
                processing_notes="",
            )
            self.repository.add_module_event(
                event_type="document_processing_failed",
                details=f"Документ {document.source_file_name or document.title}: {error}",
                cabinet_id=cabinet_id,
            )
            logger.exception("Document processing failed for document_id=%s", document.id)

    def _build_processing_event_details(self, document: Any, result: dict[str, Any]) -> str:
        name = document.source_file_name or document.title
        label = result["classification_label"]
        if result["classification_status"] == "needs_review":
            return (
                f"Документ {name} не дал подтвержденного распознавания текста. "
                f"Назначен предварительный тип {label}, требуется ручная проверка."
            )
        return f"Документ {name} распознан и классифицирован как {label}."
