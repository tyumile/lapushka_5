import html
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from urllib.parse import unquote

from app.service import IngestRegistryService


LOGGER = logging.getLogger(__name__)


class IngestRegistryHandler(BaseHTTPRequestHandler):
    service: IngestRegistryService

    @classmethod
    def build(cls, service: IngestRegistryService):
        class Handler(cls):
            pass

        Handler.service = service
        return Handler

    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND, "Page not found")
            return
        payload = render_dashboard(self.service.dashboard()).encode("utf-8")
        self._send_html(payload)

    def do_POST(self) -> None:
        if self.path == "/upload":
            self._handle_upload()
            return
        if self.path.startswith("/sync/"):
            source_name = self.path.rsplit("/", 1)[-1]
            self.service.run_sync_stub(source_name)
            self._redirect_home()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Action not found")

    def _handle_upload(self) -> None:
        filename, payload = parse_multipart_upload(self.headers, self.rfile.read(self._content_length()))
        if not filename:
            self.send_error(HTTPStatus.BAD_REQUEST, "File is required")
            return
        self.service.handle_upload(filename, payload)
        self._redirect_home()

    def _content_length(self) -> int:
        try:
            return int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return 0

    def _redirect_home(self) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", "/")
        self.end_headers()

    def _send_html(self, payload: bytes) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)


def render_dashboard(data: dict) -> str:
    file_rows = "\n".join(render_file_row(item) for item in data["files"])
    if not file_rows:
        file_rows = (
            "<tr><td colspan='7'>Registry is empty. Upload a file or run a source stub.</td></tr>"
        )

    source_blocks = "\n".join(render_source_card(item) for item in data["sources"])
    recent_events = "\n".join(render_event_row(item) for item in data["recent_logs"])
    if not recent_events:
        recent_events = "<tr><td colspan='4'>No activity yet.</td></tr>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ingest_registry</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f1e8;
      --panel: #fffdf8;
      --ink: #1c2a2f;
      --muted: #5f6b6f;
      --line: #d7d0c3;
      --accent: #245c57;
      --accent-soft: #dcebe8;
      --warn: #8a5a00;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", sans-serif;
      background: linear-gradient(180deg, #efe9db 0%, var(--bg) 55%, #ece7da 100%);
      color: var(--ink);
    }}
    main {{
      max-width: 1160px;
      margin: 0 auto;
      padding: 24px 16px 40px;
    }}
    h1, h2 {{ margin: 0 0 12px; }}
    p {{ margin: 0; color: var(--muted); }}
    .hero {{
      display: grid;
      gap: 12px;
      padding: 20px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: 0 18px 40px rgba(39, 51, 49, 0.08);
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 4px;
    }}
    .card, .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
    }}
    .metric strong {{
      display: block;
      font-size: 28px;
      color: var(--accent);
    }}
    .layout {{
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 16px;
      margin-top: 16px;
    }}
    .stack {{
      display: grid;
      gap: 16px;
    }}
    .source-grid {{
      display: grid;
      gap: 12px;
    }}
    .source-status {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 13px;
    }}
    form {{
      display: grid;
      gap: 10px;
    }}
    input[type="file"] {{
      border: 1px dashed var(--line);
      padding: 12px;
      border-radius: 10px;
      background: #faf7f0;
    }}
    button {{
      width: fit-content;
      border: 0;
      border-radius: 10px;
      background: var(--accent);
      color: white;
      padding: 10px 14px;
      cursor: pointer;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      font-size: 14px;
    }}
    th, td {{
      text-align: left;
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
    }}
    .table-wrap {{
      overflow-x: auto;
    }}
    .muted {{
      color: var(--muted);
      font-size: 13px;
    }}
    @media (max-width: 860px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>ingest_registry</h1>
      <p>Autonomous module for local uploads and future Google Drive / Yandex Disk synchronization.</p>
      <p class="muted">DB: {escape(data["db_path"])} | Port: {data["port"]}</p>
      <div class="stats">
        <div class="metric"><span class="muted">Files in registry</span><strong>{data["counts"]["files"]}</strong></div>
        <div class="metric"><span class="muted">Sources configured</span><strong>{data["counts"]["sources"]}</strong></div>
        <div class="metric"><span class="muted">Ready sources</span><strong>{data["counts"]["ready_sources"]}</strong></div>
      </div>
    </section>

    <section class="layout">
      <div class="stack">
        <section class="card">
          <h2>Local Upload</h2>
          <p class="muted">Stores the file under this module and writes metadata to the registry.</p>
          <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <button type="submit">Upload File</button>
          </form>
        </section>

        <section class="card">
          <h2>File Registry</h2>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Source</th>
                  <th>Name</th>
                  <th>Path</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Size</th>
                </tr>
              </thead>
              <tbody>
                {file_rows}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <div class="stack">
        <section class="card">
          <h2>Source Status</h2>
          <div class="source-grid">
            {source_blocks}
          </div>
        </section>

        <section class="card">
          <h2>Recent Activity</h2>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Status</th>
                  <th>Summary</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {recent_events}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </section>
  </main>
</body>
</html>
"""


def render_source_card(item: dict) -> str:
    source_name = escape(item["source_name"])
    return f"""
    <article class="card">
      <h3>{source_name}</h3>
      <p><span class="source-status">{escape(item["status"])}</span></p>
      <p class="muted">{escape(item["message"])}</p>
      <p class="muted">Last sync: {escape(item["last_sync_at"] or "not run yet")}</p>
      <form action="/sync/{source_name}" method="post">
        <button type="submit">Run Stub Sync</button>
      </form>
    </article>
    """


def render_file_row(item: dict) -> str:
    return f"""
    <tr>
      <td>{item["id"]}</td>
      <td>{escape(item["source_name"])}</td>
      <td>{escape(item["file_name"])}</td>
      <td>{escape(item["file_path"])}</td>
      <td>{escape(item["file_date"])}</td>
      <td>{escape(item["status"])}</td>
      <td>{item["file_size"]}</td>
    </tr>
    """


def render_event_row(item: dict) -> str:
    return f"""
    <tr>
      <td>{escape(item["action_type"])}</td>
      <td>{escape(item["status"])}</td>
      <td>{escape(item["summary"])}</td>
      <td>{escape(item["created_at"])}</td>
    </tr>
    """


def escape(value: str) -> str:
    return html.escape(str(value), quote=True)


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
    if marker not in header_text:
        return ""
    filename = header_text.split(marker, 1)[1].split('"', 1)[0]
    return unquote(filename)
