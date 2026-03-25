import logging
from typing import Any

from app.pipeline import classify_document, recognize_text
from db.repository import DocumentRepository


logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self, repository: DocumentRepository) -> None:
        self.repository = repository

    def get_dashboard(self) -> dict[str, Any]:
        return {
            "status": self.repository.get_status_counts(),
            "documents": self.repository.list_documents(),
        }

    def list_documents(self) -> list[Any]:
        return self.repository.list_documents()

    def get_document(self, document_id: int) -> Any:
        return self.repository.get_document(document_id)

    def rerun_document(self, document_id: int) -> None:
        document = self.repository.get_document(document_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        logger.info("Rerunning recognition and classification for document_id=%s", document_id)
        recognized_text, features = recognize_text(document.source_payload)
        label, reason, confidence = classify_document(recognized_text)
        self.repository.update_processing_result(
            document_id=document_id,
            recognition_status="done",
            classification_status="done" if label != "unknown" else "needs_review",
            recognized_text=recognized_text,
            extracted_features=features,
            classification_label=label,
            classification_reason=reason,
            classification_confidence=confidence,
            error_message="",
        )
        self.repository.add_module_event(
            event_type="document_rerun",
            details=f"Document {document.external_ref} rerun completed with label={label}",
        )
