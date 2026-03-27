from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote_plus, urlparse

from ui.templates import render_analysis_page, render_project_page, render_projects_page, render_status_page


def run_server(host: str, port: int, service: object) -> None:
    handler_class = build_handler(service)
    server = ThreadingHTTPServer((host, port), handler_class)
    server.serve_forever()


def build_handler(service: object) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            query = parse_qs(parsed.query)
            cabinet_id = query.get("cabinet_id", ["default"])[0] or "default"
            message = query.get("message", [""])[0]

            if path == "/":
                self._html_response(render_status_page(service.get_dashboard(cabinet_id=cabinet_id), cabinet_id, message))
                return

            if path == "/projects":
                self._html_response(render_projects_page(service.list_projects(cabinet_id=cabinet_id), cabinet_id))
                return

            if path == "/analysis/latest":
                analysis = service.get_latest_analysis(cabinet_id=cabinet_id)
                if analysis is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._html_response(render_analysis_page(analysis, cabinet_id))
                return

            if path.startswith("/analysis/"):
                analysis_id = self._extract_analysis_id(path)
                if analysis_id is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                analysis = service.get_analysis(analysis_id, cabinet_id=cabinet_id)
                if analysis is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._html_response(render_analysis_page(analysis, cabinet_id))
                return

            if path.startswith("/projects/"):
                project_id = self._extract_project_id(path)
                if project_id is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                project_payload = service.get_project(project_id, cabinet_id=cabinet_id)
                if project_payload is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._html_response(render_project_page(project_payload, cabinet_id))
                return

            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            if path != "/analysis/run":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content_length = int(self.headers.get("Content-Length", "0") or 0)
            payload = self.rfile.read(content_length).decode("utf-8")
            form = parse_qs(payload)
            cabinet_id = form.get("cabinet_id", ["default"])[0] or "default"
            success, message = service.trigger_project_analysis(cabinet_id=cabinet_id)
            redirect_target = f"/?cabinet_id={quote_plus(cabinet_id)}&message={quote_plus(message)}"
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", redirect_target)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

        def _extract_project_id(self, path: str) -> int | None:
            parts = path.strip("/").split("/")
            if len(parts) != 2 or parts[0] != "projects":
                return None
            return int(parts[1]) if parts[1].isdigit() else None

        def _extract_analysis_id(self, path: str) -> int | None:
            parts = path.strip("/").split("/")
            if len(parts) != 2 or parts[0] != "analysis":
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
