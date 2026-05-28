from typing import Any, Dict, List


def _format_compact(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    if abs(value - int(value)) < 1e-6:
        return f"{int(value)}"
    return f"{value:.2f}"


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
        "periodSnapshots": payload.get("periodSnapshots", {}),
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


def _snapshot_metric(snapshot: Dict[str, Any], path: List[str]) -> float:
    value: Any = snapshot
    for key in path:
        if not isinstance(value, dict):
            return 0.0
        value = value.get(key)
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _pct_change(current: float, reference: float) -> str:
    if reference == 0:
        return "n/a"
    delta = ((current - reference) / reference) * 100.0
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.1f}%"


def _pct_change_value(current: float, reference: float) -> float:
    if reference == 0:
        return 0.0
    return ((current - reference) / reference) * 100.0


def _trend_indicator(pct: float, inverse_good: bool = False) -> str:
    improving = pct <= 0 if inverse_good else pct >= 0
    if abs(pct) < 0.05:
        return "→"
    if improving:
        return "↑"
    return "↓"


def _executive_row(
    metric_label: str,
    current: float,
    last: float,
    best: float,
    inverse_good: bool = False,
) -> List[str]:
    vs_last = _pct_change_value(current, last)
    vs_best = _pct_change_value(current, best)
    return [
        metric_label,
        _format_compact(current),
        _format_compact(last),
        f"{_trend_indicator(vs_last, inverse_good)} {_pct_change(current, last)}",
        _format_compact(best),
        f"{_trend_indicator(vs_best, inverse_good)} {_pct_change(current, best)}",
    ]


def _cadence_keys(cadence: str) -> List[str]:
    cadence_map = {
        "weekly": ["Week", "currentWeek", "lastWeek", "bestWeek"],
        "monthly": ["Month", "currentMonth", "lastMonth", "bestMonth"],
        "quarterly": ["Quarter", "currentQuarter", "lastQuarter", "bestQuarter"],
    }
    return cadence_map.get(cadence, cadence_map["weekly"])


def _render_period_comparison_table(
    snapshots: Dict[str, Any],
    metric_path: List[str],
    cadence: str,
) -> str:
    if not snapshots:
        return "- No period snapshot data available."
    selected = _cadence_keys(cadence)
    rows = []
    label, current_key, last_key, best_key = selected
    current = _snapshot_metric(snapshots.get(current_key) or {}, metric_path)
    last = _snapshot_metric(snapshots.get(last_key) or {}, metric_path)
    best = _snapshot_metric(snapshots.get(best_key) or {}, metric_path)
    if any(v > 0 for v in (current, last, best)):
        rows.append(
            [
                label,
                _format_compact(current),
                _format_compact(last),
                _pct_change(current, last),
                _format_compact(best),
                _pct_change(current, best),
            ]
        )
    return _render_table(
        ["Cadence", "Current", "Last", "% vs Last", "Best", "% vs Best"], rows
    )


def _build_executive_snapshot_table(
    gsc: Dict[str, Any],
    ga4: Dict[str, Any],
    semrush: Dict[str, Any],
    semrush_ai: Dict[str, Any],
    cadence: str,
) -> str:
    rows: List[List[str]] = []
    _, current_key, last_key, best_key = _cadence_keys(cadence)

    gsc_snap = gsc.get("periodSnapshots") or {}
    if gsc_snap:
        rows.append(
            _executive_row(
                "GSC Clicks",
                _snapshot_metric(gsc_snap.get(current_key) or {}, ["totals", "clicks"]),
                _snapshot_metric(gsc_snap.get(last_key) or {}, ["totals", "clicks"]),
                _snapshot_metric(gsc_snap.get(best_key) or {}, ["totals", "clicks"]),
            )
        )

    ga4_snap = ga4.get("periodSnapshots") or {}
    if ga4_snap:
        rows.append(
            _executive_row(
                "GA4 Sessions",
                _snapshot_metric(ga4_snap.get(current_key) or {}, ["totals", "sessions"]),
                _snapshot_metric(ga4_snap.get(last_key) or {}, ["totals", "sessions"]),
                _snapshot_metric(ga4_snap.get(best_key) or {}, ["totals", "sessions"]),
            )
        )

    sem_snap = semrush.get("periodSnapshots") or {}
    if sem_snap:
        rows.append(
            _executive_row(
                "Semrush Tracked Keywords",
                _snapshot_metric(sem_snap.get(current_key) or {}, ["trackedKeywordsTop20"]),
                _snapshot_metric(sem_snap.get(last_key) or {}, ["trackedKeywordsTop20"]),
                _snapshot_metric(sem_snap.get(best_key) or {}, ["trackedKeywordsTop20"]),
            )
        )

    ai_snap = semrush_ai.get("periodSnapshots") or {}
    if ai_snap:
        rows.append(
            _executive_row(
                "Semrush AI Mentions",
                _snapshot_metric(ai_snap.get(current_key) or {}, ["estimatedAiMentions"]),
                _snapshot_metric(ai_snap.get(last_key) or {}, ["estimatedAiMentions"]),
                _snapshot_metric(ai_snap.get(best_key) or {}, ["estimatedAiMentions"]),
            )
        )

    return _render_table(
        ["Metric", "Current", "Last", "% vs Last", "Best", "% vs Best"], rows
    )


