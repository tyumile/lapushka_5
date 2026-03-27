import sys
import tempfile
import types
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace


openpyxl_stub = types.ModuleType("openpyxl")
openpyxl_stub.load_workbook = lambda *args, **kwargs: None
sys.modules.setdefault("openpyxl", openpyxl_stub)

pypdf_stub = types.ModuleType("pypdf")
pypdf_stub.PdfReader = object
pypdf_stub.PdfWriter = object
sys.modules.setdefault("pypdf", pypdf_stub)

from app.registry_source import RegistryFileRecord
from app.service import DocumentService
from db.repository import DocumentRepository
from db.setup import initialize_database
from ui.server import build_handler
from ui.templates import render_document_page, render_documents_page, render_status_page


def _registry_file(cabinet_id: str, external_id: str, signature: str) -> RegistryFileRecord:
    return RegistryFileRecord(
        cabinet_id=cabinet_id,
        external_ref=f"ingest_registry:{cabinet_id}:source:{external_id}",
        source_external_id=external_id,
        title=f"{external_id}.pdf",
        source_module="ingest_registry",
        source_name="source",
        source_type="local",
        source_url="",
        file_name=f"{external_id}.pdf",
        relative_file_path=f"uploads/{external_id}.pdf",
        absolute_file_path=Path(f"/tmp/{external_id}.pdf"),
        file_size=123,
        file_date="2026-03-27",
        modified_at="2026-03-27 10:00:00",
        page_count=1,
        status="ready",
        source_signature=signature,
    )


def _ui_document(document_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=document_id,
        title="Кабель.pdf",
        source_file_name="Кабель.pdf",
        external_ref=f"ext-{document_id}",
        source_status="received",
        recognition_status="done",
        classification_status="done",
        classification_label="quality_document",
        classification_confidence=0.95,
        classification_reason="Проверено",
        processing_notes="",
        source_payload='{"source_type":"google_drive","source_url":"https://drive.google.com/drive/folders/demo","source_external_id":"file-123"}',
        extracted_features="{}",
        structured_data='{"fields":[{"label":"Номер","value":"123"}]}',
        structured_fields=[{"label": "Номер", "value": "123"}],
        recognized_text="Текст",
        error_message="",
        updated_at="2026-03-27 10:00:00",
        source_file_path="uploads/Кабель.pdf",
    )


class RepositoryCabinetIsolationTest(unittest.TestCase):
    def test_sync_does_not_delete_other_cabinet_documents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "doc_classifier.sqlite3"
            initialize_database(db_path)
            repository = DocumentRepository(db_path)

            repository.sync_registry_documents([_registry_file("alpha", "one", "sig-a")], cabinet_id="alpha")
            repository.sync_registry_documents([_registry_file("beta", "one", "sig-b")], cabinet_id="beta")

            stats = repository.sync_registry_documents([], cabinet_id="alpha")

            self.assertEqual(stats["deleted"], 1)
            self.assertEqual(len(repository.list_documents(cabinet_id="alpha")), 0)
            self.assertEqual(len(repository.list_documents(cabinet_id="beta")), 1)


class UiCabinetIdTest(unittest.TestCase):
    def test_status_page_keeps_cabinet_id_in_sync_controls(self) -> None:
        html = render_status_page(
            {
                "status": {
                    "total_documents": 1,
                    "recognition_done": 1,
                    "classification_done": 1,
                    "pending_review": 0,
                    "last_event": None,
                },
                "working_document_groups": [],
            },
            cabinet_id="cab-7",
        )

        self.assertIn('action="sync?cabinet_id=cab-7"', html)
        self.assertIn('href="documents?cabinet_id=cab-7"', html)

    def test_documents_and_rerun_links_keep_cabinet_id(self) -> None:
        document = _ui_document()

        list_html = render_documents_page([document], filter_key="all", cabinet_id="cab-7")
        detail_html = render_document_page(document, cabinet_id="cab-7")

        self.assertIn('href="./1/file?cabinet_id=cab-7"', list_html)
        self.assertIn('action="1/rerun?cabinet_id=cab-7"', detail_html)
        self.assertIn('href=".?cabinet_id=cab-7"', detail_html)


