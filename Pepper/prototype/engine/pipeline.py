from typing import Any, Dict, List


def normalize_gsc_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    totals = payload.get("totals", {})
    return {
        "dateRange": payload.get("dateRange", "Unknown date range"),
        "totals": {
            "clicks": int(totals.get("clicks", 0)),
            "impressions": int(totals.get("impressions", 0)),
            "ctr": float(totals.get("ctr", 0.0)),
            "position": float(totals.get("position", 0.0)),
        },
        "topQueries": payload.get("topQueries", [])[:3],
        "topPages": payload.get("topPages", [])[:3],
    }


def build_highlights(normalized: Dict[str, Any]) -> List[str]:
    totals = normalized["totals"]
    highlights: List[str] = []
    if "clicks" in totals:
        highlights.append(
            f"Organic clicks reached {totals['clicks']:,} for {normalized['dateRange']}."
        )
    if "ctr" in totals and "impressions" in totals:
        highlights.append(
            f"Average CTR is {totals['ctr'] * 100:.2f}% across {totals['impressions']:,} impressions."
        )
    if "position" not in totals:
        return highlights
    if totals["position"] <= 10:
        highlights.append(
            f"Average position is {totals['position']:.1f}, indicating strong first-page visibility."
        )
    else:
        highlights.append(
            f"Average position is {totals['position']:.1f}; there is room to improve ranking depth."
        )
    return highlights


def _render_table(headers: List[str], rows: List[List[str]]) -> str:
    if not rows:
        return "- No data available."
    header_row = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return "\n".join([header_row, divider, body])


