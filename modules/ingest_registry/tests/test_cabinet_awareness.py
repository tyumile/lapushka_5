import io
import types
import unittest

from ui.http import IngestRegistryHandler


class StubService:
    def __init__(self) -> None:
        self.dashboard_calls: list[tuple[str, str]] = []
        self.add_source_calls: list[tuple[str, str, str]] = []
        self.upload_calls: list[tuple[str, bytes, str]] = []
        self.sync_calls: list[tuple[int, str]] = []

    def dashboard(self, source_filter: str = "all", cabinet_id: str = "default") -> dict:
        self.dashboard_calls.append((source_filter, cabinet_id))
        return {
            "cabinet_id": cabinet_id,
            "db_path": "data/ingest_registry.sqlite3",
            "files": [
                {
                    "file_name": "Документ.pdf",
                    "file_path": "data/storage/uploads/Документ.pdf",
                    "source_name": "Локальное хранилище",
                    "source_url": "",
                    "source_type": "local_upload",
                    "status": "ready",
                    "file_size": 1024,
                    "page_count": 3,
                    "external_id": "upload:Документ.pdf",
                    "created_at": "2026-03-27T10:00:00+00:00",
                    "created_at_remote": "2026-03-27T10:00:00+00:00",
                    "modified_at_remote": "2026-03-27T10:00:00+00:00",
                    "updated_at": "2026-03-27T10:00:00+00:00",
                }
            ],
            "sources": [
                {
                    "id": 7,
                    "cabinet_id": cabinet_id,
                    "title": "Локальное хранилище",
                    "source_url": "",
                    "sync_status": "ready",
                    "last_total_files": 1,
                    "last_added_files": 0,
                    "last_changed_files": 0,
                    "last_deleted_files": 0,
                    "last_sync_at": "2026-03-27T10:00:00+00:00",
                    "sync_message": "Синхронизация завершена.",
                    "added_at": "2026-03-27T09:59:00+00:00",
                }
            ],
            "recent_logs": [
                {
                    "action_type": "sync",
                    "status": "done",
                    "summary": "Синхронизация завершена",
                    "artifacts": "ok",
                    "created_at": "2026-03-27T10:00:00+00:00",
                }
            ],
            "source_filter": source_filter,
        }

    def add_source(self, source_type: str, source_url: str, cabinet_id: str = "default") -> int:
        self.add_source_calls.append((source_type, source_url, cabinet_id))
        return 1

    def handle_upload(self, filename: str, payload: bytes, cabinet_id: str = "default") -> None:
        self.upload_calls.append((filename, payload, cabinet_id))

    def sync_source(self, source_id: int, cabinet_id: str = "default") -> None:
        self.sync_calls.append((source_id, cabinet_id))


def build_handler(service: StubService, path: str, body: bytes = b"", content_type: str = ""):
    handler_cls = IngestRegistryHandler.build(service)
    handler = handler_cls.__new__(handler_cls)
    handler.path = path
    handler.headers = {
        "Content-Length": str(len(body)),
        "Content-Type": content_type,
    }
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler._status = None
    handler._headers = {}
    handler._error = None

    def send_response(self, code, message=None):
        self._status = code

    def send_header(self, key, value):
        self._headers[key] = value

    def end_headers(self):
        return None

    def send_error(self, code, message=None):
        self._error = (code, message)

    handler.send_response = types.MethodType(send_response, handler)
    handler.send_header = types.MethodType(send_header, handler)
    handler.end_headers = types.MethodType(end_headers, handler)
    handler.send_error = types.MethodType(send_error, handler)
    return handler


def multipart_body(filename: str, payload: bytes) -> tuple[bytes, str]:
    boundary = "----cabinet-aware-boundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + payload + f"\r\n--{boundary}--\r\n".encode("utf-8")
    return body, f"multipart/form-data; boundary={boundary}"


class CabinetAwareHttpTestCase(unittest.TestCase):
    def test_get_renders_forms_and_actions_with_current_cabinet(self) -> None:
        for cabinet_id in ("default", "test"):
            with self.subTest(cabinet_id=cabinet_id):
                service = StubService()
                handler = build_handler(
                    service,
                    f"/?cabinet_id={cabinet_id}&source=local_upload&sort=name&density=compact",
                )

                handler.do_GET()

                html = handler.wfile.getvalue().decode("utf-8")
                self.assertEqual(service.dashboard_calls, [("local_upload", cabinet_id)])
                self.assertIn(f'action="/sources/add?cabinet_id={cabinet_id}"', html)
                self.assertIn(f'action="/upload?cabinet_id={cabinet_id}"', html)
                self.assertIn(f'action="/sync/7?cabinet_id={cabinet_id}"', html)
                self.assertIn(f'href="/?cabinet_id={cabinet_id}&source=google_drive&sort=name&density=compact"', html)
                self.assertIn('class="details-toggle"', html)
                self.assertIn('href="#file-details-', html)
                self.assertIn('class="details-row ', html)
                self.assertIn('colspan="7"', html)

    def test_post_routes_preserve_cabinet_id(self) -> None:
        for cabinet_id in ("default", "test"):
            with self.subTest(cabinet_id=cabinet_id, route="sources_add"):
                service = StubService()
                body = b"source_type=google_drive&source_url=https%3A%2F%2Fexample.com%2Ffolder"
                handler = build_handler(
                    service,
                    f"/sources/add?cabinet_id={cabinet_id}",
                    body=body,
                    content_type="application/x-www-form-urlencoded",
                )
                handler.do_POST()
                self.assertEqual(service.add_source_calls, [("google_drive", "https://example.com/folder", cabinet_id)])
                self.assertEqual(handler._headers["Location"], f"/?cabinet_id={cabinet_id}")

            with self.subTest(cabinet_id=cabinet_id, route="upload"):
                service = StubService()
                body, content_type = multipart_body("cabinet.txt", b"payload")
                handler = build_handler(
                    service,
                    f"/upload?cabinet_id={cabinet_id}",
                    body=body,
                    content_type=content_type,
                )
                handler.do_POST()
                self.assertEqual(service.upload_calls, [("cabinet.txt", b"payload", cabinet_id)])
                self.assertEqual(handler._headers["Location"], f"/?cabinet_id={cabinet_id}")

            with self.subTest(cabinet_id=cabinet_id, route="sync"):
                service = StubService()
                handler = build_handler(service, f"/sync/17?cabinet_id={cabinet_id}")
                handler.do_POST()
                self.assertEqual(service.sync_calls, [(17, cabinet_id)])
                self.assertEqual(handler._headers["Location"], f"/?cabinet_id={cabinet_id}")


if __name__ == "__main__":
    unittest.main()
