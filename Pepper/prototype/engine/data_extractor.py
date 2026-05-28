import re
from typing import Any, Dict, List, Optional

try:
    from ga4.adapter import normalize_ga4_payload
    from pipeline import normalize_gsc_payload
    from semrush.adapter import normalize_semrush_payload
    from semrush.ai_adapter import normalize_semrush_ai_payload
    from sources import (
        ContentfulSource,
        GA4Source,
        GSCSource,
        SemrushSource,
        WebflowSource,
        WordPressSource,
    )
except ImportError:
    from .ga4.adapter import normalize_ga4_payload
    from .pipeline import normalize_gsc_payload
    from .semrush.adapter import normalize_semrush_payload
    from .semrush.ai_adapter import normalize_semrush_ai_payload
    from .sources import (
        ContentfulSource,
        GA4Source,
        GSCSource,
        SemrushSource,
        WebflowSource,
        WordPressSource,
    )


COMING_SOON_SOURCES = [
    {"id": "geo", "name": "GEO Visibility", "status": "coming_soon"},
]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "item"


def _format_duration(seconds: float) -> str:
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _build_gsc_items(normalized: Dict[str, Any]) -> List[Dict[str, Any]]:
    totals = normalized["totals"]
    items: List[Dict[str, Any]] = [
        {
            "id": "gsc.kpi.clicks",
            "sourceId": "gsc",
            "type": "kpi",
            "label": "Total Clicks",
            "summary": f"{totals['clicks']:,} clicks in {normalized['dateRange']}",
            "metrics": {"clicks": totals["clicks"]},
            "includedByDefault": True,
        },
        {
            "id": "gsc.kpi.impressions",
            "sourceId": "gsc",
            "type": "kpi",
            "label": "Total Impressions",
            "summary": f"{totals['impressions']:,} impressions",
            "metrics": {"impressions": totals["impressions"]},
            "includedByDefault": True,
        },
        {
            "id": "gsc.kpi.ctr",
            "sourceId": "gsc",
            "type": "kpi",
            "label": "Average CTR",
            "summary": f"{totals['ctr'] * 100:.2f}% click-through rate",
            "metrics": {"ctr": totals["ctr"]},
            "includedByDefault": True,
        },
        {
            "id": "gsc.kpi.position",
            "sourceId": "gsc",
            "type": "kpi",
            "label": "Average Position",
            "summary": f"Avg position {totals['position']:.1f}",
            "metrics": {"position": totals["position"]},
            "includedByDefault": True,
        },
    ]

    for query in normalized.get("topQueries", []):
        qtext = query.get("query", "N/A")
        items.append(
            {
                "id": f"gsc.query.{_slugify(qtext)}",
                "sourceId": "gsc",
                "type": "query",
                "label": qtext,
                "summary": (
                    f"{int(query.get('clicks', 0)):,} clicks · "
                    f"{float(query.get('ctr', 0)) * 100:.2f}% CTR · "
                    f"pos {float(query.get('position', 0)):.1f}"
                ),
                "metrics": query,
                "includedByDefault": True,
            }
        )

    for page in normalized.get("topPages", []):
        ppath = page.get("page", "N/A")
        items.append(
            {
                "id": f"gsc.page.{_slugify(ppath)}",
                "sourceId": "gsc",
                "type": "page",
                "label": ppath,
                "summary": (
                    f"{int(page.get('clicks', 0)):,} clicks · "
                    f"{float(page.get('ctr', 0)) * 100:.2f}% CTR · "
                    f"pos {float(page.get('position', 0)):.1f}"
                ),
                "metrics": page,
                "includedByDefault": True,
            }
        )

    return items


