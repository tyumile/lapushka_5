import html.parser
import io
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

import requests


PDF_PAGE_LIMIT_BYTES = 200 * 1024 * 1024
REQUEST_TIMEOUT = (5, 30)
SINGLE_SHEET_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
    ".bmp",
    ".gif",
}


@dataclass(frozen=True)
class RemoteFile:
    external_id: str
    file_path: str
    file_name: str
    file_size: int | None
    page_count: int | None
    created_at: str | None
    modified_at: str | None
    download_url: str | None = None


class SyncError(RuntimeError):
    pass


class SourceClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "lapushka-ingest-registry/1.0"})


class LocalStorageClient:
    def list_files(self, root_dir: Path, base_dir: Path) -> tuple[str, list[RemoteFile]]:
        files: list[RemoteFile] = []
        if not root_dir.exists():
            return "Локальное хранилище", files
        for path in sorted(root_dir.rglob("*")):
            if not path.is_file():
                continue
            stat = path.stat()
            files.append(
                RemoteFile(
                    external_id=str(path.relative_to(root_dir)),
                    file_path=str(path.relative_to(base_dir)),
                    file_name=path.name,
                    file_size=stat.st_size,
                    page_count=count_document_pages_from_path(path, stat.st_size),
                    created_at=isoformat_from_timestamp(stat.st_ctime),
                    modified_at=isoformat_from_timestamp(stat.st_mtime),
                )
            )
        return "Локальное хранилище", files


