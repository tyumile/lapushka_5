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
      font-family: "Segoe UI", Tahoma, sans-serif;
      line-height: 1.4;
    }}
    .shell {{
      max-width: 1720px;
      margin: 0 auto;
      padding: 20px 24px 40px;
    }}
    .topbar {{
      margin-bottom: 18px;
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
    h1, h2, h3 {{
      margin: 0 0 12px;
    }}
    h2 {{
      margin-top: 24px;
    }}
    .link {{
      color: var(--accent);
      text-decoration: none;
    }}
    .link:hover {{
      text-decoration: underline;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 260px));
      gap: 10px;
      margin: 12px 0 20px;
    }}
    .card, .panel {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 14px;
      box-shadow: 0 4px 14px rgba(52, 38, 19, 0.04);
    }}
    .toolbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      margin: 10px 0 12px;
    }}
    .toolbar-group {{
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .toolbar label {{
      font-size: 13px;
      color: var(--muted);
    }}
    .control, .button {{
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--paper);
      color: var(--text);
      padding: 8px 10px;
      font: inherit;
    }}
    .button {{
      cursor: pointer;
    }}
    .button.is-active {{
      background: var(--accent-soft);
      color: var(--accent);
      border-color: #c8b39a;
    }}
    .table-wrap {{
      overflow-x: auto;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 10px;
      box-shadow: 0 4px 14px rgba(52, 38, 19, 0.04);
      margin-bottom: 20px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--paper);
      table-layout: fixed;
    }}
    th, td {{
      text-align: left;
      padding: 10px 10px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      position: sticky;
      top: 0;
      z-index: 2;
      background: #f7f2e8;
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    tbody tr:nth-child(even) {{
      background: rgba(108, 77, 47, 0.04);
    }}
    tbody tr:hover {{
      background: rgba(108, 77, 47, 0.1);
    }}
    .row-alert {{
      background: rgba(164, 70, 50, 0.08) !important;
    }}
    .first-col-sticky th:first-child,
    .first-col-sticky td:first-child {{
      position: sticky;
      left: 0;
      z-index: 1;
      background: inherit;
    }}
    .first-col-sticky th:first-child {{
      z-index: 3;
      background: #f7f2e8;
    }}
    .compact td, .compact th {{
      padding-top: 7px;
      padding-bottom: 7px;
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
    .small {{
      font-size: 12px;
    }}
    .preview {{
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 3;
      overflow: hidden;
    }}
    .code {{
      font-family: "Courier New", monospace;
      font-size: 12px;
      white-space: nowrap;
    }}
    .section {{
      margin-bottom: 20px;
    }}
    .split {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 16px;
    }}
    details {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 0;
      margin-bottom: 12px;
      box-shadow: 0 8px 24px rgba(52, 38, 19, 0.05);
      overflow: hidden;
    }}
    summary {{
      list-style: none;
      cursor: pointer;
      padding: 16px;
      font-weight: 700;
    }}
    summary::-webkit-details-marker {{
      display: none;
    }}
    .details-body {{
      padding: 0 16px 16px;
    }}
    .summary-row {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      flex-wrap: wrap;
    }}
    .project-toggle {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 0;
      background: none;
      color: var(--text);
      padding: 0;
      margin: 0;
      font: inherit;
      cursor: pointer;
      text-align: left;
    }}
    .project-toggle::before {{
      content: "▸";
      color: var(--accent);
      font-size: 12px;
    }}
    .project-toggle[aria-expanded="true"]::before {{
      content: "▾";
    }}
    .detail-row[hidden] {{
      display: none;
    }}
    .detail-cell {{
      padding: 0;
      background: #fcf8f0;
    }}
    .detail-panel {{
      padding: 16px;
    }}
    .alert-panel {{
      background: #fff5f2;
      border-color: #d7a297;
    }}
    .success-panel {{
      background: #eef7ee;
      border-color: #b8d2bb;
    }}
    .mono {{
      font-family: "Courier New", monospace;
      font-size: 13px;
      word-break: break-all;
    }}
    .inline-form {{
      display: inline-flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      margin-top: 10px;
    }}
    @media (max-width: 980px) {{
      .split {{
        grid-template-columns: 1fr;
      }}
      .shell {{
        padding: 16px;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <div>
        <div class="brand">project_builder</div>
        <div class="tag">Реальные проекты, их состав и недостающие документы</div>
      </div>
    </div>
    {body}
  </div>
  <script>
    document.addEventListener("click", function(event) {{
      var toggle = event.target.closest("[data-toggle-row]");
      if (!toggle) return;
      var row = document.getElementById(toggle.getAttribute("data-toggle-row"));
      if (!row) return;
      var expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", expanded ? "false" : "true");
      row.hidden = expanded;
    }});

    document.addEventListener("input", function(event) {{
      var input = event.target.closest("[data-table-search]");
      if (!input) return;
      var table = document.getElementById(input.getAttribute("data-table-search"));
      if (!table) return;
      var query = input.value.trim().toLowerCase();
      table.querySelectorAll("tbody tr[data-row-text]").forEach(function(row) {{
        var statusFilter = row.closest(".table-block")?.querySelector("[data-table-status]");
        var statusValue = statusFilter ? statusFilter.value : "";
        var text = row.getAttribute("data-row-text") || "";
        var matchesText = !query || text.indexOf(query) !== -1;
        var matchesStatus = !statusValue || (row.getAttribute("data-status") || "") === statusValue;
        row.hidden = !(matchesText && matchesStatus);
      }});
    }});

    document.addEventListener("change", function(event) {{
      var select = event.target.closest("[data-table-status]");
      if (!select) return;
      var tableId = select.getAttribute("data-table-status");
      var input = document.querySelector("[data-table-search='" + tableId + "']");
      if (input) {{
        input.dispatchEvent(new Event("input", {{ bubbles: true }}));
      }}
    }});

    document.addEventListener("click", function(event) {{
      var button = event.target.closest("[data-density]");
      if (!button) return;
      var density = button.getAttribute("data-density");
      document.querySelectorAll("[data-density]").forEach(function(item) {{
        item.classList.toggle("is-active", item === button);
      }});
      document.querySelectorAll(".table-wrap table").forEach(function(table) {{
        table.classList.toggle("compact", density === "compact");
      }});
    }});
  </script>
</body>
</html>"""


def render_status_page(summary: dict[str, Any], cabinet_id: str = "default", message: str = "") -> str:
    last_event = summary["status"]["last_event"]
    action = summary.get("analysis_action") or {}
    event_rows = (
        "<tr>"
        f"<td>{html.escape(_event_title(last_event['event_type']))}</td>"
        f"<td class='code'>{html.escape(last_event['created_at'])}</td>"
        f"<td>{html.escape(_event_details(last_event['event_type'], last_event['details']))}</td>"
        "</tr>"
        if last_event
        else "<tr><td colspan='3'>Событий пока нет.</td></tr>"
    )
    body = f"""
    <h1>Статус модуля</h1>
    <p class="muted">Кабинет: {html.escape(cabinet_id)}</p>
    <p class="muted">Рабочий экран показывает только реальные проекты, которые уже были проанализированы внешним агентом.</p>
    {render_flash_message(message)}
    {render_analysis_action_panel(action, cabinet_id)}
    {render_latest_analysis_card(summary.get("latest_analysis"))}
    {render_density_controls()}
    <div class="grid">
      <div class="card"><strong>{summary['status']['total_projects']}</strong><br><span class="muted">Проектов</span></div>
      <div class="card"><strong>{summary['status']['complete_projects']}</strong><br><span class="muted">Полных проектов</span></div>
      <div class="card"><strong>{summary['status']['needs_documents']}</strong><br><span class="muted">Требуют документов</span></div>
      <div class="card"><strong>{summary['status']['total_documents']}</strong><br><span class="muted">Подтверждающих документов</span></div>
      <div class="card"><strong>{summary['status']['total_deficits']}</strong><br><span class="muted">Нужно добавить</span></div>
    </div>
    <h2>Проекты</h2>
    {render_home_projects(summary.get("project_cards", []), cabinet_id)}
    <h2>Последнее событие</h2>
    {render_simple_table("events-table", event_rows, ["Событие", "Дата", "Описание"], search_placeholder="Поиск по последнему событию")}
    """
    return render_page("project_builder | Статус", body)


def render_flash_message(message: str) -> str:
    if not message:
        return ""
    panel_class = "success-panel" if "запущен" in message.lower() else "alert-panel"
    return f"<div class='panel {panel_class}'><strong>{html.escape(message)}</strong></div>"


def render_analysis_action_panel(action: dict[str, Any], cabinet_id: str) -> str:
    if not action:
        return ""
    if action.get("available"):
        return f"""
        <div class="panel">
          <strong>Анализ проекта</strong>
          <p class="muted">{html.escape(action.get('hint') or '')}</p>
          <form class="inline-form" method="post" action="/analysis/run">
            <input type="hidden" name="cabinet_id" value="{html.escape(cabinet_id)}">
            <button class="button is-active" type="submit">Анализ проекта</button>
          </form>
        </div>
        """
    panel_class = "alert-panel" if not action.get("running") else ""
    return f"""
    <div class="panel {panel_class}">
      <strong>{html.escape(action.get('label') or 'Анализ проекта')}</strong>
      <p class="muted">{html.escape(action.get('hint') or '')}</p>
    </div>
    """


def render_latest_analysis_card(analysis: dict[str, Any] | None) -> str:
    if not analysis:
        return (
            "<div class='panel'><strong>AI-анализ</strong>"
            "<p class='muted'>Реальный результат агента пока не сохранен.</p>"
            "<p class='muted'>Загрузка файлов в ingest_registry и обработка в doc_classifier не создают проекты автоматически. "
            "Для текущего кабинета нужно отдельно запустить проектный AI-анализ через "
            "<span class='mono'>scripts/run_project_analysis.py --cabinet-id &lt;cabinet_id&gt; --project-document-id &lt;file_registry_id&gt;</span>.</p>"
            "</div>"
        )
    project = analysis.get("project", {})
    modules = analysis.get("modules", [])
    materials_count = sum(len(item.get("materials", [])) for item in modules)
    norms_count = sum(len(item.get("norms", [])) for item in modules)
    return f"""
    <div class="panel">
      <strong>Последний AI-анализ</strong>
      <p>{html.escape(project.get('project_name') or project.get('project_file_name') or 'Без названия')}</p>
      <div class="grid">
        <div class="card"><strong>{len(modules)}</strong><br><span class="muted">Модулей</span></div>
        <div class="card"><strong>{materials_count}</strong><br><span class="muted">Материалов</span></div>
        <div class="card"><strong>{norms_count}</strong><br><span class="muted">Норм</span></div>
      </div>
    </div>
    """


def render_home_projects(projects: list[Any], cabinet_id: str = "default") -> str:
    if not projects:
        return (
            "<div class='panel'><strong>Проектов пока нет.</strong>"
            f"<p class='muted'>Для кабинета {html.escape(cabinet_id)} ещё не сохранён ни один результат project_analysis.json.</p>"
            "<p class='muted'>Загрузка файлов в ingest_registry и распознавание в doc_classifier сами по себе не наполняют project_builder. "
            "Следующий шаг: запустить отдельный AI-анализ проекта для документа проекта в этом кабинете.</p>"
            "</div>"
        )
    rows = []
    for index, payload in enumerate(projects, start=1):
        project = payload.get("project", {})
        modules = payload.get("modules", [])
        unmatched = payload.get("unmatched_documents", [])
        materials_count = sum(len(item.get("materials", [])) for item in modules)
        norms_count = sum(len(item.get("norms", [])) for item in modules)
        grouped_documents = _group_project_documents(modules)
        documents_rows = "".join(
            f"""
            <tr data-row-text="{html.escape(item['row_text'])}" data-status="{html.escape(item['status_key'])}">
              <td><strong>{html.escape(item['title'])}</strong></td>
              <td>{html.escape(item['kind'])}</td>
              <td>{html.escape(item['sections_label'])}</td>
              <td><div class="preview">{html.escape(item['comment'])}</div></td>
              <td><span class="status {'ok' if item['is_confirmed'] else 'alert'}">{html.escape(item['status_label'])}</span></td>
            </tr>
            """
            for item in grouped_documents
        ) or "<tr><td colspan='5'>Материалы и документы ещё не определены.</td></tr>"
        section_breakdown = "".join(
            f"""
            <details>
              <summary>{html.escape(module.get('module_name') or f'Секция {section_index}')}</summary>
              <div class="details-body">
                <table>
                  <thead>
                    <tr>
                      <th>Документ/материал</th>
                      <th>Тип</th>
                      <th>Комментарий</th>
                      <th>Статус</th>
                    </tr>
                  </thead>
                  <tbody>{_render_section_document_rows(module.get('materials', []))}</tbody>
                </table>
              </div>
            </details>
            """
            for section_index, module in enumerate(modules, start=1)
        ) or "<div class='panel'>Секции пока не определены.</div>"
        deficits_rows = "".join(
            f"""
            <tr class="row-alert" data-row-text="{html.escape((item.get('document_name') or '') + ' ' + (item.get('reason') or '')).lower()}" data-status="needs_documents">
              <td><strong>{html.escape(item.get('document_name') or 'Нужен документ')}</strong></td>
              <td><div class="preview">{html.escape(item.get('reason') or 'Причина не указана.')}</div></td>
              <td><span class="status alert">Нужно добавить документы</span></td>
            </tr>
            """
            for item in unmatched
        ) or "<tr><td colspan='3'>Нехваток нет. По текущему анализу проект укомплектован.</td></tr>"
        row_id = f"project-details-{index}"
        row_text = " ".join(
            [
                str(project.get("project_name") or project.get("project_file_name") or ""),
                str(project.get("project_code") or ""),
                str(_project_status_label(project.get("status", ""), len(unmatched))),
            ]
        ).lower()
        row_class = "row-alert" if unmatched else ""
        rows.append(
            f"""
            <tr class="{row_class}" data-row-text="{html.escape(row_text)}" data-status="{'needs_documents' if unmatched else 'ok'}">
              <td style="width:30%;">
                <button class="project-toggle" type="button" data-toggle-row="{row_id}" aria-expanded="{'true' if index == 1 else 'false'}">
                  {html.escape(project.get('project_name') or project.get('project_file_name') or 'Проект')}
                </button>
                <div class="muted small code">{html.escape(project.get('project_code') or 'Шифр не найден')}</div>
              </td>
              <td style="width:12%;"><span class="status {'alert' if unmatched else 'ok'}">{'Нужно добавить документы' if unmatched else 'Готово'}</span></td>
              <td style="width:8%;">{len(modules)}</td>
              <td style="width:10%;">{len(grouped_documents)} / {materials_count}</td>
              <td style="width:8%;">{norms_count}</td>
              <td style="width:10%;">{len(unmatched)}</td>
              <td style="width:22%;"><div class="preview">{html.escape(_analysis_next_step_text(unmatched))}</div></td>
            </tr>
            <tr id="{row_id}" class="detail-row" {'hidden' if index != 1 else ''}>
              <td colspan="7" class="detail-cell">
                <div class="detail-panel">
                  <div class="grid">
                    <div class="card"><strong>{len(grouped_documents)}</strong><br><span class="muted">Уникальных документов</span></div>
                    <div class="card"><strong>{len(modules)}</strong><br><span class="muted">Секций</span></div>
                    <div class="card"><strong>{materials_count}</strong><br><span class="muted">Применений</span></div>
                    <div class="card"><strong>{len(unmatched)}</strong><br><span class="muted">Нужно добавить</span></div>
                  </div>
                  <div class="section">
                    <h3>Состав проекта</h3>
                    {render_table_toolbar(f"project-docs-{index}", "Поиск по документам и комментариям", include_status=True)}
                    <div class="table-wrap first-col-sticky table-block">
                      <table id="project-docs-{index}">
                        <thead>
                          <tr>
                            <th style="width:26%;">Документ/материал</th>
                            <th style="width:14%;">Тип</th>
                            <th style="width:18%;">Где используется</th>
                            <th style="width:28%;">Комментарий</th>
                            <th style="width:14%;">Статус</th>
                          </tr>
                        </thead>
                        <tbody>{documents_rows}</tbody>
                      </table>
                    </div>
                  </div>
                  <div class="section">
                    <h3>По секциям</h3>
                    {section_breakdown}
                  </div>
                  <div class="section">
                    <h3>Что нужно добавить</h3>
                    {render_table_toolbar(f"project-deficits-{index}", "Поиск по нехваткам", include_status=True)}
                    <div class="table-wrap table-block">
                      <table id="project-deficits-{index}">
                        <thead>
                          <tr>
                            <th style="width:28%;">Документ</th>
                            <th style="width:52%;">Причина</th>
                            <th style="width:20%;">Статус</th>
                          </tr>
                        </thead>
                        <tbody>{deficits_rows}</tbody>
                      </table>
                    </div>
                  </div>
                  <p><a class="link" href="/projects/{payload.get('_id', 1)}?cabinet_id={html.escape(cabinet_id)}">Открыть детальную страницу проекта</a></p>
                </div>
              </td>
            </tr>
            """
        )
    table = "".join(rows)
    return f"""
    {render_table_toolbar("home-projects-table", "Поиск по проектам и шифрам", include_status=True)}
    <div class="table-wrap first-col-sticky table-block">
      <table id="home-projects-table">
        <thead>
          <tr>
            <th>Проект</th>
            <th>Статус</th>
            <th>Секций</th>
            <th>Документов</th>
            <th>Норм</th>
            <th>Нехватки</th>
            <th>Следующий шаг</th>
          </tr>
        </thead>
        <tbody>{table}</tbody>
      </table>
    </div>
    """


def render_projects_page(projects: list[Any], cabinet_id: str = "default") -> str:
    body = f"""
    <h1>Список проектов</h1>
    <p class="muted">Здесь показываются только реальные проекты, которые уже прошли через внешний AI-анализ. Основной сценарий работы: раскрыть нужный проект прямо в таблице и посмотреть состав, нехватки, связи и секции без перехода на отдельную страницу.</p>
    {render_density_controls()}
    {render_projects_table(projects, cabinet_id)}
    """
    return render_page("project_builder | Проекты", body)


def render_projects_table(projects: list[Any], cabinet_id: str = "default") -> str:
    rows = []
    for index, project in enumerate(projects, start=1):
        status = project["status"] if isinstance(project, dict) else project.status
        total_deficits = project["total_deficits"] if isinstance(project, dict) else project.total_deficits
        status_class = "ok" if status == "complete" else "alert"
        project_id = project["id"] if isinstance(project, dict) else project.id
        project_name = project["project_name"] if isinstance(project, dict) else project.project_name
        project_code = project["project_code"] if isinstance(project, dict) else project.project_code
        assigned_documents = project["assigned_documents"] if isinstance(project, dict) else project.assigned_documents
        total_documents = project["total_documents"] if isinstance(project, dict) else project.total_documents
        total_links = project["total_links"] if isinstance(project, dict) else project.total_links
        completeness_ratio = project["completeness_ratio"] if isinstance(project, dict) else project.completeness_ratio
        missing_documents = max(total_documents - assigned_documents, 0)
        detail_row_id = f"projects-table-detail-{index}"
        rows.append(
            f"""
            <tr class="{'row-alert' if total_deficits else ''}" data-row-text="{html.escape((project_name + ' ' + project_code + ' ' + _project_status_label(status, total_deficits)).lower())}" data-status="{'needs_documents' if total_deficits else 'ok'}">
              <td style="width:32%;">
                <button class="project-toggle" type="button" data-toggle-row="{detail_row_id}" aria-expanded="false">{html.escape(project_name)}</button><br>
                <span class="muted code">{html.escape(project_code)}</span>
              </td>
              <td style="width:14%;"><span class="status {status_class}">{html.escape(_project_status_label(status, total_deficits))}</span></td>
              <td style="width:16%;">{assigned_documents} / {total_documents}<br><span class="muted small">Не хватает: {missing_documents}</span></td>
              <td style="width:10%;">{total_links}</td>
              <td style="width:14%;">{total_deficits}<br><span class="muted small">{_deficit_summary(total_deficits)}</span></td>
              <td style="width:14%;">{int(completeness_ratio * 100)}%</td>
            </tr>
            <tr id="{detail_row_id}" class="detail-row" hidden>
              <td colspan="6" class="detail-cell">
                <div class="detail-panel">
                  {render_project_detail_content(project, cabinet_id=cabinet_id, include_title=False, show_fallback_link=True, table_id_prefix=f"projects-inline-{project_id or index}", show_summary_cards=False, show_deficits=False, show_toolbars=False)}
                </div>
              </td>
            </tr>
            """
        )
    table = "".join(rows) if rows else "<tr><td colspan='6'>Проектов пока нет.</td></tr>"
    return f"""
    <div class="table-wrap first-col-sticky table-block">
      <table id="projects-table">
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
    </div>
    """


def render_project_page(payload: dict[str, Any], cabinet_id: str = "default") -> str:
    body = render_project_detail_content(
        payload,
        cabinet_id=cabinet_id,
        include_title=True,
        show_fallback_link=False,
        table_id_prefix=f"project-page-{payload.get('_id', 1)}",
    )
    return render_page("project_builder | Карточка проекта", body)


def render_project_detail_content(
    payload: dict[str, Any],
    cabinet_id: str = "default",
    include_title: bool = True,
    show_fallback_link: bool = False,
    table_id_prefix: str = "project-detail",
    show_summary_cards: bool = True,
    show_deficits: bool = True,
    show_toolbars: bool = True,
) -> str:
    project = payload.get("project", {})
    modules = payload.get("modules", [])
    unmatched = payload.get("unmatched_documents", [])
    grouped_documents = _group_project_documents(modules)
    documents_rows = "".join(
        f"""
        <tr data-row-text="{html.escape(item['row_text'])}" data-status="{html.escape(item['status_key'])}">
          <td><strong>{html.escape(item['title'])}</strong></td>
          <td>{html.escape(item['kind'])}</td>
          <td>{html.escape(item['sections_label'])}</td>
          <td><div class="preview">{html.escape(item['comment'])}</div></td>
          <td><span class="status {'ok' if item['is_confirmed'] else 'alert'}">{html.escape(item['status_label'])}</span></td>
        </tr>
        """
        for item in grouped_documents
    ) or "<tr><td colspan='5'>Материалы и документы ещё не определены.</td></tr>"
    section_breakdown = "".join(
        f"""
        <details>
          <summary>{html.escape(module.get('module_name') or f'Секция {index}')}</summary>
          <div class="details-body">
            <table>
              <thead>
                <tr>
                  <th>Документ/материал</th>
                  <th>Тип</th>
                  <th>Комментарий</th>
                  <th>Статус</th>
                </tr>
              </thead>
              <tbody>{_render_section_document_rows(module.get('materials', []))}</tbody>
            </table>
          </div>
        </details>
        """
        for index, module in enumerate(modules, start=1)
    ) or "<div class='panel'>Секции пока не определены.</div>"
    links_rows = []
    for module in modules:
        for norm in module.get("norms", []):
            links_rows.append(
                f"<tr data-row-text=\"{html.escape((str(module.get('module_name', '')) + ' ' + str(norm.get('norm_name', '')) + ' ' + _reference_text(norm.get('project_source', {}))).lower())}\" data-status=\"ok\">"
                f"<td>{html.escape(module.get('module_name', ''))}</td>"
                f"<td>{html.escape(norm.get('norm_name', ''))}</td>"
                f"<td><div class='preview'>{html.escape(_reference_text(norm.get('project_source', {})))}</div></td>"
                "</tr>"
            )
    deficit_rows = "".join(
        f"""
        <tr class="row-alert" data-row-text="{html.escape(((item.get('document_name') or '') + ' ' + (item.get('reason') or '')).lower())}" data-status="needs_documents">
          <td><strong>{html.escape(item.get('document_name') or 'Нужен документ')}</strong></td>
          <td><div class="preview">{html.escape(item.get('reason', ''))}</div></td>
          <td><span class="status alert">Нужно добавить документы</span></td>
        </tr>
        """
        for item in unmatched
    ) or "<tr><td colspan='3'>Нехваток нет. Проект укомплектован на основе текущего анализа.</td></tr>"
    title_block = (
        f"<h1>{html.escape(project.get('project_name') or project.get('project_file_name') or 'Проект')}</h1>"
        f"<p class='muted'>Шифр проекта: {html.escape(project.get('project_code') or 'не найден')}</p>"
        if include_title
        else (
            f"<div class='summary-row'><h2>{html.escape(project.get('project_name') or project.get('project_file_name') or 'Проект')}</h2>"
            f"<span class='status {'alert' if unmatched else 'ok'}'>{'Нужно добавить документы' if unmatched else 'Готов к работе'}</span></div>"
            f"<p class='muted'>Шифр проекта: {html.escape(project.get('project_code') or 'не найден')}</p>"
        )
    )
    fallback_link = (
        f"<p class='muted small'>Технический fallback: <a class='link' href='/projects/{payload.get('_id', 1)}?cabinet_id={html.escape(cabinet_id)}'>открыть отдельную страницу проекта</a>.</p>"
        if show_fallback_link
        else ""
    )
    return f"""
    {title_block}
    {f"""
    <div class="grid">
      <div class="card"><strong>Статус</strong><br><span class="status {'alert' if unmatched else 'ok'}">{'Нужно добавить документы' if unmatched else 'Готов к работе'}</span></div>
      <div class="card"><strong>Модулей</strong><br>{len(modules)}</div>
      <div class="card"><strong>Материалов</strong><br>{sum(len(item.get('materials', [])) for item in modules)}</div>
      <div class="card"><strong>Норм</strong><br>{sum(len(item.get('norms', [])) for item in modules)}</div>
      <div class="card"><strong>Нехватки</strong><br>{len(unmatched)}</div>
    </div>
    """ if show_summary_cards else ""}
    {f"""
    <div class="panel" style="border-color:#d7a297;background:#fff5f2;">
      <strong>Что нужно добавить</strong>
      <p>{html.escape(_analysis_next_step_text(unmatched))}</p>
      {render_table_toolbar(f"{table_id_prefix}-deficits-table", "Поиск по нехваткам", include_status=True) if show_toolbars else ""}
      <div class="table-wrap table-block">
        <table id="{table_id_prefix}-deficits-table">
          <thead>
            <tr>
              <th style="width:28%;">Документ</th>
              <th style="width:52%;">Причина</th>
              <th style="width:20%;">Статус</th>
            </tr>
          </thead>
          <tbody>{deficit_rows}</tbody>
        </table>
      </div>
      <p><a class="link" href="/analysis/{payload.get('_id', 1)}?cabinet_id={html.escape(cabinet_id)}">Открыть полный AI-анализ проекта</a></p>
    </div>
    """ if show_deficits else ""}
    <h2>Состав проекта</h2>
    {f"""
    <div class="grid">
      <div class="card"><strong>{len(grouped_documents)}</strong><br><span class="muted">Уникальных документов</span></div>
      <div class="card"><strong>{len(modules)}</strong><br><span class="muted">Секций</span></div>
      <div class="card"><strong>{sum(len(item.get('materials', [])) for item in modules)}</strong><br><span class="muted">Применений</span></div>
    </div>
    """ if show_summary_cards else ""}
    {render_table_toolbar(f"{table_id_prefix}-documents-table", "Поиск по составу проекта", include_status=True) if show_toolbars else ""}
    <div class="table-wrap first-col-sticky table-block">
      <table id="{table_id_prefix}-documents-table">
        <thead>
          <tr>
            <th style="width:26%;">Документ/материал</th>
            <th style="width:14%;">Тип</th>
            <th style="width:18%;">Где используется</th>
            <th style="width:28%;">Комментарий</th>
            <th style="width:14%;">Статус</th>
          </tr>
        </thead>
        <tbody>{documents_rows}</tbody>
      </table>
    </div>
    <h3>По секциям</h3>
    {section_breakdown}
    <h2>Нормы</h2>
    {render_table_toolbar(f"{table_id_prefix}-links-table", "Поиск по нормам") if show_toolbars else ""}
    <div class="table-wrap first-col-sticky table-block">
      <table id="{table_id_prefix}-links-table">
        <thead>
          <tr>
            <th style="width:20%;">Модуль</th>
            <th style="width:26%;">Норма</th>
            <th style="width:54%;">Источник в проекте</th>
          </tr>
        </thead>
        <tbody>{''.join(links_rows) or "<tr><td colspan='3'>Связи пока не найдены.</td></tr>"}</tbody>
      </table>
    </div>
    {fallback_link}
    """


def render_analysis_page(payload: dict[str, Any], cabinet_id: str = "default") -> str:
    project = payload.get("project", {})
    modules = payload.get("modules", [])
    warnings = payload.get("analysis_warnings", [])
    body = f"""
    <h1>{html.escape(project.get("project_name") or project.get("project_file_name") or "AI-анализ проекта")}</h1>
    <p class="muted">Шифр проекта: {html.escape(project.get("project_code") or "не найден")}</p>
    {render_density_controls()}
    <div class="grid">
      <div class="card"><strong>{len(modules)}</strong><br><span class="muted">Модулей</span></div>
      <div class="card"><strong>{sum(len(item.get("materials", [])) for item in modules)}</strong><br><span class="muted">Материалов</span></div>
      <div class="card"><strong>{sum(len(item.get("norms", [])) for item in modules)}</strong><br><span class="muted">Норм</span></div>
    </div>
    <div class="panel">
      <strong>Краткий вывод</strong>
      <p>{html.escape(project.get("analysis_summary") or "Резюме не заполнено")}</p>
      <p class="muted">{html.escape(project.get("analysis_notes") or "")}</p>
      <p><a class="link" href="/projects/{payload.get('_id', 1)}?cabinet_id={html.escape(cabinet_id)}">Вернуться к карточке проекта</a></p>
    </div>
    {render_analysis_modules(modules)}
    {render_analysis_warnings(warnings)}
    """
    return render_page("project_builder | AI-анализ", body)


def render_analysis_modules(modules: list[Any]) -> str:
    if not modules:
        return "<div class='panel'>Модули в результате анализа не найдены.</div>"
    blocks = []
    for index, module in enumerate(modules, start=1):
        materials = module.get("materials", [])
        norms = module.get("norms", [])
        source = module.get("source_reference", {})
        materials_table = "".join(
            (
                f"<tr data-row-text=\"{html.escape((str(item.get('material_name', '')) + ' ' + str(item.get('document_name', '')) + ' ' + str(item.get('document_number', ''))).lower())}\" data-status=\"{'ok' if item.get('document_name') else 'needs_review'}\">"
                f"<td><strong>{html.escape(item.get('material_name', ''))}</strong></td>"
                f"<td>{html.escape(item.get('document_name', '') or 'Не указан')}</td>"
                f"<td class='code'>{html.escape(item.get('document_number', '') or 'Не указан')}</td>"
                f"<td class='code'>{html.escape(item.get('document_date', '') or 'Не указана')}</td>"
                f"<td><div class='preview'>{html.escape(_reference_text(item.get('project_source', {})))}</div></td>"
                f"<td><div class='preview small'>{html.escape(_safe_document_origin(item))}</div></td>"
                "</tr>"
            )
            for item in materials
        ) or "<tr><td colspan='6'>Материалы не найдены.</td></tr>"
        norms_table = "".join(
            (
                f"<tr data-row-text=\"{html.escape((str(item.get('norm_name', '')) + ' ' + _reference_text(item.get('project_source', {}))).lower())}\" data-status=\"ok\">"
                f"<td>{html.escape(item.get('norm_name', ''))}</td>"
                f"<td><div class='preview'>{html.escape(_reference_text(item.get('project_source', {})))}</div></td>"
                "</tr>"
            )
            for item in norms
        ) or "<tr><td colspan='2'>Нормы не найдены.</td></tr>"
        blocks.append(
            f"""
            <details {'open' if index == 1 else ''}>
              <summary>{html.escape(module.get('module_name', f'Модуль {index}'))}</summary>
              <div class="details-body">
                <p class="muted">
                  Тип: {html.escape(module.get('module_type', ''))},
                  корпус: {html.escape(module.get('building', '') or 'не указан')},
                  секция: {html.escape(module.get('section', '') or 'не указана')},
                  этаж: {html.escape(module.get('floor', '') or 'не указан')},
                  раздел: {html.escape(module.get('discipline', '') or 'не указан')}
                </p>
                <p><strong>Источник в проекте:</strong> <span class="preview">{html.escape(_reference_text(source))}</span></p>
                <div class="grid">
                  <div class="card"><strong>{len(materials)}</strong><br><span class="muted">Материалов</span></div>
                  <div class="card"><strong>{len(norms)}</strong><br><span class="muted">Норм</span></div>
                </div>
                <details {'open' if index == 1 else ''}>
                  <summary>Материалы</summary>
                  <div class="details-body">
                    {render_table_toolbar(f"analysis-materials-{index}", "Поиск по материалам", include_status=True)}
                    <div class="table-wrap table-block">
                      <table id="analysis-materials-{index}">
                        <thead>
                          <tr>
                            <th style="width:24%;">Материал</th>
                            <th style="width:18%;">Документ</th>
                            <th style="width:12%;">Номер</th>
                            <th style="width:10%;">Дата</th>
                            <th style="width:20%;">Источник в проекте</th>
                            <th style="width:16%;">Источник документа</th>
                          </tr>
                        </thead>
                        <tbody>{materials_table}</tbody>
                      </table>
                    </div>
                  </div>
                </details>
                <details>
                  <summary>Нормы</summary>
                  <div class="details-body">
                    {render_table_toolbar(f"analysis-norms-{index}", "Поиск по нормам")}
                    <div class="table-wrap table-block">
                      <table id="analysis-norms-{index}">
                        <thead>
                          <tr>
                            <th style="width:36%;">Норма</th>
                            <th style="width:64%;">Источник в проекте</th>
                          </tr>
                        </thead>
                        <tbody>{norms_table}</tbody>
                      </table>
                    </div>
                  </div>
                </details>
              </div>
            </details>
            """
        )
    return "".join(blocks)


def render_analysis_warnings(warnings: list[Any]) -> str:
    if not warnings:
        return ""
    items = "".join(f"<li>{html.escape(str(item))}</li>" for item in warnings)
    return f"<div class='panel'><strong>Замечания агента</strong><ul>{items}</ul></div>"


def render_density_controls() -> str:
    return """
    <div class="toolbar">
      <div class="toolbar-group">
        <label>Плотность таблиц</label>
        <button type="button" class="button is-active" data-density="normal">Обычно</button>
        <button type="button" class="button" data-density="compact">Компактно</button>
      </div>
    </div>
    """


def render_table_toolbar(table_id: str, search_placeholder: str, include_status: bool = False) -> str:
    status_control = (
        f"""
        <label>
          Статус
          <select class="control" data-table-status="{table_id}">
            <option value="">Все</option>
            <option value="ok">Готово</option>
            <option value="needs_documents">Нужно добавить документы</option>
            <option value="needs_review">Требует внимания</option>
            <option value="error">Ошибка</option>
          </select>
        </label>
        """
        if include_status
        else ""
    )
    return f"""
    <div class="toolbar">
      <div class="toolbar-group">
        <label>
          Поиск
          <input class="control" type="search" placeholder="{html.escape(search_placeholder)}" data-table-search="{table_id}">
        </label>
        {status_control}
      </div>
      <div class="toolbar-group">
        <span class="muted small">Сортировка: по названию и статусу, проблемные строки выделены.</span>
      </div>
    </div>
    """


def render_simple_table(table_id: str, rows: str, headers: list[str], search_placeholder: str) -> str:
    header_html = "".join(f"<th>{html.escape(item)}</th>" for item in headers)
    return f"""
    {render_table_toolbar(table_id, search_placeholder)}
    <div class="table-wrap table-block">
      <table id="{table_id}">
        <thead><tr>{header_html}</tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """


def _reference_text(reference: dict[str, Any]) -> str:
    page = str(reference.get("page", "")).strip()
    sheet = str(reference.get("sheet", "")).strip()
    quote = str(reference.get("quote", "")).strip()
    fragments = []
    if page:
        fragments.append(f"стр. {page}")
    if sheet:
        fragments.append(f"лист {sheet}")
    if quote:
        fragments.append(quote)
    return "; ".join(fragments) if fragments else "не указано"


def _project_status_label(status: str, deficits: int) -> str:
    if deficits > 0:
        return "Нужно добавить документы"
    if status == "complete":
        return "Полный"
    if status == "needs_documents":
        return "Требует проверки"
    return "В работе"


def _severity_label(value: str) -> str:
    return {
        "high": "Высокий приоритет",
        "medium": "Средний приоритет",
        "low": "Низкий приоритет",
    }.get(value, "Требует внимания")


def _required_type_label(value: str) -> str:
    return {
        "structural_plan": "Конструктивный раздел",
        "permit_document": "Разрешительный документ",
        "project_document": "Проектный документ",
    }.get(value, value.replace("_", " "))


def _document_type_label(value: str) -> str:
    return {
        "architecture_plan": "План",
        "material_specification": "Спецификация",
        "estimate": "Смета",
        "structural_plan": "Конструктив",
        "engineering_scheme": "Инженерная схема",
        "project_passport": "Паспорт проекта",
    }.get(value, value.replace("_", " "))


def _event_title(value: str) -> str:
    return {
        "project_analysis_completed": "AI-анализ обновлен",
        "project_analysis_text_mode": "AI-анализ выполнен",
        "module_start": "Модуль запущен",
        "seed_demo_data": "Демонстрационные данные подготовлены",
    }.get(value, "Последнее обновление")


def _event_details(event_type: str, value: str) -> str:
    text = value.rsplit("/", 1)[-1]
    if "Saved project analysis" in value or event_type == "project_analysis_completed":
        return "Сохранён новый результат анализа проекта."
    if "Used project text mode" in value or event_type == "project_analysis_text_mode":
        return "Агент получил текст проекта и сформировал обновлённый результат."
    if event_type == "module_start":
        return "Модуль запущен и готов к работе."
    if event_type == "seed_demo_data":
        return "Внутренняя стартовая инициализация завершена."
    return text[:180]


def _deficit_summary(total: int) -> str:
    if total == 0:
        return "Без пробелов"
    if total == 1:
        return "1 пробел"
    return f"{total} пробела"


def _next_step_text(deficits: list[Any]) -> str:
    if not deficits:
        return "Следующий шаг не требуется: проект уже укомплектован."
    top_items = ", ".join(_required_type_label(item.required_type) for item in deficits[:3])
    return f"Добавьте в проект недостающие документы: {top_items}. После загрузки повторно проверьте связи и полноту проекта."


def _analysis_next_step_text(unmatched: list[Any]) -> str:
    if not unmatched:
        return "Следующий шаг не требуется: все найденные материалы уже сопоставлены с документами."
    names = ", ".join((item.get("document_name") or "недостающий документ") for item in unmatched[:3])
    return f"Следующий шаг: добавить или уточнить документы для {names}, затем повторно запустить AI-анализ проекта."


def _document_hint(item: dict[str, Any]) -> str:
    name = item.get("document_name", "")
    if "смет" in name.lower():
        return "Смета"
    if "специ" in name.lower():
        return "Спецификация"
    if "сертификат" in name.lower() or "декларац" in name.lower():
        return "Документ качества"
    return "Подтверждающий документ"


def _group_project_documents(modules: list[Any]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for index, module in enumerate(modules, start=1):
        section_name = module.get("module_name") or f"Секция {index}"
        for item in module.get("materials", []):
            title = item.get("material_name") or item.get("document_name") or "Материал"
            registry_id = str(item.get("document_registry_id") or "").strip()
            disk_path = str(item.get("document_disk_path") or "").strip()
            key = (
                registry_id,
                disk_path,
                title.strip().lower(),
            )
            entry = grouped.setdefault(
                key,
                {
                    "title": title,
                    "kind": _document_hint(item),
                    "sections": [],
                    "comments": [],
                    "is_confirmed": bool(
                        item.get("document_name")
                        or item.get("document_registry_id")
                        or item.get("document_disk_path")
                    ),
                },
            )
            if section_name not in entry["sections"]:
                entry["sections"].append(section_name)
            comment = _document_reference_summary(item)
            if comment and comment not in entry["comments"]:
                entry["comments"].append(comment)
    result = []
    for entry in grouped.values():
        comments = entry["comments"]
        comment = comments[0] if comments else "Комментарий не указан."
        if len(comments) > 1:
            comment = f"{comment} (+ ещё {len(comments) - 1})"
        sections = entry["sections"]
        result.append(
            {
                "title": entry["title"],
                "kind": entry["kind"],
                "sections_label": f"Секции: {', '.join(sections)}",
                "comment": comment,
                "is_confirmed": entry["is_confirmed"],
                "status_label": "Подтверждено" if entry["is_confirmed"] else "Нужна проверка",
                "status_key": "ok" if entry["is_confirmed"] else "needs_review",
                "row_text": " ".join([entry["title"], entry["kind"], comment, ", ".join(sections)]).lower(),
            }
        )
    return sorted(result, key=lambda item: item["title"].lower())


def _render_section_document_rows(materials: list[Any]) -> str:
    rows = []
    for item in materials:
        is_confirmed = bool(
            item.get("document_name") or item.get("document_registry_id") or item.get("document_disk_path")
        )
        comment = _document_reference_summary(item)
        rows.append(
            f"<tr data-row-text=\"{html.escape((str(item.get('material_name') or item.get('document_name') or '') + ' ' + comment).lower())}\" data-status=\"{'ok' if is_confirmed else 'needs_review'}\">"
            f"<td><strong>{html.escape(item.get('material_name') or item.get('document_name') or 'Материал')}</strong></td>"
            f"<td>{html.escape(_document_hint(item))}</td>"
            f"<td><div class='preview'>{html.escape(comment)}</div></td>"
            f"<td><span class='status {'ok' if is_confirmed else 'alert'}'>{'Подтверждено' if is_confirmed else 'Нужна проверка'}</span></td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='4'>В этой секции документы не определены.</td></tr>"


def _safe_document_origin(item: dict[str, Any]) -> str:
    source_title = str(item.get("document_source_title") or "").strip()
    registry_id = str(item.get("document_registry_id") or "").strip()
    document_name = str(item.get("document_name") or item.get("material_name") or "Документ").strip()
    if source_title and registry_id:
        return f"{source_title}, реестр {registry_id}"
    if source_title:
        return source_title
    if registry_id:
        return f"Реестр {registry_id}"
    return f"Локальный документ: {document_name}"


def _document_reference_summary(item: dict[str, Any]) -> str:
    document_type = str(item.get("document_name") or "Документ").strip()
    document_number = str(item.get("document_number") or "").strip()
    document_date = str(item.get("document_date") or "").strip()
    parts = [document_type]
    if document_number and document_number not in document_type:
        parts.append(document_number)
    summary = " ".join(part for part in parts if part).strip()
    if document_date:
        if summary:
            summary += f" [от {document_date}]"
        else:
            summary = f"[от {document_date}]"
    return summary or "Реквизиты документа не указаны."
