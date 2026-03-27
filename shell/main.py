from __future__ import annotations

import html
import json
import logging
import mimetypes
import os
import posixpath
import re
import socket
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


BASE_DIR = Path(__file__).resolve().parent
UI_DIR = BASE_DIR / "ui"
STYLE_PATH = UI_DIR / "styles.css"
DATA_DIR = BASE_DIR / "data"
CABINETS_FILE = DATA_DIR / "cabinets.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8030
DEFAULT_CABINET_ID = "default"
CABINET_SEGMENT_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

MODULES = {
    "sources": {
        "label": "Источники",
        "port": 8001,
        "base_path": "/sources",
        "description": "Локальная загрузка файлов, реестр и состояние источников импорта.",
    },
    "documents": {
        "label": "Рабочая документация",
        "port": 8002,
        "base_path": "/documents",
        "description": "Документы, распознавание текста и классификация внутри отдельного модуля.",
    },
    "project": {
        "label": "Проект",
        "port": 8003,
        "base_path": "/project",
        "description": "Проекты, связи между документами и дефициты материалов.",
    },
}

LEGACY_REDIRECTS = {
    "/index.html": f"/cabinet/{DEFAULT_CABINET_ID}/sources",
    "/sources.html": f"/cabinet/{DEFAULT_CABINET_ID}/sources",
    "/documents.html": f"/cabinet/{DEFAULT_CABINET_ID}/documents",
    "/project.html": f"/cabinet/{DEFAULT_CABINET_ID}/project",
}

REDIRECT_STATUSES = {
    HTTPStatus.MOVED_PERMANENTLY,
    HTTPStatus.FOUND,
    HTTPStatus.SEE_OTHER,
    HTTPStatus.TEMPORARY_REDIRECT,
    HTTPStatus.PERMANENT_REDIRECT,
}


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [shell] %(message)s",
    )


