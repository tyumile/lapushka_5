import hashlib
import html
import logging
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, quote_plus, urlparse

from app.service import IngestRegistryService


LOGGER = logging.getLogger(__name__)

SOURCE_STATUS_LABELS = {
    "ready": "Готово",
    "failed": "Ошибка",
    "idle": "Ожидание",
}

FILE_STATUS_LABELS = {
    "ready": "Готово",
    "uploaded": "Загружен",
    "failed": "Ошибка",
    "needs_review": "Требует внимания",
    "needs_documents": "Нужно добавить документы",
    "error": "Ошибка",
    "deleted": "Удален",
}

EVENT_ACTION_LABELS = {
    "sync": "Синхронизация",
    "upload": "Загрузка файла",
    "source_add": "Добавление источника",
}

EVENT_STATUS_LABELS = {
    "done": "Успешно",
    "failed": "Ошибка",
    "in_progress": "В работе",
}

SOURCE_FILTER_OPTIONS = [
    ("all", "Все источники"),
    ("google_drive", "Google Drive"),
    ("yandex_disk", "Яндекс Диск"),
    ("local_upload", "Локальные"),
]

SORT_OPTIONS = [
    ("updated", "Сначала новые"),
    ("name", "По названию"),
    ("source", "По источнику"),
]

DENSITY_OPTIONS = [
    ("normal", "Обычно"),
    ("compact", "Компактно"),
]

PROBLEM_STATUSES = {"failed", "needs_review", "needs_documents", "error"}


class IngestRegistryHandler(BaseHTTPRequestHandler):
    service: IngestRegistryService

    @classmethod
    def build(cls, service: IngestRegistryService):
        class Handler(cls):
            pass

        Handler.service = service
        return Handler

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND, "Page not found")
            return
        query = parse_qs(parsed.query)
        cabinet_id = normalize_cabinet_id(query.get("cabinet_id", ["default"])[0])
        source_filter = query.get("source", ["all"])[0]
        sort_by = query.get("sort", ["updated"])[0]
        density = query.get("density", ["normal"])[0]
        payload = render_dashboard(
            self.service.dashboard(source_filter=source_filter, cabinet_id=cabinet_id),
            sort_by=sort_by,
            density=density,
        ).encode("utf-8")
        self._send_html(payload)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        cabinet_id = normalize_cabinet_id(parse_qs(parsed.query).get("cabinet_id", ["default"])[0])
        if parsed.path == "/upload":
            self._handle_upload(cabinet_id)
            return
        if parsed.path == "/sources/add":
            self._handle_source_add(cabinet_id)
            return
        if parsed.path.startswith("/sync/"):
            source_id = parsed.path.rsplit("/", 1)[-1]
            try:
                self.service.sync_source(int(source_id), cabinet_id=cabinet_id)
            except ValueError:
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid source id")
                return
            self._redirect_home(cabinet_id)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Action not found")

    def _handle_upload(self, cabinet_id: str) -> None:
        filename, payload = parse_multipart_upload(self.headers, self.rfile.read(self._content_length()))
        if not filename:
            self.send_error(HTTPStatus.BAD_REQUEST, "File is required")
            return
        self.service.handle_upload(filename, payload, cabinet_id=cabinet_id)
        self._redirect_home(cabinet_id)

    def _handle_source_add(self, cabinet_id: str) -> None:
        fields = parse_form_body(self.headers, self.rfile.read(self._content_length()))
        try:
            self.service.add_source(
                fields.get("source_type", ""),
                fields.get("source_url", ""),
                cabinet_id=cabinet_id,
            )
        except ValueError as error:
            self.send_error(HTTPStatus.BAD_REQUEST, str(error))
            return
        self._redirect_home(cabinet_id)

    def _content_length(self) -> int:
        try:
            return int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return 0

    def _redirect_home(self, cabinet_id: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", build_query_href(cabinet_id=cabinet_id))
        self.end_headers()

    def _send_html(self, payload: bytes) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)


