import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from pypdf import PdfReader

from app.agent_prompt import load_prompt, render_context_block
from app.ai_client import ProjectAnalysisAIClient
from app.analysis_schema import normalize_analysis_result
from app.config import AppConfig
from app.doc_classifier_source import DocClassifierReader
from app.registry_source import IngestRegistryReader, RegistryDocument
from db.repository import ProjectBuilderRepository


class ProjectAnalysisError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProjectAnalysisRunResult:
    run_dir: Path
    request_context_path: Path
    result_path: Path
    project_document: RegistryDocument
    candidate_documents_count: int


class ProjectAnalysisRunner:
    candidate_text_excerpt_limit = 700
    project_text_limit = 10000

    def __init__(
        self,
        config: AppConfig,
        repository: ProjectBuilderRepository,
        registry_reader: IngestRegistryReader,
        ai_client: ProjectAnalysisAIClient,
        doc_classifier_reader: DocClassifierReader | None = None,
    ) -> None:
        self.config = config
        self.repository = repository
        self.registry_reader = registry_reader
        self.ai_client = ai_client
        self.doc_classifier_reader = doc_classifier_reader

    def run(
        self,
        project_document_id: int,
        cabinet_id: str = "default",
        source_ids: list[int] | None = None,
        document_ids: list[int] | None = None,
        project_file_path: Path | None = None,
        dry_run: bool = False,
    ) -> ProjectAnalysisRunResult:
        project_document = self.registry_reader.get_document(project_document_id, cabinet_id=cabinet_id)
        if project_document is None:
            raise ProjectAnalysisError(f"Документ проекта id={project_document_id} не найден в ingest_registry.")

        project_path = project_file_path or Path(project_document.absolute_file_path)
        project_file_exists = project_path.exists() and project_path.is_file()

        documents = self.registry_reader.list_documents(cabinet_id=cabinet_id, source_ids=source_ids, document_ids=document_ids)
        candidate_documents = [item for item in documents if item.id != project_document.id]
        if not candidate_documents:
            raise ProjectAnalysisError("Нет документов для сопоставления. Добавьте документы в ingest_registry или расширьте фильтр.")

        context_text = render_context_block(
            project_document=self._project_context_document(project_document),
            candidate_documents=[self._candidate_context_document(item) for item in candidate_documents],
        )
        run_dir = self._create_run_dir(project_document, cabinet_id)
        request_context_path = run_dir / "request_context.json"
        result_path = run_dir / "project_analysis.json"
        request_context_path.write_text(context_text + "\n", encoding="utf-8")

        if dry_run:
            payload = normalize_analysis_result(
                {
                    "cabinet_id": cabinet_id,
                    "project": {
                        "project_document_id": project_document.id,
                        "project_file_name": project_document.file_name,
                        "project_file_path": str(project_path),
                        "analysis_summary": "dry-run: внешний агент не вызывался",
                        "analysis_notes": (
                            "Сформирован только request_context.json для проверки payload. "
                            "Физический файл проекта для dry-run не требуется."
                        ),
                    },
                    "analysis_warnings": ["dry_run_enabled"],
                }
            )
            payload["cabinet_id"] = cabinet_id
            result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.repository.add_module_event(
                "project_analysis_dry_run",
                f"Prepared project analysis payload for document {project_document.id} in {run_dir}",
                cabinet_id=cabinet_id,
            )
            return ProjectAnalysisRunResult(
                run_dir=run_dir,
                request_context_path=request_context_path,
                result_path=result_path,
                project_document=project_document,
                candidate_documents_count=len(candidate_documents),
            )

        if not self.ai_client.is_configured():
            raise ProjectAnalysisError("Не настроен внешний AI агент через OPENAI_API_KEY/OPENAI_MODEL.")
        if not project_file_exists:
            raise ProjectAnalysisError(
                f"Файл проекта не найден на диске: {project_path}. "
                "Для удаленных источников ingest_registry передайте локальный путь через --project-file-path."
            )

        prompt_text = load_prompt(
            self.config.prompts_dir / "pto_engineer_prompt.md",
            self.config.prompts_dir / "project_analysis_output_schema.json",
        )
        project_text = self._read_project_text(project_path)
        if not project_text:
            try:
                raw_payload = self.ai_client.analyze_project(prompt_text, context_text, project_path)
            except requests.HTTPError as error:
                raise ProjectAnalysisError(
                    f"Внешний AI отклонил file-режим, а текст проекта извлечь не удалось: {error}"
                ) from error
        else:
            raw_payload = self.ai_client.analyze_project_text(
                prompt_text=prompt_text,
                context_text=context_text,
                project_text=project_text,
                project_file_name=project_document.file_name,
            )
            self.repository.add_module_event(
                "project_analysis_text_mode",
                f"Used project text mode for document {project_document.id}",
                cabinet_id=cabinet_id,
            )
        normalized_payload = normalize_analysis_result(raw_payload)
        normalized_payload["cabinet_id"] = cabinet_id
        normalized_payload["project"]["project_document_id"] = str(project_document.id)
        normalized_payload["project"]["project_file_name"] = project_document.file_name
        normalized_payload["project"]["project_file_path"] = str(project_path)
        normalized_payload = self._postprocess_result(normalized_payload, candidate_documents, cabinet_id=cabinet_id)
        result_path.write_text(json.dumps(normalized_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.repository.add_module_event(
            "project_analysis_completed",
            f"Saved project analysis for document {project_document.id} to {result_path}",
            cabinet_id=cabinet_id,
        )
        return ProjectAnalysisRunResult(
            run_dir=run_dir,
            request_context_path=request_context_path,
            result_path=result_path,
            project_document=project_document,
            candidate_documents_count=len(candidate_documents),
        )

    def _create_run_dir(self, project_document: RegistryDocument, cabinet_id: str) -> Path:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        run_dir = self.config.analysis_dir / f"{timestamp}_cabinet_{cabinet_id}_project_{project_document.id}"
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    def _read_project_text(self, project_path: Path) -> str:
        try:
            reader = PdfReader(str(project_path))
        except Exception:
            return ""
        parts: list[str] = []
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text.strip():
                parts.append(f"[Страница {page_number}]\n{text.strip()}")
            candidate = "\n\n".join(parts)
            if len(candidate) >= self.project_text_limit:
                return candidate[: self.project_text_limit]
        return "\n\n".join(parts)[: self.project_text_limit]

    def _project_context_document(self, document: RegistryDocument) -> dict[str, Any]:
        return {
            "id": document.id,
            "source_title": document.source_title,
            "source_type": document.source_type,
            "source_url": document.source_url,
            "file_name": document.file_name,
            "file_path": document.file_path,
            "absolute_file_path": document.absolute_file_path,
            "file_date": document.file_date,
            "page_count": document.page_count,
            "file_size": document.file_size,
        }

    def _candidate_context_document(self, document: RegistryDocument) -> dict[str, Any]:
        payload = {
            "id": document.id,
            "source_title": document.source_title,
            "source_type": document.source_type,
            "source_url": document.source_url,
            "file_name": document.file_name,
            "file_path": document.file_path,
            "absolute_file_path": document.absolute_file_path,
            "file_date": document.file_date,
            "page_count": document.page_count,
            "file_size": document.file_size,
        }
        if not self.doc_classifier_reader:
            return payload
        snapshot = self.doc_classifier_reader.find_best_document_snapshot(document.file_name, cabinet_id=document.cabinet_id)
        if snapshot is None:
            return payload
        structured_data = snapshot.get("structured_data", {})
        fields = structured_data.get("fields", []) if isinstance(structured_data, dict) else []
        payload["doc_classifier"] = {
            "recognition_status": snapshot.get("recognition_status", ""),
            "classification_status": snapshot.get("classification_status", ""),
            "classification_label": snapshot.get("classification_label", ""),
            "classification_reason": snapshot.get("classification_reason", ""),
            "classification_confidence": snapshot.get("classification_confidence", 0),
            "recognized_text_excerpt": self._truncate_text(snapshot.get("recognized_text", "")),
            "fields": fields[:8],
        }
        return payload

    def _truncate_text(self, text: Any) -> str:
        value = str(text or "").strip()
        if len(value) <= self.candidate_text_excerpt_limit:
            return value
        return value[: self.candidate_text_excerpt_limit - 32].rstrip() + " ...[обрезано]"

    def _postprocess_result(
        self,
        payload: dict[str, Any],
        candidate_documents: list[RegistryDocument],
        cabinet_id: str = "default",
    ) -> dict[str, Any]:
        by_id = {str(item.id): item for item in candidate_documents}
        classifier_snapshots = {
            str(item.id): self.doc_classifier_reader.find_best_document_snapshot(
                item.file_name,
                cabinet_id=item.cabinet_id or cabinet_id,
            )
            if self.doc_classifier_reader
            else None
            for item in candidate_documents
        }
        for module in payload.get("modules", []):
            for material in module.get("materials", []):
                registry_id = str(material.get("document_registry_id", "")).strip()
                document = by_id.get(registry_id)
                snapshot = classifier_snapshots.get(registry_id)
                if document:
                    material["document_disk_path"] = document.absolute_file_path
                    candidate_name = self._field_from_snapshot(snapshot, {"document_name", "act_name", "report_name"})
                    if candidate_name and self._should_replace_document_name(str(material.get("document_name") or "").strip()):
                        material["document_name"] = candidate_name
                    if not material.get("document_number"):
                        material["document_number"] = self._field_from_snapshot(snapshot, {"document_number", "act_number", "report_number"})
                    if not material.get("document_date"):
                        material["document_date"] = self._field_from_snapshot(snapshot, {"document_date", "issue_date", "act_date", "report_date"})
        for item in payload.get("unmatched_documents", []):
            registry_id = str(item.get("document_registry_id", "")).strip()
            document = by_id.get(registry_id)
            if document:
                item["document_disk_path"] = document.absolute_file_path
                if not item.get("document_name"):
                    item["document_name"] = document.file_name
        return payload

    def _field_from_snapshot(self, snapshot: dict[str, Any] | None, names: set[str]) -> str:
        if not snapshot:
            return ""
        structured = snapshot.get("structured_data")
        if not isinstance(structured, dict):
            return ""
        for item in structured.get("fields", []):
            if not isinstance(item, dict):
                continue
            if str(item.get("name", "")).strip() in names:
                return str(item.get("value", "")).strip()
        return ""

    def _should_replace_document_name(self, document_name: str) -> bool:
        if not document_name:
            return True
        lowered = document_name.lower()
        return any(lowered.endswith(suffix) for suffix in (".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"))
