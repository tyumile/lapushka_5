from typing import Any

from db.repository import ProjectBuilderRepository


class ProjectBuilderService:
    def __init__(self, repository: ProjectBuilderRepository) -> None:
        self.repository = repository

    def get_dashboard(self) -> dict[str, Any]:
        projects = self.repository.list_projects()
        return {
            "status": self.repository.get_status_counts(),
            "projects": projects,
            "module_events": self.repository.list_module_events(limit=5),
            "task_registry": self.repository.list_task_registry(limit=5),
        }

    def list_projects(self) -> list[Any]:
        return self.repository.list_projects()

    def get_project(self, project_id: int) -> dict[str, Any] | None:
        project = self.repository.get_project(project_id)
        if project is None:
            return None
        return {
            "project": project,
            "documents": self.repository.list_project_documents(project_id),
            "links": self.repository.list_project_links(project_id),
            "deficits": self.repository.list_project_deficits(project_id),
        }
