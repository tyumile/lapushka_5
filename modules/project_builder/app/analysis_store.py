import json
from pathlib import Path
from typing import Any


class AnalysisStore:
    def __init__(self, analysis_dir: Path) -> None:
        self.analysis_dir = analysis_dir

    def load_latest(self, cabinet_id: str = "default") -> dict[str, Any] | None:
        analyses = self.load_all(cabinet_id=cabinet_id)
        return analyses[0] if analyses else None

    def load_all(self, cabinet_id: str = "default") -> list[dict[str, Any]]:
        if not self.analysis_dir.exists():
            return []
        run_dirs = sorted(
            [path for path in self.analysis_dir.iterdir() if path.is_dir()],
            reverse=True,
        )
        results: list[dict[str, Any]] = []
        display_id = 1
        for run_dir in run_dirs:
            result_path = run_dir / "project_analysis.json"
            if not result_path.exists():
                continue
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            payload_cabinet_id = self._resolve_cabinet_id(payload, run_dir)
            if payload_cabinet_id != cabinet_id:
                continue
            payload["cabinet_id"] = payload_cabinet_id
            payload["_id"] = display_id
            payload["_run_dir"] = str(run_dir)
            payload["_result_path"] = str(result_path)
            request_path = run_dir / "request_context.json"
            payload["_request_path"] = str(request_path) if request_path.exists() else ""
            self._enrich_payload_from_request_context(payload, request_path)
            results.append(payload)
            display_id += 1
        return results

    def load_by_id(self, analysis_id: int, cabinet_id: str = "default") -> dict[str, Any] | None:
        for payload in self.load_all(cabinet_id=cabinet_id):
            if int(payload.get("_id", 0)) == analysis_id:
                return payload
        return None

    def _resolve_cabinet_id(self, payload: dict[str, Any], run_dir: Path) -> str:
        cabinet_id = str(payload.get("cabinet_id") or "").strip()
        if cabinet_id:
            return cabinet_id
        parts = run_dir.name.split("_")
        if "cabinet" in parts:
            index = parts.index("cabinet")
            if index + 1 < len(parts):
                return parts[index + 1]
        return "default"

    def _enrich_payload_from_request_context(self, payload: dict[str, Any], request_path: Path) -> None:
        if not request_path.exists():
            return
        try:
            request_payload = json.loads(request_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        candidates = request_payload.get("candidate_documents", [])
        if not isinstance(candidates, list):
            return
        by_id = {str(item.get("id") or "").strip(): item for item in candidates if isinstance(item, dict)}
        if not by_id:
            return
        for module in payload.get("modules", []):
            if not isinstance(module, dict):
                continue
            for material in module.get("materials", []):
                if not isinstance(material, dict):
                    continue
                registry_id = str(material.get("document_registry_id") or "").strip()
                candidate = by_id.get(registry_id)
                if not candidate:
                    continue
                candidate_name = self._snapshot_field(candidate, {"document_name", "act_name", "report_name"})
                if candidate_name and self._should_replace_document_name(str(material.get("document_name") or "").strip()):
                    material["document_name"] = candidate_name
                if not str(material.get("document_number") or "").strip():
                    candidate_number = self._snapshot_field(candidate, {"document_number", "act_number", "report_number"})
                    if candidate_number:
                        material["document_number"] = candidate_number
                if not str(material.get("document_date") or "").strip():
                    candidate_date = self._snapshot_field(
                        candidate,
                        {"document_date", "issue_date", "act_date", "report_date"},
                    )
                    if candidate_date:
                        material["document_date"] = candidate_date

    def _snapshot_field(self, candidate: dict[str, Any], names: set[str]) -> str:
        doc_classifier = candidate.get("doc_classifier", {})
        if not isinstance(doc_classifier, dict):
            return ""
        fields = doc_classifier.get("fields", [])
        if not isinstance(fields, list):
            return ""
        for item in fields:
            if not isinstance(item, dict):
                continue
            if str(item.get("name") or "").strip() in names:
                return str(item.get("value") or "").strip()
        return ""

    def _should_replace_document_name(self, document_name: str) -> bool:
        if not document_name:
            return True
        lowered = document_name.lower()
        return any(lowered.endswith(suffix) for suffix in (".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"))
