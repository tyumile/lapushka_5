import html
import json
from typing import Any
from urllib.parse import urlencode


SERVICE_FILE_NAMES = {"readme.md", "readme_1.md", "welcome.txt"}

FILTERS = [
    ("all", "Все"),
    ("ready", "Готово"),
    ("problems", "Проблемы"),
    ("unrecognized", "Требует проверки"),
    ("quality_document", "Документы качества"),
    ("project_document", "Проектные"),
    ("service", "Служебные"),
]

SORT_OPTIONS = [
    ("attention", "Сначала проблемные"),
    ("updated", "Сначала новые"),
    ("title", "По названию"),
]

DENSITY_OPTIONS = [
    ("normal", "Обычно"),
    ("compact", "Компактно"),
]


def render_page(title: str, body: str, density: str = "normal", cabinet_id: str = "default") -> str:
    density_class = "density-compact" if density == "compact" else "density-normal"
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f1ea;
      --panel: #fffdf9;
      --line: #d7d0c4;
      --line-soft: #ece5d9;
      --text: #2f2a22;
      --muted: #6b6357;
      --accent: #7f5134;
      --accent-soft: #f3e3d7;
      --warn: #8d3328;
      --warn-soft: #fae1dd;
      --warn-line: #e3b0a8;
      --ok-soft: #eef4ea;
      --ok-line: #cad8c0;
      --hover: #f7f2eb;
      --sticky: #f8f5ef;
      --mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      --font-ui: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: var(--font-ui);
      background: linear-gradient(180deg, #eee6da 0%, var(--bg) 100%);
      color: var(--text);
    }}
    .shell {{
      width: min(1760px, calc(100vw - 40px));
      margin: 0 auto;
      padding: 20px 20px 40px;
    }}
    .topbar {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 18px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--line);
    }}
    .brand {{
      font-size: 28px;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    .nav {{
      display: flex;
      gap: 18px;
      flex-wrap: wrap;
    }}
    .nav a, .link {{
      color: var(--accent);
      text-decoration: none;
    }}
    .link:hover, .nav a:hover {{
      text-decoration: underline;
    }}
    h1, h2, h3 {{
      margin: 0 0 12px;
    }}
    p {{
      margin: 0;
    }}
    .muted {{
      color: var(--muted);
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(180px, 1fr));
      gap: 12px;
      margin: 14px 0 18px;
    }}
    .card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      box-shadow: 0 4px 16px rgba(50, 40, 24, 0.04);
    }}
    .card {{
      padding: 14px 16px;
    }}
    .card strong {{
      display: block;
      font-size: 28px;
      line-height: 1.1;
      margin-bottom: 6px;
    }}
    .panel {{
      padding: 14px 16px;
      margin-bottom: 16px;
    }}
    .section-title {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 10px;
    }}
    .controls {{
      display: grid;
      gap: 10px;
      margin: 14px 0 18px;
    }}
    .control-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    .control-label {{
      font-size: 13px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-right: 4px;
    }}
    .pill, .filter, button {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fbf7f0;
      color: var(--accent);
      text-decoration: none;
      font: inherit;
      cursor: pointer;
    }}
    .pill, .filter {{
      padding: 7px 12px;
      font-size: 14px;
    }}
    .pill.active, .filter.active {{
      background: var(--accent);
      color: #fffdf9;
      border-color: var(--accent);
    }}
    button {{
      padding: 8px 14px;
      background: var(--accent);
      color: #fffdf9;
      border-color: var(--accent);
    }}
    .filter-count {{
      font-size: 12px;
      opacity: 0.9;
    }}
    .table-panel {{
      padding: 0;
      overflow: hidden;
    }}
    .table-wrap {{
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      table-layout: fixed;
      background: var(--panel);
    }}
    thead th {{
      position: sticky;
      top: 0;
      z-index: 2;
      background: var(--sticky);
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 1px solid var(--line);
    }}
    th, td {{
      text-align: left;
      vertical-align: top;
      border-bottom: 1px solid var(--line-soft);
    }}
    tbody tr:nth-child(even) {{
      background: #fcfaf6;
    }}
    tbody tr:hover {{
      background: var(--hover);
    }}
    tbody tr.row-warning {{
      background: #fff6f4;
    }}
    tbody tr.row-warning:nth-child(even) {{
      background: #fdf0ed;
    }}
    tbody tr.row-warning td {{
      border-bottom-color: var(--warn-line);
    }}
    tbody tr.row-ready {{
      background: #fcfdfb;
    }}
    .sticky-col {{
      position: sticky;
      left: 0;
      z-index: 1;
      background: inherit;
      box-shadow: 1px 0 0 var(--line-soft);
    }}
    thead .sticky-col {{
      z-index: 3;
      background: var(--sticky);
      box-shadow: 1px 0 0 var(--line);
    }}
    .density-normal thead th,
    .density-normal tbody td {{
      padding: 11px 10px;
      font-size: 14px;
      line-height: 1.42;
    }}
    .density-compact thead th,
    .density-compact tbody td {{
      padding: 8px 9px;
      font-size: 13px;
      line-height: 1.32;
    }}
    .col-title {{ width: 24%; }}
    .col-type {{ width: 12%; }}
    .col-status {{ width: 10%; }}
    .col-short {{ width: 9%; }}
    .col-data {{ width: 26%; }}
    .col-updated {{ width: 10%; }}
    .col-actions {{ width: 7%; }}
    .col-field {{ min-width: 180px; width: 14%; }}
    .title-cell {{
      min-width: 280px;
    }}
    .title-main {{
      display: block;
      font-weight: 700;
      margin-bottom: 4px;
    }}
    .title-secondary {{
      color: var(--text);
      font-size: 13px;
      margin-bottom: 4px;
    }}
    .title-meta {{
      color: var(--muted);
      font-size: 12px;
    }}
    .status {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 110px;
      padding: 4px 8px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
      text-align: center;
    }}
    .status.failed {{
      background: var(--warn-soft);
      color: var(--warn);
    }}
    .status.ready {{
      background: var(--ok-soft);
      color: #46633d;
      border: 1px solid var(--ok-line);
    }}
    .confidence {{
      display: inline-block;
      min-width: 52px;
      text-align: center;
      padding: 4px 7px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: #f6efe4;
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
      margin-left: 6px;
    }}
    .mono {{
      font-family: var(--mono);
      font-size: 12px;
      word-break: break-word;
    }}
    .data-preview {{
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 3;
      overflow: hidden;
    }}
    .data-preview strong {{
      color: var(--muted);
    }}
    .data-preview.empty {{
      color: var(--muted);
    }}
    .clamp-2 {{
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
      overflow: hidden;
    }}
    .actions {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .table-link {{
      white-space: nowrap;
    }}
    .event-title {{
      font-weight: 700;
      margin-bottom: 6px;
    }}
    .event-time {{
      color: var(--muted);
      margin-bottom: 8px;
      font-size: 13px;
    }}
    .details-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(220px, 1fr));
      gap: 12px;
      margin-top: 12px;
    }}
    .field {{
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fffaf4;
    }}
    .field strong {{
      display: block;
      margin-bottom: 4px;
      font-size: 13px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
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
    details {{
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fbf7ef;
      padding: 12px;
    }}
    details summary {{
      cursor: pointer;
      color: var(--accent);
      font-weight: 700;
    }}
    form {{
      margin: 0;
    }}
    @media (max-width: 1100px) {{
      .shell {{
        width: calc(100vw - 24px);
        padding: 14px 12px 28px;
      }}
      .summary-grid {{
        grid-template-columns: repeat(2, minmax(180px, 1fr));
      }}
      .details-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body class="{density_class}">
  <div class="shell">
    <div class="topbar">
      <div>
        <div class="brand">doc_classifier</div>
        <div class="muted">Реестр распознавания и классификации документов</div>
      </div>
      <div class="nav">
        <a href="{_build_query_href(_nav_status_href(title), _cabinet_params(cabinet_id))}">Статус</a>
        <a href="{_build_query_href(_nav_documents_href(title), _cabinet_params(cabinet_id))}">Документы</a>
      </div>
    </div>
    {body}
  </div>
</body>
</html>"""


def render_status_page(summary: dict[str, Any], cabinet_id: str = "default", density: str = "normal") -> str:
    last_event = summary["status"]["last_event"]
    groups = summary.get("working_document_groups", [])
    group_blocks = "".join(_render_group_block(group, density, cabinet_id) for group in groups) or (
        "<div class='panel'>Документы из ingest_registry пока не распознаны.</div>"
    )
    event_block = _render_last_event(last_event)
    density_bar = _render_density_switch(".", density, _cabinet_params(cabinet_id))
    body = f"""
    <h1>Статус модуля</h1>
    <p class="muted">Экран рассчитан на широкое рабочее окно: сверху краткая сводка, ниже быстрые действия и таблицы для сравнения длинных списков документов.</p>
    <div class="summary-grid">
      <div class="card"><strong>{summary['status']['total_documents']}</strong><span class="muted">Всего документов</span></div>
      <div class="card"><strong>{summary['status']['recognition_done']}</strong><span class="muted">Распознавание выполнено</span></div>
      <div class="card"><strong>{summary['status']['classification_done']}</strong><span class="muted">Классификация завершена</span></div>
      <div class="card"><strong>{summary['status']['pending_review']}</strong><span class="muted">Требуют проверки</span></div>
    </div>
    <div class="controls">
      <div class="control-row">
        <form method="post" action="{_build_query_href('sync', _cabinet_params(cabinet_id))}">
          <button type="submit">Синхронизировать реестр и распознать документы</button>
        </form>
      </div>
      <div class="control-row">
        <span class="control-label">Плотность строк</span>
        {density_bar}
      </div>
    </div>
    <div class="section-title">
      <h2>Рабочая документация по типам</h2>
      <span class="muted">Строки с проблемами подсвечены. Порядок: сначала проблемные, затем новые.</span>
    </div>
    {group_blocks}
    <div class="section-title" style="margin-top: 22px;">
      <h2>Последнее событие</h2>
    </div>
    {event_block}
    """
    return render_page("doc_classifier | Статус", body, density=density, cabinet_id=cabinet_id)


def render_documents_page(
    documents: list[Any],
    filter_key: str,
    cabinet_id: str = "default",
    density: str = "normal",
    sort_key: str = "attention",
) -> str:
    sorted_documents = _sort_documents(documents, sort_key)
    visible_documents = [item for item in sorted_documents if _matches_filter(item, filter_key)]
    field_columns = _collect_field_columns(visible_documents)
    filter_bar = "".join(
        _render_filter(
            sorted_documents,
            current_key=filter_key,
            filter_key=key,
            label=label,
            density=density,
            sort_key=sort_key,
            cabinet_id=cabinet_id,
        )
        for key, label in FILTERS
    )
    sort_bar = _render_sort_switch(filter_key, density, sort_key, cabinet_id)
    density_bar = _render_density_switch("documents", density, {**_cabinet_params(cabinet_id), "filter": filter_key, "sort": sort_key})
    rows = "".join(_render_document_registry_row(item, cabinet_id, field_columns) for item in visible_documents) or (
        f"<tr><td colspan='{7 + len(field_columns)}' class='muted'>Подходящих документов нет.</td></tr>"
    )
    field_headers = "".join(f"<th class='col-field'>{html.escape(label)}</th>" for label in field_columns)
    body = f"""
    <h1>Документы</h1>
    <p class="muted">Основной рабочий реестр для просмотра длинного списка, сравнения статусов и быстрого перехода к деталям.</p>
    <div class="summary-grid">
      <div class="card"><strong>{len([item for item in documents if not _is_service_document(item)])}</strong><span class="muted">Рабочих документов</span></div>
      <div class="card"><strong>{len([item for item in documents if _display_status(item) == 'Готово'])}</strong><span class="muted">Готово</span></div>
      <div class="card"><strong>{len([item for item in documents if _display_status(item) == 'Требует проверки'])}</strong><span class="muted">Требует проверки</span></div>
      <div class="card"><strong>{len([item for item in documents if _display_status(item) == 'Ошибка'])}</strong><span class="muted">Ошибки</span></div>
    </div>
    <div class="controls">
      <div class="control-row">
        <span class="control-label">Фильтр</span>
        {filter_bar}
      </div>
      <div class="control-row">
        <span class="control-label">Сортировка</span>
        {sort_bar}
      </div>
      <div class="control-row">
        <span class="control-label">Плотность строк</span>
        {density_bar}
        <a class="pill" href="{_build_query_href('.', _cabinet_params(cabinet_id))}">Сбросить фильтры</a>
        <form method="post" action="{_build_query_href('../sync', _cabinet_params(cabinet_id))}">
          <button type="submit">Синхронизировать и распознать</button>
        </form>
      </div>
    </div>
    <div class="panel table-panel">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="sticky-col col-title">Материал</th>
              <th class="col-type">Тип</th>
              <th class="col-status">Статус</th>
              <th class="col-short">Распознавание</th>
              <th class="col-short">Классификация</th>
              {field_headers}
              <th class="col-updated">Обновлено</th>
              <th class="col-actions">Исходный файл</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>
    """
    return render_page("doc_classifier | Документы", body, density=density, cabinet_id=cabinet_id)


def render_document_page(document: Any, cabinet_id: str = "default") -> str:
    features = document.extracted_features or "{}"
    pretty_features = json.dumps(json.loads(features), ensure_ascii=False, indent=2) if features else "{}"
    structured = json.dumps(json.loads(document.structured_data or "{}"), ensure_ascii=False, indent=2)
    error_block = f"<p><strong>Ошибка:</strong> {html.escape(document.error_message)}</p>" if document.error_message else ""
    confidence_value = f"{document.classification_confidence:.2f}" if _show_confidence_value(document) else "—"
    recognized_text = html.escape(document.recognized_text or "Текст не извлечен.")
    extracted_fields = _render_detail_fields(document)
    body = f"""
    <h1>{html.escape(document.title)}</h1>
    <p class="muted">Тип: {html.escape(_user_type_label(document))} | Статус: {_user_status_label(document)}</p>
    <div class="summary-grid">
      <div class="card"><strong>{_display_status(document)}</strong><span class="muted">Готовность</span></div>
      <div class="card"><strong>{html.escape(_user_type_label(document))}</strong><span class="muted">Тип документа</span></div>
      <div class="card"><strong>{html.escape(confidence_value)}</strong><span class="muted">Уверенность</span></div>
      <div class="card"><strong>{html.escape(document.updated_at)}</strong><span class="muted">Обновлено</span></div>
    </div>
    <div class="panel">
      <div class="actions">
        <form method="post" action="{_build_query_href(f'{document.id}/rerun', _cabinet_params(cabinet_id))}">
          <button type="submit">Повторно прогнать документ</button>
        </form>
        <a class="pill" href="{_build_query_href('.', _cabinet_params(cabinet_id))}">Назад к списку</a>
      </div>
    </div>
    <div class="section-title" style="margin-top: 20px;">
      <h2>Распознанные данные</h2>
    </div>
    <div class="panel"><div class="details-grid">{extracted_fields}</div></div>
    <div class="section-title" style="margin-top: 20px;">
      <h2>Текст документа</h2>
    </div>
    <div class="panel"><pre>{recognized_text}</pre></div>
    <div class="section-title" style="margin-top: 20px;">
      <h2>Результат классификации</h2>
    </div>
    <div class="panel">
      <p><strong>Тип:</strong> {html.escape(_user_type_label(document))}</p>
      <p><strong>Причина:</strong> {html.escape(document.classification_reason or "-")}</p>
      <p><strong>Уверенность:</strong> {confidence_value}</p>
      <p><strong>Заметки:</strong> {html.escape(document.processing_notes or "-")}</p>
      {error_block}
    </div>
    <details style="margin-top: 16px;">
      <summary>Показать технические данные</summary>
      <div style="margin-top: 12px;">
        <p><strong>Источник:</strong> <span class="mono">{html.escape(document.external_ref)}</span></p>
        <p><strong>Файл в реестре:</strong> <span class="mono">{html.escape(document.source_file_path)}</span></p>
        <p><strong>Исходный статус:</strong> {html.escape(document.source_status)}</p>
        <p><strong>Статус распознавания:</strong> {html.escape(_recognition_status_label(document))}</p>
        <p><strong>Статус классификации:</strong> {html.escape(_classification_status_label(document))}</p>
      </div>
      <h3>Извлеченные данные JSON</h3>
      <pre>{html.escape(structured)}</pre>
      <h3>Технические признаки обработки</h3>
      <pre>{html.escape(pretty_features)}</pre>
    </details>
    """
    return render_page(f"doc_classifier | {document.title}", body, cabinet_id=cabinet_id)


def _render_last_event(last_event: dict[str, Any] | None) -> str:
    if not last_event:
        return "<div class='panel'>Событий пока нет.</div>"
    title = _event_type_label(str(last_event.get("event_type", "")))
    details = html.escape(str(last_event.get("details", "") or ""))
    created_at = html.escape(str(last_event.get("created_at", "") or ""))
    return (
        "<div class='panel'>"
        f"<div class='event-title'>{title}</div>"
        f"<div class='event-time'>{created_at}</div>"
        f"<div>{details}</div>"
        "</div>"
    )


def _render_group_block(group: dict[str, Any], density: str, cabinet_id: str = "default") -> str:
    documents = [item for item in group["documents"] if not _is_service_document(item)]
    if not documents:
        return ""
    sorted_documents = _sort_documents(documents, "attention")
    rows = "".join(_render_document_group_row(item, cabinet_id) for item in sorted_documents)
    return f"""
    <div class="panel table-panel">
      <div class="section-title" style="padding: 14px 16px 0;">
        <h3>{html.escape(group['title'])}</h3>
        <span class="muted">{len(sorted_documents)} строк</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="sticky-col col-title">Материал</th>
              <th class="col-type">Тип</th>
              <th class="col-status">Статус</th>
              <th class="col-data">Данные</th>
              <th class="col-updated">Обновлено</th>
              <th class="col-actions">Исходный файл</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>
    """


def _render_document_group_row(document: Any, cabinet_id: str = "default") -> str:
    row_class = _table_row_class(document)
    return f"""
    <tr class="{row_class}">
      <td class="sticky-col title-cell">
        <a class="link title-main" href="{_build_query_href(f'documents/{document.id}', _cabinet_params(cabinet_id))}">{html.escape(_material_title(document))}</a>
        <div class="title-meta mono clamp-2">{html.escape(document.source_file_name or document.title)}</div>
      </td>
      <td>{html.escape(_user_type_label(document))}</td>
      <td>{_status_badge(_display_status(document))}</td>
      <td><div class="data-preview">{_field_preview(document)}</div></td>
      <td>{html.escape(_short_datetime(document.updated_at))}</td>
      <td class="table-link">{_document_file_link(document, cabinet_id)}</td>
    </tr>
    """


def _render_document_registry_row(document: Any, cabinet_id: str = "default", field_columns: list[str] | None = None) -> str:
    row_class = _table_row_class(document)
    field_columns = field_columns or []
    field_cells = "".join(
        f"<td>{_field_value_preview(_field_value(document, label))}</td>"
        for label in field_columns
    )
    document_href = _build_query_href(f"./{document.id}", _cabinet_params(cabinet_id))
    return f"""
    <tr class="{row_class}">
      <td class="sticky-col title-cell">
        <a class="link title-main" href="{document_href}">{html.escape(_material_title(document))}</a>
        <div class="title-meta mono clamp-2">{html.escape(document.source_file_name or document.title)}</div>
      </td>
      <td>{html.escape(_user_type_label(document))}</td>
      <td>{_status_badge(_display_status(document))}</td>
      <td>{html.escape(_recognition_status_label(document))}</td>
      <td>{html.escape(_classification_status_label(document))}</td>
      {field_cells}
      <td>{html.escape(_short_datetime(document.updated_at))}</td>
      <td class="table-link">{_document_file_link(document, cabinet_id)}</td>
    </tr>
    """


def _render_filter(
    documents: list[Any],
    current_key: str,
    filter_key: str,
    label: str,
    density: str,
    sort_key: str,
    cabinet_id: str,
) -> str:
    count = sum(1 for item in documents if _matches_filter(item, filter_key))
    active = " active" if current_key == filter_key else ""
    href = _build_query_href(".", {**_cabinet_params(cabinet_id), "filter": filter_key if filter_key != "all" else "", "density": density, "sort": sort_key})
    return (
        f"<a class='filter{active}' href='{href}'>{html.escape(label)}"
        f" <span class='filter-count'>{count}</span></a>"
    )


def _document_file_link(document: Any, cabinet_id: str) -> str:
    href = document.source_link if hasattr(document, "source_link") else None
    if not href:
        href = _build_query_href(f"./{document.id}/file", _cabinet_params(cabinet_id))
    attrs = ' target="_blank" rel="noopener noreferrer"' if href else ""
    return f'<a class="filter" href="{html.escape(href)}"{attrs}>Файл</a>'


def _render_sort_switch(filter_key: str, density: str, current_sort: str, cabinet_id: str) -> str:
    return "".join(
        f"<a class='pill{' active' if key == current_sort else ''}' "
        f"href='{_build_query_href('.', {**_cabinet_params(cabinet_id), 'filter': filter_key if filter_key != 'all' else '', 'density': density, 'sort': key})}'>{html.escape(label)}</a>"
        for key, label in SORT_OPTIONS
    )


def _render_density_switch(base_path: str, current_density: str, extra_params: dict[str, str] | None = None) -> str:
    params = extra_params or {}
    return "".join(
        f"<a class='pill{' active' if key == current_density else ''}' "
        f"href='{_build_query_href(base_path, {**params, 'density': key})}'>{html.escape(label)}</a>"
        for key, label in DENSITY_OPTIONS
    )


def _render_detail_fields(document: Any) -> str:
    fields = [
        item
        for item in getattr(document, "structured_fields", [])
        if str(item.get("value") or "").strip()
    ]
    if not fields:
        return "<div class='field'><strong>Данные</strong>Не распознаны</div>"
    return "".join(
        f"<div class='field'><strong>{html.escape(item['label'])}</strong>{html.escape(item['value'])}</div>"
        for item in fields
    )


def _status_badge(value: str) -> str:
    css = "status ready" if value == "Готово" else "status"
    if value == "Ошибка":
        css = "status failed"
    elif value in {"Требует внимания", "Не распознан", "Требует проверки"}:
        css = "status warning"
    return f"<span class='{css}'>{html.escape(value)}</span>"


def _confidence_percent(value: float) -> str:
    return f"{round((value or 0.0) * 100):d}%"


def _confidence_badge(document: Any) -> str:
    if _display_status(document) != "Готово":
        return ""
    return f"<span class='confidence'>{_confidence_percent(document.classification_confidence)}</span>"


def _field_preview(document: Any) -> str:
    fields = [
        item
        for item in getattr(document, "structured_fields", [])
        if str(item.get("value") or "").strip()
    ]
    if not fields:
        return "<span class='empty'>Данные не распознаны</span>"
    preview = "".join(
        f"<div><strong>{html.escape(item['label'])}:</strong> {html.escape(str(item['value']))}</div>"
        for item in fields[:4]
    )
    return preview


def _collect_field_columns(documents: list[Any]) -> list[str]:
    counts: dict[str, int] = {}
    order: list[str] = []
    for document in documents:
        seen: set[str] = set()
        for item in getattr(document, "structured_fields", []) or []:
            label = str(item.get("label") or "").strip()
            if not label or label in seen:
                continue
            seen.add(label)
            counts[label] = counts.get(label, 0) + 1
            if label not in order:
                order.append(label)
    return sorted(order, key=lambda label: (-counts.get(label, 0), order.index(label)))


def _field_value(document: Any, label: str) -> str:
    for item in getattr(document, "structured_fields", []) or []:
        if str(item.get("label") or "").strip() == label:
            return str(item.get("value") or "").strip()
    return ""


def _field_value_preview(value: str) -> str:
    if not value:
        return "<span class='muted'>—</span>"
    return f"<div class='data-preview'>{html.escape(value)}</div>"


def _material_title(document: Any) -> str:
    preferred_labels = (
        "Наименование материала",
        "Название продукции",
        "Наименование продукции",
        "Продукция",
        "Наименование объекта",
        "Название документа",
    )
    for label in preferred_labels:
        value = _field_value(document, label)
        if value:
            return value
    return getattr(document, "title", "") or getattr(document, "source_file_name", "") or "Документ"




def _has_recognized_data(document: Any) -> bool:
    fields = getattr(document, "structured_fields", []) or []
    return any(str(item.get("value") or "").strip() for item in fields if isinstance(item, dict))


def _is_service_document(document: Any) -> bool:
    title = (getattr(document, "title", "") or "").strip().lower()
    file_name = (getattr(document, "source_file_name", "") or "").strip().lower()
    return title in SERVICE_FILE_NAMES or file_name in SERVICE_FILE_NAMES


def _display_status(document: Any) -> str:
    if _is_service_document(document):
        return "Служебный файл"
    if _needs_attention(document):
        if document.classification_status == "failed" or document.recognition_status == "failed":
            return "Ошибка"
        if document.classification_status == "needs_review":
            return "Требует проверки"
        if document.recognition_status in {"empty", "queued"} or not _has_recognized_data(document):
            return "Не распознан"
        return "Требует внимания"
    if document.classification_status == "done" and _has_recognized_data(document):
        return "Готово"
    return "В обработке"


def _recognition_status_label(document: Any) -> str:
    mapping = {
        "done": "Есть данные",
        "empty": "Нет данных",
        "queued": "В очереди",
        "processing": "В обработке",
        "failed": "Ошибка",
    }
    return mapping.get(getattr(document, "recognition_status", "") or "", "Неизвестно")


def _classification_status_label(document: Any) -> str:
    mapping = {
        "done": "Готово",
        "needs_review": "Требует проверки",
        "queued": "В очереди",
        "processing": "В обработке",
        "failed": "Ошибка",
    }
    return mapping.get(getattr(document, "classification_status", "") or "", "Неизвестно")


def _next_step_label(document: Any) -> str:
    status = _display_status(document)
    if status == "Готово":
        return "Документ готов к использованию в проектной работе."
    if status == "Требует проверки":
        return "Проверить тип документа и подтвердить извлеченные поля вручную."
    if status == "Не распознан":
        return "Проверить читаемость файла и повторно запустить распознавание."
    if status == "Ошибка":
        return "Открыть карточку, посмотреть причину и повторно прогнать документ."
    if status == "Требует внимания":
        return "Уточнить извлеченные данные и сверить документ с исходником."
    if status == "Служебный файл":
        return "Служебная запись. Действий не требуется."
    return "Дождаться завершения обработки."


def _show_confidence_value(document: Any) -> bool:
    return _display_status(document) == "Готово"


def _user_type_label(document: Any) -> str:
    mapping = {
        "quality_document": "Документ качества",
        "project_document": "Проектный документ",
        "estimate_document": "Сметный документ",
        "order_document": "Приказ",
        "work_log": "Журнал работ",
        "act_document": "Акт",
        "as_built_scheme": "Исполнительная схема",
        "test_report": "Протокол испытаний",
        "permit_document": "Разрешительный документ",
        "other_working_document": "Прочая рабочая документация",
        "": "Тип не определен",
    }
    if _is_service_document(document):
        return "Служебный файл"
    return mapping.get(getattr(document, "classification_label", "") or "", "Прочая рабочая документация")


def _document_summary(document: Any) -> str:
    source = ""
    try:
        payload = json.loads(getattr(document, "structured_data", "") or "{}")
        source = str(payload.get("summary") or "").strip()
    except json.JSONDecodeError:
        source = ""
    if not source:
        source = str(getattr(document, "classification_reason", "") or getattr(document, "processing_notes", "") or "").strip()
    if not source:
        if _is_service_document(document):
            source = "Служебный файл реестра. Не относится к рабочей документации."
        elif getattr(document, "recognition_status", "") in {"empty", "queued"}:
            source = "Документ еще не дал полезных распознанных данных."
        else:
            source = "Краткое описание пока не сформировано."
    return _trim_text(source, 220)


def _trim_text(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _needs_attention(document: Any) -> bool:
    if _is_service_document(document):
        return False
    if getattr(document, "classification_status", "") in {"failed", "needs_review", "queued", "processing"}:
        return True
    if getattr(document, "recognition_status", "") in {"failed", "empty", "queued", "processing"}:
        return True
    return not _has_recognized_data(document)


def _matches_filter(document: Any, filter_key: str) -> bool:
    is_service = _is_service_document(document)
    if filter_key == "service":
        return is_service
    if is_service:
        return False
    if filter_key == "all":
        return True
    if filter_key == "ready":
        return _display_status(document) == "Готово"
    if filter_key == "problems":
        return _display_status(document) in {"Требует внимания", "Требует проверки", "Ошибка"}
    if filter_key == "unrecognized":
        return _display_status(document) in {"Не распознан", "Требует проверки"}
    return getattr(document, "classification_label", "") == filter_key


def _user_status_label(document: Any) -> str:
    return _display_status(document)


def _table_row_class(document: Any) -> str:
    if _display_status(document) in {"Требует внимания", "Требует проверки", "Не распознан", "Ошибка"}:
        return "row-warning"
    if _display_status(document) == "Готово":
        return "row-ready"
    return ""


def _sort_documents(documents: list[Any], sort_key: str) -> list[Any]:
    if sort_key == "title":
        return sorted(documents, key=lambda item: ((getattr(item, "title", "") or "").lower(), -_status_rank(item)))
    if sort_key == "updated":
        return sorted(documents, key=lambda item: (getattr(item, "updated_at", "") or "", (getattr(item, "title", "") or "").lower()), reverse=True)
    return sorted(
        documents,
        key=lambda item: (_status_rank(item), -(int(str(getattr(item, "id", 0) or 0))), (getattr(item, "title", "") or "").lower()),
    )


def _status_rank(document: Any) -> int:
    mapping = {
        "Ошибка": 0,
        "Требует проверки": 1,
        "Не распознан": 2,
        "Требует внимания": 3,
        "В обработке": 4,
        "Готово": 5,
        "Служебный файл": 6,
    }
    return mapping.get(_display_status(document), 9)


def _short_datetime(value: str) -> str:
    return value[:16] if value else ""


def _event_type_label(value: str) -> str:
    mapping = {
        "registry_sync": "Синхронизация реестра",
        "document_processed": "Документ обработан",
        "document_processed_needs_review": "Документ требует проверки",
        "document_processed_fallback": "Документ классифицирован по имени файла",
        "document_processing_failed": "Ошибка обработки документа",
    }
    return mapping.get(value, "Событие модуля")


def _build_query_href(base_path: str, params: dict[str, str]) -> str:
    clean_params = {key: value for key, value in params.items() if value}
    if not clean_params:
        return base_path
    return f"{base_path}?{urlencode(clean_params)}"


def _cabinet_params(cabinet_id: str) -> dict[str, str]:
    if not cabinet_id or cabinet_id == "default":
        return {}
    return {"cabinet_id": cabinet_id}


def _nav_status_href(title: str) -> str:
    if " | Документы" in title:
        return ".."
    return "."


def _nav_documents_href(title: str) -> str:
    if " | Документы" in title:
        return "."
    return "documents"
