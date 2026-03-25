from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DocumentRecord:
    id: int
    external_ref: str
    title: str
    source_status: str
    recognition_status: str
    classification_status: str
    source_payload: str
    recognized_text: str
    extracted_features: str
    classification_label: str
    classification_reason: str
    classification_confidence: float
    error_message: str
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: Any) -> "DocumentRecord":
        return cls(
            id=row["id"],
            external_ref=row["external_ref"],
            title=row["title"],
            source_status=row["source_status"],
            recognition_status=row["recognition_status"],
            classification_status=row["classification_status"],
            source_payload=row["source_payload"] or "",
            recognized_text=row["recognized_text"] or "",
            extracted_features=row["extracted_features"] or "",
            classification_label=row["classification_label"] or "",
            classification_reason=row["classification_reason"] or "",
            classification_confidence=float(row["classification_confidence"] or 0.0),
            error_message=row["error_message"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
