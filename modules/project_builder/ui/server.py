from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from ui.templates import render_project_page, render_projects_page, render_status_page


def run_server(host: str, port: int, service: object) -> None:
    handler_class = build_handler(service)
    server = ThreadingHTTPServer((host, port), handler_class)
    server.serve_forever()


def build_handler(service: object) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"

            if path == "/":
                self._html_response(render_status_page(service.get_dashboard()))
                return

            if path == "/projects":
                self._html_response(render_projects_page(service.list_projects()))
                return

            if path.startswith("/projects/"):
                project_id = self._extract_project_id(path)
                if project_id is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                project_payload = service.get_project(project_id)
                if project_payload is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._html_response(render_project_page(project_payload))
                return

            self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:
            return

        def _extract_project_id(self, path: str) -> int | None:
            parts = path.strip("/").split("/")
            if len(parts) != 2 or parts[0] != "projects":
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
