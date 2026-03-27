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


REVIEWER_TYPES = {
    "frontend_reviewer": "frontend",
    "backend_reviewer": "backend",
    "db_reviewer": "db",
    "prompt_reviewer": "prompt",
}

MODULE_ACTIVE_STATUSES = ("todo", "in_progress", "ready_for_review", "failed", "blocked")
REVIEW_RESULTS = {
    "reviewed": "passed",
    "done": "passed",
    "failed": "failed",
    "blocked": "blocked",
}
TASK_STATUS_BY_ACTION = {
    "start": "in_progress",
    "progress": "in_progress",
    "done": "done",
    "blocked": "blocked",
    "error": "failed",
}
SHEET_HEADERS = [
    "task_id",
    "cabinet_id",
    "module_name",
    "task_status",
    "source_agent",
    "target_agent",
    "review_type",
    "handoff_status",
    "review_result",
    "summary",
    "implementation_report",
    "checks_required",
    "policy_checks",
    "artifacts",
    "updated_at",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
    ensure_task_schema_migrations(conn)
    migrate_legacy_registry(conn)
    conn.commit()


def infer_review_type(agent_name: str) -> str:
    return REVIEWER_TYPES.get(agent_name, "")


def normalize_task_status(action_type: str, status: str) -> str:
    return TASK_STATUS_BY_ACTION.get(action_type, status or "in_progress")


def normalize_review_result(status: str, explicit_result: str) -> str:
    if explicit_result:
        return explicit_result
    return REVIEW_RESULTS.get(status, "passed")


def task_exists(conn: sqlite3.Connection, task_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    return row is not None


def upsert_task(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    cabinet_id: str,
    module_name: str,
    title: str,
    created_by: str,
    assigned_agent: str,
    status: str,
    latest_summary: str,
    latest_artifacts: str,
    created_at: str,
    updated_at: str,
) -> None:
    existing = conn.execute(
        """
        SELECT task_id, title, created_by, created_at
        FROM tasks
        WHERE task_id = ?
        """,
        (task_id,),
    ).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE tasks
            SET cabinet_id = ?,
                module_name = ?,
                title = ?,
                assigned_agent = ?,
                status = ?,
                latest_summary = ?,
                latest_artifacts = ?,
                updated_at = ?
            WHERE task_id = ?
            """,
            (
                cabinet_id,
                module_name,
                title or existing[1],
                assigned_agent,
                status,
                latest_summary,
                latest_artifacts,
                updated_at,
                task_id,
            ),
        )
        return
    conn.execute(
        """
        INSERT INTO tasks (
            task_id,
            cabinet_id,
            module_name,
            title,
            created_by,
            assigned_agent,
            status,
            latest_summary,
            latest_artifacts,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            cabinet_id,
            module_name,
            title,
            created_by,
            assigned_agent,
            status,
            latest_summary,
            latest_artifacts,
            created_at,
            updated_at,
        ),
    )


def insert_event(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    cabinet_id: str,
    module_name: str,
    event_type: str,
    source_agent: str,
    target_agent: str,
    status: str,
    summary: str,
    details: str,
    artifacts: str,
    created_at: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO task_events (
            task_id,
            cabinet_id,
            module_name,
            event_type,
            source_agent,
            target_agent,
            status,
            summary,
            details,
            artifacts,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            cabinet_id,
            module_name,
            event_type,
            source_agent,
            target_agent,
            status,
            summary,
            details,
            artifacts,
            created_at,
        ),
    )
    return int(cursor.lastrowid)


def add_handoff(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    cabinet_id: str,
    module_name: str,
    source_agent: str,
    target_agent: str,
    review_type: str,
    summary: str,
    implementation_report: str,
    checks_required: str,
    artifacts: str,
    created_at: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO task_handoffs (
            task_id,
            cabinet_id,
            module_name,
            source_agent,
            target_agent,
            review_type,
            summary,
            implementation_report,
            checks_required,
            artifacts,
            status,
            created_at,
            claimed_at,
            reviewed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, '', '')
        """,
        (
            task_id,
            cabinet_id,
            module_name,
            source_agent,
            target_agent,
            review_type,
            summary,
            implementation_report,
            checks_required,
            artifacts,
            created_at,
        ),
    )
    return int(cursor.lastrowid)


def find_open_handoff(conn: sqlite3.Connection, task_id: str, reviewer_agent: str) -> sqlite3.Row | None:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        """
        SELECT id, task_id, module_name, source_agent, target_agent, review_type, status
        FROM task_handoffs
        WHERE task_id = ?
          AND target_agent = ?
          AND status IN ('pending', 'claimed')
        ORDER BY id DESC
        LIMIT 1
        """,
        (task_id, reviewer_agent),
    ).fetchone()


def insert_review(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    handoff_id: int,
    cabinet_id: str,
    module_name: str,
    reviewer_agent: str,
    review_type: str,
    result: str,
    summary: str,
    what_works: str,
    what_fails: str,
    policy_checks: str,
    artifacts: str,
    created_at: str,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO task_reviews (
            task_id,
            handoff_id,
            cabinet_id,
            module_name,
            reviewer_agent,
            review_type,
            result,
            summary,
            what_works,
            what_fails,
            policy_checks,
            artifacts,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            handoff_id,
            cabinet_id,
            module_name,
            reviewer_agent,
            review_type,
            result,
            summary,
            what_works,
            what_fails,
            policy_checks,
            artifacts,
            created_at,
        ),
    )
    return int(cursor.lastrowid)


def update_task_status(
    conn: sqlite3.Connection,
    task_id: str,
    cabinet_id: str,
    status: str,
    summary: str,
    artifacts: str,
    updated_at: str,
) -> None:
    conn.execute(
        """
        UPDATE tasks
        SET cabinet_id = ?,
            status = ?,
            latest_summary = ?,
            latest_artifacts = ?,
            updated_at = ?
        WHERE task_id = ?
        """,
        (cabinet_id, status, summary, artifacts, updated_at, task_id),
    )


def recompute_task_review_status(conn: sqlite3.Connection, task_id: str) -> None:
    pending_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM task_handoffs
        WHERE task_id = ?
          AND status IN ('pending', 'claimed')
        """,
        (task_id,),
    ).fetchone()[0]
    failed_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM task_reviews
        WHERE task_id = ?
          AND result IN ('failed', 'blocked')
        """,
        (task_id,),
    ).fetchone()[0]
    if pending_count:
        status = "ready_for_review"
    elif failed_count:
        status = "failed"
    else:
        status = "reviewed"
    conn.execute(
        "UPDATE tasks SET status = ?, updated_at = ? WHERE task_id = ?",
        (status, now_iso(), task_id),
    )


def has_table(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def ensure_column(conn: sqlite3.Connection, table_name: str, column_sql: str, column_name: str) -> None:
    if has_table(conn, table_name) and not has_column(conn, table_name, column_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def ensure_task_schema_migrations(conn: sqlite3.Connection) -> None:
    ensure_column(conn, "tasks", "cabinet_id TEXT NOT NULL DEFAULT 'default'", "cabinet_id")
    ensure_column(conn, "task_handoffs", "cabinet_id TEXT NOT NULL DEFAULT 'default'", "cabinet_id")
    ensure_column(conn, "task_reviews", "cabinet_id TEXT NOT NULL DEFAULT 'default'", "cabinet_id")
    ensure_column(conn, "task_events", "cabinet_id TEXT NOT NULL DEFAULT 'default'", "cabinet_id")
    ensure_column(conn, "task_registry", "cabinet_id TEXT NOT NULL DEFAULT 'default'", "cabinet_id")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_cabinet_id ON tasks (cabinet_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_handoffs_cabinet_id ON task_handoffs (cabinet_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_reviews_cabinet_id ON task_reviews (cabinet_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_events_cabinet_id ON task_events (cabinet_id)")


def meta_value(conn: sqlite3.Connection, key: str) -> str:
    row = conn.execute(
        "SELECT value FROM task_meta WHERE key = ?",
        (key,),
    ).fetchone()
    return row[0] if row else ""


def set_meta_value(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO task_meta (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def migrate_legacy_registry(conn: sqlite3.Connection) -> None:
    if meta_value(conn, "legacy_task_registry_migrated") == "1":
        return
    if conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] > 0:
        set_meta_value(conn, "legacy_task_registry_migrated", "1")
        return
    if not has_table(conn, "task_registry"):
        set_meta_value(conn, "legacy_task_registry_migrated", "1")
        return

    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, task_id, cabinet_id, source_agent, target_agent, module_name,
               action_type, summary, status, artifacts, created_at
        FROM task_registry
        ORDER BY id ASC
        """
    ).fetchall()

    for row in rows:
        created_at = str(row["created_at"])
        task_id = str(row["task_id"])
        cabinet_id = str(row["cabinet_id"] or "default")
        source_agent = str(row["source_agent"])
        target_agent = str(row["target_agent"])
        module_name = str(row["module_name"])
        action_type = str(row["action_type"])
        summary = str(row["summary"])
        status = str(row["status"])
        artifacts = str(row["artifacts"] or "")
        review_type = infer_review_type(target_agent) or infer_review_type(source_agent)

        if action_type in {"start", "progress"}:
            upsert_task(
                conn,
                task_id=task_id,
                cabinet_id=cabinet_id,
                module_name=module_name,
                title=summary,
                created_by=source_agent,
                assigned_agent=source_agent,
                status=normalize_task_status(action_type, status),
                latest_summary=summary,
                latest_artifacts=artifacts,
                created_at=created_at,
                updated_at=created_at,
            )
            insert_event(
                conn,
                task_id=task_id,
                cabinet_id=cabinet_id,
                module_name=module_name,
                event_type=action_type,
                source_agent=source_agent,
                target_agent=target_agent,
                status=status,
                summary=summary,
                details="migrated from legacy registry",
                artifacts=artifacts,
                created_at=created_at,
            )
            continue

        if action_type == "handoff" or (action_type == "done" and review_type and source_agent != target_agent):
            if not task_exists(conn, task_id):
                upsert_task(
                    conn,
                    task_id=task_id,
                    cabinet_id=cabinet_id,
                    module_name=module_name,
                    title=summary,
                    created_by=source_agent,
                    assigned_agent=source_agent,
                    status="ready_for_review",
                    latest_summary=summary,
                    latest_artifacts=artifacts,
                    created_at=created_at,
                    updated_at=created_at,
                )
            else:
                update_task_status(conn, task_id, cabinet_id, "ready_for_review", summary, artifacts, created_at)
            add_handoff(
                conn,
                task_id=task_id,
                cabinet_id=cabinet_id,
                module_name=module_name,
                source_agent=source_agent,
                target_agent=target_agent,
                review_type=review_type or "review",
                summary=summary,
                implementation_report=summary,
                checks_required="migrated from legacy registry",
                artifacts=artifacts,
                created_at=created_at,
            )
            insert_event(
                conn,
                task_id=task_id,
                cabinet_id=cabinet_id,
                module_name=module_name,
                event_type="handoff",
                source_agent=source_agent,
                target_agent=target_agent,
                status="pending",
                summary=summary,
                details="migrated from legacy registry",
                artifacts=artifacts,
                created_at=created_at,
            )
            continue

        if action_type == "review":
            open_handoff = find_open_handoff(conn, task_id, source_agent)
            if open_handoff is None:
                synthetic_handoff_id = add_handoff(
                    conn,
                    task_id=task_id,
                    cabinet_id=cabinet_id,
                    module_name=module_name,
                    source_agent=target_agent or module_name,
                    target_agent=source_agent,
                    review_type=review_type or "review",
                    summary="Migrated synthetic handoff for legacy review",
                    implementation_report="migrated from legacy registry",
                    checks_required="migrated from legacy registry",
                    artifacts=artifacts,
                    created_at=created_at,
                )
                conn.execute(
                    """
                    UPDATE task_handoffs
                    SET status = 'reviewed', reviewed_at = ?
                    WHERE id = ?
                    """,
                    (created_at, synthetic_handoff_id),
                )
                handoff_id = synthetic_handoff_id
                handoff_review_type = review_type or "review"
            else:
                handoff_id = int(open_handoff["id"])
                handoff_review_type = str(open_handoff["review_type"])
                conn.execute(
                    """
                    UPDATE task_handoffs
                    SET status = 'reviewed', reviewed_at = ?
                    WHERE id = ?
                    """,
                    (created_at, handoff_id),
                )
            insert_review(
                conn,
                task_id=task_id,
                handoff_id=handoff_id,
                cabinet_id=cabinet_id,
                module_name=module_name,
                reviewer_agent=source_agent,
                review_type=handoff_review_type,
                result=normalize_review_result(status, ""),
                summary=summary,
                what_works="",
                what_fails="",
                policy_checks="migrated from legacy registry",
                artifacts=artifacts,
                created_at=created_at,
            )
            insert_event(
                conn,
                task_id=task_id,
                cabinet_id=cabinet_id,
                module_name=module_name,
                event_type="review",
                source_agent=source_agent,
                target_agent=target_agent,
                status=status,
                summary=summary,
                details="migrated from legacy registry",
                artifacts=artifacts,
                created_at=created_at,
            )
            recompute_task_review_status(conn, task_id)
            continue

        mapped_status = normalize_task_status(action_type, status)
        if not task_exists(conn, task_id):
            upsert_task(
                conn,
                task_id=task_id,
                cabinet_id=cabinet_id,
                module_name=module_name,
                title=summary,
                created_by=source_agent,
                assigned_agent=source_agent,
                status=mapped_status,
                latest_summary=summary,
                latest_artifacts=artifacts,
                created_at=created_at,
                updated_at=created_at,
            )
        else:
            update_task_status(conn, task_id, cabinet_id, mapped_status, summary, artifacts, created_at)
        insert_event(
            conn,
            task_id=task_id,
            cabinet_id=cabinet_id,
            module_name=module_name,
            event_type=action_type,
            source_agent=source_agent,
            target_agent=target_agent,
            status=status,
            summary=summary,
            details="migrated from legacy registry",
            artifacts=artifacts,
            created_at=created_at,
        )

    set_meta_value(conn, "legacy_task_registry_migrated", "1")


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
    if sheets:
        return sheets[0]["properties"]["title"]
    raise RuntimeError("Spreadsheet has no sheets.")


