from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from chart_renderer import render_charts
    from data_extractor import extract_customer_data, filter_normalized_by_selection
    from html_renderer import markdown_to_html, render_html_report
    from llm_client import generate_template_narrative_report
    from report_context import build_report_context
    from report_templates import load_template, list_templates
    from pdf_renderer import render_pdf
    from pipeline import render_report_markdown
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
    from .llm_client import generate_template_narrative_report
    from .report_context import build_report_context
    from .report_templates import load_template, list_templates
    from .pdf_renderer import render_pdf
    from .pipeline import normalize_gsc_payload, render_report_markdown
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

    charts = render_charts(customer_id, report_context, CHARTS_DIR)
    fallback_markdown = render_report_markdown(
        customer_name=customer["name"],
        report_type=display_report_type,
        instructions=instructions,
        report_context=report_context,
    )

    narrative, llm_error, llm_provider = generate_template_narrative_report(
        customer_name=customer["name"],
        template=report_context["template"],
        report_context=report_context,
        instructions=instructions,
    )

    used_llm = narrative is not None
    if used_llm:
        report_markdown = f"# {display_report_type} — {customer['name']}\n\n{narrative}\n"
    else:
        report_markdown = fallback_markdown

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