def _build_ga4_items(normalized: Dict[str, Any]) -> List[Dict[str, Any]]:
    totals = normalized["totals"]
    organic = normalized.get("organicChannel") or {}
    items: List[Dict[str, Any]] = [
        {
            "id": "ga4.kpi.sessions",
            "sourceId": "ga4",
            "type": "kpi",
            "label": "Total Sessions",
            "summary": f"{totals['sessions']:,} sessions in {normalized['dateRange']}",
            "metrics": {"sessions": totals["sessions"]},
            "includedByDefault": True,
        },
        {
            "id": "ga4.kpi.activeUsers",
            "sourceId": "ga4",
            "type": "kpi",
            "label": "Active Users",
            "summary": f"{totals['activeUsers']:,} active users",
            "metrics": {"activeUsers": totals["activeUsers"]},
            "includedByDefault": True,
        },
        {
            "id": "ga4.kpi.engagedSessions",
            "sourceId": "ga4",
            "type": "kpi",
            "label": "Engaged Sessions",
            "summary": f"{totals['engagedSessions']:,} engaged sessions",
            "metrics": {"engagedSessions": totals["engagedSessions"]},
            "includedByDefault": False,
        },
        {
            "id": "ga4.kpi.engagementRate",
            "sourceId": "ga4",
            "type": "kpi",
            "label": "Engagement Rate",
            "summary": f"{totals['engagementRate'] * 100:.2f}% engagement rate",
            "metrics": {"engagementRate": totals["engagementRate"]},
            "includedByDefault": False,
        },
        {
            "id": "ga4.kpi.conversions",
            "sourceId": "ga4",
            "type": "kpi",
            "label": "Conversions",
            "summary": f"{totals['conversions']:,} conversions",
            "metrics": {"conversions": totals["conversions"]},
            "includedByDefault": False,
        },
        {
            "id": "ga4.channel.organic-search",
            "sourceId": "ga4",
            "type": "channel",
            "label": "Organic Search (GA4)",
            "summary": (
                f"{int(organic.get('sessions', 0)):,} sessions · "
                f"{int(organic.get('activeUsers', 0)):,} users — complements GSC clicks"
            ),
            "metrics": organic,
            "includedByDefault": True,
        },
    ]

    for landing in normalized.get("topLandingPages", []):
        path = landing.get("pagePath", "N/A")
        items.append(
            {
                "id": f"ga4.page.{_slugify(path)}",
                "sourceId": "ga4",
                "type": "landing_page",
                "label": path,
                "summary": (
                    f"{int(landing.get('sessions', 0)):,} sessions · "
                    f"{float(landing.get('bounceRate', 0)) * 100:.1f}% bounce · "
                    f"avg {_format_duration(float(landing.get('averageSessionDuration', 0)))}"
                ),
                "metrics": landing,
                "includedByDefault": True,
            }
        )

    return items