def collect_dashboard_rows(conn: sqlite3.Connection) -> list[list[str]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        WITH latest_reviews AS (
            SELECT r.*
            FROM task_reviews AS r
            INNER JOIN (
                SELECT handoff_id, MAX(id) AS max_id
                FROM task_reviews
                GROUP BY handoff_id
            ) AS grouped
                ON grouped.handoff_id = r.handoff_id
               AND grouped.max_id = r.id
        )
        SELECT t.task_id,
               t.cabinet_id,
               t.module_name,
               t.status AS task_status,
               COALESCE(h.source_agent, t.created_by) AS source_agent,
               COALESCE(h.target_agent, '') AS target_agent,
               COALESCE(h.review_type, '') AS review_type,
               COALESCE(h.status, '') AS handoff_status,
               COALESCE(r.result, '') AS review_result,
               COALESCE(h.summary, t.latest_summary) AS summary,
               COALESCE(h.implementation_report, '') AS implementation_report,
               COALESCE(h.checks_required, '') AS checks_required,
               COALESCE(r.policy_checks, '') AS policy_checks,
               COALESCE(r.artifacts, h.artifacts, t.latest_artifacts) AS artifacts,
               COALESCE(r.created_at, h.reviewed_at, h.created_at, t.updated_at) AS updated_at
        FROM tasks AS t
        LEFT JOIN task_handoffs AS h
            ON h.task_id = t.task_id
        LEFT JOIN latest_reviews AS r
            ON r.handoff_id = h.id
        ORDER BY t.updated_at DESC, h.id DESC
        """
    ).fetchall()
    output: list[list[str]] = []
    for row in rows:
        output.append([str(row[key] or "") for key in SHEET_HEADERS])
    return output


def rewrite_sheet(service: Any, spreadsheet_id: str, sheet_name: str, rows: list[list[str]]) -> int:
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A:Z",
        body={},
    ).execute()
    values = [SHEET_HEADERS]
    values.extend(rows)
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="RAW",
        body={"values": values},
    ).execute()
    return len(rows)


def sync_rows(conn: sqlite3.Connection, env: dict[str, str]) -> int:
    service = build_sheets_service(env)
    spreadsheet_id = get_sheet_id(env)
    sheet_name = get_target_sheet_name(service, spreadsheet_id, env)
    rows = collect_dashboard_rows(conn)
    return rewrite_sheet(service, spreadsheet_id, sheet_name, rows)


def fetch_event_rows(conn: sqlite3.Connection, args: argparse.Namespace) -> list[sqlite3.Row]:
    clauses = []
    params: list[str | int] = []
    if args.task_id:
        clauses.append("task_id = ?")
        params.append(args.task_id)
    if args.cabinet_id:
        clauses.append("cabinet_id = ?")
        params.append(args.cabinet_id)
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
    return conn.execute(
        f"""
        SELECT id, task_id, cabinet_id, module_name, event_type, source_agent, target_agent,
               status, summary, details, artifacts, created_at
        FROM task_events
        {where_sql}
        ORDER BY id DESC
        LIMIT ?
        """,
        params,
    ).fetchall()


def fetch_module_task_rows(conn: sqlite3.Connection, agent: str, limit: int, cabinet_id: str) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    placeholders = ", ".join("?" for _ in MODULE_ACTIVE_STATUSES)
    params: list[str | int] = [agent, cabinet_id]
    params.extend(MODULE_ACTIVE_STATUSES)
    params.append(limit)
    return conn.execute(
        f"""
        SELECT task_id, cabinet_id, module_name, title, assigned_agent, status,
               latest_summary, latest_artifacts, created_at, updated_at
        FROM tasks
        WHERE assigned_agent = ?
          AND cabinet_id = ?
          AND status IN ({placeholders})
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        params,
    ).fetchall()


