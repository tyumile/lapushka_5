from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from ui.templates import (
    render_document_page,
    render_documents_page,
    render_status_page,
)


def build_server(host: str, port: int, service: object) -> ThreadingHTTPServer:
    handler_class = build_handler(service)
    return ThreadingHTTPServer((host, port), handler_class)


def build_handler(service: object) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"

            if path == "/":
                self._html_response(render_status_page(service.get_dashboard()))
                return

            if path == "/documents":
                self._html_response(render_documents_page(service.list_documents()))
                return

            if path.startswith("/documents/"):
                document_id = self._extract_document_id(path)
                if document_id is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                document = service.get_document(document_id)
                if document is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._html_response(render_document_page(document))
                return

            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")
            if path.startswith("/documents/") and path.endswith("/rerun"):
                document_id = self._extract_document_id(path.removesuffix("/rerun"))
                if document_id is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                try:
                    service.rerun_document(document_id)
                except ValueError:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header("Location", f"/documents/{document_id}")
                self.end_headers()
                return

            self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:
            return

        def _extract_document_id(self, path: str) -> int | None:
            parts = path.strip("/").split("/")
            if len(parts) != 2 or parts[0] != "documents":
                return None
            return int(parts[1]) if parts[1].isdigit() else None

        def _html_response(self, payload: str) -> None:
            content = payload.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    return Handler