def _combined_top_pages_table(
    gsc_pages: List[Dict[str, Any]], ga4_pages: List[Dict[str, Any]]
) -> str:
    gsc_map = {p.get("page", "N/A"): p for p in gsc_pages}
    ga4_map = {p.get("pagePath", "N/A"): p for p in ga4_pages}
    all_pages = list(dict.fromkeys(list(gsc_map.keys()) + list(ga4_map.keys())))
    rows: List[List[str]] = []
    for page in all_pages[:8]:
        gsc_row = gsc_map.get(page, {})
        ga4_row = ga4_map.get(page, {})
        rows.append(
            [
                page,
                f"{int(gsc_row.get('clicks', 0)):,}",
                f"{int(gsc_row.get('impressions', 0)):,}",
                f"{float(gsc_row.get('ctr', 0.0)) * 100:.2f}%",
                f"{int(ga4_row.get('sessions', 0)):,}",
                f"{int(ga4_row.get('activeUsers', 0)):,}",
                f"{float(ga4_row.get('bounceRate', 0.0)) * 100:.1f}%",
            ]
        )
    return _render_table(
        [
            "Page",
            "Clicks",
            "Impressions",
            "CTR",
            "Sessions",
            "Active Users",
            "Bounce Rate",
        ],
        rows,
    )


def _deliverables_status_table(
    wordpress: Dict[str, Any], webflow: Dict[str, Any], contentful: Dict[str, Any]
) -> str:
    wp_posts = wordpress.get("posts") or []
    wf_items = webflow.get("items") or []
    cf_entries = contentful.get("entries") or []

    content_names: List[str] = []
    for post in wp_posts:
        name = post.get("title") or post.get("slug", "")
        if name and name not in content_names:
            content_names.append(name)
    for item in wf_items:
        name = item.get("name") or item.get("slug", "")
        if name and name not in content_names:
            content_names.append(name)
    for entry in cf_entries:
        name = entry.get("title") or entry.get("slug", "")
        if name and name not in content_names:
            content_names.append(name)

    content_names = content_names[:8]
    wp_map = {
        (p.get("title") or p.get("slug", "")): (
            "✓" if str(p.get("status", "")).lower() == "publish" else "✗"
        )
        for p in wp_posts
    }
    wf_map = {
        (i.get("name") or i.get("slug", "")): (
            "✗" if i.get("isDraft") else "✓"
        )
        for i in wf_items
    }
    cf_map = {
        (e.get("title") or e.get("slug", "")): (
            "✓" if e.get("publishDate") else "✗"
        )
        for e in cf_entries
    }

    rows: List[List[str]] = []
    for content in content_names:
        rows.append(
            [
                content,
                cf_map.get(content, "-"),
                wp_map.get(content, "-"),
                wf_map.get(content, "-"),
            ]
        )

    headers = ["Content", "Contentful", "Webpress", "Webflow"]
    return _render_table(headers, rows)


