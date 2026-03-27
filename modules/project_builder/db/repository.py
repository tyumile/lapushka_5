import sqlite3
from pathlib import Path
from typing import Any

from app.models import (
    ProjectDeficit,
    ProjectDocument,
    ProjectLink,
    ProjectSummary,
    TaskRegistryEntry,
)


class ProjectBuilderRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def seed_demo_data(self, cabinet_id: str = "default") -> None:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT COUNT(*) AS count FROM projects WHERE cabinet_id = ?",
                (cabinet_id,),
            ).fetchone()["count"]
            if existing:
                return

            project_specs = [
                {
                    "project_code": "PB-001",
                    "project_name": "Жилой блок A",
                    "status": "needs_documents",
                    "documents": [
                        {
                            "document_code": "ARCH-001",
                            "title": "Архитектурный план этажа 1",
                            "document_type": "architecture_plan",
                            "status": "matched",
                            "assignment_reason": "В названии и примечании найден код проекта PB-001.",
                            "source_note": "Лист A1, объект Жилой блок A, версия 2026-03.",
                        },
                        {
                            "document_code": "SPEC-001",
                            "title": "Спецификация дверей",
                            "document_type": "material_specification",
                            "status": "matched",
                            "assignment_reason": "Спецификация ссылается на архитектурный план ARCH-001.",
                            "source_note": "Таблица дверей для проекта PB-001.",
                        },
                        {
                            "document_code": "EST-001",
                            "title": "Смета на перегородки",
                            "document_type": "estimate",
                            "status": "matched",
                            "assignment_reason": "Смета содержит те же шифры помещений, что и ARCH-001.",
                            "source_note": "Раздел внутренние перегородки.",
                        },
                    ],
                    "links": [
                        {
                            "source_document_code": "ARCH-001",
                            "target_document_code": "SPEC-001",
                            "relation_type": "specifies",
                            "evidence": "Спецификация дверей указывает лист A1 и таблицу проемов.",
                        },
                        {
                            "source_document_code": "EST-001",
                            "target_document_code": "ARCH-001",
                            "relation_type": "estimates",
                            "evidence": "Смета повторяет объемы по помещениям из архитектурного плана.",
                        },
                    ],
                    "deficits": [
                        {
                            "required_type": "structural_plan",
                            "severity": "high",
                            "summary": "Нет конструктивного раздела.",
                            "details": "Для проекта нет документа с несущими решениями и привязкой узлов.",
                        },
                        {
                            "required_type": "permit_document",
                            "severity": "medium",
                            "summary": "Нет разрешительного документа.",
                            "details": "Нужен документ, подтверждающий согласование работ по проекту.",
                        },
                    ],
                },
                {
                    "project_code": "PB-002",
                    "project_name": "Складской модуль B",
                    "status": "complete",
                    "documents": [
                        {
                            "document_code": "STR-201",
                            "title": "Конструктивный каркас склада",
                            "document_type": "structural_plan",
                            "status": "matched",
                            "assignment_reason": "Документ явно помечен кодом проекта PB-002.",
                            "source_note": "Каркас склада, выпуск 2.",
                        },
                        {
                            "document_code": "MEP-201",
                            "title": "Инженерные сети склада",
                            "document_type": "engineering_scheme",
                            "status": "matched",
                            "assignment_reason": "Схема сетей ссылается на тот же конструктивный выпуск.",
                            "source_note": "Вентиляция и электрика для PB-002.",
                        },
                        {
                            "document_code": "PASS-201",
                            "title": "Паспорт проекта склада",
                            "document_type": "project_passport",
                            "status": "matched",
                            "assignment_reason": "Паспорт содержит идентификатор PB-002 и заказчика.",
                            "source_note": "Паспорт выпуска 2026-Q1.",
                        },
                    ],
                    "links": [
                        {
                            "source_document_code": "PASS-201",
                            "target_document_code": "STR-201",
                            "relation_type": "describes",
                            "evidence": "Паспорт проекта перечисляет конструктивный выпуск STR-201.",
                        },
                        {
                            "source_document_code": "MEP-201",
                            "target_document_code": "STR-201",
                            "relation_type": "depends_on",
                            "evidence": "Инженерная схема использует координаты осей из конструктивного каркаса.",
                        },
                    ],
                    "deficits": [],
                },
            ]

            for spec in project_specs:
                cursor = connection.execute(
                    """
                    INSERT INTO projects (project_code, project_name, status, completeness_ratio)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        cabinet_id,
                        spec["project_code"],
                        spec["project_name"],
                        spec["status"],
                        self._compute_completeness_ratio(spec["documents"], spec["deficits"]),
                    ),
                )
                project_id = cursor.lastrowid
                for item in spec["documents"]:
                    connection.execute(
                        """
                        INSERT INTO project_documents (
                            cabinet_id, project_id, document_code, title, document_type, status,
                            assignment_reason, source_note
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            cabinet_id,
                            project_id,
                            item["document_code"],
                            item["title"],
                            item["document_type"],
                            item["status"],
                            item["assignment_reason"],
                            item["source_note"],
                        ),
                    )
                for item in spec["links"]:
                    connection.execute(
                        """
                        INSERT INTO project_links (
                            cabinet_id, project_id, source_document_code, target_document_code, relation_type, evidence
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            cabinet_id,
                            project_id,
                            item["source_document_code"],
                            item["target_document_code"],
                            item["relation_type"],
                            item["evidence"],
                        ),
                    )
                for item in spec["deficits"]:
                    connection.execute(
                        """
                        INSERT INTO project_deficits (
                            cabinet_id, project_id, required_type, severity, summary, details
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            cabinet_id,
                            project_id,
                            item["required_type"],
                            item["severity"],
                            item["summary"],
                            item["details"],
                        ),
                    )

            connection.execute(
                """
                INSERT INTO module_events (event_type, details)
                VALUES (?, ?, ?)
                """,
                (cabinet_id, "seed_demo_data", "Inserted demo projects, document links and deficits"),
            )
            connection.commit()

    def add_module_event(self, event_type: str, details: str, cabinet_id: str = "default") -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO module_events (cabinet_id, event_type, details) VALUES (?, ?, ?)",
                (cabinet_id, event_type, details),
            )
            connection.commit()

    def add_task_registry_entry(
        self,
        task_id: str,
        source_agent: str,
        target_agent: str,
        module_name: str,
        action_type: str,
        summary: str,
        status: str,
        artifacts: str,
        cabinet_id: str = "default",
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO task_registry_log (
                    cabinet_id, task_id, source_agent, target_agent, module_name,
                    action_type, summary, status, artifacts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cabinet_id,
                    task_id,
                    source_agent,
                    target_agent,
                    module_name,
                    action_type,
                    summary,
                    status,
                    artifacts,
                ),
            )
            connection.commit()

    def list_projects(self) -> list[ProjectSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    p.id,
                    p.project_code,
                    p.project_name,
                    p.status,
                    p.completeness_ratio,
                    (SELECT COUNT(*) FROM project_documents d WHERE d.project_id = p.id) AS total_documents,
                    (SELECT COUNT(*) FROM project_links l WHERE l.project_id = p.id) AS total_links,
                    (SELECT COUNT(*) FROM project_deficits deficit WHERE deficit.project_id = p.id) AS total_deficits,
                    (
                        SELECT COUNT(*)
                        FROM project_documents d
                        WHERE d.project_id = p.id AND d.status = 'matched'
                    ) AS assigned_documents
                FROM projects p
                ORDER BY p.project_code
                """
            ).fetchall()
        return [ProjectSummary.from_row(row) for row in rows]

    def get_project(self, project_id: int) -> ProjectSummary | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    p.id,
                    p.project_code,
                    p.project_name,
                    p.status,
                    p.completeness_ratio,
                    (SELECT COUNT(*) FROM project_documents d WHERE d.project_id = p.id) AS total_documents,
                    (SELECT COUNT(*) FROM project_links l WHERE l.project_id = p.id) AS total_links,
                    (SELECT COUNT(*) FROM project_deficits deficit WHERE deficit.project_id = p.id) AS total_deficits,
                    (
                        SELECT COUNT(*)
                        FROM project_documents d
                        WHERE d.project_id = p.id AND d.status = 'matched'
                    ) AS assigned_documents
                FROM projects p
                WHERE p.id = ?
                """,
                (project_id,),
            ).fetchone()
        return ProjectSummary.from_row(row) if row else None

    def list_project_documents(self, project_id: int) -> list[ProjectDocument]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM project_documents
                WHERE project_id = ?
                ORDER BY document_code
                """,
                (project_id,),
            ).fetchall()
        return [ProjectDocument.from_row(row) for row in rows]

    def list_project_links(self, project_id: int) -> list[ProjectLink]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM project_links
                WHERE project_id = ?
                ORDER BY id
                """,
                (project_id,),
            ).fetchall()
        return [ProjectLink.from_row(row) for row in rows]

    def list_project_deficits(self, project_id: int) -> list[ProjectDeficit]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM project_deficits
                WHERE project_id = ?
                ORDER BY
                    CASE severity
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        ELSE 3
                    END,
                    id
                """,
                (project_id,),
            ).fetchall()
        return [ProjectDeficit.from_row(row) for row in rows]

    def list_module_events(self, limit: int = 10, cabinet_id: str = "default") -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_type, details, created_at
                FROM module_events
                WHERE cabinet_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (cabinet_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_task_registry(self, limit: int = 10, cabinet_id: str = "default") -> list[TaskRegistryEntry]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT task_id, source_agent, target_agent, module_name, action_type,
                       summary, status, artifacts, created_at
                FROM task_registry_log
                WHERE cabinet_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (cabinet_id, limit),
            ).fetchall()
        return [TaskRegistryEntry(**dict(row)) for row in rows]

    def get_status_counts(self, cabinet_id: str = "default") -> dict[str, Any]:
        with self._connect() as connection:
            totals = connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM projects WHERE cabinet_id = ?) AS total_projects,
                    (SELECT COUNT(*) FROM project_documents WHERE cabinet_id = ?) AS total_documents,
                    (SELECT COUNT(*) FROM project_links WHERE cabinet_id = ?) AS total_links,
                    (SELECT COUNT(*) FROM project_deficits WHERE cabinet_id = ?) AS total_deficits,
                    (SELECT COUNT(*) FROM projects WHERE cabinet_id = ? AND status = 'complete') AS complete_projects
                """,
                (cabinet_id, cabinet_id, cabinet_id, cabinet_id, cabinet_id),
            ).fetchone()
            last_event = connection.execute(
                """
                SELECT event_type, details, created_at
                FROM module_events
                WHERE cabinet_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (cabinet_id,),
            ).fetchone()
        return {
            "total_projects": totals["total_projects"],
            "total_documents": totals["total_documents"],
            "total_links": totals["total_links"],
            "total_deficits": totals["total_deficits"],
            "complete_projects": totals["complete_projects"],
            "last_event": dict(last_event) if last_event else None,
        }

    @staticmethod
    def _compute_completeness_ratio(documents: list[dict[str, str]], deficits: list[dict[str, str]]) -> float:
        required_slots = max(len(documents) + len(deficits), 1)
        return round(len(documents) / required_slots, 2)