def render_report_markdown(
    customer_name: str,
    report_type: str,
    instructions: str,
    report_context: Dict[str, Any],
) -> str:
    # Backward-compatible path for legacy callers that pass raw GSC normalized payload.
    if "totals" in report_context and "gsc" not in report_context:
        report_context = {"gsc": report_context}

    gsc = report_context.get("gsc") or report_context.get("gscFiltered") or {}
    ga4 = report_context.get("ga4") or {}
    semrush = report_context.get("semrush") or {}
    semrush_ai = report_context.get("semrushAi") or {}
    wordpress = report_context.get("wordpress") or {}
    webflow = report_context.get("webflow") or {}
    contentful = report_context.get("contentful") or {}
    url_inspection = report_context.get("gscUrlInspection") or []

    totals = gsc.get("totals", {})
    highlights = build_highlights(gsc) if gsc else []

    query_lines = "\n".join(
        [
            f"- `{q.get('query', 'N/A')}`: {int(q.get('clicks', 0)):,} clicks, "
            f"{int(q.get('impressions', 0)):,} impressions, "
            f"{float(q.get('ctr', 0.0)) * 100:.2f}% CTR, pos {float(q.get('position', 0.0)):.1f}"
            for q in gsc.get("topQueries", [])
        ]
    )
    page_lines = "\n".join(
        [
            f"- `{p.get('page', 'N/A')}`: {int(p.get('clicks', 0)):,} clicks, "
            f"{int(p.get('impressions', 0)):,} impressions, "
            f"{float(p.get('ctr', 0.0)) * 100:.2f}% CTR, pos {float(p.get('position', 0.0)):.1f}"
            for p in gsc.get("topPages", [])
        ]
    )

    safe_instructions = instructions.strip() or "No additional instructions provided."
    highlight_lines = "\n".join([f"- {h}" for h in highlights]) if highlights else "- No highlights available."

    kpi_lines = []
    if "clicks" in totals:
        kpi_lines.append(f"- Clicks: {totals['clicks']:,}")
    if "impressions" in totals:
        kpi_lines.append(f"- Impressions: {totals['impressions']:,}")
    if "ctr" in totals:
        kpi_lines.append(f"- CTR: {totals['ctr'] * 100:.2f}%")
    if "position" in totals:
        kpi_lines.append(f"- Average Position: {totals['position']:.1f}")
    kpi_block = "\n".join(kpi_lines) if kpi_lines else "- No KPI metrics selected."

    ga4_totals = ga4.get("totals", {})
    ga4_kpis = []
    if "sessions" in ga4_totals:
        ga4_kpis.append(f"- Sessions: {int(ga4_totals['sessions']):,}")
    if "activeUsers" in ga4_totals:
        ga4_kpis.append(f"- Active Users: {int(ga4_totals['activeUsers']):,}")
    if "engagementRate" in ga4_totals:
        ga4_kpis.append(f"- Engagement Rate: {float(ga4_totals['engagementRate']) * 100:.2f}%")
    if "conversions" in ga4_totals:
        ga4_kpis.append(f"- Conversions: {int(ga4_totals['conversions']):,}")
    ga4_kpi_block = "\n".join(ga4_kpis) if ga4_kpis else "- No GA4 metrics selected."

    semrush_backlinks = semrush.get("customerBacklinks") or {}
    semrush_kpis = []
    if semrush_backlinks.get("authorityScore") is not None:
        semrush_kpis.append(f"- Authority Score: {int(semrush_backlinks.get('authorityScore', 0))}")
    if semrush_backlinks.get("totalBacklinks") is not None:
        semrush_kpis.append(
            f"- Total Backlinks: {int(semrush_backlinks.get('totalBacklinks', 0)):,}"
        )
    if semrush_backlinks.get("referringDomains") is not None:
        semrush_kpis.append(
            f"- Referring Domains: {int(semrush_backlinks.get('referringDomains', 0)):,}"
        )
    semrush_kpi_block = "\n".join(semrush_kpis) if semrush_kpis else "- No Semrush KPI metrics selected."

    visibility = semrush_ai.get("visibilityOverview") or {}
    ai_kpis = []
    if visibility.get("visibilityScore") is not None:
        ai_kpis.append(f"- AI Visibility Score: {int(visibility.get('visibilityScore', 0))}")
    if visibility.get("mentions") is not None:
        ai_kpis.append(f"- Mentions: {int(visibility.get('mentions', 0)):,}")
    if visibility.get("citations") is not None:
        ai_kpis.append(f"- Citations: {int(visibility.get('citations', 0)):,}")
    ai_kpi_block = "\n".join(ai_kpis) if ai_kpis else "- No Semrush AI metrics selected."

    top_landing_pages = ga4.get("topLandingPages") or []
    ga4_pages_table = _render_table(
        ["Page", "Sessions", "Active Users", "Bounce Rate"],
        [
            [
                p.get("pagePath", "N/A"),
                f"{int(p.get('sessions', 0)):,}",
                f"{int(p.get('activeUsers', 0)):,}",
                f"{float(p.get('bounceRate', 0.0)) * 100:.1f}%",
            ]
            for p in top_landing_pages[:5]
        ],
    )

    competitor_table = _render_table(
        ["Competitor", "Authority", "Backlinks"],
        [
            [
                c.get("label") or c.get("domain", "N/A"),
                str(int(c.get("authorityScore", 0))),
                f"{int(c.get('totalBacklinks', 0)):,}",
            ]
            for c in (semrush.get("competitorSummaries") or [])[:5]
        ],
    )

    ai_citation_table = _render_table(
        ["URL", "Citation Count", "Avg Position"],
        [
            [
                row.get("url", "N/A"),
                str(int(row.get("citationCount", 0))),
                f"{float(row.get('avgCitationPosition', 0.0)):.1f}",
            ]
            for row in (semrush_ai.get("citationTracking") or [])[:5]
        ],
    )

    cms_counts = [
        f"- WordPress posts: {len(wordpress.get('items') or []):,}",
        f"- Webflow items: {len(webflow.get('items') or []):,}",
        f"- Contentful entries: {len(contentful.get('items') or []):,}",
    ]
    cms_count_block = "\n".join(cms_counts)

    indexing_table = _render_table(
        ["URL", "Issue", "Severity", "Recommendation"],
        [
            [
                row.get("url", "N/A"),
                row.get("issue") or "None",
                row.get("severity", "none"),
                row.get("recommendation") or "No action needed.",
            ]
            for row in url_inspection[:10]
        ],
    )

    date_range = (
        gsc.get("dateRange")
        or ga4.get("dateRange")
        or semrush.get("dateRange")
        or semrush_ai.get("dateRange")
        or "Unknown date range"
    )

    return f"""# {report_type} Report - {customer_name}

## Report Context
- Data sources: GSC, GA4, Semrush, Semrush AI, CMS (as available)
- Date range: {date_range}
- CSM instructions: {safe_instructions}

## GSC KPI Snapshot
{kpi_block}

## GSC Highlights
{highlight_lines}

## Top Queries
{query_lines if query_lines else '- No query data available.'}

## Top Pages
{page_lines if page_lines else '- No page data available.'}

## GA4 KPI Snapshot
{ga4_kpi_block}

## Top Landing Pages (GA4)
{ga4_pages_table}

## Semrush KPI Snapshot
{semrush_kpi_block}

## Competitor Overview (Semrush)
{competitor_table}

## AI Visibility Snapshot (Semrush AI)
{ai_kpi_block}

## Top AI Citations
{ai_citation_table}

## Published Content Footprint
{cms_count_block}

## Indexing & Technical Health
{indexing_table}
"""