def fetch_reviewer_handoffs(conn: sqlite3.Connection, agent: str, limit: int, cabinet_id: str) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        """
        SELECT h.id, h.task_id, h.cabinet_id, h.module_name, h.source_agent, h.target_agent,
               h.review_type, h.summary, h.implementation_report,
               h.checks_required, h.artifacts, h.status, h.created_at,
               t.status AS task_status
        FROM task_handoffs AS h
        INNER JOIN tasks AS t
            ON t.task_id = h.task_id
        WHERE h.target_agent = ?
          AND h.cabinet_id = ?
          AND h.status IN ('pending', 'claimed')
        ORDER BY h.created_at DESC, h.id DESC
        LIMIT ?
        """,
        (agent, cabinet_id, limit),
    ).fetchall()


def fetch_task_card(conn: sqlite3.Connection, task_id: str, cabinet_id: str | None = None) -> dict[str, Any]:
    conn.row_factory = sqlite3.Row
    task_row = conn.execute(
        """
        SELECT task_id, cabinet_id, module_name, title, created_by, assigned_agent, status,
               latest_summary, latest_artifacts, created_at, updated_at
        FROM tasks
        WHERE task_id = ?
        """,
        (task_id,),
    ).fetchone()
    if task_row is None:
        raise ValueError(f"Task '{task_id}' was not found.")
    if cabinet_id and str(task_row["cabinet_id"]) != cabinet_id:
        raise ValueError(f"Task '{task_id}' does not belong to cabinet '{cabinet_id}'.")
    handoffs = conn.execute(
        """
        SELECT id, task_id, cabinet_id, module_name, source_agent, target_agent, review_type,
               summary, implementation_report, checks_required, artifacts,
               status, created_at, claimed_at, reviewed_at
        FROM task_handoffs
        WHERE task_id = ?
        ORDER BY id DESC
        """,
        (task_id,),
    ).fetchall()
    reviews = conn.execute(
        """
        SELECT id, task_id, handoff_id, cabinet_id, module_name, reviewer_agent, review_type,
               result, summary, what_works, what_fails, policy_checks,
               artifacts, created_at
        FROM task_reviews
        WHERE task_id = ?
        ORDER BY id DESC
        """,
        (task_id,),
    ).fetchall()
    events = conn.execute(
        """
        SELECT id, task_id, cabinet_id, module_name, event_type, source_agent, target_agent,
               status, summary, details, artifacts, created_at
        FROM task_events
        WHERE task_id = ?
        ORDER BY id DESC
        """,
        (task_id,),
    ).fetchall()
    return {
        "task": {key: task_row[key] for key in task_row.keys()},
        "handoffs": [{key: row[key] for key in row.keys()} for row in handoffs],
        "reviews": [{key: row[key] for key in row.keys()} for row in reviews],
        "events": [{key: row[key] for key in row.keys()} for row in events],
    }


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
        rows = fetch_event_rows(conn, args)
    finally:
        conn.close()
    print(json.dumps([{key: row[key] for key in row.keys()} for row in rows], ensure_ascii=False, indent=2))
    return 0


