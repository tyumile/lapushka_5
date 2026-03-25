from dataclasses import dataclass
from sqlite3 import Row


@dataclass(frozen=True)
class ProjectSummary:
    id: int
    project_code: str
    project_name: str
    status: str
    completeness_ratio: float
    total_documents: int
    total_links: int
    total_deficits: int
    assigned_documents: int

    @classmethod
    def from_row(cls, row: Row) -> "ProjectSummary":
        return cls(
            id=row["id"],
            project_code=row["project_code"],
            project_name=row["project_name"],
            status=row["status"],
            completeness_ratio=float(row["completeness_ratio"]),
            total_documents=row["total_documents"],
            total_links=row["total_links"],
            total_deficits=row["total_deficits"],
            assigned_documents=row["assigned_documents"],
        )


@dataclass(frozen=True)
class ProjectDocument:
    id: int
    project_id: int
    document_code: str
    title: str
    document_type: str
    status: str
    assignment_reason: str
    source_note: str

    @classmethod
    def from_row(cls, row: Row) -> "ProjectDocument":
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            document_code=row["document_code"],
            title=row["title"],
            document_type=row["document_type"],
            status=row["status"],
            assignment_reason=row["assignment_reason"],
            source_note=row["source_note"],
        )


@dataclass(frozen=True)
class ProjectLink:
    id: int
    project_id: int
    source_document_code: str
    target_document_code: str
    relation_type: str
    evidence: str

    @classmethod
    def from_row(cls, row: Row) -> "ProjectLink":
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            source_document_code=row["source_document_code"],
            target_document_code=row["target_document_code"],
            relation_type=row["relation_type"],
            evidence=row["evidence"],
        )


@dataclass(frozen=True)
class ProjectDeficit:
    id: int
    project_id: int
    required_type: str
    severity: str
    summary: str
    details: str

    @classmethod
    def from_row(cls, row: Row) -> "ProjectDeficit":
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            required_type=row["required_type"],
            severity=row["severity"],
            summary=row["summary"],
            details=row["details"],
        )


@dataclass(frozen=True)
class TaskRegistryEntry:
    task_id: str
    source_agent: str
    target_agent: str
    module_name: str
    action_type: str
    summary: str
    status: str
    artifacts: str
    created_at: str
