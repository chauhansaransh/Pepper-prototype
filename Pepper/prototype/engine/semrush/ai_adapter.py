from typing import Any, Dict, List


def build_ai_legacy_payload(
    visibility_overview: Dict[str, Any],
    prompt_mentions: Dict[str, Any],
    citation_tracking: Dict[str, Any],
    date_range_label: str,
    customer_domain: str,
) -> Dict[str, Any]:
    metrics = visibility_overview.get("metrics") or {}
    return {
        "dateRange": date_range_label,
        "customerDomain": customer_domain,
        "visibilityOverview": {
            "visibilityScore": int(metrics.get("visibilityScore", 0)),
            "mentions": int(metrics.get("mentions", 0)),
            "citations": int(metrics.get("citations", 0)),
            "citedPages": int(metrics.get("citedPages", 0)),
            "monthlyAudience": int(metrics.get("monthlyAudience", 0)),
            "byLlm": visibility_overview.get("byLlm") or [],
            "competitorComparison": visibility_overview.get("competitorComparison") or [],
        },
        "promptMentions": list(prompt_mentions.get("rows") or []),
        "citationTracking": list(citation_tracking.get("rows") or []),
    }


def normalize_semrush_ai_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    overview = payload.get("visibilityOverview") or {}
    return {
        "dateRange": payload.get("dateRange", "Unknown date range"),
        "customerDomain": payload.get("customerDomain", ""),
        "visibilityOverview": overview,
        "promptMentions": (payload.get("promptMentions") or [])[:6],
        "citationTracking": (payload.get("citationTracking") or [])[:5],
    }
