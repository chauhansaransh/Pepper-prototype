from pathlib import Path
import re
from typing import Any, Dict, List, Optional

try:
    from chart_renderer import render_charts
    from data_extractor import extract_customer_data, filter_normalized_by_selection
    from html_renderer import markdown_to_html, render_html_report
    from llm_client import (
        generate_deliverables_status_pointers,
        generate_executive_table_insights,
        generate_template_narrative_report,
        generate_top_pages_pointers,
        generate_top_queries_pointers,
        generate_weekly_recommendations,
    )
    from report_context import build_report_context
    from report_templates import load_template, list_templates
    from pdf_renderer import render_pdf
    from pipeline import render_executive_snapshot_markdown, render_report_markdown
    from sources import (
        ContentfulSource,
        GA4Source,
        GSCSource,
        SemrushSource,
        WebflowSource,
        WordPressSource,
    )
except ImportError:
    from .chart_renderer import render_charts
    from .data_extractor import extract_customer_data, filter_normalized_by_selection
    from .html_renderer import markdown_to_html, render_html_report
    from .llm_client import (
        generate_deliverables_status_pointers,
        generate_executive_table_insights,
        generate_template_narrative_report,
        generate_top_pages_pointers,
        generate_top_queries_pointers,
        generate_weekly_recommendations,
    )
    from .report_context import build_report_context
    from .report_templates import load_template, list_templates
    from .pdf_renderer import render_pdf
    from .pipeline import (
        normalize_gsc_payload,
        render_executive_snapshot_markdown,
        render_report_markdown,
    )
    from .sources import (
        ContentfulSource,
        GA4Source,
        GSCSource,
        SemrushSource,
        WebflowSource,
        WordPressSource,
    )


ROOT_DIR = Path(__file__).resolve().parents[1]
GSC_MOCK_ROOT = ROOT_DIR / "data" / "mock_inputs" / "gsc"
GA4_MOCK_ROOT = ROOT_DIR / "data" / "mock_inputs" / "ga4"
SEMRUSH_MOCK_ROOT = ROOT_DIR / "data" / "mock_inputs" / "semrush"
CMS_MOCK_ROOT = ROOT_DIR / "data" / "mock_inputs" / "cms"
OUTPUT_DIR = ROOT_DIR / "outputs"
OUTPUT_FILE = OUTPUT_DIR / "sample_report.md"
OUTPUT_HTML = OUTPUT_DIR / "sample_report.html"
OUTPUT_PDF = OUTPUT_DIR / "sample_report.pdf"
CHARTS_DIR = OUTPUT_DIR / "charts"
GSC_SOURCE = GSCSource(GSC_MOCK_ROOT)
GA4_SOURCE = GA4Source(GA4_MOCK_ROOT)
SEMRUSH_SOURCE = SemrushSource(SEMRUSH_MOCK_ROOT)
WORDPRESS_SOURCE = WordPressSource(CMS_MOCK_ROOT)
WEBFLOW_SOURCE = WebflowSource(CMS_MOCK_ROOT)
CONTENTFUL_SOURCE = ContentfulSource(CMS_MOCK_ROOT)


def list_customers():
    return GSC_SOURCE.list_customers()


def _append_final_section(markdown: str, heading: str, section_body: str) -> str:
    """Append a section at the end of the report, or replace it if already present."""
    existing = _extract_markdown_section(markdown, heading)
    if existing is not None:
        return _upsert_markdown_section(markdown, heading, section_body)
    section = f"## {heading}\n{section_body.strip()}\n"
    return markdown.rstrip() + "\n\n" + section


def _upsert_markdown_section(markdown: str, heading: str, section_body: str) -> str:
    section = f"## {heading}\n{section_body.strip()}\n"
    pattern = re.compile(
        rf"(?ms)^##\s+{re.escape(heading)}\s*\n.*?(?=^##\s+|\Z)"
    )
    if pattern.search(markdown):
        return pattern.sub(section + "\n", markdown, count=1)
    insert_after_title = re.compile(r"(?ms)^# .+?\n")
    m = insert_after_title.search(markdown)
    if m:
        return markdown[: m.end()] + "\n" + section + "\n" + markdown[m.end() :]
    return section + "\n" + markdown


