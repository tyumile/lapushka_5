import unittest
from types import SimpleNamespace
import sys
import types
from pathlib import Path
from unittest.mock import patch


openpyxl_stub = types.ModuleType("openpyxl")
openpyxl_stub.load_workbook = lambda *args, **kwargs: None
sys.modules.setdefault("openpyxl", openpyxl_stub)

pypdf_stub = types.ModuleType("pypdf")
pypdf_stub.PdfReader = object
pypdf_stub.PdfWriter = object
sys.modules.setdefault("pypdf", pypdf_stub)

from app.service import DocumentService
from app.pipeline import DocumentProcessor
from ui.templates import _display_status, _next_step_label, render_documents_page


class UiStatusesTest(unittest.TestCase):
    def test_fallback_document_is_marked_for_review(self) -> None:
        document = SimpleNamespace(
            title="fallback.pdf",
            source_file_name="fallback.pdf",
            recognition_status="empty",
            classification_status="needs_review",
            structured_fields=[],
        )

        self.assertEqual(_display_status(document), "Требует проверки")

    def test_successful_document_is_ready(self) -> None:
        document = SimpleNamespace(
            title="ok.pdf",
            source_file_name="ok.pdf",
            recognition_status="done",
            classification_status="done",
            structured_fields=[{"label": "Номер", "value": "123"}],
        )

        self.assertEqual(_display_status(document), "Готово")

    def test_fallback_document_has_human_next_step(self) -> None:
        document = SimpleNamespace(
            title="fallback.pdf",
            source_file_name="fallback.pdf",
            recognition_status="empty",
            classification_status="needs_review",
            structured_fields=[],
        )

        self.assertIn("Проверить тип документа", _next_step_label(document))


class ProcessingEventDetailsTest(unittest.TestCase):
    def test_needs_review_event_mentions_preliminary_type(self) -> None:
        service = DocumentService.__new__(DocumentService)
        document = SimpleNamespace(title="fallback.pdf", source_file_name="fallback.pdf")
        result = {"classification_status": "needs_review", "classification_label": "quality_document"}

        details = service._build_processing_event_details(document, result)

        self.assertIn("не дал подтвержденного распознавания текста", details)
        self.assertIn("предварительный тип quality_document", details)


class DocumentsTableRenderTest(unittest.TestCase):
    def test_documents_page_renders_table_headers(self) -> None:
        document = SimpleNamespace(
            id=1,
            title="кабель.pdf",
            source_file_name="кабель.pdf",
            external_ref="doc-1",
            source_payload='{"source_type":"google_drive","source_url":"https://drive.google.com/drive/folders/demo","source_external_id":"file-123"}',
            recognition_status="done",
            classification_status="done",
            classification_label="quality_document",
            classification_confidence=0.95,
            updated_at="2026-03-27 10:00:00",
            structured_fields=[{"label": "Номер", "value": "123"}],
        )

        html = render_documents_page([document], filter_key="all")

        self.assertIn("<th class=\"sticky-col col-title\">Материал</th>", html)
        self.assertIn("Номер", html)
        self.assertIn(">Файл</a>", html)

    def test_documents_page_prefers_external_links(self) -> None:
        document = SimpleNamespace(
            id=2,
            title="кабель.pdf",
            source_file_name="кабель.pdf",
            external_ref="doc-2",
            source_payload='{"source_type":"google_drive","source_external_id":"file-123"}',
            recognition_status="done",
            classification_status="done",
            classification_label="quality_document",
            classification_confidence=0.95,
            updated_at="2026-03-27 10:00:00",
            structured_fields=[{"label": "Номер", "value": "123"}],
            source_link="https://drive.google.com/file/d/file-123/view",
        )

        html = render_documents_page([document], filter_key="all")

        self.assertIn('href="https://drive.google.com/file/d/file-123/view"', html)


class PipelinePdfRoutingTest(unittest.TestCase):
    def test_pdf_without_text_uses_file_mode_before_fallback(self) -> None:
        processor = DocumentProcessor(
            ai_client=SimpleNamespace(max_input_chars_per_request=1000),
            temp_dir=Path("/tmp"),
            pdf_chunk_size_bytes=10_000_000,
        )
        document = SimpleNamespace(source_file_size=1024)

        with patch.object(processor, "_prepare_pdf_chunks", return_value=[Path("/tmp/test.pdf")]):
            with patch("app.pipeline.read_document_as_text", return_value=("", "pdf_text")):
                recognized_text, input_mode, chunk_paths = processor._prepare_input(document, Path("/tmp/test.pdf"))

        self.assertEqual(recognized_text, "")
        self.assertEqual(input_mode, "file")
        self.assertEqual(chunk_paths, [Path("/tmp/test.pdf")])


if __name__ == "__main__":
    unittest.main()
