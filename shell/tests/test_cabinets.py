from __future__ import annotations

import json
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import main


class ShellCabinetsTest(unittest.TestCase):
    def test_generate_cabinet_id_uses_fallback_and_suffix(self) -> None:
        existing = {"cabinet", "cabinet-2"}
        self.assertEqual(main.generate_cabinet_id("ЖК Южный корпус", existing), "cabinet-3")

    def test_parse_cabinets_combines_default_env_and_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cabinets_file = Path(tmp_dir) / "cabinets.json"
            cabinets_file.write_text(
                json.dumps(
                    [
                        {"id": "alpha", "title": "Альфа", "status": "active", "created_at": "2026-03-27T00:00:00+00:00"},
                        {"id": "default", "title": "Переопределение", "status": "active", "created_at": ""},
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(main, "CABINETS_FILE", cabinets_file), patch.dict(
                "os.environ",
                {"SHELL_CABINETS": "beta:Бета"},
                clear=False,
            ):
                cabinets = main.parse_cabinets()

        self.assertEqual([item["id"] for item in cabinets[:3]], ["default", "beta", "alpha"])
        self.assertEqual(cabinets[0]["title"], "Основной кабинет")

    def test_create_cabinet_persists_new_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_dir = Path(tmp_dir) / "data"
            cabinets_file = data_dir / "cabinets.json"

            with patch.object(main, "DATA_DIR", data_dir), patch.object(main, "CABINETS_FILE", cabinets_file):
                cabinet = main.create_cabinet("ЖК Север")

            saved = json.loads(cabinets_file.read_text(encoding="utf-8"))

        self.assertEqual(cabinet["title"], "ЖК Север")
        self.assertEqual(cabinet["id"], "cabinet")
        self.assertEqual(saved[0]["id"], "cabinet")

    def test_build_upstream_query_always_uses_current_cabinet(self) -> None:
        query = main.build_upstream_query("alpha", "sort=updated&cabinet_id=default")
        self.assertEqual(query, "sort=updated&cabinet_id=alpha")

    def test_normalize_module_url_rewrites_absolute_module_path_without_duplicate_segment(self) -> None:
        value = main.normalize_module_url("/sources/add?cabinet_id=111", "111", "sources", "/")
        self.assertEqual(value, "/cabinet/111/sources/add")

    def test_normalize_module_url_rewrites_dot_query_without_duplicate_cabinet(self) -> None:
        value = main.normalize_module_url(".?cabinet_id=111&filter=ready", "111", "documents", "/documents")
        self.assertEqual(value, "/cabinet/111/documents/list?filter=ready")

    def test_rewrite_upstream_location_keeps_shell_route(self) -> None:
        value = main.rewrite_upstream_location(".?cabinet_id=111", "111", "documents", "/documents")
        self.assertEqual(value, "/cabinet/111/documents/list")

    def test_rewrite_upstream_location_maps_documents_sync_redirect_back_to_status_page(self) -> None:
        value = main.rewrite_upstream_location(".?cabinet_id=111", "111", "documents", "/sync")
        self.assertEqual(value, "/cabinet/111/documents")

    def test_rewrite_html_updates_formaction_without_duplicate_query(self) -> None:
        _, _, body = main.rewrite_html(
            '<form method="post"><button formaction="./sync?cabinet_id=111" type="submit">Синхронизировать</button></form>',
            "111",
            "documents",
            "/documents",
        )
        self.assertIn('formaction="/cabinet/111/documents/sync"', body)
        self.assertNotIn("cabinet_id=111", body)

    def test_fetch_module_response_does_not_read_redirect_body(self) -> None:
        redirect_error = HTTPError(
            url="http://127.0.0.1:8001/sources/add?cabinet_id=111",
            code=302,
            msg="Found",
            hdrs={"Location": "/?cabinet_id=111"},
            fp=BytesIO(b""),
        )
        redirect_error.read = Mock(side_effect=AssertionError("redirect body should not be read"))  # type: ignore[method-assign]
        opener = Mock()
        opener.open.side_effect = redirect_error

        with patch.object(main, "build_opener", return_value=opener):
            status, headers, payload = main.fetch_module_response(
                cabinet_id="111",
                module_name="sources",
                module_path="/sources/add",
                method="POST",
                body=b"source_type=google_drive",
                headers={"Content-Type": "application/x-www-form-urlencoded", "__query__": ""},
            )

        self.assertEqual(status, 302)
        self.assertEqual(headers["Location"], "/?cabinet_id=111")
        self.assertEqual(payload, b"")

    def test_fetch_module_response_returns_gateway_timeout_for_slow_post(self) -> None:
        opener = Mock()
        opener.open.side_effect = TimeoutError("slow sync")

        with patch.object(main, "build_opener", return_value=opener):
            status, headers, payload = main.fetch_module_response(
                cabinet_id="111",
                module_name="sources",
                module_path="/sources/add",
                method="POST",
                body=b"source_type=google_drive",
                headers={"Content-Type": "application/x-www-form-urlencoded", "__query__": ""},
            )

        self.assertEqual(status, 504)
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("отвечает слишком долго", payload.decode("utf-8"))

    def test_resolve_public_module_path_maps_clean_documents_route_back_to_upstream(self) -> None:
        self.assertEqual(main.resolve_public_module_path("documents", "/5"), "/documents/5")

    def test_resolve_public_module_path_maps_clean_project_route_back_to_upstream(self) -> None:
        self.assertEqual(main.resolve_public_module_path("project", "/7"), "/projects/7")


if __name__ == "__main__":
    unittest.main()