def _extract_markdown_section(markdown: str, heading: str) -> Optional[str]:
    pattern = re.compile(
        rf"(?ms)^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)"
    )
    match = pattern.search(markdown)
    if not match:
        return None
    body = match.group(1).strip()
    return body or None


MAX_BULLET_WORDS = 55
MAX_BULLET_CHARS = 360


def _normalize_bullet(line: str) -> str:
    """Ensure markdown bullet formatting without truncating substantive LLM output."""
    text = line.strip().lstrip("-").strip()
    if not text:
        return "- (No insight generated.)"
    words = text.split()
    if len(words) > MAX_BULLET_WORDS:
        text = " ".join(words[:MAX_BULLET_WORDS]).rstrip(",.") + "."
    if len(text) > MAX_BULLET_CHARS:
        text = text[: MAX_BULLET_CHARS - 1].rsplit(" ", 1)[0].rstrip(",.") + "."
    if text[-1] not in ".!?":
        text += "."
    return f"- {text}"


def _extract_bullets(markdown: str, max_items: int = 2) -> List[str]:
    bullets: List[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(_normalize_bullet(stripped))
        if len(bullets) >= max_items:
            break
    return bullets


def _append_to_section(markdown: str, heading: str, append_body: str) -> str:
    pattern = re.compile(
        rf"(?ms)^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)"
    )
    match = pattern.search(markdown)
    if not match:
        return markdown
    section_body = match.group(1).rstrip()
    updated = f"## {heading}\n{section_body}\n\n{append_body.strip()}\n"
    return pattern.sub(updated + "\n", markdown, count=1)


def _bullets_block(bullets: List[str]) -> str:
    return "\n".join(bullets)


def _section_has_pointer_bullets(markdown: str, section_heading: str) -> bool:
    section = _extract_section_markdown(markdown, section_heading) or ""
    remainder = section[len(_section_table_markdown(section)) :].strip()
    return any(line.strip().startswith("- ") for line in remainder.splitlines())


def _extract_insights_bullets_from_report(markdown: str) -> List[str]:
    """Collect pointer bullets from table sections (before Recommendations)."""
    rec_pos = markdown.find("## Recommendations")
    scope = markdown[:rec_pos] if rec_pos >= 0 else markdown
    return [
        line.strip()
        for line in scope.splitlines()
        if line.strip().startswith("- ")
    ]


def _section_table_markdown(section_body: str) -> str:
    """Table markdown only (strip appended ### subsections)."""
    return section_body.split("###")[0].strip()


def _fallback_executive_insights(report_context: Dict[str, Any]) -> List[str]:
    return ["- Fix the metric with the largest negative % vs last week first."]


def _fallback_top_pages_pointers(report_context: Dict[str, Any]) -> List[str]:
    gsc = report_context.get("gsc") or report_context.get("gscFiltered") or {}
    ga4 = report_context.get("ga4") or {}
    pages = gsc.get("topPages") or []
    landing = {
        p.get("pagePath"): p for p in (ga4.get("topLandingPages") or [])
    }
    if not pages:
        return ["- Review top landing pages once GSC page data is available."]
    top = pages[0]
    page = top.get("page", "N/A")
    clicks = int(top.get("clicks", 0))
    return [
        f"- Refresh `{page}` to protect {clicks:,} weekly clicks.",
        "- Fix high-bounce pages with stronger CTAs and internal links.",
    ]


def _fallback_weekly_recommendations(
    report_markdown: str, report_context: Dict[str, Any]
) -> List[str]:
    from_insights = [
        _normalize_bullet(b)
        for b in _extract_insights_bullets_from_report(report_markdown)
    ]
    if len(from_insights) >= 3:
        return from_insights[:4]

    url_rows = [
        row
        for row in (report_context.get("gscUrlInspection") or [])
        if str(row.get("verdict", "")).upper() != "PASS"
    ]
    recs = [
        "- Fix metrics with negative week-over-week trends first.",
        "- Refresh underperforming top pages and queries this week.",
    ]
    if url_rows:
        recs.append(
            f"- Re-submit {len(url_rows)} flagged URL(s) for indexing after fixes."
        )
    matrix = (report_context.get("semrush") or {}).get("keywordCompetitiveMatrix") or {}
    high_opp = [
        r
        for r in matrix.get("rows") or []
        if str(r.get("opportunity", "")).lower() == "high"
    ]
    if high_opp:
        recs.append("- Ship content updates for High-opportunity competitor keywords.")
    recs.append("- Boost AI visibility on your weakest platform this sprint.")
    return [_normalize_bullet(r) for r in recs[:4]]


def _fallback_top_queries_pointers(report_context: Dict[str, Any]) -> List[str]:
    gsc = report_context.get("gsc") or report_context.get("gscFiltered") or {}
    queries = gsc.get("topQueries") or []
    if not queries:
        return ["- Review top queries once Search Console data is available."]
    top = queries[0]
    q = top.get("query", "N/A")
    pos = float(top.get("position", 0.0))
    return [
        f"- Improve `{q}` content to move off position {pos:.0f}.",
        "- Test new titles on high-impression, low-CTR queries.",
    ]


def _fallback_deliverables_pointers(report_context: Dict[str, Any]) -> List[str]:
    wp = (report_context.get("wordpress") or {}).get("posts") or []
    wf = (report_context.get("webflow") or {}).get("items") or []
    cf = (report_context.get("contentful") or {}).get("entries") or []

    wp_published = sum(
        1 for p in wp if str(p.get("status", "")).lower() == "publish"
    )
    wf_published = sum(1 for i in wf if not i.get("isDraft"))
    cf_published = sum(1 for e in cf if e.get("publishDate"))
    coverage = sum(
        1
        for source_items in (wp, wf, cf)
        if len(source_items) > 0
    )
    return [
        f"- Publish pending items across {coverage}/3 CMS sources this week.",
        "- Align mixed ✓/✗ content rows across WordPress, Webflow, and Contentful.",
    ]


def _extract_section_markdown(markdown: str, heading: str) -> Optional[str]:
    pattern = re.compile(
        rf"(?ms)^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)"
    )
    match = pattern.search(markdown)
    if not match:
        return None
    body = match.group(1).strip()
    return body or None


def _to_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "").replace("%", "")
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text or text in {"-", ".", "-."}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _extract_markdown_tables(report_markdown: str) -> List[Dict[str, Any]]:
    lines = report_markdown.splitlines()
    tables: List[Dict[str, Any]] = []
    current_section = ""
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("## "):
            current_section = line[3:].strip()
            i += 1
            continue
        if line.startswith("|") and line.endswith("|") and i + 1 < len(lines):
            sep = lines[i + 1].strip()
            if sep.startswith("|") and sep.endswith("|"):
                header = [h.strip().lower() for h in line.strip("|").split("|")]
                if header:
                    rows: List[List[str]] = []
                    i += 2
                    while i < len(lines):
                        row_line = lines[i].strip()
                        if not (row_line.startswith("|") and row_line.endswith("|")):
                            break
                        rows.append([c.strip() for c in row_line.strip("|").split("|")])
                        i += 1
                    tables.append(
                        {
                            "section": current_section.lower(),
                            "headers": header,
                            "rows": rows,
                        }
                    )
                    continue
        i += 1
    return tables