def _keyword_position_comparison_table(semrush: Dict[str, Any]) -> str:
    """Keyword positioning table from Semrush keywordCompetitiveMatrix raw data."""
    matrix = semrush.get("keywordCompetitiveMatrix") or {}
    raw_rows = matrix.get("rows") or []
    if not raw_rows:
        return "_No keyword positioning data available._"

    customer_label = matrix.get("customerLabel") or "You"
    headers = [
        "Keyword",
        "Volume",
        customer_label,
        "Competitor",
        "Winner",
        "Opportunity",
    ]
    rows: List[List[str]] = []
    for row in raw_rows:
        rows.append(
            [
                row.get("keyword", "N/A"),
                f"{int(row.get('volume', 0)):,}",
                str(int(row.get("customerPosition", 0))),
                str(int(row.get("competitorPosition", 0))),
                row.get("winner", "—"),
                row.get("opportunity", "—"),
            ]
        )
    return _render_table(headers, rows)


def _semrush_ai_performance_table(semrush_ai: Dict[str, Any]) -> str:
    """AI visibility table from Semrush AI aiPerformanceMatrix raw data."""
    matrix = semrush_ai.get("aiPerformanceMatrix") or {}
    raw_rows = matrix.get("rows") or []
    if raw_rows:
        table_rows: List[List[str]] = []
        for row in raw_rows:
            table_rows.append(
                [
                    row.get("platform", "N/A"),
                    f"{float(row.get('visibilityShare', 0.0)):.1f}%",
                    f"{int(row.get('mentions', 0)):,}",
                    f"{int(row.get('citations', 0)):,}",
                ]
            )
        return _render_table(
            ["Platform", "Visibility", "Mentions", "Citations"], table_rows
        )

    overview = semrush_ai.get("visibilityOverview") or {}
    by_llm = overview.get("byLlm") or []
    if not by_llm and not overview:
        return "_No Semrush AI performance data available._"

    rows: List[List[str]] = [
        [
            "Overall",
            str(int(overview.get("visibilityScore", 0))),
            f"{int(overview.get('mentions', 0)):,}",
            f"{int(overview.get('citations', 0)):,}",
        ]
    ]
    for row in by_llm[:5]:
        rows.append(
            [
                row.get("platform", "N/A"),
                f"{float(row.get('visibilityShare', 0.0)):.1f}%",
                f"{int(row.get('mentions', 0)):,}",
                f"{int(row.get('citations', 0)):,}",
            ]
        )
    return _render_table(["Platform", "Visibility", "Mentions", "Citations"], rows)


def _url_inspection_data_table(url_inspection: List[Dict[str, Any]]) -> str:
    """URLs that need attention (verdict is not PASS) from GSC URL Inspection mocks."""
    failing = [
        row
        for row in url_inspection
        if str(row.get("verdict", "")).upper() != "PASS"
    ]
    if not failing:
        return "_No URLs require inspection this period._"
    rows: List[List[str]] = []
    for row in failing:
        rows.append(
            [
                row.get("url", "N/A"),
                row.get("verdict", "—"),
                row.get("coverageState", "—"),
                row.get("severity", "none"),
                row.get("recommendation") or "No action needed.",
            ]
        )
    return _render_table(
        ["URL", "Verdict", "Coverage", "Severity", "Recommendation"],
        rows,
    )


def _deliverables_and_inspection_table(
    wordpress: Dict[str, Any],
    webflow: Dict[str, Any],
    contentful: Dict[str, Any],
    url_inspection: List[Dict[str, Any]],
) -> str:
    rows: List[List[str]] = []
    for item in (wordpress.get("items") or [])[:5]:
        rows.append(["Deliverable", "WordPress", item.get("title", "N/A"), "Published"])
    for item in (webflow.get("items") or [])[:5]:
        rows.append(["Deliverable", "Webflow", item.get("name", "N/A"), "Published"])
    for item in (contentful.get("items") or [])[:5]:
        rows.append(["Deliverable", "Contentful", item.get("title", "N/A"), "Published"])
    for row in url_inspection[:8]:
        status = row.get("severity", "none")
        rows.append(
            [
                "Inspection",
                "GSC URL Inspection",
                row.get("url", "N/A"),
                status,
            ]
        )
    return _render_table(["Type", "Source", "Item", "Status"], rows)