def cmd_mine(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    env = load_env(project_root)
    conn = connect_db(project_root, env)
    try:
        ensure_db(conn, project_root)
        if infer_review_type(args.agent):
            rows = fetch_reviewer_handoffs(conn, args.agent, args.limit, args.cabinet_id)
        else:
            rows = fetch_module_task_rows(conn, args.agent, args.limit, args.cabinet_id)
    finally:
        conn.close()
    print(json.dumps([{key: row[key] for key in row.keys()} for row in rows], ensure_ascii=False, indent=2))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    env = load_env(project_root)
    conn = connect_db(project_root, env)
    try:
        ensure_db(conn, project_root)
        card = fetch_task_card(conn, args.task_id, args.cabinet_id)
    finally:
        conn.close()
    print(json.dumps(card, ensure_ascii=False, indent=2))
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    env = load_env(project_root)
    conn = connect_db(project_root, env)
    created_at = args.created_at or now_iso()
    task_title = args.title or args.summary
    event_id = 0
    handoff_id = 0
    review_id = 0
    synced = 0
    try:
        ensure_db(conn, project_root)
        action_type = args.action_type
        if action_type in {"start", "progress"}:
            upsert_task(
                conn,
                task_id=args.task_id,
                cabinet_id=args.cabinet_id,
                module_name=args.module_name,
                title=task_title,
                created_by=args.source_agent,
                assigned_agent=args.source_agent,
                status=normalize_task_status(action_type, args.status),
                latest_summary=args.summary,
                latest_artifacts=args.artifacts or "",
                created_at=created_at,
                updated_at=created_at,
            )
            event_id = insert_event(
                conn,
                task_id=args.task_id,
                cabinet_id=args.cabinet_id,
                module_name=args.module_name,
                event_type=action_type,
                source_agent=args.source_agent,
                target_agent=args.target_agent,
                status=args.status,
                summary=args.summary,
                details=args.details or "",
                artifacts=args.artifacts or "",
                created_at=created_at,
            )
        elif action_type == "handoff":
            review_type = args.review_type or infer_review_type(args.target_agent)
            if not review_type:
                raise ValueError("Handoff requires --review-type or a known reviewer target_agent.")
            if not task_exists(conn, args.task_id):
                upsert_task(
                    conn,
                    task_id=args.task_id,
                    cabinet_id=args.cabinet_id,
                    module_name=args.module_name,
                    title=task_title,
                    created_by=args.source_agent,
                    assigned_agent=args.source_agent,
                    status="ready_for_review",
                    latest_summary=args.summary,
                    latest_artifacts=args.artifacts or "",
                    created_at=created_at,
                    updated_at=created_at,
                )
            else:
                update_task_status(conn, args.task_id, args.cabinet_id, "ready_for_review", args.summary, args.artifacts or "", created_at)
            handoff_id = add_handoff(
                conn,
                task_id=args.task_id,
                cabinet_id=args.cabinet_id,
                module_name=args.module_name,
                source_agent=args.source_agent,
                target_agent=args.target_agent,
                review_type=review_type,
                summary=args.summary,
                implementation_report=args.implementation_report or args.summary,
                checks_required=args.checks_required or "",
                artifacts=args.artifacts or "",
                created_at=created_at,
            )
            event_id = insert_event(
                conn,
                task_id=args.task_id,
                cabinet_id=args.cabinet_id,
                module_name=args.module_name,
                event_type="handoff",
                source_agent=args.source_agent,
                target_agent=args.target_agent,
                status="pending",
                summary=args.summary,
                details=args.implementation_report or "",
                artifacts=args.artifacts or "",
                created_at=created_at,
            )
        elif action_type == "review":
            open_handoff = None
            if args.handoff_id:
                conn.row_factory = sqlite3.Row
                open_handoff = conn.execute(
                    """
                    SELECT id, task_id, module_name, source_agent, target_agent, review_type
                    FROM task_handoffs
                    WHERE id = ?
                    """,
                    (args.handoff_id,),
                ).fetchone()
            else:
                open_handoff = find_open_handoff(conn, args.task_id, args.source_agent)
            if open_handoff is None:
                raise ValueError("Review requires an open handoff for this reviewer. Use --handoff-id if needed.")
            handoff_id = int(open_handoff["id"])
            review_id = insert_review(
                conn,
                task_id=args.task_id,
                handoff_id=handoff_id,
                cabinet_id=args.cabinet_id,
                module_name=args.module_name,
                reviewer_agent=args.source_agent,
                review_type=str(open_handoff["review_type"]),
                result=normalize_review_result(args.status, args.result),
                summary=args.summary,
                what_works=args.what_works or "",
                what_fails=args.what_fails or "",
                policy_checks=args.policy_checks or "",
                artifacts=args.artifacts or "",
                created_at=created_at,
            )
            conn.execute(
                """
                UPDATE task_handoffs
                SET status = 'reviewed', reviewed_at = ?
                WHERE id = ?
                """,
                (created_at, handoff_id),
            )
            event_id = insert_event(
                conn,
                task_id=args.task_id,
                cabinet_id=args.cabinet_id,
                module_name=args.module_name,
                event_type="review",
                source_agent=args.source_agent,
                target_agent=args.target_agent,
                status=normalize_review_result(args.status, args.result),
                summary=args.summary,
                details=args.policy_checks or "",
                artifacts=args.artifacts or "",
                created_at=created_at,
            )
            recompute_task_review_status(conn, args.task_id)
        elif action_type in {"done", "blocked", "error"}:
            if not task_exists(conn, args.task_id):
                upsert_task(
                    conn,
                    task_id=args.task_id,
                    cabinet_id=args.cabinet_id,
                    module_name=args.module_name,
                    title=task_title,
                    created_by=args.source_agent,
                    assigned_agent=args.source_agent,
                    status=normalize_task_status(action_type, args.status),
                    latest_summary=args.summary,
                    latest_artifacts=args.artifacts or "",
                    created_at=created_at,
                    updated_at=created_at,
                )
            else:
                update_task_status(
                    conn,
                    args.task_id,
                    args.cabinet_id,
                    normalize_task_status(action_type, args.status),
                    args.summary,
                    args.artifacts or "",
                    created_at,
                )
            event_id = insert_event(
                conn,
                task_id=args.task_id,
                cabinet_id=args.cabinet_id,
                module_name=args.module_name,
                event_type=action_type,
                source_agent=args.source_agent,
                target_agent=args.target_agent,
                status=args.status,
                summary=args.summary,
                details=args.details or "",
                artifacts=args.artifacts or "",
                created_at=created_at,
            )
        else:
            raise ValueError(f"Unsupported action_type '{action_type}'.")
        conn.commit()
        if args.sync:
            synced = sync_rows(conn, env)
    finally:
        conn.close()
    print(f"event_id={event_id}")
    print(f"handoff_id={handoff_id}")
    print(f"review_id={review_id}")
    print(f"task_id={args.task_id}")
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

    ensure_parser = subparsers.add_parser("ensure-db", help="Create task registry tables if needed")
    ensure_parser.set_defaults(func=cmd_ensure_db)

    list_parser = subparsers.add_parser("list", help="List task history events")
    list_parser.add_argument("--task-id")
    list_parser.add_argument("--cabinet-id", default="")
    list_parser.add_argument("--module-name")
    list_parser.add_argument("--target-agent")
    list_parser.add_argument("--source-agent")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.set_defaults(func=cmd_list)

    mine_parser = subparsers.add_parser("mine", help="List current tasks or pending reviewer handoffs")
    mine_parser.add_argument("--agent", required=True)
    mine_parser.add_argument("--cabinet-id", default="default")
    mine_parser.add_argument("--limit", type=int, default=20)
    mine_parser.set_defaults(func=cmd_mine)

    show_parser = subparsers.add_parser("show", help="Show a task with handoffs, reviews, and events")
    show_parser.add_argument("--task-id", required=True)
    show_parser.add_argument("--cabinet-id")
    show_parser.set_defaults(func=cmd_show)

    add_parser = subparsers.add_parser("add", help="Write to the task workflow database")
    add_parser.add_argument("--task-id", required=True)
    add_parser.add_argument("--cabinet-id", default="default")
    add_parser.add_argument("--source-agent", required=True)
    add_parser.add_argument("--target-agent", required=True)
    add_parser.add_argument("--module-name", required=True)
    add_parser.add_argument("--action-type", required=True, choices=["start", "progress", "handoff", "review", "done", "blocked", "error"])
    add_parser.add_argument("--summary", required=True)
    add_parser.add_argument("--status", required=True)
    add_parser.add_argument("--artifacts", default="")
    add_parser.add_argument("--created-at")
    add_parser.add_argument("--title")
    add_parser.add_argument("--details", default="")
    add_parser.add_argument("--review-type", default="")
    add_parser.add_argument("--implementation-report", default="")
    add_parser.add_argument("--checks-required", default="")
    add_parser.add_argument("--handoff-id", type=int)
    add_parser.add_argument("--result", default="")
    add_parser.add_argument("--what-works", default="")
    add_parser.add_argument("--what-fails", default="")
    add_parser.add_argument("--policy-checks", default="")
    add_parser.add_argument("--sync", action="store_true", help="Rewrite Google Sheets from the new workflow tables")
    add_parser.set_defaults(func=cmd_add)

    sync_parser = subparsers.add_parser("sync", help="Rewrite Google Sheets from the new workflow tables")
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