def _column_index(headers: List[str], options: List[str]) -> int:
    for idx, header in enumerate(headers):
        if any(opt in header for opt in options):
            return idx
    return -1


def _build_chart_specs_from_markdown(report_markdown: str) -> Dict[str, Dict[str, Any]]:
    specs: Dict[str, Dict[str, Any]] = {}
    tables = _extract_markdown_tables(report_markdown)

    for table in tables:
        section = table["section"]
        headers = table["headers"]
        rows = table["rows"]

        if "top performing content" in section:
            page_idx = _column_index(headers, ["page"])
            clicks_idx = _column_index(headers, ["clicks"])
            sessions_idx = _column_index(headers, ["sessions"])
            if page_idx >= 0 and clicks_idx >= 0:
                labels, values = [], []
                for row in rows:
                    if max(page_idx, clicks_idx) >= len(row):
                        continue
                    n = _to_number(row[clicks_idx])
                    if n is None:
                        continue
                    labels.append(row[page_idx])
                    values.append(int(n))
                if labels:
                    specs["top_pages"] = {
                        "id": "top_pages",
                        "title": "Top Pages by Clicks",
                        "type": "bar",
                        "xLabel": "Page",
                        "yLabel": "Clicks",
                        "labels": labels[:5],
                        "values": values[:5],
                    }
            if page_idx >= 0 and sessions_idx >= 0:
                labels, values = [], []
                for row in rows:
                    if max(page_idx, sessions_idx) >= len(row):
                        continue
                    n = _to_number(row[sessions_idx])
                    if n is None:
                        continue
                    labels.append(row[page_idx])
                    values.append(int(n))
                if labels:
                    specs["ga4_top_landing_pages"] = {
                        "id": "ga4_top_landing_pages",
                        "title": "GA4 Top Landing Pages by Sessions",
                        "type": "bar",
                        "xLabel": "Landing Page",
                        "yLabel": "Sessions",
                        "labels": labels[:5],
                        "values": values[:5],
                    }

        if "top query changes" in section:
            query_idx = _column_index(headers, ["query"])
            clicks_idx = _column_index(headers, ["clicks"])
            if query_idx >= 0 and clicks_idx >= 0:
                labels, values = [], []
                for row in rows:
                    if max(query_idx, clicks_idx) >= len(row):
                        continue
                    n = _to_number(row[clicks_idx])
                    if n is None:
                        continue
                    labels.append(row[query_idx])
                    values.append(int(n))
                if labels:
                    existing = specs.get("top_queries")
                    if existing:
                        existing["labels"].extend(labels)
                        existing["values"].extend(values)
                    else:
                        specs["top_queries"] = {
                            "id": "top_queries",
                            "title": "Top Queries by Clicks",
                            "type": "bar",
                            "xLabel": "Query",
                            "yLabel": "Clicks",
                            "labels": labels,
                            "values": values,
                        }

        if "competitor highlights" in section:
            comp_idx = _column_index(headers, ["competitor"])
            auth_idx = _column_index(headers, ["authority"])
            if comp_idx >= 0 and auth_idx >= 0:
                labels, values = [], []
                for row in rows:
                    if max(comp_idx, auth_idx) >= len(row):
                        continue
                    n = _to_number(row[auth_idx])
                    if n is None:
                        continue
                    labels.append(row[comp_idx])
                    values.append(int(n))
                if labels:
                    specs["semrush_competitor_authority"] = {
                        "id": "semrush_competitor_authority",
                        "title": "Semrush Competitor Authority Score",
                        "type": "bar",
                        "xLabel": "Competitor",
                        "yLabel": "Authority Score",
                        "labels": labels[:5],
                        "values": values[:5],
                    }

        if "geo / ai visibility signals" in section:
            platform_idx = _column_index(headers, ["platform"])
            visibility_idx = _column_index(headers, ["visibility share"])
            mentions_idx = _column_index(headers, ["mentions"])
            metric_idx = visibility_idx if visibility_idx >= 0 else mentions_idx
            if platform_idx >= 0 and metric_idx >= 0:
                labels, values = [], []
                for row in rows:
                    if max(platform_idx, metric_idx) >= len(row):
                        continue
                    n = _to_number(row[metric_idx])
                    if n is None:
                        continue
                    labels.append(row[platform_idx])
                    values.append(float(n))
                if labels:
                    specs["ai_visibility_by_platform"] = {
                        "id": "ai_visibility_by_platform",
                        "title": "AI Visibility Share by Platform",
                        "type": "doughnut",
                        "labels": labels[:5],
                        "values": values[:5],
                    }

    top_queries = specs.get("top_queries")
    if top_queries:
        merged = list(zip(top_queries["labels"], top_queries["values"]))
        merged = sorted(merged, key=lambda x: x[1], reverse=True)[:5]
        top_queries["labels"] = [m[0] for m in merged]
        top_queries["values"] = [m[1] for m in merged]

    # Deliverables section is list-based, derive counts from bullets if present.
    wp_count = len(
        re.findall(r"^\s*-\s.*$", report_markdown, flags=re.MULTILINE)
    )
    if wp_count > 0 and "cms_content_counts" not in specs:
        specs["cms_content_counts"] = {
            "id": "cms_content_counts",
            "title": "Published Content by CMS Source",
            "type": "pie",
            "labels": ["Published Items"],
            "values": [wp_count],
        }

    return specs


