import html
import json
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
      --bg: #f5f1e8;
      --panel: #fffdf8;
      --line: #d7cebf;
      --text: #2d2418;
      --muted: #6f6251;
      --accent: #8a4b2a;
      --accent-soft: #f4e2d6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: linear-gradient(180deg, #efe6d7 0%, var(--bg) 100%);
      color: var(--text);
    }}
    .shell {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 24px 16px 48px;
    }}
    .topbar {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 20px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--line);
    }}
    .brand {{
      font-size: 26px;
      font-weight: 700;
    }}
    .nav a, .link {{
      color: var(--accent);
      text-decoration: none;
      margin-right: 16px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
      margin: 16px 0 24px;
    }}
    .card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 4px 14px rgba(60, 44, 20, 0.05);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      overflow: hidden;
    }}
    th, td {{
      text-align: left;
      padding: 12px 10px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{
      font-size: 13px;
      color: var(--muted);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .status {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 13px;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #fbf7ef;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 12px;
      margin: 0;
    }}
    form {{
      margin: 0;
    }}
    button {{
      border: 1px solid var(--accent);
      background: var(--accent);
      color: #fffdf8;
      border-radius: 10px;
      padding: 8px 12px;
      cursor: pointer;
      font: inherit;
    }}
    .muted {{
      color: var(--muted);
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <div class="brand">doc_classifier</div>
      <div class="nav">
        <a href="/">Статус</a>
        <a href="/documents">Документы</a>
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
    body = f"""
    <h1>Статус модуля</h1>
    <p class="muted">Автономный модуль распознавания и классификации документов на локальной SQLite БД.</p>
    <div class="grid">
      <div class="card"><strong>{summary['status']['total_documents']}</strong><br><span class="muted">Всего документов</span></div>
      <div class="card"><strong>{summary['status']['recognition_done']}</strong><br><span class="muted">Распознавание выполнено</span></div>
      <div class="card"><strong>{summary['status']['classification_done']}</strong><br><span class="muted">Классификация выполнена</span></div>
      <div class="card"><strong>{summary['status']['pending_review']}</strong><br><span class="muted">Нужно проверить</span></div>
    </div>
    <h2>Последнее событие</h2>
    {event_block}
    """
    return render_page("doc_classifier | Статус", body)


def render_documents_page(documents: list[Any]) -> str:
    rows = []
    for item in documents:
        rows.append(
            f"""
            <tr>
              <td><a class="link" href="/documents/{item.id}">{html.escape(item.title)}</a><br><span class="muted">{html.escape(item.external_ref)}</span></td>
              <td><span class="status">{html.escape(item.source_status)}</span></td>
              <td><span class="status">{html.escape(item.recognition_status)}</span></td>
              <td><span class="status">{html.escape(item.classification_status)}</span></td>
              <td>{html.escape(item.classification_label or "-")}</td>
              <td>{item.classification_confidence:.2f}</td>
            </tr>
            """
        )
    table = "".join(rows) if rows else "<tr><td colspan='6'>Документов пока нет.</td></tr>"
    body = f"""
    <h1>Документы</h1>
    <table>
      <thead>
        <tr>
          <th>Документ</th>
          <th>Исходный статус</th>
          <th>Распознавание</th>
          <th>Классификация</th>
          <th>Тип</th>
          <th>Уверенность</th>
        </tr>
      </thead>
      <tbody>{table}</tbody>
    </table>
    """
    return render_page("doc_classifier | Документы", body)


def render_document_page(document: Any) -> str:
    features = document.extracted_features or "{}"
    pretty_features = json.dumps(json.loads(features), ensure_ascii=False, indent=2) if features else "{}"
    error_block = f"<p><strong>Ошибка:</strong> {html.escape(document.error_message)}</p>" if document.error_message else ""
    body = f"""
    <h1>{html.escape(document.title)}</h1>
    <p class="muted">Источник: {html.escape(document.external_ref)} | обновлено: {html.escape(document.updated_at)}</p>
    <div class="grid">
      <div class="card"><strong>Исходный статус</strong><br><span class="status">{html.escape(document.source_status)}</span></div>
      <div class="card"><strong>Статус распознавания</strong><br><span class="status">{html.escape(document.recognition_status)}</span></div>
      <div class="card"><strong>Статус классификации</strong><br><span class="status">{html.escape(document.classification_status)}</span></div>
      <div class="card"><strong>Тип документа</strong><br>{html.escape(document.classification_label or "unknown")}</div>
    </div>
    <div class="panel" style="margin-bottom: 16px;">
      <form method="post" action="/documents/{document.id}/rerun">
        <button type="submit">Повторно прогнать документ</button>
      </form>
    </div>
    <h2>Результат распознавания</h2>
    <div class="panel"><pre>{html.escape(document.recognized_text)}</pre></div>
    <h2>Извлеченные признаки</h2>
    <div class="panel"><pre>{html.escape(pretty_features)}</pre></div>
    <h2>Результат классификации</h2>
    <div class="panel">
      <p><strong>Метка:</strong> {html.escape(document.classification_label or "unknown")}</p>
      <p><strong>Причина:</strong> {html.escape(document.classification_reason or "-")}</p>
      <p><strong>Уверенность:</strong> {document.classification_confidence:.2f}</p>
      {error_block}
    </div>
    """
    return render_page(f"doc_classifier | {document.title}", body)
