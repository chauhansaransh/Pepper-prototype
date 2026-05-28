import html
import json
import re
from typing import Any, Dict, List, Tuple


def _format_inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*\*([^*]+)\*\*\*", r"<strong><em>\1</em></strong>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def _format_table_cell(text: str) -> str:
    raw = text.strip()
    rendered = _format_inline_markdown(raw)
    if raw.startswith("↑ "):
        return f'<span class="trend-up">{rendered}</span>'
    if raw.startswith("↓ "):
        return f'<span class="trend-down">{rendered}</span>'
    if raw.startswith("→ "):
        return f'<span class="trend-flat">{rendered}</span>'
    return rendered


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    parts: List[str] = []
    in_list = False
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        if not line:
            if in_list:
                parts.append("</ul>")
                in_list = False
            i += 1
            continue

        # Markdown table support:
        # | col | col |
        # | --- | --- |
        # | ... | ... |
        if line.startswith("|") and line.endswith("|") and i + 1 < len(lines):
            sep_line = lines[i + 1].strip()
            is_separator = (
                sep_line.startswith("|")
                and sep_line.endswith("|")
                and all(
                    set(cell.strip()) <= {"-", ":"}
                    for cell in sep_line.strip("|").split("|")
                    if cell.strip()
                )
            )
            if is_separator:
                if in_list:
                    parts.append("</ul>")
                    in_list = False
                header_cells = [
                    _format_inline_markdown(cell.strip())
                    for cell in line.strip("|").split("|")
                ]
                parts.append('<table class="md-table">')
                parts.append(
                    "<thead><tr>"
                    + "".join(f"<th>{cell}</th>" for cell in header_cells)
                    + "</tr></thead>"
                )
                parts.append("<tbody>")
                i += 2
                while i < len(lines):
                    row_line = lines[i].strip()
                    if not (row_line.startswith("|") and row_line.endswith("|")):
                        break
                    row_cells = [
                        _format_table_cell(cell.strip())
                        for cell in row_line.strip("|").split("|")
                    ]
                    parts.append(
                        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row_cells) + "</tr>"
                    )
                    i += 1
                parts.append("</tbody></table>")
                continue

        if line.startswith("### "):
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("- "):
            if not in_list:
                parts.append("<ul>")
                in_list = True
            text = _format_inline_markdown(line[2:])
            parts.append(f"<li>{text}</li>")
        else:
            if in_list:
                parts.append("</ul>")
                in_list = False
            text = _format_inline_markdown(line)
            parts.append(f"<p>{text}</p>")
        i += 1

    if in_list:
        parts.append("</ul>")
    return "\n".join(parts)


def render_html_report(
    customer_name: str,
    report_type: str,
    narrative_html: str,
    charts: List[Dict[str, str]],
    date_range: str,
    used_llm: bool,
    llm_provider: str = "none",
) -> str:
    chart_html_by_id = {
        c.get("id", ""): _build_chart_block(c) for c in charts
    }
    narrative_with_charts, unmatched = _inject_charts_into_narrative(
        narrative_html, chart_html_by_id
    )
    trailing_blocks = "".join(
        chart_html_by_id[cid] for cid in unmatched if cid in chart_html_by_id
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(report_type)} — {html.escape(customer_name)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
    rel="stylesheet"
  />
  <link rel="stylesheet" href="/report.css" />
</head>
<body class="report-body">
  <header class="report-hero">
    <div class="report-brand-row">
      <img src="/assets/peppercontent_logo.jpeg" alt="" class="report-logo" />
      <h1>{html.escape(report_type)}</h1>
      <p class="report-meta">{html.escape(customer_name)} · {html.escape(date_range)}</p>
    </div>
  </header>
  <main class="report-content">
    <section class="narrative">{narrative_with_charts}</section>
    {f'<section class="charts-section"><h2>Additional Visuals</h2><div class="chart-grid chart-grid-overview">{trailing_blocks}</div></section>' if trailing_blocks else ''}
  </main>
  <footer class="report-footer">Generated by Pepper AI Builder · For customer sharing after CSM review</footer>
</body>
</html>
"""


def _build_chart_block(chart: Dict[str, str]) -> str:
    src = f"/outputs/charts/{chart['filename']}"
    return f"""
    <figure class="chart-card">
      <img src="{html.escape(src)}" alt="{html.escape(chart.get('title', 'Chart'))}" />
      <figcaption>{html.escape(chart.get('title', ''))}</figcaption>
    </figure>
    """


def _chart_section_keywords(chart_id: str) -> List[str]:
    if chart_id.startswith("gsc_period_comparison_"):
        return ["gsc period comparison", "gsc", "search console", "kpi snapshot"]
    if chart_id.startswith("ga4_period_comparison_"):
        return ["ga4 period comparison", "ga4", "landing pages", "engagement"]
    if chart_id.startswith("semrush_ai_period_comparison_"):
        return ["semrush ai period comparison", "ai visibility", "ai"]
    if chart_id.startswith("semrush_period_comparison_"):
        return ["semrush period comparison", "semrush", "competitor"]

    mapping = {
        "kpi_summary": ["kpi", "executive snapshot", "kpi overview", "summary"],
        "top_queries": ["query", "keyword"],
        "top_pages": ["top pages", "content", "performing content"],
        "ga4_top_landing_pages": ["landing", "content", "engagement"],
        "semrush_competitor_authority": ["competitor", "competitive"],
        "ai_visibility_by_platform": ["geo", "ai visibility", "ai search", "visibility"],
        "cms_content_counts": ["deliverables", "content footprint", "published content", "content"],
    }
    return mapping.get(chart_id, [])


def _inject_charts_into_narrative(
    narrative_html: str, chart_html_by_id: Dict[str, str]
) -> Tuple[str, List[str]]:
    heading_pattern = re.compile(r"<h2>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
    matches = list(heading_pattern.finditer(narrative_html))
    if not matches:
        return narrative_html, list(chart_html_by_id.keys())

    headings = [html.unescape(m.group(1)).strip().lower() for m in matches]
    used_ids: set = set()
    insertion_at: Dict[int, List[str]] = {}

    for chart_id in chart_html_by_id.keys():
        keywords = _chart_section_keywords(chart_id)
        if not keywords:
            continue
        for idx, heading in enumerate(headings):
            if any(k in heading for k in keywords):
                insertion_at.setdefault(idx, []).append(chart_html_by_id[chart_id])
                used_ids.add(chart_id)
                break

    out_parts: List[str] = []
    cursor = 0
    for idx, match in enumerate(matches):
        start, end = match.span()
        out_parts.append(narrative_html[cursor:end])
        for block in insertion_at.get(idx, []):
            out_parts.append(block)
        cursor = end
    out_parts.append(narrative_html[cursor:])

    unmatched = [cid for cid in chart_html_by_id.keys() if cid not in used_ids]
    return "".join(out_parts), unmatched
