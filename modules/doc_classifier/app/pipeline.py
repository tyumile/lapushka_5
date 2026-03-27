import json
import re
from pathlib import Path
from typing import Any

import requests

from app.ai_client import AIExtractionResult, OpenAIClassifierClient
from app.file_readers import (
    extract_pdf_page_images,
    read_document_as_text,
    serialize_processing_features,
    split_pdf_by_size,
)
from app.models import DocumentRecord


class DocumentProcessingError(RuntimeError):
    pass


class DocumentProcessor:
    def __init__(
        self,
        ai_client: OpenAIClassifierClient,
        temp_dir: Path,
        pdf_chunk_size_bytes: int,
    ) -> None:
        self.ai_client = ai_client
        self.temp_dir = temp_dir
        self.pdf_chunk_size_bytes = pdf_chunk_size_bytes

    def process_document(self, document: DocumentRecord, file_path: Path) -> dict[str, Any]:
        if not file_path.exists() or not file_path.is_file():
            raise DocumentProcessingError(f"Файл не найден: {file_path}")
        if not self.ai_client.is_configured():
            raise DocumentProcessingError("Не настроен внешний AI агент через OPENAI_API_KEY/OPENAI_MODEL")

        metadata = {
            "file_name": document.source_file_name or file_path.name,
            "file_path": document.source_file_path,
            "file_size": document.source_file_size,
            "page_count": document.page_count,
        }
        recognized_text, input_mode, chunk_paths = self._prepare_input(document, file_path)
        fallback_used = False
        try:
            if input_mode == "file":
                ai_result = self.ai_client.classify_file_document(metadata, chunk_paths, recognized_text)
            elif input_mode == "image":
                ai_result = self.ai_client.classify_image_document(metadata, chunk_paths[0])
            elif input_mode == "pdf_images":
                ai_result = self.ai_client.classify_image_document_batch(metadata, chunk_paths)
            elif input_mode == "heuristic":
                ai_result = self._classify_from_filename(document, file_path)
            else:
                ai_result = self.ai_client.classify_text_document(metadata, recognized_text)
        except requests.HTTPError as error:
            if input_mode == "file" and recognized_text:
                fallback_used = True
                ai_result = self.ai_client.classify_text_document(metadata, recognized_text)
            elif input_mode == "file":
                image_paths = extract_pdf_page_images(file_path, self.temp_dir / "pdf_images")
                if image_paths:
                    fallback_used = True
                    ai_result = self.ai_client.classify_image_document_batch(metadata, image_paths)
                else:
                    fallback_used = True
                    ai_result = self._classify_from_filename(document, file_path)
            elif input_mode == "pdf_images":
                fallback_used = True
                ai_result = self._classify_from_filename(document, file_path)
            else:
                raise DocumentProcessingError(str(error)) from error

        structured_payload = {
            "document_type": ai_result.document_type,
            "document_type_label": ai_result.document_type_label,
            "summary": ai_result.summary,
            "fields": ai_result.fields,
            "executive_doc_targets": ai_result.executive_doc_targets,
        }
        processing_features = serialize_processing_features(
            {
                "input_mode": input_mode,
                "fallback_to_text": fallback_used,
                "chunk_count": len(chunk_paths),
                "source_file_size": document.source_file_size,
                "page_count": document.page_count,
                "executive_doc_targets": ai_result.executive_doc_targets,
                "raw_response": ai_result.raw_response,
            }
        )
        return {
            "recognition_status": "done" if ai_result.recognized_text or recognized_text else "empty",
            "classification_status": self._classification_status_for_result(ai_result),
            "recognized_text": ai_result.recognized_text or recognized_text,
            "extracted_features": processing_features,
            "classification_label": ai_result.document_type or "other_working_document",
            "classification_reason": ai_result.reasoning or ai_result.summary,
            "classification_confidence": ai_result.confidence,
            "error_message": "",
            "structured_data": json.dumps(structured_payload, ensure_ascii=False, indent=2),
            "processing_notes": ai_result.notes,
        }

    def _prepare_input(self, document: DocumentRecord, file_path: Path) -> tuple[str, str, list[Path]]:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            chunk_paths = self._prepare_pdf_chunks(document, file_path)
            recognized_text, _ = read_document_as_text(file_path, self.ai_client.max_input_chars_per_request)
            return recognized_text, "file", chunk_paths
        if suffix in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
            return "", "image", [file_path]

        recognized_text, _ = read_document_as_text(file_path, self.ai_client.max_input_chars_per_request)
        if not recognized_text:
            raise DocumentProcessingError(f"Не удалось извлечь текст из {file_path.name}")
        return recognized_text, "text", []

    def _prepare_pdf_chunks(self, document: DocumentRecord, file_path: Path) -> list[Path]:
        if document.source_file_size <= self.pdf_chunk_size_bytes:
            return [file_path]
        return split_pdf_by_size(file_path, self.temp_dir, self.pdf_chunk_size_bytes)

    def fallback_result_from_filename(self, document: DocumentRecord, file_path: Path) -> dict[str, Any]:
        ai_result = self._classify_from_filename(document, file_path)
        structured_payload = {
            "document_type": ai_result.document_type,
            "document_type_label": ai_result.document_type_label,
            "summary": ai_result.summary,
            "fields": ai_result.fields,
            "executive_doc_targets": ai_result.executive_doc_targets,
        }
        processing_features = serialize_processing_features(
            {
                "input_mode": "heuristic",
                "fallback_to_text": False,
                "chunk_count": 0,
                "source_file_size": document.source_file_size,
                "page_count": document.page_count,
                "executive_doc_targets": ai_result.executive_doc_targets,
                "raw_response": ai_result.raw_response,
            }
        )
        return {
            "recognition_status": "empty",
            "classification_status": "needs_review",
            "recognized_text": "",
            "extracted_features": processing_features,
            "classification_label": ai_result.document_type,
            "classification_reason": ai_result.reasoning or ai_result.summary,
            "classification_confidence": ai_result.confidence,
            "error_message": "",
            "structured_data": json.dumps(structured_payload, ensure_ascii=False, indent=2),
            "processing_notes": ai_result.notes,
        }

    def _classify_from_filename(self, document: DocumentRecord, file_path: Path) -> AIExtractionResult:
        name = (document.source_file_name or file_path.name).lower()
        if re.search(r"\b\d{3,5}[-_а-яa-z0-9]+р[-_а-яa-z0-9]*эом\b", name):
            return AIExtractionResult(
                document_type="project_document",
                document_type_label="Проект",
                summary="Тип документа предположен по имени файла, но содержимое документа не подтверждено.",
                confidence=0.35,
                reasoning="Имя файла похоже на шифр проектной документации раздела ЭОМ, но реквизиты не подтверждены текстом.",
                fields=[],
                executive_doc_targets=["проектная документация", "рабочие чертежи"],
                recognized_text="",
                notes="Использован fallback по имени файла, так как AI file-input не обработал PDF и полезный текст не извлечен.",
                raw_response={"fallback": "filename_project"},
            )

        quality_keywords = (
            "кабель",
            "эмаль",
            "грунт",
            "труба",
            "лоток",
            "пластин",
            "винт",
            "гайк",
            "анкер",
        )
        if any(keyword in name for keyword in quality_keywords):
            return AIExtractionResult(
                document_type="quality_document",
                document_type_label="Документ качества",
                summary="Тип документа предположен по имени файла материала, но реквизиты не подтверждены содержимым.",
                confidence=0.35,
                reasoning="Имя файла содержит наименование строительного материала или изделия, но текст документа не распознан.",
                fields=[],
                executive_doc_targets=["документы качества материалов"],
                recognized_text="",
                notes="Использован fallback по имени файла, так как AI file-input не обработал PDF и полезный текст не извлечен.",
                raw_response={"fallback": "filename_quality"},
            )

        return AIExtractionResult(
            document_type="other_working_document",
            document_type_label="Прочая рабочая документация",
            summary="Тип документа не подтвержден содержимым, использован только запасной анализ имени файла.",
            confidence=0.2,
            reasoning="Не удалось обработать документ через AI file-input и извлечь полезный текст, поэтому вывод основан только на имени файла.",
            fields=[],
            executive_doc_targets=["прочая рабочая документация"],
            recognized_text="",
            notes="Использован fallback по имени файла после сбоя AI file-input без подтвержденных реквизитов.",
            raw_response={"fallback": "filename_other"},
        )

    def _classification_status_for_result(self, ai_result: AIExtractionResult) -> str:
        if ai_result.raw_response.get("fallback"):
            return "needs_review"
        return "done" if ai_result.document_type else "needs_review"
