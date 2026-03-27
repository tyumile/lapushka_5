import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.modules.setdefault("pypdf", SimpleNamespace(PdfReader=object))

from app.analysis_store import AnalysisStore
from app.config import AppConfig
from app.project_analysis import ProjectAnalysisRunner
from app.registry_source import RegistryDocument
from db.repository import ProjectBuilderRepository
from db.setup import initialize_database


class _FakeRegistryReader:
    def __init__(self, documents_by_cabinet: dict[str, list[RegistryDocument]]) -> None:
        self.documents_by_cabinet = documents_by_cabinet

    def get_document(self, document_id: int, cabinet_id: str = "default") -> RegistryDocument | None:
        for item in self.documents_by_cabinet.get(cabinet_id, []):
            if item.id == document_id:
                return item
        return None

    def list_documents(
        self,
        cabinet_id: str = "default",
        source_ids: list[int] | None = None,
        document_ids: list[int] | None = None,
    ) -> list[RegistryDocument]:
        documents = list(self.documents_by_cabinet.get(cabinet_id, []))
        if document_ids:
            documents = [item for item in documents if item.id in document_ids]
        return documents


class _FakeAIClient:
    def is_configured(self) -> bool:
        return False


class _RecordingDocClassifierReader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def find_best_document_snapshot(self, file_name: str, cabinet_id: str = "default") -> dict[str, object]:
        self.calls.append((file_name, cabinet_id))
        return {
            "structured_data": {
                "fields": [
                    {"name": "document_name", "value": f"{cabinet_id}:{file_name}"},
                    {"name": "document_number", "value": f"num-{cabinet_id}"},
                ]
            }
        }


def _document(doc_id: int, cabinet_id: str, file_name: str) -> RegistryDocument:
    return RegistryDocument(
        id=doc_id,
        cabinet_id=cabinet_id,
        source_id=1,
        source_name="source",
        source_title="Source",
        source_type="drive",
        source_url="https://example.invalid",
        external_id=str(doc_id),
        file_path=file_name,
        absolute_file_path=f"/tmp/{cabinet_id}/{file_name}",
        file_name=file_name,
        file_date="2026-03-27",
        created_at_remote="",
        modified_at_remote="",
        page_count=1,
        status="ready",
        file_size=100,
    )


class CabinetAwareTests(unittest.TestCase):
    def test_dry_run_results_are_isolated_per_cabinet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            analysis_dir = root / "analyses"
            db_path = root / "project_builder.sqlite3"
            initialize_database(db_path)
            config = AppConfig(
                module_name="project_builder",
                host="127.0.0.1",
                port=8003,
                base_dir=root,
                project_root=root,
                data_dir=root,
                logs_dir=root,
                db_path=db_path,
                log_path=root / "project_builder.log",
                prompts_dir=root,
                analysis_dir=analysis_dir,
                ingest_registry_db_path=root / "ingest.sqlite3",
                ingest_registry_base_dir=root,
                doc_classifier_db_path=root / "doc_classifier.sqlite3",
                openai_api_key="",
                openai_model="gpt-4.1-mini",
                openai_timeout_seconds=180,
                openai_max_input_chars_per_request=18000,
            )
            registry = _FakeRegistryReader(
                {
                    "cab-a": [_document(101, "cab-a", "project-a.pdf"), _document(201, "cab-a", "doc-a.pdf")],
                    "cab-b": [_document(102, "cab-b", "project-b.pdf"), _document(202, "cab-b", "doc-b.pdf")],
                }
            )
            runner = ProjectAnalysisRunner(
                config=config,
                repository=ProjectBuilderRepository(db_path),
                registry_reader=registry,
                ai_client=_FakeAIClient(),
                doc_classifier_reader=None,
            )

            first = runner.run(project_document_id=101, cabinet_id="cab-a", dry_run=True)
            second = runner.run(project_document_id=102, cabinet_id="cab-b", dry_run=True)

            payload_a = json.loads(first.result_path.read_text(encoding="utf-8"))
            payload_b = json.loads(second.result_path.read_text(encoding="utf-8"))
            self.assertEqual(payload_a["cabinet_id"], "cab-a")
            self.assertEqual(payload_b["cabinet_id"], "cab-b")
            self.assertIn("_cabinet_cab-a_", first.run_dir.name)
            self.assertIn("_cabinet_cab-b_", second.run_dir.name)

            store = AnalysisStore(analysis_dir)
            self.assertEqual([item["cabinet_id"] for item in store.load_all("cab-a")], ["cab-a"])
            self.assertEqual([item["cabinet_id"] for item in store.load_all("cab-b")], ["cab-b"])

    def test_analysis_store_falls_back_to_run_dir_cabinet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            analysis_dir = Path(tmp)
            run_dir = analysis_dir / "20260327T120000Z_cabinet_cab-z_project_5"
            run_dir.mkdir(parents=True)
            (run_dir / "project_analysis.json").write_text(
                json.dumps({"project": {"project_name": "Fallback cabinet"}}, ensure_ascii=False),
                encoding="utf-8",
            )

            store = AnalysisStore(analysis_dir)
            items = store.load_all("cab-z")
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["cabinet_id"], "cab-z")

    def test_postprocess_uses_doc_classifier_from_same_cabinet(self) -> None:
        reader = _RecordingDocClassifierReader()
        runner = ProjectAnalysisRunner(
            config=AppConfig(
                module_name="project_builder",
                host="127.0.0.1",
                port=8003,
                base_dir=Path("."),
                project_root=Path("."),
                data_dir=Path("."),
                logs_dir=Path("."),
                db_path=Path("project_builder.sqlite3"),
                log_path=Path("project_builder.log"),
                prompts_dir=Path("."),
                analysis_dir=Path("."),
                ingest_registry_db_path=Path("ingest.sqlite3"),
                ingest_registry_base_dir=Path("."),
                doc_classifier_db_path=Path("doc_classifier.sqlite3"),
                openai_api_key="",
                openai_model="gpt-4.1-mini",
                openai_timeout_seconds=180,
                openai_max_input_chars_per_request=18000,
            ),
            repository=ProjectBuilderRepository(Path("project_builder.sqlite3")),
            registry_reader=_FakeRegistryReader({}),
            ai_client=_FakeAIClient(),
            doc_classifier_reader=reader,
        )
        payload = {
            "modules": [
                {
                    "materials": [
                        {"document_registry_id": "1", "document_name": "", "document_number": "", "document_date": ""}
                    ]
                }
            ],
            "unmatched_documents": [],
        }
        candidate_documents = [_document(1, "cab-special", "snapshot.pdf")]

        result = runner._postprocess_result(payload, candidate_documents, cabinet_id="default")

        self.assertEqual(reader.calls, [("snapshot.pdf", "cab-special")])
        material = result["modules"][0]["materials"][0]
        self.assertEqual(material["document_name"], "cab-special:snapshot.pdf")
        self.assertEqual(material["document_number"], "num-cab-special")


if __name__ == "__main__":
    unittest.main()
