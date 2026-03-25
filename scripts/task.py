#!/usr/bin/env python3
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from google.oauth2 import service_account
from googleapiclient.discovery import build


HEADERS = [
    "task_id",
    "source_agent",
    "target_agent",
    "module_name",
    "action_type",
    "summary",
    "status",
    "artifacts",
    "created_at",
]


def load_env(project_root: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = project_root / ".env"
    if not env_path.exists():
        return env
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key] = value
    return env


def sqlite_path_from_url(db_url: str) -> Path:
    if not db_url.startswith("sqlite:///"):
        raise ValueError("Only sqlite URLs are supported by this script.")
    parsed = urlparse(db_url)
    return Path(parsed.path)


def connect_db(project_root: Path, env: dict[str, str]) -> sqlite3.Connection:
    db_url = env.get("TASK_REGISTRY_DB_URL", "")
    if not db_url:
        raise ValueError("TASK_REGISTRY_DB_URL is not set in .env")
    db_path = sqlite_path_from_url(db_url)
    if not db_path.is_absolute():
        db_path = project_root / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def ensure_db(conn: sqlite3.Connection, project_root: Path) -> None:
    schema = (project_root / "shared" / "task_registry.sql").read_text()
    conn.executescript(schema)
    conn.commit()


def build_sheets_service(env: dict[str, str], readonly: bool = False) -> Any:
    json_path = env.get("GOOGLE_SERVICE_ACCOUNT_JSON_PATH", "")
    if not json_path:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON_PATH is not set in .env")
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    if not readonly:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file(json_path, scopes=scopes)
    return build("sheets", "v4", credentials=creds)


def get_sheet_id(env: dict[str, str]) -> str:
    sheet_id = env.get("GOOGLE_SHEETS_DASHBOARD_ID", "")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEETS_DASHBOARD_ID is not set in .env")
    return sheet_id


def get_target_sheet_name(service: Any, spreadsheet_id: str, env: dict[str, str]) -> str:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = meta.get("sheets", [])
    env_sheet = env.get("GOOGLE_SHEETS_WORKSHEET_NAME", "").strip()
    if env_sheet:
        for sheet in sheets:
            title = sheet["properties"]["title"]
            if title == env_sheet:
                return title
        raise RuntimeError(f"Worksheet '{env_sheet}' was not found in the spreadsheet.")
    for sheet in sheets:
        if sheet["properties"]["sheetId"] == 0:
            return sheet["properties"]["title"]
    for sheet in sheets:
        title = sheet["properties"]["title"]
        if title == "tasks":
            return title
    if sheets:
        return sheets[0]["properties"]["title"]
    raise RuntimeError("Spreadsheet has no sheets.")


def ensure_sheet_headers(service: Any, spreadsheet_id: str, sheet_name: str) -> None:
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1:I1",
        valueInputOption="RAW",
        body={"values": [HEADERS]},
    ).execute()


def insert_task(conn: sqlite3.Connection, row: dict[str, str]) -> int:
    cursor = conn.execute(
        """
        INSERT INTO task_registry (
            task_id,
            source_agent,
            target_agent,
            module_name,
            action_type,
            summary,
            status,
            artifacts,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["task_id"],
            row["source_agent"],
            row["target_agent"],
            row["module_name"],
            row["action_type"],
            row["summary"],
            row["status"],
            row["artifacts"],
            row["created_at"],
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def fetch_rows(conn: sqlite3.Connection, args: argparse.Namespace) -> list[sqlite3.Row]:
    clauses = []
    params: list[str | int] = []
    if args.task_id:
        clauses.append("task_id = ?")
        params.append(args.task_id)
    if args.module_name:
        clauses.append("module_name = ?")
        params.append(args.module_name)
    if args.target_agent:
        clauses.append("target_agent = ?")
        params.append(args.target_agent)
    if args.source_agent:
        clauses.append("source_agent = ?")
        params.append(args.source_agent)
    where_sql = ""
    if clauses:
        where_sql = "WHERE " + " AND ".join(clauses)
    params.append(args.limit)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        f"""
        SELECT id, task_id, source_agent, target_agent, module_name,
               action_type, summary, status, artifacts, created_at
        FROM task_registry
        {where_sql}
        ORDER BY id DESC
        LIMIT ?
        """,
        params,
    )
    return cursor.fetchall()


def normalize_sheet_row(row: list[str]) -> tuple[str, ...]:
    normalized = list(row[: len(HEADERS)])
    while len(normalized) < len(HEADERS):
        normalized.append("")
    return tuple(normalized)


def read_sheet_rows(service: Any, spreadsheet_id: str, sheet_name: str) -> set[tuple[str, ...]]:
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A2:I",
    ).execute()
    values = result.get("values", [])
    return {normalize_sheet_row(row) for row in values if any(cell.strip() for cell in row)}


def sync_rows(conn: sqlite3.Connection, env: dict[str, str]) -> int:
    service = build_sheets_service(env)
    spreadsheet_id = get_sheet_id(env)
    sheet_name = get_target_sheet_name(service, spreadsheet_id, env)
    ensure_sheet_headers(service, spreadsheet_id, sheet_name)
    existing_rows = read_sheet_rows(service, spreadsheet_id, sheet_name)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT task_id, source_agent, target_agent, module_name,
               action_type, summary, status, artifacts, created_at
        FROM task_registry
        ORDER BY id ASC
        """
    ).fetchall()
    to_append = []
    for row in rows:
        values = tuple(str(row[key] or "") for key in HEADERS)
        if values not in existing_rows:
            to_append.append(list(values))
    if not to_append:
        return 0
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A:I",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": to_append},
    ).execute()
    return len(to_append)


