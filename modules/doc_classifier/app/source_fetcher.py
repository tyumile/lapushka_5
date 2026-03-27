import html.parser
import re
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import requests

from app.registry_source import RegistryFileRecord


REQUEST_TIMEOUT = (10, 60)


class GoogleDriveFolderParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.entries: list[dict[str, str]] = []
        self._pending_href: str | None = None
        self._pending_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag == "a" and attrs_map.get("href"):
            self._pending_href = attrs_map["href"]
            self._pending_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._pending_href:
            name = "".join(self._pending_text).strip()
            if name:
                self.entries.append({"href": self._pending_href, "name": name})
            self._pending_href = None
            self._pending_text = []

    def handle_data(self, data: str) -> None:
        if self._pending_href is not None:
            self._pending_text.append(data)


class SourceFileFetcher:
    yandex_endpoint = "https://cloud-api.yandex.net/v1/disk/public/resources"

    def __init__(self, temp_dir: Path) -> None:
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "lapushka-doc-classifier/1.0"})

    def resolve_file(self, record: RegistryFileRecord) -> Path:
        if record.absolute_file_path.exists():
            return record.absolute_file_path
        if record.source_type == "google_drive":
            return self._download_file(google_file_download_url(record.source_external_id), record.file_name)
        if record.source_type == "yandex_disk":
            return self._download_file(self._yandex_download_url(record), record.file_name)
        raise FileNotFoundError(f"Не удалось получить файл {record.file_name}")

    def source_link(self, record: RegistryFileRecord) -> str | None:
        if record.source_type == "google_drive" and record.source_external_id:
            return f"https://drive.google.com/file/d/{quote(record.source_external_id)}/view"
        if record.source_type == "yandex_disk":
            try:
                return self._yandex_download_url(record)
            except Exception:
                return record.source_url or None
        return None

    def _download_file(self, url: str, file_name: str) -> Path:
        target = self.temp_dir / file_name
        response = self.session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    handle.write(chunk)
        return target

    def _yandex_download_url(self, record: RegistryFileRecord) -> str:
        payload = self._get_yandex_resource(record.source_url)
        found = self._find_yandex_item(payload, record.source_external_id)
        if not found:
            raise FileNotFoundError(f"Файл {record.file_name} не найден в публичном Yandex Disk источнике")
        download_url = found.get("file")
        if not download_url:
            raise FileNotFoundError(f"Для файла {record.file_name} нет download URL")
        return str(download_url)

    def _find_yandex_item(self, payload: dict, external_id: str) -> dict | None:
        for item in self._embedded_items(payload):
            resource_id = str(item.get("resource_id") or item.get("path") or "")
            if resource_id == external_id:
                return item
            if item.get("type") == "dir":
                nested = self._get_yandex_resource(payload["public_key"], item.get("path"))
                found = self._find_yandex_item(nested, external_id)
                if found:
                    return found
        return None

    def _embedded_items(self, payload: dict) -> list[dict]:
        embedded = payload.get("_embedded") or {}
        return list(embedded.get("items") or [])

    def _get_yandex_resource(self, source_url: str, path: str | None = None) -> dict:
        params = {"public_key": source_url, "limit": 200}
        if path:
            params["path"] = path
        response = self.session.get(self.yandex_endpoint, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        payload["public_key"] = source_url
        return payload


def google_file_download_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?id={quote(file_id)}&export=download"
