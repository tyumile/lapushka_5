import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote


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
    source_module: str
    source_file_path: str
    source_file_name: str
    source_file_size: int
    source_file_date: str
    source_modified_at: str
    page_count: int
    source_signature: str
    structured_data: str
    processing_notes: str
    created_at: str
    updated_at: str

    @property
    def structured_fields(self) -> list[dict[str, str]]:
        if not self.structured_data:
            return []
        try:
            payload = json.loads(self.structured_data)
        except json.JSONDecodeError:
            return []
        fields = payload.get("fields")
        return fields if isinstance(fields, list) else []

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
            source_module=row["source_module"] or "",
            source_file_path=row["source_file_path"] or "",
            source_file_name=row["source_file_name"] or "",
            source_file_size=int(row["source_file_size"] or 0),
            source_file_date=row["source_file_date"] or "",
            source_modified_at=row["source_modified_at"] or "",
            page_count=int(row["page_count"] or 0),
            source_signature=row["source_signature"] or "",
            structured_data=row["structured_data"] or "",
            processing_notes=row["processing_notes"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @property
    def source_payload_data(self) -> dict[str, str]:
        if not self.source_payload:
            return {}
        try:
            payload = json.loads(self.source_payload)
        except json.JSONDecodeError:
            return {}
        return {key: str(value) for key, value in payload.items() if value is not None}

    @property
    def source_link(self) -> str | None:
        payload = self.source_payload_data
        source_type = payload.get("source_type", "")
        external_id = payload.get("source_external_id", "")
        source_url = payload.get("source_url")
        if source_type == "google_drive" and external_id:
            return f"https://drive.google.com/file/d/{quote(external_id)}/view"
        if source_type == "yandex_disk" and source_url:
            return source_url
        return source_url