def cmd_ensure_db(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    env = load_env(project_root)
    conn = connect_db(project_root, env)
    try:
        ensure_db(conn, project_root)
    finally:
        conn.close()
    print("db_ready=yes")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    env = load_env(project_root)
    conn = connect_db(project_root, env)
    try:
        ensure_db(conn, project_root)
        rows = fetch_rows(conn, args)
    finally:
        conn.close()
    output = []
    for row in rows:
        output.append({key: row[key] for key in row.keys()})
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    env = load_env(project_root)
    conn = connect_db(project_root, env)
    created_at = args.created_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    row = {
        "task_id": args.task_id,
        "source_agent": args.source_agent,
        "target_agent": args.target_agent,
        "module_name": args.module_name,
        "action_type": args.action_type,
        "summary": args.summary,
        "status": args.status,
        "artifacts": args.artifacts or "",
        "created_at": created_at,
    }
    try:
        ensure_db(conn, project_root)
        row_id = insert_task(conn, row)
        synced = 0
        if args.sync:
            synced = sync_rows(conn, env)
    finally:
        conn.close()
    print(f"inserted_id={row_id}")
    print(f"task_id={row['task_id']}")
    print(f"synced_rows={synced}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    env = load_env(project_root)
    conn = connect_db(project_root, env)
    try:
        ensure_db(conn, project_root)
        synced = sync_rows(conn, env)
    finally:
        conn.close()
    print(f"synced_rows={synced}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lapushka 5 task registry CLI")
    parser.add_argument(
        "--project-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Project root containing .env and shared/task_registry.sql",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ensure_parser = subparsers.add_parser("ensure-db", help="Create task registry table if needed")
    ensure_parser.set_defaults(func=cmd_ensure_db)

    list_parser = subparsers.add_parser("list", help="List task records from SQL")
    list_parser.add_argument("--task-id")
    list_parser.add_argument("--module-name")
    list_parser.add_argument("--target-agent")
    list_parser.add_argument("--source-agent")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.set_defaults(func=cmd_list)

    add_parser = subparsers.add_parser("add", help="Insert a task record into SQL")
    add_parser.add_argument("--task-id", required=True)
    add_parser.add_argument("--source-agent", required=True)
    add_parser.add_argument("--target-agent", required=True)
    add_parser.add_argument("--module-name", required=True)
    add_parser.add_argument("--action-type", required=True)
    add_parser.add_argument("--summary", required=True)
    add_parser.add_argument("--status", required=True)
    add_parser.add_argument("--artifacts", default="")
    add_parser.add_argument("--created-at")
    add_parser.add_argument("--sync", action="store_true", help="Append missing SQL rows to Google Sheets")
    add_parser.set_defaults(func=cmd_add)

    sync_parser = subparsers.add_parser("sync", help="Sync SQL rows to Google Sheets")
    sync_parser.set_defaults(func=cmd_sync)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(f"error={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