def _build_semrush_items(normalized: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    backlinks = normalized.get("customerBacklinks") or {}
    keywords = normalized.get("customerKeywords") or []

    items.append(
        {
            "id": "semrush.kpi.authority-score",
            "sourceId": "semrush",
            "type": "kpi",
            "label": "Authority Score (Semrush)",
            "summary": (
                f"AS {backlinks.get('authorityScore', 0)} · "
                f"{backlinks.get('referringDomains', 0):,} referring domains"
            ),
            "metrics": backlinks,
            "includedByDefault": True,
        }
    )
    items.append(
        {
            "id": "semrush.kpi.organic-keywords",
            "sourceId": "semrush",
            "type": "kpi",
            "label": "Ranking Organic Keywords",
            "summary": f"{len(keywords)} tracked keywords in top 20 (mock sample)",
            "metrics": {"organicKeywordsSample": len(keywords)},
            "includedByDefault": True,
        }
    )

    for comp in normalized.get("competitorSummaries") or []:
        domain = comp.get("domain", "")
        items.append(
            {
                "id": f"semrush.competitor.{_slugify(domain)}",
                "sourceId": "semrush",
                "type": "competitor",
                "label": f"Competitor: {comp.get('label', domain)}",
                "summary": (
                    f"AS {comp.get('authorityScore', 0)} · "
                    f"{comp.get('referringDomains', 0):,} ref. domains · "
                    f"top keyword pos {comp['topKeywords'][0]['position'] if comp.get('topKeywords') else '—'}"
                ),
                "metrics": comp,
                "includedByDefault": True,
            }
        )

    for kw in keywords[:3]:
        phrase = kw.get("keyword", "N/A")
        items.append(
            {
                "id": f"semrush.keyword.{_slugify(phrase)}",
                "sourceId": "semrush",
                "type": "keyword",
                "label": phrase,
                "summary": (
                    f"Pos {int(kw.get('position', 0))} · "
                    f"vol {int(kw.get('searchVolume', 0)):,} · "
                    f"{float(kw.get('trafficPercent', 0)):.1f}% traffic share"
                ),
                "metrics": kw,
                "includedByDefault": True,
            }
        )

    for page in normalized.get("customerPages") or []:
        url = page.get("url", "N/A")
        items.append(
            {
                "id": f"semrush.page.{_slugify(url)}",
                "sourceId": "semrush",
                "type": "organic_page",
                "label": url,
                "summary": (
                    f"{int(page.get('keywordsCount', 0))} ranking keywords · "
                    f"{float(page.get('trafficPercent', 0)):.1f}% traffic share"
                ),
                "metrics": page,
                "includedByDefault": False,
            }
        )

    for insight in normalized.get("phraseInsights") or []:
        phrase = insight.get("phrase", "N/A")
        items.append(
            {
                "id": f"semrush.phrase.{_slugify(phrase)}",
                "sourceId": "semrush",
                "type": "phrase",
                "label": f"SERP: {phrase}",
                "summary": (
                    f"KD {int(insight.get('keywordDifficulty', 0))} · "
                    f"leader {insight.get('topSerpDomain', '—')}"
                ),
                "metrics": insight,
                "includedByDefault": True,
            }
        )

    items.append(
        {
            "id": "semrush.backlinks.overview",
            "sourceId": "semrush",
            "type": "backlinks",
            "label": "Backlinks overview",
            "summary": (
                f"{backlinks.get('totalBacklinks', 0):,} backlinks · "
                f"follow {backlinks.get('followLinks', 0):,} / "
                f"nofollow {backlinks.get('nofollowLinks', 0):,}"
            ),
            "metrics": backlinks,
            "includedByDefault": True,
        }
    )

    tracking = normalized.get("positionTracking") or {}
    for row in tracking.get("keywords") or []:
        keyword = row.get("keyword", "N/A")
        delta = row.get("previousPosition", 0) - row.get("position", 0)
        trend = f"+{delta}" if delta > 0 else str(delta)
        items.append(
            {
                "id": f"semrush.position.{_slugify(keyword)}",
                "sourceId": "semrush",
                "type": "position",
                "label": f"Rank track: {keyword}",
                "summary": (
                    f"Pos {int(row.get('position', 0))} ({trend}) · "
                    f"vs {row.get('competitorBestDomain', '—')} "
                    f"#{int(row.get('competitorBestPosition', 0))}"
                ),
                "metrics": row,
                "includedByDefault": True,
            }
        )

    return items


def _build_semrush_ai_items(normalized: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    overview = normalized.get("visibilityOverview") or {}

    items.append(
        {
            "id": "semrush-ai.kpi.visibility-score",
            "sourceId": "semrush-ai",
            "type": "kpi",
            "label": "AI Visibility Score",
            "summary": (
                f"Score {overview.get('visibilityScore', 0)}/100 · "
                f"{overview.get('mentions', 0):,} mentions · "
                f"{overview.get('citations', 0):,} citations"
            ),
            "metrics": {
                "visibilityScore": overview.get("visibilityScore", 0),
                "mentions": overview.get("mentions", 0),
                "citations": overview.get("citations", 0),
                "citedPages": overview.get("citedPages", 0),
                "monthlyAudience": overview.get("monthlyAudience", 0),
            },
            "includedByDefault": True,
        }
    )

    for comp in overview.get("competitorComparison") or []:
        domain = comp.get("domain", "")
        if domain == normalized.get("customerDomain"):
            continue
        items.append(
            {
                "id": f"semrush-ai.competitor.{_slugify(domain)}",
                "sourceId": "semrush-ai",
                "type": "ai_competitor",
                "label": f"AI visibility: {domain}",
                "summary": (
                    f"Score {comp.get('visibilityScore', 0)} · "
                    f"{comp.get('mentions', 0):,} mentions · "
                    f"{comp.get('citations', 0):,} citations"
                ),
                "metrics": comp,
                "includedByDefault": True,
            }
        )

    top_llm = sorted(
        overview.get("byLlm") or [],
        key=lambda x: float(x.get("visibilityShare", 0)),
        reverse=True,
    )
    if top_llm:
        lead = top_llm[0]
        items.append(
            {
                "id": "semrush-ai.llm.leader",
                "sourceId": "semrush-ai",
                "type": "ai_platform",
                "label": f"Top LLM: {lead.get('platform', '—')}",
                "summary": (
                    f"{float(lead.get('visibilityShare', 0)):.1f}% visibility share · "
                    f"{lead.get('mentions', 0)} mentions"
                ),
                "metrics": lead,
                "includedByDefault": False,
            }
        )

    for row in normalized.get("promptMentions") or []:
        prompt = row.get("prompt", "N/A")
        mentioned = row.get("brandMentioned", False)
        items.append(
            {
                "id": f"semrush-ai.prompt.{_slugify(prompt)}",
                "sourceId": "semrush-ai",
                "type": "ai_prompt",
                "label": prompt,
                "summary": (
                    f"{'Mentioned' if mentioned else 'Not mentioned'} · "
                    f"audience ~{int(row.get('audience', 0)):,} · "
                    f"vs {', '.join((row.get('competitorsMentioned') or [])[:2]) or '—'}"
                ),
                "metrics": row,
                "includedByDefault": mentioned,
            }
        )

    for row in normalized.get("citationTracking") or []:
        url = row.get("url", "N/A")
        items.append(
            {
                "id": f"semrush-ai.citation.{_slugify(url)}",
                "sourceId": "semrush-ai",
                "type": "ai_citation",
                "label": url,
                "summary": (
                    f"{int(row.get('citationCount', 0))} citations · "
                    f"avg pos {float(row.get('avgCitationPosition', 0)):.1f} · "
                    f"{int(row.get('promptsCitedIn', 0))} prompts"
                ),
                "metrics": row,
                "includedByDefault": True,
            }
        )

    return items


def _build_wordpress_items(normalized: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = [
        {
            "id": "wordpress.kpi.published-posts",
            "sourceId": "wordpress",
            "type": "kpi",
            "label": "Published posts",
            "summary": f"{normalized.get('totalItems', 0)} live posts via WP REST API",
            "metrics": {"totalItems": normalized.get("totalItems", 0)},
            "includedByDefault": True,
        }
    ]
    for post in normalized.get("posts") or []:
        slug = post.get("slug", "post")
        items.append(
            {
                "id": f"wordpress.post.{_slugify(slug)}",
                "sourceId": "wordpress",
                "type": "post",
                "label": post.get("title") or slug,
                "summary": (
                    f"{post.get('link', '')} · updated {post.get('modified', '')[:10]}"
                ),
                "metrics": post,
                "includedByDefault": True,
            }
        )
    return items


def _build_webflow_items(normalized: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = [
        {
            "id": "webflow.kpi.live-items",
            "sourceId": "webflow",
            "type": "kpi",
            "label": "Live collection items",
            "summary": (
                f"{normalized.get('totalItems', 0)} items in collection "
                f"{normalized.get('collectionId', '')}"
            ),
            "metrics": {
                "totalItems": normalized.get("totalItems", 0),
                "collectionId": normalized.get("collectionId", ""),
            },
            "includedByDefault": True,
        }
    ]
    for item in normalized.get("items") or []:
        slug = item.get("slug", "item")
        items.append(
            {
                "id": f"webflow.item.{_slugify(slug)}",
                "sourceId": "webflow",
                "type": "cms_item",
                "label": item.get("name") or slug,
                "summary": (
                    f"{item.get('urlPath', '')} · published "
                    f"{(item.get('lastPublished') or '')[:10]}"
                ),
                "metrics": item,
                "includedByDefault": True,
            }
        )
    return items


def _build_contentful_items(normalized: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = [
        {
            "id": "contentful.kpi.entries",
            "sourceId": "contentful",
            "type": "kpi",
            "label": "CDA entries",
            "summary": (
                f"{normalized.get('total', 0)} entries · "
                f"{normalized.get('space', '')}/{normalized.get('environment', '')}"
            ),
            "metrics": {
                "total": normalized.get("total", 0),
                "space": normalized.get("space", ""),
                "environment": normalized.get("environment", ""),
            },
            "includedByDefault": True,
        }
    ]
    for entry in normalized.get("entries") or []:
        slug = entry.get("slug", "entry")
        items.append(
            {
                "id": f"contentful.entry.{_slugify(slug)}",
                "sourceId": "contentful",
                "type": "entry",
                "label": entry.get("title") or slug,
                "summary": (
                    f"{entry.get('path', '')} · {entry.get('contentType', '')} · "
                    f"updated {(entry.get('updatedAt') or '')[:10]}"
                ),
                "metrics": entry,
                "includedByDefault": True,
            }
        )
    return items


def extract_customer_data(
    customer_id: str,
    gsc_source: GSCSource,
    ga4_source: Optional[GA4Source] = None,
    semrush_source: Optional[SemrushSource] = None,
    wordpress_source: Optional[WordPressSource] = None,
    webflow_source: Optional[WebflowSource] = None,
    contentful_source: Optional[ContentfulSource] = None,
) -> Dict[str, Any]:
    gsc_payload = gsc_source.get_customer_payload(customer_id)
    gsc_normalized = normalize_gsc_payload(gsc_payload)
    items = _build_gsc_items(gsc_normalized)

    ga4_normalized: Optional[Dict[str, Any]] = None
    if ga4_source is not None:
        ga4_payload = ga4_source.get_customer_payload(customer_id)
        ga4_normalized = normalize_ga4_payload(ga4_payload)
        items.extend(_build_ga4_items(ga4_normalized))

    semrush_normalized: Optional[Dict[str, Any]] = None
    semrush_ai_normalized: Optional[Dict[str, Any]] = None
    if semrush_source is not None:
        semrush_payload = semrush_source.get_customer_payload(customer_id)
        semrush_normalized = normalize_semrush_payload(semrush_payload)
        items.extend(_build_semrush_items(semrush_normalized))
        semrush_ai_payload = semrush_source.get_ai_payload(customer_id)
        semrush_ai_normalized = normalize_semrush_ai_payload(semrush_ai_payload)
        items.extend(_build_semrush_ai_items(semrush_ai_normalized))

    wordpress_normalized: Optional[Dict[str, Any]] = None
    if wordpress_source is not None:
        wordpress_normalized = wordpress_source.get_customer_payload(customer_id)
        items.extend(_build_wordpress_items(wordpress_normalized))

    webflow_normalized: Optional[Dict[str, Any]] = None
    if webflow_source is not None:
        webflow_normalized = webflow_source.get_customer_payload(customer_id)
        items.extend(_build_webflow_items(webflow_normalized))

    contentful_normalized: Optional[Dict[str, Any]] = None
    if contentful_source is not None:
        contentful_normalized = contentful_source.get_customer_payload(customer_id)
        items.extend(_build_contentful_items(contentful_normalized))

    sources: List[Dict[str, Any]] = [
        {
            "id": "gsc",
            "name": "Google Search Console",
            "status": "active",
            "dateRange": gsc_normalized["dateRange"],
        },
    ]
    if ga4_normalized is not None:
        sources.append(
            {
                "id": "ga4",
                "name": "Google Analytics 4",
                "status": "active",
                "dateRange": ga4_normalized["dateRange"],
            }
        )
    if semrush_normalized is not None:
        sources.append(
            {
                "id": "semrush",
                "name": "Semrush",
                "status": "active",
                "dateRange": semrush_normalized["dateRange"],
            }
        )
    if semrush_ai_normalized is not None:
        sources.append(
            {
                "id": "semrush-ai",
                "name": "Semrush AI Visibility",
                "status": "active",
                "dateRange": semrush_ai_normalized["dateRange"],
            }
        )
    if wordpress_normalized is not None:
        sources.append(
            {
                "id": "wordpress",
                "name": "WordPress",
                "status": "active",
                "dateRange": wordpress_normalized["dateRange"],
            }
        )
    if webflow_normalized is not None:
        sources.append(
            {
                "id": "webflow",
                "name": "Webflow",
                "status": "active",
                "dateRange": webflow_normalized["dateRange"],
            }
        )
    if contentful_normalized is not None:
        sources.append(
            {
                "id": "contentful",
                "name": "Contentful",
                "status": "active",
                "dateRange": contentful_normalized["dateRange"],
            }
        )
    sources.extend(COMING_SOON_SOURCES)

    return {
        "customerId": customer_id,
        "normalized": gsc_normalized,
        "ga4Normalized": ga4_normalized,
        "semrushNormalized": semrush_normalized,
        "semrushAiNormalized": semrush_ai_normalized,
        "wordpressNormalized": wordpress_normalized,
        "webflowNormalized": webflow_normalized,
        "contentfulNormalized": contentful_normalized,
        "sources": sources,
        "items": items,
        "reportOutline": build_report_outline(items),
    }


def build_report_outline(items: List[Dict[str, Any]]) -> List[str]:
    outline = [
        "Executive summary of organic search performance",
        "Performance story based on selected GSC metrics",
    ]
    if any(i["sourceId"] == "ga4" and i["type"] == "channel" for i in items):
        outline.append("GA4 organic sessions vs GSC clicks (discovery vs on-site demand)")
    if any(i["type"] == "query" for i in items):
        outline.append("Top query opportunities and click drivers")
    if any(i["type"] == "page" for i in items):
        outline.append("Top landing page performance highlights (GSC search clicks)")
    if any(i["type"] == "landing_page" for i in items):
        outline.append("Landing page engagement from GA4 (sessions, bounce, time on site)")
    if any(i["sourceId"] == "semrush" and i["type"] == "competitor" for i in items):
        outline.append("Competitive landscape: authority, backlinks, and keyword gaps (Semrush)")
    if any(i["sourceId"] == "semrush" and i["type"] == "phrase" for i in items):
        outline.append("SERP difficulty and leader domains for priority keywords")
    if any(i["sourceId"] == "semrush" and i["type"] == "position" for i in items):
        outline.append("Position tracking vs top competitor ranks")
    if any(i["sourceId"] == "semrush-ai" for i in items):
        outline.append(
            "AI search visibility: mentions, citations, and gaps vs competitors (Semrush AI)"
        )
    if any(i["sourceId"] == "semrush-ai" and i["type"] == "ai_prompt" for i in items):
        outline.append("Prompt-level brand presence and competitor mentions in LLM answers")
    if any(i["sourceId"] == "wordpress" for i in items):
        outline.append("Published WordPress posts aligned with SEO landing pages")
    if any(i["sourceId"] == "webflow" for i in items):
        outline.append("Live Webflow CMS items and last-published timestamps")
    if any(i["sourceId"] == "contentful" for i in items):
        outline.append("Contentful entries (CDA) for structured page inventory")
    outline.append("Recommended next actions for the customer")
    return outline


def filter_normalized_by_selection(
    normalized: Dict[str, Any], included_item_ids: List[str]
) -> Dict[str, Any]:
    included = set(included_item_ids)
    totals = normalized["totals"].copy()

    if "gsc.kpi.clicks" not in included:
        totals.pop("clicks", None)
    if "gsc.kpi.impressions" not in included:
        totals.pop("impressions", None)
    if "gsc.kpi.ctr" not in included:
        totals.pop("ctr", None)
    if "gsc.kpi.position" not in included:
        totals.pop("position", None)

    filtered_queries = []
    for query in normalized.get("topQueries", []):
        item_id = f"gsc.query.{_slugify(query.get('query', ''))}"
        if item_id in included:
            filtered_queries.append(query)

    filtered_pages = []
    for page in normalized.get("topPages", []):
        item_id = f"gsc.page.{_slugify(page.get('page', ''))}"
        if item_id in included:
            filtered_pages.append(page)

    return {
        "dateRange": normalized.get("dateRange", "Unknown date range"),
        "totals": totals,
        "topQueries": filtered_queries,
        "topPages": filtered_pages,
    }