def render_executive_snapshot_markdown(
    report_context: Dict[str, Any], cadence: str = "weekly"
) -> str:
    gsc = report_context.get("gsc") or report_context.get("gscFiltered") or {}
    ga4 = report_context.get("ga4") or {}
    semrush = report_context.get("semrush") or {}
    semrush_ai = report_context.get("semrushAi") or {}
    executive_snapshot_table = _build_executive_snapshot_table(
        gsc, ga4, semrush, semrush_ai, cadence
    )
    return f"## Executive Snapshot\n{executive_snapshot_table}\n"


def render_report_markdown(
    customer_name: str,
    report_type: str,
    instructions: str,
    report_context: Dict[str, Any],
    cadence: str = "weekly",
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
    if cadence == "weekly":
        gsc_snap = gsc.get("periodSnapshots") or {}
        ga4_snap = ga4.get("periodSnapshots") or {}
        current_key, last_key, best_key = "currentWeek", "lastWeek", "bestWeek"

        weekly_table = _render_table(
            ["Metric", "Current Week", "Last Week", "% vs Last", "Best Week", "% vs Best"],
            [
                _executive_row(
                    "Clicks",
                    _snapshot_metric(gsc_snap.get(current_key) or {}, ["totals", "clicks"]),
                    _snapshot_metric(gsc_snap.get(last_key) or {}, ["totals", "clicks"]),
                    _snapshot_metric(gsc_snap.get(best_key) or {}, ["totals", "clicks"]),
                ),
                _executive_row(
                    "Impressions",
                    _snapshot_metric(gsc_snap.get(current_key) or {}, ["totals", "impressions"]),
                    _snapshot_metric(gsc_snap.get(last_key) or {}, ["totals", "impressions"]),
                    _snapshot_metric(gsc_snap.get(best_key) or {}, ["totals", "impressions"]),
                ),
                _executive_row(
                    "CTR",
                    _snapshot_metric(gsc_snap.get(current_key) or {}, ["totals", "ctr"]) * 100.0,
                    _snapshot_metric(gsc_snap.get(last_key) or {}, ["totals", "ctr"]) * 100.0,
                    _snapshot_metric(gsc_snap.get(best_key) or {}, ["totals", "ctr"]) * 100.0,
                ),
                _executive_row(
                    "Position",
                    _snapshot_metric(gsc_snap.get(current_key) or {}, ["totals", "position"]),
                    _snapshot_metric(gsc_snap.get(last_key) or {}, ["totals", "position"]),
                    _snapshot_metric(gsc_snap.get(best_key) or {}, ["totals", "position"]),
                    inverse_good=True,
                ),
                _executive_row(
                    "Sessions",
                    _snapshot_metric(ga4_snap.get(current_key) or {}, ["totals", "sessions"]),
                    _snapshot_metric(ga4_snap.get(last_key) or {}, ["totals", "sessions"]),
                    _snapshot_metric(ga4_snap.get(best_key) or {}, ["totals", "sessions"]),
                ),
                _executive_row(
                    "Active Users",
                    _snapshot_metric(ga4_snap.get(current_key) or {}, ["totals", "activeUsers"]),
                    _snapshot_metric(ga4_snap.get(last_key) or {}, ["totals", "activeUsers"]),
                    _snapshot_metric(ga4_snap.get(best_key) or {}, ["totals", "activeUsers"]),
                ),
                _executive_row(
                    "Engaged Sessions",
                    _snapshot_metric(ga4_snap.get(current_key) or {}, ["totals", "engagedSessions"]),
                    _snapshot_metric(ga4_snap.get(last_key) or {}, ["totals", "engagedSessions"]),
                    _snapshot_metric(ga4_snap.get(best_key) or {}, ["totals", "engagedSessions"]),
                ),
                _executive_row(
                    "Engagement Rate",
                    _snapshot_metric(ga4_snap.get(current_key) or {}, ["totals", "engagementRate"]) * 100.0,
                    _snapshot_metric(ga4_snap.get(last_key) or {}, ["totals", "engagementRate"]) * 100.0,
                    _snapshot_metric(ga4_snap.get(best_key) or {}, ["totals", "engagementRate"]) * 100.0,
                ),
                _executive_row(
                    "Conversions",
                    _snapshot_metric(ga4_snap.get(current_key) or {}, ["totals", "conversions"]),
                    _snapshot_metric(ga4_snap.get(last_key) or {}, ["totals", "conversions"]),
                    _snapshot_metric(ga4_snap.get(best_key) or {}, ["totals", "conversions"]),
                ),
            ],
        )
        top_pages_combined_table = _combined_top_pages_table(
            gsc.get("topPages") or [], ga4.get("topLandingPages") or []
        )
        top_queries_table = _render_table(
            ["Query", "Clicks", "Impressions", "CTR", "Position"],
            [
                [
                    q.get("query", "N/A"),
                    f"{int(q.get('clicks', 0)):,}",
                    f"{int(q.get('impressions', 0)):,}",
                    f"{float(q.get('ctr', 0.0)) * 100:.2f}%",
                    f"{float(q.get('position', 0.0)):.1f}",
                ]
                for q in gsc.get("topQueries", [])
            ],
        )
        keyword_competitive_table = _keyword_position_comparison_table(semrush)
        semrush_ai_table = _semrush_ai_performance_table(semrush_ai)
        url_inspection_table = _url_inspection_data_table(url_inspection)
        deliverables_table = _deliverables_status_table(
            wordpress, webflow, contentful
        )
        return f"""# Weekly report for {customer_name}

## Executive Summary
{weekly_table}

## Deliverables
{deliverables_table}

## Top Pages
{top_pages_combined_table}

## Top Queries
{top_queries_table}

## Competitor Analysis
{keyword_competitive_table}

## AI Performance
{semrush_ai_table}

## URL Inspection Required
{url_inspection_table}
"""

    highlights = build_highlights(gsc) if gsc else []

    query_table = _render_table(
        ["Query", "Clicks", "Impressions", "CTR", "Position"],
        [
            [
                q.get("query", "N/A"),
                f"{int(q.get('clicks', 0)):,}",
                f"{int(q.get('impressions', 0)):,}",
                f"{float(q.get('ctr', 0.0)) * 100:.2f}%",
                f"{float(q.get('position', 0.0)):.1f}",
            ]
            for q in gsc.get("topQueries", [])
        ],
    )
    page_table = _render_table(
        ["Page", "Clicks", "Impressions", "CTR", "Position"],
        [
            [
                p.get("page", "N/A"),
                f"{int(p.get('clicks', 0)):,}",
                f"{int(p.get('impressions', 0)):,}",
                f"{float(p.get('ctr', 0.0)) * 100:.2f}%",
                f"{float(p.get('position', 0.0)):.1f}",
            ]
            for p in gsc.get("topPages", [])
        ],
    )

    safe_instructions = instructions.strip() or "No additional instructions provided."

    gsc_kpi_table = _render_table(
        ["Metric", "Value"],
        [
            ["Clicks", f"{totals.get('clicks', 0):,}"],
            ["Impressions", f"{totals.get('impressions', 0):,}"],
            ["CTR", f"{totals.get('ctr', 0.0) * 100:.2f}%"],
            ["Average Position", f"{totals.get('position', 0.0):.1f}"],
        ],
    )

    ga4_totals = ga4.get("totals", {})
    ga4_kpi_table = _render_table(
        ["Metric", "Value"],
        [
            ["Sessions", f"{int(ga4_totals.get('sessions', 0)):,}"],
            ["Active Users", f"{int(ga4_totals.get('activeUsers', 0)):,}"],
            ["Engagement Rate", f"{float(ga4_totals.get('engagementRate', 0.0)) * 100:.2f}%"],
            ["Conversions", f"{int(ga4_totals.get('conversions', 0)):,}"],
        ],
    )

    semrush_backlinks = semrush.get("customerBacklinks") or {}
    semrush_kpi_table = _render_table(
        ["Metric", "Value"],
        [
            ["Authority Score", f"{int(semrush_backlinks.get('authorityScore', 0))}"],
            ["Total Backlinks", f"{int(semrush_backlinks.get('totalBacklinks', 0)):,}"],
            ["Referring Domains", f"{int(semrush_backlinks.get('referringDomains', 0)):,}"],
        ],
    )

    visibility = semrush_ai.get("visibilityOverview") or {}
    ai_kpi_table = _render_table(
        ["Metric", "Value"],
        [
            ["AI Visibility Score", f"{int(visibility.get('visibilityScore', 0))}"],
            ["Mentions", f"{int(visibility.get('mentions', 0)):,}"],
            ["Citations", f"{int(visibility.get('citations', 0)):,}"],
        ],
    )

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

    ga4_segments = ga4.get("lastWeekSegments") or {}
    ga4_device_table = _render_table(
        ["Device", "Sessions", "Active Users", "Engagement Rate"],
        [
            [
                row.get("deviceCategory", "N/A"),
                f"{int(row.get('sessions', 0)):,}",
                f"{int(row.get('activeUsers', 0)):,}",
                f"{float(row.get('engagementRate', 0.0)) * 100:.1f}%",
            ]
            for row in (ga4_segments.get("byDeviceCategory") or [])
        ],
    )
    ga4_country_table = _render_table(
        ["Country", "Sessions", "Conversions"],
        [
            [
                row.get("country", "N/A"),
                f"{int(row.get('sessions', 0)):,}",
                f"{int(row.get('conversions', 0)):,}",
            ]
            for row in (ga4_segments.get("byCountry") or [])
        ],
    )
    ga4_user_type_table = _render_table(
        ["User Type", "Sessions", "Active Users"],
        [
            [
                row.get("userType", "N/A"),
                f"{int(row.get('sessions', 0)):,}",
                f"{int(row.get('activeUsers', 0)):,}",
            ]
            for row in (ga4_segments.get("byUserType") or [])
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

    gsc_period_table = _render_period_comparison_table(
        gsc.get("periodSnapshots") or {}, ["totals", "clicks"], cadence
    )
    ga4_period_table = _render_period_comparison_table(
        ga4.get("periodSnapshots") or {}, ["totals", "sessions"], cadence
    )
    semrush_period_table = _render_period_comparison_table(
        semrush.get("periodSnapshots") or {}, ["trackedKeywordsTop20"], cadence
    )
    semrush_ai_period_table = _render_period_comparison_table(
        semrush_ai.get("periodSnapshots") or {}, ["estimatedAiMentions"], cadence
    )
    executive_snapshot_table = _build_executive_snapshot_table(
        gsc, ga4, semrush, semrush_ai, cadence
    )
    top_pages_combined_table = _combined_top_pages_table(
        gsc.get("topPages") or [], top_landing_pages
    )
    keyword_competitive_table = _keyword_position_comparison_table(semrush)
    semrush_ai_table = _semrush_ai_performance_table(semrush_ai)
    deliverables_inspection_table = _deliverables_and_inspection_table(
        wordpress, webflow, contentful, url_inspection
    )

    cms_count_block = _render_table(
        ["Source", "Items"],
        [
            ["WordPress posts", f"{len(wordpress.get('items') or []):,}"],
            ["Webflow items", f"{len(webflow.get('items') or []):,}"],
            ["Contentful entries", f"{len(contentful.get('items') or []):,}"],
        ],
    )

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
    insights = [
        "Prioritize rows with DOWN trend first; close biggest gap-to-best metrics in the next cycle.",
        "Align content updates to pages where both search demand and on-site sessions are strong.",
        "Prioritize High-opportunity keywords where competitors outrank you on high-volume terms.",
    ]
    recommendations = [
        "Refresh top 3 pages with weakest trend and re-submit for indexing.",
        "Ship one SEO fix, one content update, and one CRO tweak per cycle.",
        "Review this same table set next report and retain only actions that improved % vs Last.",
    ]
    insights_block = "\n".join(f"- {item}" for item in insights)
    recommendations_block = "\n".join(f"- {item}" for item in recommendations)

    return f"""# {report_type} Report - {customer_name}

## Executive Snapshot
{executive_snapshot_table}
### Insight
- Focus first on the metrics with DOWN trend and highest negative % vs Best.

## Source Data Tables
## Top Queries
{query_table}
### Insight
- Keep query gains by refreshing pages tied to top-click queries and protecting rankings.

## Top Pages
{top_pages_combined_table}
### Insight
- Prioritize pages where GSC clicks and GA4 sessions both underperform relative to leaders.

## Competitor Analysis
{keyword_competitive_table}

## AI Performance
{semrush_ai_table}
### Insight
- Increase visibility on the lowest-performing AI platforms using prompt-aligned content.

## Deliverables and URL Inspection
{deliverables_inspection_table}
### Insight
- Fix high-severity inspection rows first, then scale what worked from published deliverables.

## Insights
{insights_block}

## Recommendations
{recommendations_block}
"""

