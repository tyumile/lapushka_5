from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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
            query = parse_qs(parsed.query)
            cabinet_id = self._cabinet_id(parsed.query)

            if path == "/":
                density = query.get("density", ["normal"])[0]
                self._html_response(render_status_page(service.get_dashboard(cabinet_id=cabinet_id), cabinet_id=cabinet_id, density=density))
                return

            if path == "/documents":
                filter_key = query.get("filter", ["all"])[0]
                density = query.get("density", ["normal"])[0]
                sort_key = query.get("sort", ["attention"])[0]
                self._html_response(
                    render_documents_page(
                        service.list_documents(cabinet_id=cabinet_id),
                        filter_key,
                        cabinet_id=cabinet_id,
                        density=density,
                        sort_key=sort_key,
                    )
                )
                return

            if path.startswith("/documents/") and path.endswith("/file"):
                document_id = self._extract_document_id(path)
                if document_id is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                try:
                    source_link = service.get_document_source_link(document_id, cabinet_id=cabinet_id)
                except ValueError:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                if source_link:
                    self.send_response(HTTPStatus.SEE_OTHER)
                    self.send_header("Location", source_link)
                    self.end_headers()
                    return
                try:
                    file_path, content_type = service.get_document_file(document_id, cabinet_id=cabinet_id)
                except (ValueError, FileNotFoundError):
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._file_response(file_path, content_type)
                return

            if path.startswith("/documents/"):
                document_id = self._extract_document_id(path)
                if document_id is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                document = service.get_document(document_id, cabinet_id=cabinet_id)
                if document is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._html_response(render_document_page(document, cabinet_id=cabinet_id))
                return

            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")
            cabinet_id = self._cabinet_id(parsed.query)
            if path == "/sync":
                service.sync_registry_documents(cabinet_id=cabinet_id)
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header("Location", self._with_cabinet(".", cabinet_id))
                self.end_headers()
                return

            if path.startswith("/documents/") and path.endswith("/rerun"):
                document_id = self._extract_document_id(path.removesuffix("/rerun"))
                if document_id is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                try:
                    service.rerun_document(document_id, cabinet_id=cabinet_id)
                except ValueError:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header("Location", self._with_cabinet(f"../{document_id}", cabinet_id))
                self.end_headers()
                return

            self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:
            return

        def _extract_document_id(self, path: str) -> int | None:
            parts = path.strip("/").split("/")
            if len(parts) < 2 or parts[0] != "documents":
                return None
            return int(parts[1]) if parts[1].isdigit() else None

        def _cabinet_id(self, query: str) -> str:
            return parse_qs(query).get("cabinet_id", ["default"])[0] or "default"

        def _with_cabinet(self, path: str, cabinet_id: str) -> str:
            if not cabinet_id or cabinet_id == "default":
                return path
            separator = "&" if "?" in path else "?"
            return f"{path}{separator}cabinet_id={cabinet_id}"

        def _html_response(self, payload: str) -> None:
            content = payload.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def _file_response(self, file_path: Path, content_type: str) -> None:
            content = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Content-Disposition", f'inline; filename="{file_path.name}"')
            self.end_headers()
            self.wfile.write(content)

    return Handler