def get_server_address() -> tuple[str, int]:
    host = os.getenv("SHELL_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
    port_value = os.getenv("SHELL_PORT", str(DEFAULT_PORT)).strip() or str(DEFAULT_PORT)

    try:
        port = int(port_value)
    except ValueError as error:
        raise ValueError(f"Invalid SHELL_PORT value: {port_value}") from error

    return host, port


def read_shell_styles() -> str:
    if not STYLE_PATH.exists():
        raise FileNotFoundError(f"Shell stylesheet is missing: {STYLE_PATH}")
    return STYLE_PATH.read_text(encoding="utf-8")


def parse_cabinets() -> list[dict[str, str]]:
    cabinets: list[dict[str, str]] = []
    seen: set[str] = set()

    for cabinet in [build_default_cabinet(), *read_env_cabinets(), *read_persisted_cabinets()]:
        cabinet_id = cabinet["id"]
        if cabinet_id in seen:
            continue
        seen.add(cabinet_id)
        cabinets.append(cabinet)

    return cabinets


def build_default_cabinet() -> dict[str, str]:
    return {
        "id": DEFAULT_CABINET_ID,
        "slug": DEFAULT_CABINET_ID,
        "title": "Основной кабинет",
        "status": "active",
        "created_at": "",
    }


def read_env_cabinets() -> list[dict[str, str]]:
    raw = os.getenv("SHELL_CABINETS", "").strip()
    if not raw:
        return []

    cabinets: list[dict[str, str]] = []
    for item in raw.split(","):
        entry = item.strip()
        if not entry:
            continue
        cabinet_id, _, title = entry.partition(":")
        cabinet_id = cabinet_id.strip()
        if not CABINET_SEGMENT_RE.match(cabinet_id):
            continue
        cabinets.append(
            {
                "id": cabinet_id,
                "slug": cabinet_id,
                "title": title.strip() or cabinet_id,
                "status": "active",
                "created_at": "",
            }
        )
    return cabinets


def read_persisted_cabinets() -> list[dict[str, str]]:
    if not CABINETS_FILE.exists():
        return []

    try:
        payload = json.loads(CABINETS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logging.exception("Failed to read persisted cabinets from %s", CABINETS_FILE)
        return []

    if not isinstance(payload, list):
        return []

    cabinets: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        cabinet_id = str(item.get("id") or "").strip()
        title = str(item.get("title") or "").strip()
        if not CABINET_SEGMENT_RE.match(cabinet_id):
            continue
        cabinets.append(
            {
                "id": cabinet_id,
                "slug": cabinet_id,
                "title": title or cabinet_id,
                "status": str(item.get("status") or "active"),
                "created_at": str(item.get("created_at") or ""),
            }
        )
    return cabinets


def create_cabinet(title: str) -> dict[str, str]:
    clean_title = " ".join(title.split()).strip()
    if not clean_title:
        raise ValueError("Введите название кабинета.")

    cabinets = parse_cabinets()
    cabinet_id = generate_cabinet_id(clean_title, {item["id"] for item in cabinets})
    cabinet = {
        "id": cabinet_id,
        "slug": cabinet_id,
        "title": clean_title,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    persisted = read_persisted_cabinets()
    persisted.append(cabinet)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CABINETS_FILE.write_text(
        json.dumps(persisted, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return cabinet


def generate_cabinet_id(title: str, existing_ids: set[str]) -> str:
    normalized = title.lower().replace(" ", "-")
    normalized = re.sub(r"[^a-z0-9_-]+", "", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-_")
    base = normalized or "cabinet"

    candidate = base
    suffix = 2
    while candidate in existing_ids:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def get_cabinet(cabinet_id: str) -> dict[str, str] | None:
    for cabinet in parse_cabinets():
        if cabinet["id"] == cabinet_id:
            return cabinet
    return None


def build_cabinet_module_path(cabinet_id: str, module_name: str, module_path: str = "/") -> str:
    normalized_path = module_path if module_path.startswith("/") else f"/{module_path}"
    if normalized_path == "/":
        return f"/cabinet/{cabinet_id}/{module_name}"
    return f"/cabinet/{cabinet_id}/{module_name}{normalized_path}"


def build_public_module_path(cabinet_id: str, module_name: str, upstream_path: str) -> str:
    normalized_path = upstream_path if upstream_path.startswith("/") else f"/{upstream_path}"

    if module_name == "sources":
        if normalized_path == "/sources/add":
            return build_cabinet_module_path(cabinet_id, module_name, "/add")
        return build_cabinet_module_path(cabinet_id, module_name, normalized_path)

    if module_name == "documents":
        if normalized_path == "/documents":
            return build_cabinet_module_path(cabinet_id, module_name, "/list")
        if normalized_path.startswith("/documents/"):
            return build_cabinet_module_path(cabinet_id, module_name, normalized_path[len("/documents") :])
        return build_cabinet_module_path(cabinet_id, module_name, normalized_path)

    if module_name == "project":
        if normalized_path == "/projects":
            return build_cabinet_module_path(cabinet_id, module_name, "/list")
        if normalized_path.startswith("/projects/"):
            return build_cabinet_module_path(cabinet_id, module_name, normalized_path[len("/projects") :])
        return build_cabinet_module_path(cabinet_id, module_name, normalized_path)

    return build_cabinet_module_path(cabinet_id, module_name, normalized_path)


def resolve_public_module_path(module_name: str, module_path: str) -> str:
    normalized_path = module_path if module_path.startswith("/") else f"/{module_path}"

    if module_name == "sources":
        if normalized_path == "/add":
            return "/sources/add"
        return normalized_path

    if module_name == "documents":
        if normalized_path == "/list":
            return "/documents"
        if normalized_path == "/" or normalized_path.startswith("/sync"):
            return normalized_path
        if normalized_path.startswith("/documents"):
            return normalized_path
        return f"/documents{normalized_path}"

    if module_name == "project":
        if normalized_path == "/list":
            return "/projects"
        if normalized_path == "/" or normalized_path.startswith("/analysis"):
            return normalized_path
        if normalized_path.startswith("/projects"):
            return normalized_path
        return f"/projects{normalized_path}"

    return normalized_path


def resolve_legacy_module_route(request_path: str) -> tuple[str, str] | None:
    for module_name, module in MODULES.items():
        base_path = module["base_path"]
        if request_path == base_path:
            return module_name, "/"
        if request_path.startswith(f"{base_path}/"):
            remainder = request_path[len(base_path) :]
            return module_name, remainder or "/"
    return None


def resolve_cabinet_route(request_path: str) -> tuple[str, str, str] | None:
    if request_path == "/cabinet":
        return None
    path = request_path.rstrip("/") or "/"
    if path.startswith("/cabinet/"):
        remainder = path[len("/cabinet/") :]
        cabinet_id, _, module_path = remainder.partition("/")
        if not CABINET_SEGMENT_RE.match(cabinet_id):
            return None
        if not module_path:
            return cabinet_id, "sources", "/"
        if module_path in MODULES:
            return cabinet_id, module_path, "/"
        for module_name in MODULES:
            prefix = f"{module_name}/"
            if module_path.startswith(prefix):
                nested_path = module_path[len(module_name) :]
                normalized_path = nested_path if nested_path.startswith("/") else f"/{nested_path}"
                return cabinet_id, module_name, resolve_public_module_path(module_name, normalized_path)
    return None


def extract_html_parts(document: str) -> tuple[str, str, str]:
    title_match = re.search(r"<title>(.*?)</title>", document, re.IGNORECASE | re.DOTALL)
    title = html.unescape(title_match.group(1).strip()) if title_match else ""

    styles = "\n".join(
        match.group(0)
        for match in re.finditer(r"<style.*?>.*?</style>", document, re.IGNORECASE | re.DOTALL)
    )

    body_match = re.search(r"<body.*?>(.*)</body>", document, re.IGNORECASE | re.DOTALL)
    body = body_match.group(1) if body_match else document
    return title, styles, body


def normalize_module_url(
    original: str,
    cabinet_id: str,
    module_name: str,
    current_module_path: str,
) -> str:
    stripped = original.strip()
    if not stripped or stripped.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return original

    parsed = urlsplit(stripped)
    if parsed.scheme or parsed.netloc:
        return original

    normalized_path = normalize_module_path(parsed.path, cabinet_id, module_name, current_module_path, stripped)
    normalized_query = normalize_module_query(parsed.query)
    return urlunsplit(("", "", normalized_path, normalized_query, parsed.fragment))


def normalize_module_path(
    path: str,
    cabinet_id: str,
    module_name: str,
    current_module_path: str,
    original: str,
) -> str:
    module_root = MODULES[module_name]["base_path"]

    if original.startswith("?"):
        target_path = current_module_path
    elif path.startswith("/"):
        if path == module_root or path.startswith(f"{module_root}/"):
            target_path = path[len(module_root) :] or "/"
        else:
            target_path = path
    else:
        current_page = current_module_path or "/"
        current_dir = posixpath.dirname(current_page.rstrip("/")) or "/"

        if path in {"", "."}:
            if module_name == "documents" and current_page == "/sync":
                target_path = "/"
            else:
                target_path = current_page
        else:
            target_path = posixpath.normpath(posixpath.join(current_dir, path))
            if not target_path.startswith("/"):
                target_path = f"/{target_path}"

    return build_public_module_path(cabinet_id, module_name, target_path)


def normalize_module_query(query: str) -> str:
    pairs = [(key, value) for key, value in parse_qsl(query, keep_blank_values=True) if key != "cabinet_id"]
    return urlencode(pairs)


def rewrite_upstream_location(
    location: str,
    cabinet_id: str,
    module_name: str,
    current_module_path: str,
) -> str:
    normalized = normalize_module_url(location, cabinet_id, module_name, current_module_path)
    return normalized if normalized else build_cabinet_module_path(cabinet_id, module_name, current_module_path)


def rewrite_html(
    document: str,
    cabinet_id: str,
    module_name: str,
    current_module_path: str,
) -> tuple[str, str, str]:
    title, styles, body = extract_html_parts(document)

    def replace_attr(match: re.Match[str]) -> str:
        prefix, quote, value = match.groups()
        normalized = normalize_module_url(value, cabinet_id, module_name, current_module_path)
        return f"{prefix}{quote}{normalized}{quote}"

    rewritten_body = re.sub(
        r"""((?:href|src|action|formaction)=)(["'])(.*?)\2""",
        replace_attr,
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return title, styles, rewritten_body


def build_home_page(error_message: str = "", title_value: str = "") -> bytes:
    shell_styles = read_shell_styles()
    cabinet_cards = []
    for cabinet in parse_cabinets():
        created_at = cabinet.get("created_at", "")
        created_label = ""
        if created_at:
            created_label = f"<p class='cabinet-card-meta'>Создан: {html.escape(created_at[:10])}</p>"
        cabinet_cards.append(
            (
                "<a class='cabinet-card' href='"
                + html.escape(build_cabinet_module_path(cabinet["id"], "sources"))
                + "'>"
                + f"<p class='cabinet-card-eyebrow'>{html.escape(cabinet['id'])}</p>"
                + f"<h2>{html.escape(cabinet['title'])}</h2>"
                + created_label
                + "<p>Открыть shell в контексте выбранного кабинета.</p>"
                + "</a>"
            )
        )

    error_block = (
        "<p class='cabinet-form-error'>"
        + html.escape(error_message)
        + "</p>"
        if error_message
        else ""
    )

    document = f"""<!DOCTYPE html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Выбор кабинета | Shell</title>
    <style>{shell_styles}</style>
  </head>
  <body class="shell-layout">
    <main class="shell-home">
      <section class="shell-home-hero">
        <p class="shell-eyebrow">Lapushka 5</p>
        <h1 class="shell-title">Выбор кабинета</h1>
        <p class="shell-home-text">
          Сначала создайте кабинет или выберите существующий. Shell хранит кабинет только как навигационный
          контекст и передает его в модули через `cabinet_id`.
        </p>
      </section>
      <section class="cabinet-entry panel">
        <div class="cabinet-entry-copy">
          <p class="shell-eyebrow">Новый кабинет</p>
          <h2 class="cabinet-entry-title">Создать рабочий кабинет</h2>
          <p class="shell-home-text">
            Введите понятное название кабинета. Shell сам сформирует `cabinet_id` и сразу откроет модуль
            источников в новом контексте.
          </p>
        </div>
        <form class="cabinet-form" method="post" action="/cabinet/create">
          <label class="cabinet-form-field">
            <span>Название кабинета</span>
            <input
              type="text"
              name="title"
              value="{html.escape(title_value)}"
              placeholder="Например: ЖК Южный корпус А"
              maxlength="120"
              required
            />
          </label>
          <div class="cabinet-form-actions">
            <button class="cabinet-submit" type="submit">Создать и открыть</button>
            <p class="cabinet-form-hint">Системный кабинет <strong>{html.escape(DEFAULT_CABINET_ID)}</strong> остается доступен всегда.</p>
          </div>
          {error_block}
        </form>
      </section>
      <section class="cabinet-list-head">
        <div>
          <p class="shell-eyebrow">Существующие кабинеты</p>
          <h2 class="cabinet-entry-title">Выбрать кабинет</h2>
        </div>
      </section>
      <section class="cabinet-grid">
        {''.join(cabinet_cards)}
      </section>
    </main>
  </body>
</html>
"""
    return document.encode("utf-8")


def build_shell_page(
    cabinet_id: str,
    module_name: str,
    module_title: str,
    module_styles: str,
    module_body: str,
) -> bytes:
    cabinet = get_cabinet(cabinet_id) or {"id": cabinet_id, "title": cabinet_id}
    nav_links = []
    for current_name, module in MODULES.items():
        active_class = " is-active" if current_name == module_name else ""
        nav_links.append(
            (
                f'<a class="top-link{active_class}" href="{build_cabinet_module_path(cabinet_id, current_name)}">'
                f'<span class="top-link-label">{html.escape(module["label"])}</span>'
                f'<span class="top-link-meta">модуль</span>'
                "</a>"
            )
        )

    module = MODULES[module_name]
    shell_styles = read_shell_styles()
    page_title = html.escape(module_title or module["label"])

    document = f"""<!DOCTYPE html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{page_title} | Shell</title>
    <style>{shell_styles}</style>
    {module_styles}
  </head>
  <body class="shell-layout">
    <header class="shell-header">
      <div class="shell-header-inner">
        <div class="shell-brand">
          <div>
            <p class="shell-eyebrow">Lapushka 5</p>
            <h1 class="shell-title">Единый фронт системы</h1>
          </div>
          <div class="shell-cabinet-box">
            <p class="shell-cabinet-label">Текущий кабинет</p>
            <p class="shell-cabinet-title">{html.escape(cabinet["title"])}</p>
            <a class="shell-cabinet-link" href="/">Сменить кабинет</a>
          </div>
        </div>
        <nav class="top-nav" aria-label="Главная навигация">
          {''.join(nav_links)}
        </nav>
      </div>
    </header>
    <main class="shell-main">
      <section class="shell-module-meta">
        <div>
          <p class="shell-module-label">{html.escape(module["label"])}</p>
          <p class="shell-module-description">{html.escape(module["description"])}</p>
        </div>
        <div class="shell-module-side">
          <p class="shell-module-port">порт {module["port"]}</p>
          <p class="shell-module-cabinet">cabinet_id: {html.escape(cabinet_id)}</p>
        </div>
      </section>
      <section class="module-host">
        {module_body}
      </section>
    </main>
  </body>
</html>
"""
    return document.encode("utf-8")


def fetch_module_response(
    cabinet_id: str,
    module_name: str,
    module_path: str,
    method: str,
    body: bytes | None,
    headers: dict[str, str],
) -> tuple[int, dict[str, str], bytes]:
    port = MODULES[module_name]["port"]
    query = headers.pop("__query__", "")
    upstream_url = f"http://127.0.0.1:{port}{module_path}"
    upstream_query = build_upstream_query(cabinet_id, query)
    if upstream_query:
        upstream_url = f"{upstream_url}?{upstream_query}"
    timeout = 90 if method.upper() != "GET" else 10

    request = Request(upstream_url, data=body, method=method)
    for header_name, header_value in headers.items():
        request.add_header(header_name, header_value)

    opener = build_opener(NoRedirectHandler)

    try:
        with opener.open(request, timeout=timeout) as response:
            response_headers = {key: value for key, value in response.headers.items()}
            return response.status, response_headers, response.read()
    except HTTPError as error:
        response_headers = {key: value for key, value in error.headers.items()}
        if error.code in REDIRECT_STATUSES:
            return error.code, response_headers, b""
        return error.code, response_headers, error.read()
    except (TimeoutError, socket.timeout) as error:
        logging.error("Upstream %s timed out after %ss: %s", module_name, timeout, error)
        message = (
            "<div class='shell-error'>"
            f"<h2>{html.escape(MODULES[module_name]['label'])} отвечает слишком долго</h2>"
            "<p>Shell дождался ответа модуля, но операция не завершилась вовремя. "
            "Проверьте страницу еще раз: действие могло уже выполниться.</p>"
            "</div>"
        ).encode("utf-8")
        return HTTPStatus.GATEWAY_TIMEOUT, {"Content-Type": "text/html; charset=utf-8"}, message
    except URLError as error:
        logging.error("Upstream %s is unavailable: %s", module_name, error)
        message = (
            "<div class='shell-error'>"
            f"<h2>{html.escape(MODULES[module_name]['label'])} недоступен</h2>"
            "<p>Shell не смог получить ответ от модуля. Проверьте, что модуль запущен.</p>"
            "</div>"
        ).encode("utf-8")
        return HTTPStatus.BAD_GATEWAY, {"Content-Type": "text/html; charset=utf-8"}, message


class ShellHandler(BaseHTTPRequestHandler):
    server_version = "LapushkaShell/1.1"

    def do_GET(self) -> None:  # noqa: N802
        self.handle_request()

    def do_POST(self) -> None:  # noqa: N802
        self.handle_request(with_body=True)

    def handle_request(self, with_body: bool = False) -> None:
        split = urlsplit(self.path)
        path = split.path

        if path in LEGACY_REDIRECTS:
            self.redirect(LEGACY_REDIRECTS[path], split.query)
            return

        if path == "/styles.css":
            self.serve_static(STYLE_PATH)
            return

        if path in {"", "/"}:
            self.send_response(HTTPStatus.OK)
            payload = build_home_page()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if path == "/cabinet/create" and with_body and self.command == "POST":
            self.handle_cabinet_create()
            return

        if path == f"/cabinet/{DEFAULT_CABINET_ID}":
            self.redirect(build_cabinet_module_path(DEFAULT_CABINET_ID, "sources"), split.query)
            return

        resolved = resolve_cabinet_route(path)
        if resolved:
            cabinet_id, module_name, module_path = resolved
            if get_cabinet(cabinet_id) is None:
                self.send_error(HTTPStatus.NOT_FOUND, "Unknown cabinet")
                return
            self.serve_module_page(cabinet_id, module_name, module_path, split.query, with_body)
            return

        legacy_route = resolve_legacy_module_route(path)
        if legacy_route:
            module_name, module_path = legacy_route
            self.redirect(build_cabinet_module_path(DEFAULT_CABINET_ID, module_name, module_path), split.query)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def handle_cabinet_create(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length) if length else b""
        fields = dict(parse_qsl(payload.decode("utf-8", errors="replace"), keep_blank_values=True))
        title = fields.get("title", "")

        try:
            cabinet = create_cabinet(title)
        except ValueError as error:
            body = build_home_page(str(error), title)
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.redirect(build_cabinet_module_path(cabinet["id"], "sources"), "")

    def redirect(self, location: str, query: str) -> None:
        target = location
        if query:
            target = f"{location}?{query}"
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", target)
        self.end_headers()

    def serve_static(self, file_path: Path) -> None:
        if not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        content = file_path.read_bytes()
        content_type, _ = mimetypes.guess_type(str(file_path))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def serve_module_page(
        self,
        cabinet_id: str,
        module_name: str,
        module_path: str,
        query: str,
        with_body: bool,
    ) -> None:
        body = None
        headers = {"Accept-Encoding": "identity", "__query__": query}

        if with_body:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b""
            content_type = self.headers.get("Content-Type")
            if content_type:
                headers["Content-Type"] = content_type

        status, response_headers, payload = fetch_module_response(
            cabinet_id=cabinet_id,
            module_name=module_name,
            module_path=module_path,
            method=self.command,
            body=body,
            headers=headers,
        )

        if status in REDIRECT_STATUSES and response_headers.get("Location"):
            location = rewrite_upstream_location(
                response_headers["Location"],
                cabinet_id=cabinet_id,
                module_name=module_name,
                current_module_path=module_path,
            )
            self.send_response(status)
            self.send_header("Location", location)
            self.end_headers()
            return

        content_type = response_headers.get("Content-Type", "")
        if "text/html" in content_type:
            upstream_html = payload.decode("utf-8", errors="replace")
            title, styles, rewritten_body = rewrite_html(upstream_html, cabinet_id, module_name, module_path)
            wrapped = build_shell_page(cabinet_id, module_name, title, styles, rewritten_body)
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(wrapped)))
            self.end_headers()
            self.wfile.write(wrapped)
            return

        self.send_response(status)
        for header_name, header_value in response_headers.items():
            if header_name.lower() in {"content-length", "connection", "content-encoding"}:
                continue
            self.send_header(header_name, header_value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        logging.info("%s - %s", self.address_string(), format % args)


def build_upstream_query(cabinet_id: str, query: str) -> str:
    pairs = parse_qsl(query, keep_blank_values=True)
    filtered = [(key, value) for key, value in pairs if key != "cabinet_id"]
    filtered.append(("cabinet_id", cabinet_id))
    return urlencode(filtered)


def main() -> None:
    configure_logging()

    host, port = get_server_address()
    server = ThreadingHTTPServer((host, port), ShellHandler)
    logging.info("Serving shell UI at http://%s:%s", host, port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shell UI stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
