import html
from typing import Any


def render_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f2efe7;
      --paper: #fffdf8;
      --line: #d5cec0;
      --text: #31291d;
      --muted: #6b6257;
      --accent: #6c4d2f;
      --accent-soft: #efe3d2;
      --danger: #a44632;
      --ok: #3f6e4e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top right, rgba(180, 139, 92, 0.16), transparent 30%),
        linear-gradient(180deg, #ece6d7 0%, var(--bg) 100%);
      color: var(--text);
      font-family: Georgia, "Times New Roman", serif;
    }}
    .shell {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px 16px 40px;
    }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 16px;
      margin-bottom: 24px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--line);
    }}
    .brand {{
      font-size: 28px;
      font-weight: 700;
    }}
    .tag {{
      color: var(--muted);
      font-size: 14px;
      margin-top: 4px;
    }}
    .nav a, .link {{
      color: var(--accent);
      text-decoration: none;
      margin-left: 16px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin: 16px 0 24px;
    }}
    .card, .panel {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      box-shadow: 0 8px 24px rgba(52, 38, 19, 0.05);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 14px;
      overflow: hidden;
      margin-bottom: 20px;
    }}
    th, td {{
      text-align: left;
      padding: 12px 10px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .status {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 13px;
    }}
    .status.ok {{
      color: var(--ok);
      background: #e0efe4;
    }}
    .status.alert {{
      color: var(--danger);
      background: #f7ddd7;
    }}
    .muted {{
      color: var(--muted);
    }}
    .split {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 16px;
    }}
    @media (max-width: 820px) {{
      .split {{
        grid-template-columns: 1fr;
      }}
      .nav a {{
        margin-left: 10px;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <div>
        <div class="brand">project_builder</div>
        <div class="tag">Проекты, связи документов и нехватки в одной локальной БД</div>
      </div>
      <div class="nav">
        <a href="/">Статус</a>
        <a href="/projects">Проекты</a>
      </div>
    </div>
    {body}
  </div>
</body>
</html>"""


def render_status_page(summary: dict[str, Any]) -> str:
    last_event = summary["status"]["last_event"]
    event_block = (
        f"<div class='panel'><strong>{html.escape(last_event['event_type'])}</strong><br>"
        f"<span class='muted'>{html.escape(last_event['created_at'])}</span><p>{html.escape(last_event['details'])}</p></div>"
        if last_event
        else "<div class='panel'>Событий пока нет.</div>"
    )
    registry_items = "".join(
        (
            "<tr>"
            f"<td>{html.escape(item.task_id)}</td>"
            f"<td>{html.escape(item.action_type)}</td>"
            f"<td>{html.escape(item.status)}</td>"
            f"<td>{html.escape(item.summary)}</td>"
            f"<td>{html.escape(item.created_at)}</td>"
            "</tr>"
        )
        for item in summary["task_registry"]
    ) or "<tr><td colspan='5'>Записей пока нет.</td></tr>"
    body = f"""
    <h1>Статус модуля</h1>
    <p class="muted">Стартовая реализация автономного модуля формирования проектов на локальной SQLite БД.</p>
    <div class="grid">
      <div class="card"><strong>{summary['status']['total_projects']}</strong><br><span class="muted">Проектов</span></div>
      <div class="card"><strong>{summary['status']['total_documents']}</strong><br><span class="muted">Документов</span></div>
      <div class="card"><strong>{summary['status']['total_links']}</strong><br><span class="muted">Связей</span></div>
      <div class="card"><strong>{summary['status']['total_deficits']}</strong><br><span class="muted">Нехваток</span></div>
      <div class="card"><strong>{summary['status']['complete_projects']}</strong><br><span class="muted">Полных проектов</span></div>
    </div>
    <div class="split">
      <div>
        <h2>Проекты</h2>
        {render_projects_table(summary["projects"])}
      </div>
      <div>
        <h2>Последнее событие</h2>
        {event_block}
      </div>
    </div>
    <h2>Локальный журнал реестра задач</h2>
    <table>
      <thead>
        <tr>
          <th>Task ID</th>
          <th>Action</th>
          <th>Status</th>
          <th>Summary</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>{registry_items}</tbody>
    </table>
    """
    return render_page("project_builder | Статус", body)


def render_projects_page(projects: list[Any]) -> str:
    body = f"""
    <h1>Список проектов</h1>
    <p class="muted">Каждый проект показывает состав документов, число найденных связей и открытые дефициты.</p>
    {render_projects_table(projects)}
    """
    return render_page("project_builder | Проекты", body)


def render_projects_table(projects: list[Any]) -> str:
    rows = []
    for project in projects:
        status_class = "ok" if project.status == "complete" else "alert"
        rows.append(
            f"""
            <tr>
              <td><a class="link" href="/projects/{project.id}">{html.escape(project.project_name)}</a><br><span class="muted">{html.escape(project.project_code)}</span></td>
              <td><span class="status {status_class}">{html.escape(project.status)}</span></td>
              <td>{project.assigned_documents} / {project.total_documents}</td>
              <td>{project.total_links}</td>
              <td>{project.total_deficits}</td>
              <td>{int(project.completeness_ratio * 100)}%</td>
            </tr>
            """
        )
    table = "".join(rows) if rows else "<tr><td colspan='6'>Проектов пока нет.</td></tr>"
    return f"""
    <table>
      <thead>
        <tr>
          <th>Проект</th>
          <th>Статус</th>
          <th>Документы</th>
          <th>Связи</th>
          <th>Нехватки</th>
          <th>Полнота</th>
        </tr>
      </thead>
      <tbody>{table}</tbody>
    </table>
    """


def render_project_page(payload: dict[str, Any]) -> str:
    project = payload["project"]
    documents = payload["documents"]
    links = payload["links"]
    deficits = payload["deficits"]
    status_class = "ok" if project.status == "complete" else "alert"

    document_rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(item.document_code)}</td>"
            f"<td>{html.escape(item.title)}</td>"
            f"<td>{html.escape(item.document_type)}</td>"
            f"<td><span class='status'>{html.escape(item.status)}</span></td>"
            f"<td>{html.escape(item.assignment_reason)}</td>"
            "</tr>"
        )
        for item in documents
    ) or "<tr><td colspan='5'>Документов пока нет.</td></tr>"

    link_rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(item.source_document_code)}</td>"
            f"<td>{html.escape(item.relation_type)}</td>"
            f"<td>{html.escape(item.target_document_code)}</td>"
            f"<td>{html.escape(item.evidence)}</td>"
            "</tr>"
        )
        for item in links
    ) or "<tr><td colspan='4'>Связей пока нет.</td></tr>"

    deficit_rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(item.required_type)}</td>"
            f"<td><span class='status alert'>{html.escape(item.severity)}</span></td>"
            f"<td>{html.escape(item.summary)}</td>"
            f"<td>{html.escape(item.details)}</td>"
            "</tr>"
        )
        for item in deficits
    ) or "<tr><td colspan='4'>Нехваток нет.</td></tr>"

    body = f"""
    <h1>{html.escape(project.project_name)}</h1>
    <p class="muted">Код проекта: {html.escape(project.project_code)}</p>
    <div class="grid">
      <div class="card"><strong>Статус</strong><br><span class="status {status_class}">{html.escape(project.status)}</span></div>
      <div class="card"><strong>Полнота</strong><br>{int(project.completeness_ratio * 100)}%</div>
      <div class="card"><strong>Документы</strong><br>{project.total_documents}</div>
      <div class="card"><strong>Связи</strong><br>{project.total_links}</div>
      <div class="card"><strong>Нехватки</strong><br>{project.total_deficits}</div>
    </div>
    <h2>Документы проекта</h2>
    <table>
      <thead>
        <tr>
          <th>Код</th>
          <th>Документ</th>
          <th>Тип</th>
          <th>Статус</th>
          <th>Почему отнесен к проекту</th>
        </tr>
      </thead>
      <tbody>{document_rows}</tbody>
    </table>
    <h2>Найденные связи</h2>
    <table>
      <thead>
        <tr>
          <th>От</th>
          <th>Тип связи</th>
          <th>К</th>
          <th>Основание</th>
        </tr>
      </thead>
      <tbody>{link_rows}</tbody>
    </table>
    <h2>Нехватки</h2>
    <table>
      <thead>
        <tr>
          <th>Что отсутствует</th>
          <th>Критичность</th>
          <th>Кратко</th>
          <th>Детали</th>
        </tr>
      </thead>
      <tbody>{deficit_rows}</tbody>
    </table>
    """
    return render_page(f"project_builder | {project.project_name}", body)