class YandexDiskPublicClient(SourceClient):
    endpoint = "https://cloud-api.yandex.net/v1/disk/public/resources"

    def list_files(self, source_url: str) -> tuple[str, list[RemoteFile]]:
        root = self._get_resource(source_url)
        title = root.get("name") or "Yandex Disk"
        files: list[RemoteFile] = []
        self._walk(source_url, root, "", files)
        return str(title), files

    def _walk(
        self,
        source_url: str,
        payload: dict[str, Any],
        current_path: str,
        files: list[RemoteFile],
    ) -> None:
        for item in self._embedded_items(source_url, payload):
            item_type = item.get("type")
            name = str(item.get("name") or "")
            next_path = f"{current_path}/{name}".strip("/")
            if item_type == "dir":
                nested = self._get_resource(source_url, item.get("path"))
                self._walk(source_url, nested, next_path, files)
                continue
            if item_type != "file":
                continue
            file_size = int(item["size"]) if item.get("size") is not None else None
            download_url = item.get("file")
            files.append(
                RemoteFile(
                    external_id=str(item.get("resource_id") or item.get("path") or next_path),
                    file_path=next_path or name,
                    file_name=name,
                    file_size=file_size,
                    page_count=count_document_pages_from_url(download_url, file_size, name, self.session),
                    created_at=normalize_remote_timestamp(item.get("created")),
                    modified_at=normalize_remote_timestamp(item.get("modified")),
                    download_url=download_url,
                )
            )

    def _embedded_items(self, source_url: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        embedded = payload.get("_embedded") or {}
        items = list(embedded.get("items") or [])
        total = int(embedded.get("total") or len(items))
        offset = int(embedded.get("offset") or 0)
        limit = int(embedded.get("limit") or len(items) or 200)
        path = payload.get("path")
        while offset + len(items) < total:
            offset += limit
            extra = self._get_resource(source_url, path=path, offset=offset, limit=limit)
            extra_embedded = extra.get("_embedded") or {}
            items.extend(list(extra_embedded.get("items") or []))
        return items

    def _get_resource(
        self,
        source_url: str,
        path: str | None = None,
        offset: int | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"public_key": source_url, "limit": limit}
        if path:
            params["path"] = path
        if offset:
            params["offset"] = offset
        response = self.session.get(self.endpoint, params=params, timeout=REQUEST_TIMEOUT)
        if response.status_code >= 400:
            raise SyncError(f"Yandex Disk returned {response.status_code}")
        payload = response.json()
        if "error" in payload:
            message = payload.get("description") or payload.get("message") or payload["error"]
            raise SyncError(f"Yandex Disk error: {message}")
        return payload


class GoogleDriveFolderParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._inside_title = False
        self._pending_href: str | None = None
        self._pending_text: list[str] = []
        self.entries: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag == "title":
            self._inside_title = True
        if tag == "a":
            href = attrs_map.get("href")
            if href:
                self._pending_href = href
                self._pending_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._inside_title = False
        if tag == "a" and self._pending_href:
            name = "".join(self._pending_text).strip()
            if name:
                self.entries.append({"href": self._pending_href, "name": name})
            self._pending_href = None
            self._pending_text = []

    def handle_data(self, data: str) -> None:
        if self._inside_title:
            self.title += data
        if self._pending_href is not None:
            self._pending_text.append(data)


class GoogleDrivePublicClient(SourceClient):
    def list_files(self, source_url: str) -> tuple[str, list[RemoteFile]]:
        folder_id = extract_google_folder_id(source_url)
        if not folder_id:
            raise SyncError("Не удалось определить id папки Google Drive")
        files: list[RemoteFile] = []
        title = self._walk(folder_id, "", files, set())
        return title or "Google Drive", files

    def _walk(
        self,
        folder_id: str,
        current_path: str,
        files: list[RemoteFile],
        visited: set[str],
    ) -> str:
        if folder_id in visited:
            return current_path or "Google Drive"
        visited.add(folder_id)
        parser = GoogleDriveFolderParser()
        html_text = self._fetch_embedded(folder_id)
        parser.feed(html_text)
        folder_title = sanitize_google_title(parser.title) or current_path or "Google Drive"
        for entry in parser.entries:
            href = entry["href"]
            name = entry["name"]
            file_id = extract_google_file_id(href)
            child_folder_id = extract_google_folder_id(href)
            next_path = f"{current_path}/{name}".strip("/")
            if child_folder_id:
                self._walk(child_folder_id, next_path, files, visited)
                continue
            if not file_id:
                continue
            download_url = google_file_download_url(file_id)
            file_size = get_remote_file_size(download_url, self.session)
            files.append(
                RemoteFile(
                    external_id=file_id,
                    file_path=next_path or name,
                    file_name=name,
                    file_size=file_size,
                    page_count=count_document_pages_from_url(
                        download_url,
                        file_size,
                        name,
                        self.session,
                    ),
                    created_at=None,
                    modified_at=None,
                    download_url=download_url,
                )
            )
        return folder_title

    def _fetch_embedded(self, folder_id: str) -> str:
        url = f"https://drive.google.com/embeddedfolderview?id={quote(folder_id)}#list"
        response = self.session.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code >= 400:
            raise SyncError(f"Google Drive returned {response.status_code}")
        return response.text


def extract_google_folder_id(value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.netloc.endswith("drive.google.com"):
        match = re.search(r"/folders/([a-zA-Z0-9_-]+)", parsed.path)
        if match:
            return match.group(1)
        query = parse_qs(parsed.query)
        if "id" in query:
            return query["id"][0]
    if re.fullmatch(r"[a-zA-Z0-9_-]{10,}", value):
        return value
    return None


def extract_google_file_id(value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.netloc.endswith("drive.google.com"):
        match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", parsed.path)
        if match:
            return match.group(1)
        query = parse_qs(parsed.query)
        if "id" in query:
            return query["id"][0]
    return None


def sanitize_google_title(title: str) -> str:
    cleaned = title.replace(" - Google Drive", "").strip()
    return cleaned


def google_file_download_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?id={quote(file_id)}&export=download"


def normalize_remote_timestamp(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.astimezone(UTC).replace(microsecond=0).isoformat()


def isoformat_from_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, tz=UTC).replace(microsecond=0).isoformat()


def count_pdf_pages_from_path(path: Path, size_bytes: int | None) -> int | None:
    if path.suffix.lower() != ".pdf":
        return None
    if size_bytes is not None and size_bytes > PDF_PAGE_LIMIT_BYTES:
        return None
    try:
        payload = path.read_bytes()
    except OSError:
        return None
    return count_pdf_pages(payload)


def count_document_pages_from_path(path: Path, size_bytes: int | None) -> int | None:
    if path.suffix.lower() in SINGLE_SHEET_EXTENSIONS:
        return 1
    return count_pdf_pages_from_path(path, size_bytes)


def count_pdf_pages_from_url(
    download_url: str | None,
    size_bytes: int | None,
    file_name: str,
    session: requests.Session,
) -> int | None:
    if not download_url or not file_name.lower().endswith(".pdf"):
        return None
    if size_bytes is not None and size_bytes > PDF_PAGE_LIMIT_BYTES:
        return None
    try:
        response = session.get(download_url, timeout=REQUEST_TIMEOUT, stream=True)
        response.raise_for_status()
        buffer = io.BytesIO()
        for chunk in response.iter_content(chunk_size=65536):
            if not chunk:
                continue
            buffer.write(chunk)
            if buffer.tell() > PDF_PAGE_LIMIT_BYTES:
                return None
        return count_pdf_pages(buffer.getvalue())
    except requests.RequestException:
        return None


def count_document_pages_from_url(
    download_url: str | None,
    size_bytes: int | None,
    file_name: str,
    session: requests.Session,
) -> int | None:
    suffix = Path(file_name).suffix.lower()
    if suffix in SINGLE_SHEET_EXTENSIONS:
        return 1
    return count_pdf_pages_from_url(download_url, size_bytes, file_name, session)


def get_remote_file_size(download_url: str | None, session: requests.Session) -> int | None:
    if not download_url:
        return None
    try:
        response = session.head(download_url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        response.raise_for_status()
        value = response.headers.get("content-length")
        if value and value.isdigit():
            return int(value)
    except requests.RequestException:
        return None
    return None


def count_pdf_pages(payload: bytes) -> int | None:
    if not payload.startswith(b"%PDF"):
        return None
    count = len(re.findall(rb"/Type\s*/Page\b", payload))
    return count or None