def _spec_has_values(spec: Dict[str, Any]) -> bool:
    values = spec.get("values") or []
    for v in values:
        try:
            if v is not None and float(v) != 0.0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _merge_chart_specs(
    context_specs: List[Dict[str, Any]], markdown_specs: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for spec in context_specs:
        sid = spec.get("id")
        md_spec = markdown_specs.get(sid or "")
        if (not _spec_has_values(spec)) and md_spec:
            merged.append(md_spec)
        else:
            merged.append(spec)
    existing_ids = {spec.get("id") for spec in merged}
    for sid, spec in markdown_specs.items():
        if sid not in existing_ids:
            merged.append(spec)
    return merged


def _build_chart_specs(report_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    gsc = report_context.get("gsc") or report_context.get("gscFiltered") or {}
    ga4 = report_context.get("ga4") or {}
    semrush = report_context.get("semrush") or {}
    semrush_ai = report_context.get("semrushAi") or {}
    wordpress = report_context.get("wordpress") or {}
    webflow = report_context.get("webflow") or {}
    contentful = report_context.get("contentful") or {}

    top_queries = gsc.get("topQueries") or []
    if top_queries:
        specs.append(
            {
                "id": "top_queries",
                "title": "Top Queries by Clicks",
                "type": "bar",
                "xLabel": "Query",
                "yLabel": "Clicks",
                "labels": [q.get("query", "N/A") for q in top_queries[:5]],
                "values": [int(q.get("clicks", 0)) for q in top_queries[:5]],
            }
        )

    top_pages = gsc.get("topPages") or []
    if top_pages:
        specs.append(
            {
                "id": "top_pages",
                "title": "Top Pages by Clicks",
                "type": "bar",
                "xLabel": "Page",
                "yLabel": "Clicks",
                "labels": [p.get("page", "N/A") for p in top_pages[:5]],
                "values": [int(p.get("clicks", 0)) for p in top_pages[:5]],
            }
        )

    top_landing = ga4.get("topLandingPages") or []
    if top_landing:
        specs.append(
            {
                "id": "ga4_top_landing_pages",
                "title": "GA4 Top Landing Pages by Sessions",
                "type": "bar",
                "xLabel": "Landing Page",
                "yLabel": "Sessions",
                "labels": [p.get("pagePath", "N/A") for p in top_landing[:5]],
                "values": [int(p.get("sessions", 0)) for p in top_landing[:5]],
            }
        )

    competitors = semrush.get("competitorSummaries") or []
    if competitors:
        specs.append(
            {
                "id": "semrush_competitor_authority",
                "title": "Semrush Competitor Authority Score",
                "type": "bar",
                "xLabel": "Competitor",
                "yLabel": "Authority Score",
                "labels": [
                    c.get("label") or c.get("domain", "N/A") for c in competitors[:5]
                ],
                "values": [int(c.get("authorityScore", 0)) for c in competitors[:5]],
            }
        )

    llm_rows = (semrush_ai.get("visibilityOverview") or {}).get("byLlm") or []
    if llm_rows:
        specs.append(
            {
                "id": "ai_visibility_by_platform",
                "title": "AI Visibility Share by Platform",
                "type": "doughnut",
                "labels": [r.get("platform", "N/A") for r in llm_rows[:5]],
                "values": [
                    int(float(r.get("visibilityShare", r.get("mentions", 0))))
                    for r in llm_rows[:5]
                ],
            }
        )

    cms_counts = [
        ("WordPress", len(wordpress.get("items") or [])),
        ("Webflow", len(webflow.get("items") or [])),
        ("Contentful", len(contentful.get("items") or [])),
    ]
    cms_counts = [item for item in cms_counts if item[1] > 0]
    if cms_counts:
        specs.append(
            {
                "id": "cms_content_counts",
                "title": "Published Content by CMS Source",
                "type": "pie",
                "labels": [name for name, _ in cms_counts],
                "values": [count for _, count in cms_counts],
            }
        )

    return specs


def gsc_search_analytics_query(
    customer_id: str, dimensions: Optional[str] = None
) -> Dict[str, Any]:
    _resolve_customer(customer_id)
    dim_list: Optional[List[str]] = None
    if dimensions == "query":
        dim_list = ["query"]
    elif dimensions == "page":
        dim_list = ["page"]
    elif dimensions in (None, "", "property"):
        dim_list = []
    else:
        raise ValueError(
            f"Unsupported dimensions '{dimensions}'. Use query, page, or omit for property totals."
        )
    return GSC_SOURCE.search_analytics_query(customer_id, dimensions=dim_list)


def gsc_url_inspection(customer_id: str, inspection_url: str) -> Dict[str, Any]:
    _resolve_customer(customer_id)
    if not inspection_url:
        raise ValueError("url query parameter is required.")
    return GSC_SOURCE.get_url_inspection(customer_id, inspection_url)


def ga4_run_report(customer_id: str, report_key: str) -> Dict[str, Any]:
    _resolve_customer(customer_id)
    if not report_key:
        raise ValueError("report query parameter is required.")
    return GA4_SOURCE.run_report(customer_id, report_key)


def semrush_fetch_report(
    customer_id: str,
    report_type: str,
    domain: Optional[str] = None,
    phrase: Optional[str] = None,
) -> Dict[str, Any]:
    _resolve_customer(customer_id)
    if not report_type:
        raise ValueError("type query parameter is required.")
    return SEMRUSH_SOURCE.fetch_report(
        customer_id, report_type, domain=domain, phrase=phrase
    )


def semrush_ai_fetch_report(customer_id: str, report_type: str) -> Dict[str, Any]:
    _resolve_customer(customer_id)
    if not report_type:
        raise ValueError("type query parameter is required.")
    return SEMRUSH_SOURCE.fetch_ai_report(customer_id, report_type)


def wordpress_list_posts(customer_id: str) -> Dict[str, Any]:
    _resolve_customer(customer_id)
    return WORDPRESS_SOURCE.list_posts(customer_id)


def webflow_list_items(customer_id: str) -> Dict[str, Any]:
    _resolve_customer(customer_id)
    return WEBFLOW_SOURCE.list_live_items(customer_id)


def contentful_list_entries(customer_id: str) -> Dict[str, Any]:
    _resolve_customer(customer_id)
    return CONTENTFUL_SOURCE.list_entries(customer_id)


def _resolve_customer(customer_id: str) -> Dict[str, str]:
    customer_map = {c["id"]: c["name"] for c in GSC_SOURCE.list_customers()}
    if customer_id not in customer_map:
        raise ValueError(f"Unknown customer '{customer_id}'.")
    return {"id": customer_id, "name": customer_map[customer_id]}


def list_report_templates() -> List[Dict[str, Any]]:
    return [t.to_metadata() for t in list_templates()]


def get_report_template(template_id: str) -> Dict[str, Any]:
    return load_template(template_id).to_dict()


def extract_for_customer(customer_id: str) -> Dict[str, Any]:
    _resolve_customer(customer_id)
    data = extract_customer_data(
        customer_id,
        GSC_SOURCE,
        GA4_SOURCE,
        SEMRUSH_SOURCE,
        WORDPRESS_SOURCE,
        WEBFLOW_SOURCE,
        CONTENTFUL_SOURCE,
    )
    # Do not expose full normalized in API response (large); client gets items only
    return {
        "customerId": data["customerId"],
        "sources": data["sources"],
        "items": data["items"],
        "reportOutline": data["reportOutline"],
    }


def generate_report_draft(
    customer_id: str,
    report_type: str,
    instructions: str,
    included_item_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    customer = _resolve_customer(customer_id)
    template = load_template(report_type)
    report_context = build_report_context(
        customer_id,
        template,
        GSC_SOURCE,
        GA4_SOURCE,
        SEMRUSH_SOURCE,
        WORDPRESS_SOURCE,
        WEBFLOW_SOURCE,
        CONTENTFUL_SOURCE,
    )

    if included_item_ids:
        report_context["selectedItemIds"] = included_item_ids
        gsc_full = report_context.get("gsc") or {}
        report_context["gscFiltered"] = filter_normalized_by_selection(
            gsc_full, included_item_ids
        )

    display_report_type = template.label

    charts: List[Dict[str, str]] = []
    fallback_markdown = render_report_markdown(
        customer_name=customer["name"],
        report_type=display_report_type,
        instructions=instructions,
        report_context=report_context,
        cadence=template.id,
    )

    report_markdown = fallback_markdown
    llm_error = None
    llm_provider = "none"
    used_llm = False

    llm_focus_instruction = (
        (instructions.strip() + "\n\n" if instructions.strip() else "")
        + "Generate only two sections with exactly these headings: "
        + "'## Insights' and '## Recommendations'. "
        + "Use 4-6 substantive bullets per section (1-2 sentences each). "
        + "Cite specific metrics, pages, queries, or URLs from the provided data. "
        + "Do not invent numbers or trends."
    )
    if template.id == "weekly":
        pointer_instruction_suffix = (
            "Each insight must be 1-2 sentences, cite specific values from that section's table, "
            "and include a clear next step. Do not invent data."
        )
        base_pointer_instruction = (
            (instructions.strip() + "\n\n" if instructions.strip() else "")
            + pointer_instruction_suffix
        )

        def _append_table_pointers(
            section_heading: str,
            table_markdown: str,
            generate_fn: Any,
            table_kwarg: str,
            fallback_fn: Any,
        ) -> None:
            nonlocal report_markdown, llm_error, llm_provider, used_llm
            if _section_has_pointer_bullets(report_markdown, section_heading):
                return
            bullets: List[str] = []
            if table_markdown:
                llm_out, err, provider = generate_fn(
                    customer_name=customer["name"],
                    report_type=display_report_type,
                    instructions=base_pointer_instruction,
                    **{table_kwarg: table_markdown},
                )
                if llm_out:
                    bullets = _extract_bullets(llm_out, max_items=2)
                    if bullets:
                        used_llm = True
                        llm_provider = provider or llm_provider
                if err and not llm_error:
                    llm_error = err
            if not bullets:
                bullets = fallback_fn(report_context)
            if bullets:
                report_markdown = _append_to_section(
                    report_markdown,
                    section_heading,
                    _bullets_block(bullets),
                )

        executive_table = _section_table_markdown(
            _extract_section_markdown(report_markdown, "Executive Summary") or ""
        )
        _append_table_pointers(
            "Executive Summary",
            executive_table,
            generate_executive_table_insights,
            "executive_table_markdown",
            _fallback_executive_insights,
        )

        deliverables_table = _section_table_markdown(
            _extract_section_markdown(report_markdown, "Deliverables") or ""
        )
        _append_table_pointers(
            "Deliverables",
            deliverables_table,
            generate_deliverables_status_pointers,
            "deliverables_table_markdown",
            _fallback_deliverables_pointers,
        )

        top_pages_table = _section_table_markdown(
            _extract_section_markdown(report_markdown, "Top Pages") or ""
        )
        _append_table_pointers(
            "Top Pages",
            top_pages_table,
            generate_top_pages_pointers,
            "top_pages_table_markdown",
            _fallback_top_pages_pointers,
        )

        top_queries_table = _section_table_markdown(
            _extract_section_markdown(report_markdown, "Top Queries") or ""
        )
        _append_table_pointers(
            "Top Queries",
            top_queries_table,
            generate_top_queries_pointers,
            "top_queries_table_markdown",
            _fallback_top_queries_pointers,
        )

        recommendations_instruction = (
            (instructions.strip() + "\n\n" if instructions.strip() else "")
            + "Each recommendation must be 1-2 sentences, grounded in the weekly report tables, "
            + "and cite specific metrics, pages, queries, competitors, or URLs where possible."
        )
        llm_recommendations, rec_llm_error, rec_llm_provider = (
            generate_weekly_recommendations(
                customer_name=customer["name"],
                report_type=display_report_type,
                report_markdown=report_markdown,
                instructions=recommendations_instruction,
            )
        )
        recommendation_bullets: List[str] = []
        if llm_recommendations:
            recommendation_bullets = _extract_bullets(
                llm_recommendations, max_items=4
            )
            if recommendation_bullets:
                used_llm = True
                llm_provider = rec_llm_provider or llm_provider
        if rec_llm_error and not llm_error:
            llm_error = rec_llm_error
        if not recommendation_bullets:
            recommendation_bullets = _fallback_weekly_recommendations(
                report_markdown, report_context
            )
        recommendations_body = "\n".join(recommendation_bullets)
        report_markdown = _append_final_section(
            report_markdown, "Recommendations", recommendations_body
        )

    else:
        llm_narrative, llm_error, llm_provider = generate_template_narrative_report(
            customer_name=customer["name"],
            template=report_context["template"],
            report_context=report_context,
            instructions=llm_focus_instruction,
        )
        if llm_narrative:
            insights_body = _extract_markdown_section(llm_narrative, "Insights")
            recommendations_body = _extract_markdown_section(llm_narrative, "Recommendations")
            if insights_body:
                report_markdown = _upsert_markdown_section(
                    report_markdown, "Insights", insights_body
                )
                used_llm = True
            if recommendations_body:
                report_markdown = _upsert_markdown_section(
                    report_markdown, "Recommendations", recommendations_body
                )
                used_llm = True

    narrative_html = markdown_to_html(report_markdown)
    report_html = render_html_report(
        customer_name=customer["name"],
        report_type=display_report_type,
        narrative_html=narrative_html,
        charts=[{"id": c["id"], "title": c["title"], "filename": c["filename"]} for c in charts],
        date_range=(report_context.get("gsc") or {}).get("dateRange", template.period_label),
        used_llm=used_llm,
        llm_provider=llm_provider,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(report_markdown, encoding="utf-8")
    OUTPUT_HTML.write_text(report_html, encoding="utf-8")

    return {
        "reportMarkdown": report_markdown,
        "reportHtml": report_html,
        "charts": [
            {"id": c["id"], "title": c["title"], "filename": c["filename"]}
            for c in charts
        ],
        "usedLlm": used_llm,
        "llmError": llm_error,
        "llmProvider": llm_provider,
        "customerId": customer_id,
        "customerName": customer["name"],
        "reportType": template.id,
        "reportTypeLabel": display_report_type,
        "templateId": template.id,
        "sourcesUsed": template.sources,
        "dataSourcesUsed": template.data_sources,
    }


def generate_report(customer_id: str, report_type: str, instructions: str) -> str:
    """Backward-compatible markdown-only helper."""
    result = generate_report_draft(customer_id, report_type, instructions)
    return result["reportMarkdown"]


def export_report_pdf(
    report_markdown: str,
    customer_name: str,
    report_type: str,
    chart_filenames: Optional[List[str]] = None,
) -> bytes:
    chart_paths: List[Path] = []
    if chart_filenames:
        for filename in chart_filenames:
            path = CHARTS_DIR / filename
            if path.exists():
                chart_paths.append(path)

    pdf_bytes = render_pdf(
        report_markdown=report_markdown,
        customer_name=customer_name,
        report_type=report_type,
        chart_paths=chart_paths,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PDF.write_bytes(pdf_bytes)
    return pdf_bytes