def render_dashboard(data: dict, sort_by: str = "updated", density: str = "normal") -> str:
    sort_by = sort_by if sort_by in {value for value, _ in SORT_OPTIONS} else "updated"
    density = density if density in {value for value, _ in DENSITY_OPTIONS} else "normal"
    cabinet_id = normalize_cabinet_id(data.get("cabinet_id", "default"))

    files = sort_files(data["files"], sort_by)
    sources = sort_sources(data["sources"])
    recent_logs = data["recent_logs"]

    summary = build_summary(sources, files)
    file_rows = "\n".join(render_file_row(item) for item in files)
    if not file_rows:
        file_rows = "<tr><td colspan='7' class='table-empty'>Под выбранные фильтры записи пока не попали.</td></tr>"

    source_rows = "\n".join(render_source_row(item) for item in sources)
    if not source_rows:
        source_rows = "<tr><td colspan='8' class='table-empty'>Источники еще не добавлены.</td></tr>"

    recent_events = "\n".join(render_event_row(item) for item in recent_logs)
    if not recent_events:
        recent_events = "<tr><td colspan='4' class='table-empty'>История действий пока пуста.</td></tr>"

    filter_links = "\n".join(
        render_state_link(
            active_value=data["source_filter"],
            value=value,
            label=label,
            param_name="source",
            cabinet_id=cabinet_id,
            source_filter=value,
            sort_by=sort_by,
            density=density,
        )
        for value, label in SOURCE_FILTER_OPTIONS
    )
    sort_links = "\n".join(
        render_state_link(
            active_value=sort_by,
            value=value,
            label=label,
            param_name="sort",
            cabinet_id=cabinet_id,
            source_filter=data["source_filter"],
            sort_by=value,
            density=density,
        )
        for value, label in SORT_OPTIONS
    )
    density_links = "\n".join(
        render_state_link(
            active_value=density,
            value=value,
            label=label,
            param_name="density",
            cabinet_id=cabinet_id,
            source_filter=data["source_filter"],
            sort_by=sort_by,
            density=value,
        )
        for value, label in DENSITY_OPTIONS
    )

    density_class = "density-compact" if density == "compact" else "density-normal"

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ingest_registry</title>
  <style>
    :root {{
      --bg: #edf1f4;
      --panel: #ffffff;
      --panel-soft: #f7f9fb;
      --ink: #1d2935;
      --muted: #627181;
      --line: #d4dce4;
      --line-strong: #bcc8d3;
      --accent: #245a7d;
      --accent-soft: #e7f0f7;
      --good: #25624a;
      --good-soft: #e5f3ec;
      --danger: #a53a2c;
      --danger-soft: #fbe8e5;
      --warning: #8f5a10;
      --warning-soft: #f8eedb;
      --shadow: 0 10px 28px rgba(26, 38, 49, 0.08);
      --radius: 16px;
      --row-height: 13px;
      --row-height-compact: 9px;
      --font-ui: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      --font-mono: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: var(--font-ui);
      color: var(--ink);
      background:
        linear-gradient(180deg, rgba(255,255,255,0.8), rgba(255,255,255,0.6)),
        linear-gradient(135deg, #f7fafc 0%, var(--bg) 52%, #e6edf3 100%);
    }}
    main {{
      max-width: 1720px;
      margin: 0 auto;
      padding: 24px 20px 36px;
    }}
    h1, h2, h3, p {{ margin: 0; }}
    a {{
      color: var(--accent);
      text-decoration: none;
    }}
    .page {{
      display: grid;
      gap: 18px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }}
    .hero {{
      padding: 22px 24px;
      display: grid;
      gap: 14px;
    }}
    .hero-head {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
    }}
    .hero-title {{
      display: grid;
      gap: 8px;
      max-width: 900px;
    }}
    .hero-title p,
    .muted {{
      color: var(--muted);
    }}
    .meta-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel-soft);
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(180px, 1fr));
      gap: 12px;
    }}
    .metric {{
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: linear-gradient(180deg, #fff 0%, #f8fafc 100%);
      display: grid;
      gap: 6px;
    }}
    .metric strong {{
      font-size: 30px;
      line-height: 1;
      color: var(--accent);
    }}
    .metric .hint {{
      font-size: 13px;
      color: var(--muted);
    }}
    .controls {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 18px;
      align-items: start;
    }}
    .panel-body {{
      padding: 18px 20px 20px;
      display: grid;
      gap: 14px;
    }}
    .form-grid {{
      display: grid;
      gap: 12px;
    }}
    .inline-form {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: end;
    }}
    .upload-box {{
      border: 1px dashed var(--line-strong);
      border-radius: 14px;
      padding: 14px;
      background: var(--panel-soft);
      display: grid;
      gap: 12px;
    }}
    label {{
      display: grid;
      gap: 6px;
      font-size: 13px;
      color: var(--muted);
    }}
    input[type="url"],
    input[type="file"] {{
      width: 100%;
      min-width: 0;
      border: 1px solid var(--line-strong);
      border-radius: 10px;
      padding: 11px 12px;
      background: #fff;
      color: var(--ink);
      font: inherit;
    }}
    button {{
      border: 0;
      border-radius: 10px;
      padding: 11px 14px;
      background: var(--accent);
      color: #fff;
      font: inherit;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
    }}
    .toolbar {{
      display: grid;
      gap: 12px;
    }}
    .toolbar-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px 14px;
      align-items: center;
      justify-content: space-between;
    }}
    .toolbar-label {{
      font-size: 13px;
      color: var(--muted);
      min-width: 110px;
    }}
    .toolbar-group {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    .chip-link {{
      display: inline-flex;
      align-items: center;
      min-height: 36px;
      padding: 7px 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
    }}
    .chip-link.active {{
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }}
    .section-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
    }}
    .section-copy {{
      display: grid;
      gap: 5px;
    }}
    .table-wrap {{
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
    }}
    table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      table-layout: fixed;
      font-size: 14px;
    }}
    thead th {{
      position: sticky;
      top: 0;
      z-index: 2;
      padding: 12px 10px;
      border-bottom: 1px solid var(--line-strong);
      background: #f3f7fa;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    tbody td {{
      padding: var(--row-height) 10px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    .density-compact tbody td {{
      padding-top: var(--row-height-compact);
      padding-bottom: var(--row-height-compact);
      font-size: 13px;
    }}
    tbody tr:nth-child(even) td {{
      background: #fbfcfd;
    }}
    tbody tr:hover td {{
      background: #eef5fb;
    }}
    tbody tr.problem-row td {{
      background: #fff6f4;
    }}
    tbody tr.problem-row:nth-child(even) td {{
      background: #fdf0ed;
    }}
    .table-empty {{
      padding: 20px 12px;
      color: var(--muted);
      text-align: center;
    }}
    .col-sticky {{
      position: sticky;
      left: 0;
      z-index: 1;
      background: inherit;
      box-shadow: 1px 0 0 var(--line);
    }}
    thead .col-sticky {{
      z-index: 3;
      background: #f3f7fa;
    }}
    .col-title {{ width: 25%; }}
    .col-source {{ width: 17%; }}
    .col-status {{ width: 9%; }}
    .col-size {{ width: 8%; }}
    .col-pages {{ width: 6%; }}
    .col-date {{ width: 11%; }}
    .col-actions {{ width: 10%; }}
    .cell-main {{
      display: grid;
      gap: 4px;
    }}
    .cell-title {{
      display: -webkit-box;
      overflow: hidden;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      font-weight: 600;
      line-height: 1.35;
    }}
    .cell-subtle {{
      display: -webkit-box;
      overflow: hidden;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      color: var(--muted);
      line-height: 1.35;
    }}
    .mono {{
      font-family: var(--font-mono);
      font-size: 12px;
      word-break: break-all;
    }}
    .number {{
      white-space: nowrap;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    .status-badge {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 26px;
      padding: 3px 9px;
      border-radius: 999px;
      background: var(--good-soft);
      color: var(--good);
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .status-badge.warning {{
      background: var(--warning-soft);
      color: var(--warning);
    }}
    .status-badge.failed {{
      background: var(--danger-soft);
      color: var(--danger);
    }}
    .details-toggle {{
      display: inline-flex;
      align-items: center;
      cursor: pointer;
      color: var(--accent);
      font-size: 13px;
      font-weight: 600;
      text-decoration: none;
    }}
    .details-row {{
      display: none;
    }}
    .details-row td {{
      padding-top: 0;
      border-top: 0;
      background: var(--panel);
    }}
    .details-row:target {{
      display: table-row;
    }}
    .details-card {{
      margin: 0 0 10px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel-soft);
      display: grid;
      gap: 6px;
    }}
    .details-card-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }}
    .details-card-title {{
      font-size: 13px;
      font-weight: 700;
      color: var(--text);
    }}
    .details-close {{
      display: inline-flex;
      align-items: center;
      cursor: pointer;
      color: var(--accent);
      font-size: 13px;
      font-weight: 600;
      white-space: nowrap;
      text-decoration: none;
    }}
    .details-grid {{
      display: grid;
      grid-template-columns: 130px 1fr;
      gap: 6px 12px;
      font-size: 13px;
    }}
    .next-step {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
    }}
    .history-note {{
      font-size: 13px;
      color: var(--muted);
    }}
    @media (max-width: 1180px) {{
      .controls {{
        grid-template-columns: 1fr;
      }}
      .stats {{
        grid-template-columns: repeat(2, minmax(180px, 1fr));
      }}
    }}
    @media (max-width: 860px) {{
      main {{
        padding-left: 12px;
        padding-right: 12px;
      }}
      .hero-head,
      .toolbar-row {{
        flex-direction: column;
        align-items: stretch;
      }}
      .stats {{
        grid-template-columns: 1fr;
      }}
      .inline-form {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <div class="page {density_class}">
      <section class="panel hero">
        <div class="hero-head">
          <div class="hero-title">
            <h1>Реестр загрузок и синхронизации</h1>
            <p>Экран рассчитан на широкое рабочее окно: сверху краткое состояние, ниже быстрые действия и плотные таблицы для просмотра длинных списков без карточного режима.</p>
          </div>
          <div class="meta-chip">База модуля: <span class="mono">{escape(data["db_path"])}</span></div>
        </div>
        <div class="stats">
          <div class="metric">
            <span class="muted">Файлов в текущем срезе</span>
            <strong>{summary["file_count"]}</strong>
            <span class="hint">После выбранного фильтра по источнику</span>
          </div>
          <div class="metric">
            <span class="muted">Источников</span>
            <strong>{summary["source_count"]}</strong>
            <span class="hint">Все подключенные каналы загрузки</span>
          </div>
          <div class="metric">
            <span class="muted">Ошибки и проблемные записи</span>
            <strong>{summary["problem_count"]}</strong>
            <span class="hint">Требуют проверки или повторной синхронизации</span>
          </div>
          <div class="metric">
            <span class="muted">Последняя активность</span>
            <strong>{escape(summary["latest_activity"])}</strong>
            <span class="hint">По файлам и журналу действий модуля</span>
          </div>
        </div>
      </section>

      <section class="controls">
        <section class="panel panel-body">
          <div class="section-copy">
            <h2>Быстрые действия</h2>
            <p class="muted">Новые источники добавляются сразу в реестр и запускают синхронизацию автоматически.</p>
          </div>
          <div class="form-grid">
            <form action="{build_post_action('/sources/add', cabinet_id)}" method="post" class="inline-form">
              <label>
                Ссылка на папку Google Drive
                <input type="url" name="source_url" placeholder="https://drive.google.com/drive/folders/..." required>
                <input type="hidden" name="source_type" value="google_drive">
              </label>
              <button type="submit">Добавить Google Drive</button>
            </form>
            <form action="{build_post_action('/sources/add', cabinet_id)}" method="post" class="inline-form">
              <label>
                Ссылка на папку Яндекс Диска
                <input type="url" name="source_url" placeholder="https://disk.yandex.ru/d/..." required>
                <input type="hidden" name="source_type" value="yandex_disk">
              </label>
              <button type="submit">Добавить Яндекс Диск</button>
            </form>
          </div>
        </section>

        <section class="panel panel-body">
          <div class="section-copy">
            <h2>Локальная загрузка</h2>
            <p class="muted">Файл сохраняется в локальное хранилище модуля и сразу появляется в табличном реестре ниже.</p>
          </div>
          <div class="upload-box">
            <form action="{build_post_action('/upload', cabinet_id)}" method="post" enctype="multipart/form-data" class="form-grid">
              <label>
                Выберите файл
                <input type="file" name="file" required>
              </label>
              <button type="submit">Загрузить файл</button>
            </form>
          </div>
        </section>
      </section>

      <section class="panel panel-body">
        <div class="section-head">
          <div class="section-copy">
            <h2>Фильтры и режимы</h2>
            <p class="muted">Сначала отберите нужный поток файлов, затем переключайте порядок строк и плотность таблицы.</p>
          </div>
        </div>
        <div class="toolbar">
          <div class="toolbar-row">
            <div class="toolbar-group">
              <span class="toolbar-label">Показать:</span>
              {filter_links}
            </div>
          </div>
          <div class="toolbar-row">
            <div class="toolbar-group">
              <span class="toolbar-label">Порядок строк:</span>
              {sort_links}
            </div>
            <div class="toolbar-group">
              <span class="toolbar-label">Плотность:</span>
              {density_links}
            </div>
          </div>
        </div>
      </section>

      <section class="panel panel-body">
        <div class="section-head">
          <div class="section-copy">
            <h2>Источники</h2>
            <p class="muted">Таблица показывает состояние каждой синхронизации, последнюю статистику и следующее действие для проблемных строк.</p>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="col-sticky col-title">Источник</th>
                <th class="col-status">Состояние</th>
                <th class="col-size">Файлов</th>
                <th class="col-size">Добавлено</th>
                <th class="col-size">Изменено</th>
                <th class="col-size">Удалено</th>
                <th class="col-date">Последняя синхронизация</th>
                <th class="col-actions">Действия и детали</th>
              </tr>
            </thead>
            <tbody>
              {source_rows}
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel panel-body">
        <div class="section-head">
          <div class="section-copy">
            <h2>Реестр файлов</h2>
            <p class="muted">Главный рабочий список для сравнения строк: название и источник закреплены слева, служебные поля компактны, детали открываются точечно.</p>
          </div>
          <div class="meta-chip">Порядок: {escape(sort_label(sort_by))}</div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="col-sticky col-title">Название и путь</th>
                <th class="col-source">Источник</th>
                <th class="col-status">Состояние</th>
                <th class="col-size number">Размер</th>
                <th class="col-pages number">Листы</th>
                <th class="col-date">Обновлено</th>
                <th class="col-actions">Подробнее</th>
              </tr>
            </thead>
            <tbody>
              {file_rows}
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel panel-body">
        <div class="section-head">
          <div class="section-copy">
            <h2>Журнал действий</h2>
            <p class="history-note">Последние системные события модуля без лишнего шума: загрузки, добавление источников и синхронизации.</p>
          </div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="col-status">Действие</th>
                <th class="col-status">Результат</th>
                <th>Итог</th>
                <th class="col-date">Когда</th>
              </tr>
            </thead>
            <tbody>
              {recent_events}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </main>
</body>
</html>
"""


def build_summary(sources: list[dict], files: list[dict]) -> dict[str, str | int]:
    problem_sources = sum(1 for item in sources if item.get("sync_status") in PROBLEM_STATUSES)
    problem_files = sum(1 for item in files if item.get("status") in PROBLEM_STATUSES)
    latest_candidates = [
        item.get("modified_at_remote") or item.get("updated_at")
        for item in files
        if item.get("modified_at_remote") or item.get("updated_at")
    ]
    latest_activity = format_datetime(max(latest_candidates)) if latest_candidates else "Нет данных"
    return {
        "file_count": len(files),
        "source_count": len(sources),
        "problem_count": problem_sources + problem_files,
        "latest_activity": latest_activity,
    }


def sort_files(items: list[dict], sort_by: str) -> list[dict]:
    if sort_by == "name":
        return sorted(items, key=lambda item: (str(item["file_name"]).lower(), str(item["source_name"]).lower()))
    if sort_by == "source":
        return sorted(
            items,
            key=lambda item: (
                str(item["source_name"]).lower(),
                str(item["file_name"]).lower(),
            ),
        )
    return sorted(
        items,
        key=lambda item: (
            item.get("modified_at_remote") or item.get("updated_at") or "",
            str(item["file_name"]).lower(),
        ),
        reverse=True,
    )


def sort_sources(items: list[dict]) -> list[dict]:
    return sorted(
        items,
        key=lambda item: (
            0 if item.get("sync_status") in PROBLEM_STATUSES else 1,
            item.get("last_sync_at") or "",
            str(item.get("title", "")).lower(),
        ),
        reverse=True,
    )


def render_source_row(item: dict) -> str:
    problem = item["sync_status"] in PROBLEM_STATUSES
    row_class = "problem-row" if problem else ""
    source_link = (
        f'<a href="{escape(item["source_url"])}" target="_blank" rel="noreferrer" class="mono">{escape(item["source_url"])}</a>'
        if item["source_url"]
        else "<span class='muted'>Локальное хранилище без внешней ссылки</span>"
    )
    return f"""
    <tr class="{row_class}">
      <td class="col-sticky">
        <div class="cell-main">
          <div class="cell-title">{escape(item["title"])}</div>
          <div class="cell-subtle">{source_link}</div>
        </div>
      </td>
      <td>{render_status_badge(item["sync_status"], kind="source")}</td>
      <td class="number">{escape(item["last_total_files"] or 0)}</td>
      <td class="number">{escape(item["last_added_files"] or 0)}</td>
      <td class="number">{escape(item["last_changed_files"] or 0)}</td>
      <td class="number">{escape(item["last_deleted_files"] or 0)}</td>
      <td>{escape(format_datetime(item["last_sync_at"]) if item["last_sync_at"] else "Не запускалась")}</td>
      <td>
        <div class="cell-main">
          <form action="{build_post_action(f'/sync/{item["id"]}', item["cabinet_id"])}" method="post">
            <button type="submit">Синхронизировать</button>
          </form>
          <div class="next-step">{escape(next_step_for_source(item["sync_status"]))}</div>
          <details class="inline-details">
            <summary>Показать итог</summary>
            <div class="details-card">
              <div>{escape(item["sync_message"] or "Нет данных о синхронизации.")}</div>
              <div class="details-grid">
                <div class="muted">Добавлен</div>
                <div>{escape(format_datetime(item["added_at"]))}</div>
              </div>
            </div>
          </details>
        </div>
      </td>
    </tr>
    """


def render_file_row(item: dict) -> str:
    file_status = item.get("status") or "ready"
    row_class = "problem-row" if file_status in PROBLEM_STATUSES else ""
    source_name = item["source_name"]
    source_url = item.get("source_url")
    source_note = f"Источник открыт по ссылке" if source_url else "Локальное хранилище модуля"
    modified = item["modified_at_remote"] or item["updated_at"]
    row_key = hashlib.md5(
        f'{item.get("external_id", "")}|{item.get("file_path", "")}|{item.get("created_at", "")}'.encode("utf-8")
    ).hexdigest()[:12]
    details_id = f"file-details-{row_key}"
    return f"""
    <tr class="{row_class}">
      <td class="col-sticky">
        <div class="cell-main">
          <div class="cell-title">{escape(item["file_name"])}</div>
          <div class="cell-subtle mono">{escape(item["file_path"])}</div>
        </div>
      </td>
      <td>
        <div class="cell-main">
          <div class="cell-title">{escape(source_name)}</div>
          <div class="cell-subtle">{escape(source_note)}</div>
        </div>
      </td>
      <td>{render_status_badge(file_status, kind="file")}</td>
      <td class="number">{format_size(item["file_size"])}</td>
      <td class="number">{escape(item["page_count"] if item["page_count"] is not None else "—")}</td>
      <td>{escape(format_datetime(modified))}</td>
      <td>
        <a class="details-toggle" href="#{details_id}">Открыть детали</a>
      </td>
    </tr>
    <tr class="details-row {row_class}" id="{details_id}">
      <td colspan="7">
        <div class="details-card">
          <div class="details-card-header">
            <div class="details-card-title">Подробности по файлу</div>
            <a class="details-close" href="#">Скрыть детали</a>
          </div>
          <div class="details-grid">
            <div class="muted">Полный путь</div>
            <div class="mono">{escape(item["file_path"])}</div>
            <div class="muted">Внешний id</div>
            <div class="mono">{escape(item["external_id"])}</div>
            <div class="muted">Создан</div>
            <div>{escape(format_datetime(item["created_at_remote"] or item["created_at"]))}</div>
            <div class="muted">Обновлен</div>
            <div>{escape(format_datetime(modified))}</div>
          </div>
          <div class="next-step">{escape(next_step_for_file(file_status))}</div>
        </div>
      </td>
    </tr>
    """


def render_event_row(item: dict) -> str:
    row_class = "problem-row" if item["status"] in PROBLEM_STATUSES else ""
    return f"""
    <tr class="{row_class}">
      <td>{escape(format_event_action(item["action_type"]))}</td>
      <td>{render_status_badge(item["status"], kind="event")}</td>
      <td>
        <div class="cell-main">
          <div class="cell-title">{escape(item["summary"])}</div>
          <div class="cell-subtle mono">{escape(item["artifacts"])}</div>
        </div>
      </td>
      <td>{escape(format_datetime(item["created_at"]))}</td>
    </tr>
    """


def render_state_link(
    active_value: str,
    value: str,
    label: str,
    param_name: str,
    cabinet_id: str,
    source_filter: str,
    sort_by: str,
    density: str,
) -> str:
    css_class = "chip-link active" if active_value == value else "chip-link"
    href = build_query_href(
        cabinet_id=cabinet_id,
        source_filter=source_filter,
        sort_by=sort_by,
        density=density,
        override={param_name: value},
    )
    return f'<a class="{css_class}" href="{href}">{escape(label)}</a>'


def build_query_href(
    cabinet_id: str = "default",
    source_filter: str = "all",
    sort_by: str = "updated",
    density: str = "normal",
    override: dict[str, str] | None = None,
) -> str:
    params = {
        "cabinet_id": normalize_cabinet_id(cabinet_id),
        "source": source_filter,
        "sort": sort_by,
        "density": density,
    }
    if override:
        params.update(override)
    query_parts = []
    for key in ("cabinet_id", "source", "sort", "density"):
        value = params[key]
        if key == "source" and value == "all":
            continue
        if key == "sort" and value == "updated":
            continue
        if key == "density" and value == "normal":
            continue
        query_parts.append(f"{key}={quote_plus(value)}")
    return "/" if not query_parts else f"/?{'&'.join(query_parts)}"


def build_post_action(path: str, cabinet_id: str) -> str:
    return f"{path}?cabinet_id={quote_plus(normalize_cabinet_id(cabinet_id))}"


def normalize_cabinet_id(value: str | None) -> str:
    cleaned = (value or "").strip()
    return cleaned or "default"


def render_status_badge(value: str, kind: str) -> str:
    label = format_status_label(value, kind)
    css_class = "status-badge"
    if value in {"failed", "error"}:
      css_class += " failed"
    elif value in {"idle", "in_progress", "needs_review", "needs_documents"}:
      css_class += " warning"
    return f'<span class="{css_class}">{escape(label)}</span>'


def format_status_label(value: str, kind: str) -> str:
    if kind == "source":
        return format_source_status(value)
    if kind == "file":
        return FILE_STATUS_LABELS.get(value, value)
    if kind == "event":
        return format_event_status(value)
    return value


def next_step_for_source(status: str) -> str:
    if status == "failed":
        return "Проверьте ссылку и повторите синхронизацию."
    if status == "idle":
        return "Запустите первую синхронизацию для заполнения реестра."
    return "Следующий шаг не требуется."


def next_step_for_file(status: str) -> str:
    if status in {"failed", "error"}:
        return "Нужна повторная загрузка или повторная синхронизация источника."
    if status == "needs_review":
        return "Проверьте файл вручную и уточните источник данных."
    if status == "needs_documents":
        return "Добавьте недостающие документы в исходную папку."
    return "Файл готов к дальнейшей работе."


def sort_label(sort_by: str) -> str:
    for value, label in SORT_OPTIONS:
        if value == sort_by:
            return label
    return "Сначала новые"


def format_size(value: int | None) -> str:
    if value is None:
        return "—"
    size = float(value)
    units = ["B", "KB", "MB", "GB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def format_datetime(value: str | None) -> str:
    if not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    return parsed.strftime("%d.%m.%Y %H:%M")


def format_source_status(value: str) -> str:
    return SOURCE_STATUS_LABELS.get(value, value)


def format_event_action(value: str) -> str:
    return EVENT_ACTION_LABELS.get(value, value)


def format_event_status(value: str) -> str:
    return EVENT_STATUS_LABELS.get(value, value)


def escape(value) -> str:
    return html.escape(str(value), quote=True)


def parse_form_body(headers, body: bytes) -> dict[str, str]:
    content_type = headers.get("Content-Type", "")
    if "application/x-www-form-urlencoded" not in content_type:
        return {}
    parsed = parse_qs(body.decode("utf-8", errors="ignore"), keep_blank_values=True)
    return {key: values[0] for key, values in parsed.items()}


def parse_multipart_upload(headers, body: bytes) -> tuple[str, bytes]:
    content_type = headers.get("Content-Type", "")
    boundary_mark = "boundary="
    if boundary_mark not in content_type:
        return "", b""

    boundary = content_type.split(boundary_mark, 1)[1].strip().strip('"')
    delimiter = f"--{boundary}".encode("utf-8")
    for part in body.split(delimiter):
        stripped = part.strip()
        if not stripped or stripped == b"--":
            continue
        header_blob, separator, payload = stripped.partition(b"\r\n\r\n")
        if not separator:
            continue
        header_text = header_blob.decode("utf-8", errors="ignore")
        if 'name="file"' not in header_text or "filename=" not in header_text:
            continue
        filename = extract_filename(header_text)
        return filename, payload.rstrip(b"\r\n")
    return "", b""


def extract_filename(header_text: str) -> str:
    marker = 'filename="'
    start = header_text.find(marker)
    if start == -1:
        return ""
    start += len(marker)
    end = header_text.find('"', start)
    if end == -1:
        return ""
    return header_text[start:end]