class ServiceCabinetSyncTest(unittest.TestCase):
    def test_sync_for_cabinet_creates_documents_visible_in_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "doc_classifier.sqlite3"
            initialize_database(db_path)
            repository = DocumentRepository(db_path)
            test_file = Path(tmp_dir) / "sample.pdf"
            test_file.write_text("sample", encoding="utf-8")
            registry_file = RegistryFileRecord(
                cabinet_id="111",
                external_ref="ingest_registry:111:source:file-1",
                source_external_id="file-1",
                title="sample.pdf",
                source_module="ingest_registry",
                source_name="source",
                source_type="local",
                source_url="",
                file_name="sample.pdf",
                relative_file_path="sample.pdf",
                absolute_file_path=test_file,
                file_size=6,
                file_date="2026-03-27",
                modified_at="2026-03-27 10:00:00",
                page_count=1,
                status="ready",
                source_signature="sig-1",
            )
            registry_reader = SimpleNamespace(
                base_dir=Path(tmp_dir),
                list_ready_files=lambda cabinet_id="default": [registry_file] if cabinet_id == "111" else [],
                get_file_by_external_ref=lambda external_ref, cabinet_id="default": registry_file if cabinet_id == "111" else None,
            )
            processor = SimpleNamespace(
                process_document=lambda document, file_path: {
                    "recognition_status": "done",
                    "classification_status": "done",
                    "recognized_text": "sample",
                    "extracted_features": "{}",
                    "classification_label": "quality_document",
                    "classification_reason": "ok",
                    "classification_confidence": 1.0,
                    "error_message": "",
                    "structured_data": '{"fields":[{"label":"Номер","value":"123"}]}',
                    "processing_notes": "",
                },
                fallback_result_from_filename=lambda document, file_path: {},
            )
            fetcher = SimpleNamespace(resolve_file=lambda record: test_file)
            service = DocumentService(repository, registry_reader, processor, fetcher)

            service.sync_registry_documents(cabinet_id="111")
            dashboard = service.get_dashboard(cabinet_id="111")

            self.assertEqual(dashboard["status"]["total_documents"], 1)
            self.assertEqual(len(dashboard["documents"]), 1)
            self.assertEqual(dashboard["documents"][0].title, "sample.pdf")
            self.assertEqual(dashboard["status"]["last_event"]["event_type"], "document_processed")

    def test_sync_continues_when_one_document_fails_for_same_cabinet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "doc_classifier.sqlite3"
            initialize_database(db_path)
            repository = DocumentRepository(db_path)
            ok_file = Path(tmp_dir) / "ok.pdf"
            ok_file.write_text("sample", encoding="utf-8")
            broken_file = _registry_file("111", "broken", "sig-broken")
            ok_registry_file = _registry_file("111", "ok", "sig-ok")
            records = {
                broken_file.external_ref: broken_file,
                ok_registry_file.external_ref: ok_registry_file,
            }
            registry_reader = SimpleNamespace(
                base_dir=Path(tmp_dir),
                list_ready_files=lambda cabinet_id="default": list(records.values()) if cabinet_id == "111" else [],
                get_file_by_external_ref=lambda external_ref, cabinet_id="default": records.get(external_ref) if cabinet_id == "111" else None,
            )

            def resolve_file(record):
                if record.source_external_id == "broken":
                    raise RuntimeError("boom")
                return ok_file

            processor = SimpleNamespace(
                process_document=lambda document, file_path: {
                    "recognition_status": "done",
                    "classification_status": "done",
                    "recognized_text": "sample",
                    "extracted_features": "{}",
                    "classification_label": "quality_document",
                    "classification_reason": "ok",
                    "classification_confidence": 1.0,
                    "error_message": "",
                    "structured_data": '{"fields":[{"label":"Номер","value":"123"}]}',
                    "processing_notes": "",
                },
                fallback_result_from_filename=lambda document, file_path: {
                    "recognition_status": "empty",
                    "classification_status": "needs_review",
                    "recognized_text": "",
                    "extracted_features": "{}",
                    "classification_label": "quality_document",
                    "classification_reason": "fallback",
                    "classification_confidence": 0.2,
                    "error_message": "",
                    "structured_data": '{"fields":[]}',
                    "processing_notes": "",
                },
            )
            fetcher = SimpleNamespace(resolve_file=resolve_file)
            service = DocumentService(repository, registry_reader, processor, fetcher)

            service.sync_registry_documents(cabinet_id="111")

            documents = repository.list_documents(cabinet_id="111")
            self.assertEqual(len(documents), 2)
            processed = {item.external_ref: item for item in documents}
            self.assertEqual(processed[ok_registry_file.external_ref].classification_status, "done")
            self.assertEqual(processed[broken_file.external_ref].classification_status, "failed")
            self.assertGreaterEqual(
                repository.get_status_counts(cabinet_id="111")["total_documents"],
                2,
            )


class FileHandlerRedirectTest(unittest.TestCase):
    def test_file_route_redirects_to_external_source_link(self) -> None:
        service = SimpleNamespace(
            get_document_source_link=lambda document_id, cabinet_id="default": "https://disk.yandex.ru/i/demo-file",
            get_document_file=lambda document_id, cabinet_id="default": None,
            get_dashboard=lambda cabinet_id="default": {},
            list_documents=lambda cabinet_id="default": [],
            get_document=lambda document_id, cabinet_id="default": None,
        )
        handler_class = build_handler(service)
        handler = handler_class.__new__(handler_class)
        handler.path = "/documents/1/file?cabinet_id=cab-7"
        handler.command = "GET"
        handler.request_version = "HTTP/1.1"
        handler.rfile = BytesIO()
        handler.wfile = BytesIO()
        handler.client_address = ("127.0.0.1", 12345)
        handler.server = SimpleNamespace()
        headers: dict[str, str] = {}
        status_codes: list[int] = []
        handler.send_response = lambda code: status_codes.append(code)
        handler.send_header = lambda key, value: headers.__setitem__(key, value)
        handler.end_headers = lambda: None
        handler.send_error = lambda code: status_codes.append(code)

        handler.do_GET()

        self.assertEqual(status_codes[0], 303)
        self.assertEqual(headers["Location"], "https://disk.yandex.ru/i/demo-file")


if __name__ == "__main__":
    unittest.main()
