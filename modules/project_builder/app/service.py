import logging
import threading
from pathlib import Path
from typing import Any

from app.analysis_store import AnalysisStore
from app.project_analysis import ProjectAnalysisError, ProjectAnalysisRunner
from app.registry_source import IngestRegistryReader, RegistryDocument
from db.repository import ProjectBuilderRepository


class ProjectBuilderService:
    def __init__(
        self,
        repository: ProjectBuilderRepository,
        analysis_store: AnalysisStore | None = None,
        registry_reader: IngestRegistryReader | None = None,
        analysis_runner: ProjectAnalysisRunner | None = None,
    ) -> None:
        self.repository = repository
        self.analysis_store = analysis_store
        self.registry_reader = registry_reader
        self.analysis_runner = analysis_runner
        self._analysis_lock = threading.Lock()
        self._running_cabinets: set[str] = set()

    def get_dashboard(self, cabinet_id: str = "default") -> dict[str, Any]:
        analyses = self.list_projects(cabinet_id=cabinet_id)
        latest = self.get_latest_analysis(cabinet_id=cabinet_id)
        return {
            "cabinet_id": cabinet_id,
            "status": self._real_status_counts(analyses, latest, cabinet_id),
            "projects": analyses,
            "project_cards": self.analysis_store.load_all(cabinet_id=cabinet_id) if self.analysis_store else [],
            "module_events": self.repository.list_module_events(limit=5, cabinet_id=cabinet_id),
            "latest_analysis": latest,
            "analysis_action": self.get_analysis_action(cabinet_id=cabinet_id),
        }

    def list_projects(self, cabinet_id: str = "default") -> list[Any]:
        if not self.analysis_store:
            return []
        projects = []
        for payload in self.analysis_store.load_all(cabinet_id=cabinet_id):
            modules = payload.get("modules", [])
            unmatched = payload.get("unmatched_documents", [])
            assigned_documents = sum(len(item.get("materials", [])) for item in modules)
            payload["id"] = payload.get("_id")
            payload["project_name"] = payload.get("project", {}).get("project_name") or payload.get("project", {}).get("project_file_name") or "Без названия"
            payload["project_code"] = payload.get("project", {}).get("project_code") or ""
            payload["status"] = "needs_documents" if unmatched else "complete"
            payload["assigned_documents"] = assigned_documents
            payload["total_documents"] = assigned_documents + len(unmatched)
            payload["total_links"] = sum(len(item.get("norms", [])) for item in modules)
            payload["total_deficits"] = len(unmatched)
            payload["completeness_ratio"] = 1.0 if not unmatched else max(
                0.0,
                1 - (len(unmatched) / max(assigned_documents, 1)),
            )
            projects.append(payload)
        return projects

    def get_project(self, project_id: int, cabinet_id: str = "default") -> dict[str, Any] | None:
        if not self.analysis_store:
            return None
        return self.analysis_store.load_by_id(project_id, cabinet_id=cabinet_id)

    def get_latest_analysis(self, cabinet_id: str = "default") -> dict[str, Any] | None:
        if not self.analysis_store:
            return None
        return self.analysis_store.load_latest(cabinet_id=cabinet_id)

    def get_analysis(self, analysis_id: int, cabinet_id: str = "default") -> dict[str, Any] | None:
        if not self.analysis_store:
            return None
        return self.analysis_store.load_by_id(analysis_id, cabinet_id=cabinet_id)

    def get_analysis_action(self, cabinet_id: str = "default") -> dict[str, Any]:
        candidate = self._pick_project_document(cabinet_id=cabinet_id)
        with self._analysis_lock:
            is_running = cabinet_id in self._running_cabinets
        if is_running:
            return {
                "available": False,
                "running": True,
                "label": "Анализ уже запущен",
                "hint": "Для этого кабинета уже выполняется проектный AI-анализ. Обновите страницу через некоторое время.",
                "project_document_id": candidate.id if candidate else None,
                "project_document_name": candidate.file_name if candidate else "",
            }
        if candidate is None:
            return {
                "available": False,
                "running": False,
                "label": "Нет документа проекта",
                "hint": "В текущем кабинете не найден подходящий файл проекта для запуска анализа.",
                "project_document_id": None,
                "project_document_name": "",
            }
        return {
            "available": True,
            "running": False,
            "label": "Анализ проекта",
            "hint": f"Будет использован файл проекта: {candidate.file_name}",
            "project_document_id": candidate.id,
            "project_document_name": candidate.file_name,
        }

    def trigger_project_analysis(self, cabinet_id: str = "default") -> tuple[bool, str]:
        if not self.analysis_runner or not self.registry_reader:
            return False, "Запуск анализа недоступен: модуль не инициализировал runner."
        candidate = self._pick_project_document(cabinet_id=cabinet_id)
        if candidate is None:
            return False, "Не найден документ проекта для запуска анализа в текущем кабинете."
        with self._analysis_lock:
            if cabinet_id in self._running_cabinets:
                return False, "Для этого кабинета анализ уже выполняется."
            self._running_cabinets.add(cabinet_id)
        self.repository.add_module_event(
            "project_analysis_requested",
            f"Запущен анализ проекта из UI для документа {candidate.id}",
            cabinet_id=cabinet_id,
        )
        thread = threading.Thread(
            target=self._run_analysis_in_background,
            args=(cabinet_id, candidate.id),
            daemon=True,
        )
        thread.start()
        return True, f"Анализ проекта запущен для файла {candidate.file_name}."

    def _real_status_counts(self, analyses: list[dict[str, Any]], latest: dict[str, Any] | None, cabinet_id: str) -> dict[str, Any]:
        complete = len([item for item in analyses if item["status"] == "complete"])
        return {
            "total_projects": len(analyses),
            "total_documents": sum(item["total_documents"] for item in analyses),
            "total_links": sum(item["total_links"] for item in analyses),
            "total_deficits": sum(item["total_deficits"] for item in analyses),
            "complete_projects": complete,
            "needs_documents": len(analyses) - complete,
            "last_event": self.repository.get_status_counts(cabinet_id=cabinet_id)["last_event"],
            "latest_project_name": latest.get("project", {}).get("project_name") if latest else "",
            "cabinet_id": cabinet_id,
        }

    def _pick_project_document(self, cabinet_id: str = "default") -> RegistryDocument | None:
        if not self.registry_reader:
            return None
        documents = self.registry_reader.list_documents(cabinet_id=cabinet_id)
        if not documents:
            return None
        ranked = sorted(documents, key=self._project_document_sort_key)
        return ranked[0] if ranked else None

    def _project_document_sort_key(self, document: RegistryDocument) -> tuple[int, int, int, str]:
        file_name = document.file_name.lower()
        is_pdf = 1 if file_name.endswith(".pdf") else 0
        project_markers = ["-р-", "эом", "проект", "том", "раздел"]
        marker_score = sum(1 for marker in project_markers if marker in file_name)
        page_count = document.page_count or 0
        return (-marker_score, -page_count, -is_pdf, file_name)

    def _run_analysis_in_background(self, cabinet_id: str, project_document_id: int) -> None:
        try:
            assert self.analysis_runner is not None
            self.analysis_runner.run(
                project_document_id=project_document_id,
                cabinet_id=cabinet_id,
            )
        except ProjectAnalysisError as error:
            logging.getLogger(__name__).exception("Project analysis failed for cabinet %s", cabinet_id)
            self.repository.add_module_event(
                "project_analysis_failed",
                f"Ошибка запуска анализа проекта {project_document_id}: {error}",
                cabinet_id=cabinet_id,
            )
        except Exception as error:  # noqa: BLE001
            logging.getLogger(__name__).exception("Unexpected project analysis failure for cabinet %s", cabinet_id)
            self.repository.add_module_event(
                "project_analysis_failed",
                f"Непредвиденная ошибка анализа проекта {project_document_id}: {error}",
                cabinet_id=cabinet_id,
            )
        finally:
            with self._analysis_lock:
                self._running_cabinets.discard(cabinet_id)
