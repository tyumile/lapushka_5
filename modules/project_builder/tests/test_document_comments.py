import json
import tempfile
import unittest
from pathlib import Path

from app.analysis_store import AnalysisStore
from ui.templates import _document_reference_summary


class DocumentCommentTests(unittest.TestCase):
    def test_reference_summary_uses_bracketed_date_without_duplicate_number(self) -> None:
        summary = _document_reference_summary(
            {
                "document_name": "Сертификат соответствия № 04ИДЮ101.RU.C05459",
                "document_number": "04ИДЮ101.RU.C05459",
                "document_date": "21.03.2023",
            }
        )

        self.assertEqual(summary, "Сертификат соответствия № 04ИДЮ101.RU.C05459 [от 21.03.2023]")

    def test_analysis_store_enriches_file_name_from_request_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            analysis_dir = Path(tmp)
            run_dir = analysis_dir / "20260327T120000Z_cabinet_default_project_5"
            run_dir.mkdir(parents=True)

            (run_dir / "project_analysis.json").write_text(
                json.dumps(
                    {
                        "cabinet_id": "default",
                        "project": {"project_name": "Test project"},
                        "modules": [
                            {
                                "materials": [
                                    {
                                        "material_name": "Лоток EKF",
                                        "document_registry_id": "114",
                                        "document_name": "12,13 лоток крышка.pdf",
                                        "document_number": "",
                                        "document_date": "",
                                    }
                                ]
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (run_dir / "request_context.json").write_text(
                json.dumps(
                    {
                        "candidate_documents": [
                            {
                                "id": 114,
                                "doc_classifier": {
                                    "fields": [
                                        {"name": "document_name", "value": "Сертификат соответствия"},
                                        {"name": "document_number", "value": "04ИДЮ101.RU.C05459"},
                                        {"name": "issue_date", "value": "21.03.2023"},
                                    ]
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = AnalysisStore(analysis_dir).load_all("default")[0]
            material = payload["modules"][0]["materials"][0]

            self.assertEqual(material["document_name"], "Сертификат соответствия")
            self.assertEqual(material["document_number"], "04ИДЮ101.RU.C05459")
            self.assertEqual(material["document_date"], "21.03.2023")


if __name__ == "__main__":
    unittest.main()
