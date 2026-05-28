from typing import Any, Dict, List, Optional


def _first_row(report: Dict[str, Any]) -> Dict[str, Any]:
    rows = report.get("rows") or []
    return dict(rows[0]) if rows else {}


def _float_val(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int_val(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _parse_domain_organic_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    parsed = []
    for row in rows:
        parsed.append(
            {
                "keyword": row.get("Ph", ""),
                "position": _int_val(row.get("Po")),
                "searchVolume": _int_val(row.get("Nq")),
                "trafficPercent": _float_val(row.get("Tr")),
                "cpc": _float_val(row.get("Cp")),
                "url": row.get("Ur", ""),
            }
        )
    return parsed


def _parse_organic_pages(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    parsed = []
    for row in rows:
        parsed.append(
            {
                "url": row.get("Ur", ""),
                "keywordsCount": _int_val(row.get("Pc")),
                "trafficPercent": _float_val(row.get("Tr")),
                "position": _int_val(row.get("Po")),
            }
        )
    return parsed


def _parse_backlinks(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "authorityScore": _int_val(row.get("ascore")),
        "totalBacklinks": _int_val(row.get("total")),
        "referringDomains": _int_val(row.get("domains_num")),
        "referringUrls": _int_val(row.get("urls_num")),
        "followLinks": _int_val(row.get("follows_num")),
        "nofollowLinks": _int_val(row.get("nofollows_num")),
    }


def _parse_position_tracking(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = report.get("rows") or []
    parsed = []
    for row in rows:
        parsed.append(
            {
                "keyword": row.get("keyword", ""),
                "position": _int_val(row.get("position")),
                "previousPosition": _int_val(row.get("previousPosition")),
                "visibility": _float_val(row.get("visibility")),
                "competitorBestDomain": row.get("competitorBestDomain", ""),
                "competitorBestPosition": _int_val(row.get("competitorBestPosition")),
            }
        )
    return parsed


def _merge_phrase_insight(
    phrase: str,
    phrase_organic: Optional[Dict[str, Any]],
    phrase_kdi: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    kdi_row = _first_row(phrase_kdi or {})
    serp_rows = (phrase_organic or {}).get("rows") or []
    leaders = [
        {
            "domain": r.get("Dn", ""),
            "url": r.get("Ur", ""),
            "position": _int_val(r.get("Po")),
        }
        for r in serp_rows[:5]
    ]
    return {
        "phrase": phrase,
        "keywordDifficulty": _int_val(kdi_row.get("Kd")),
        "serpLeaders": leaders,
        "topSerpDomain": leaders[0]["domain"] if leaders else "",
    }


def build_legacy_customer_payload(
    customer_domain: str,
    competitors: List[Dict[str, str]],
    domain_organic_by_domain: Dict[str, Dict[str, Any]],
    domain_organic_pages_by_domain: Dict[str, Dict[str, Any]],
    phrase_organic_by_phrase: Dict[str, Dict[str, Any]],
    phrase_kdi_by_phrase: Dict[str, Dict[str, Any]],
    backlinks_by_domain: Dict[str, Dict[str, Any]],
    position_tracking: Dict[str, Any],
    date_range_label: str,
) -> Dict[str, Any]:
    customer_organic = _parse_domain_organic_rows(
        (domain_organic_by_domain.get(customer_domain) or {}).get("rows") or []
    )
    customer_pages = _parse_organic_pages(
        (domain_organic_pages_by_domain.get(customer_domain) or {}).get("rows") or []
    )
    customer_backlinks = _parse_backlinks(
        _first_row(backlinks_by_domain.get(customer_domain) or {})
    )

    competitor_summaries = []
    for comp in competitors:
        domain = comp["domain"]
        organic_rows = _parse_domain_organic_rows(
            (domain_organic_by_domain.get(domain) or {}).get("rows") or []
        )
        bl = _parse_backlinks(_first_row(backlinks_by_domain.get(domain) or {}))
        competitor_summaries.append(
            {
                "domain": domain,
                "label": comp.get("label", domain),
                "topKeywords": organic_rows[:3],
                "authorityScore": bl.get("authorityScore", 0),
                "totalBacklinks": bl.get("totalBacklinks", 0),
                "referringDomains": bl.get("referringDomains", 0),
            }
        )

    phrases = sorted(
        set(phrase_organic_by_phrase.keys()) | set(phrase_kdi_by_phrase.keys())
    )
    phrase_insights = [
        _merge_phrase_insight(
            phrase,
            phrase_organic_by_phrase.get(phrase),
            phrase_kdi_by_phrase.get(phrase),
        )
        for phrase in phrases
    ]

    return {
        "dateRange": date_range_label,
        "customerDomain": customer_domain,
        "competitors": competitors,
        "customerKeywords": customer_organic,
        "customerPages": customer_pages,
        "customerBacklinks": customer_backlinks,
        "competitorSummaries": competitor_summaries,
        "phraseInsights": phrase_insights,
        "positionTracking": {
            "campaignId": position_tracking.get("campaignId"),
            "campaignName": position_tracking.get("campaignName"),
            "targetDomain": position_tracking.get("targetDomain"),
            "keywords": _parse_position_tracking(position_tracking),
        },
    }


def normalize_semrush_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "dateRange": payload.get("dateRange", "Unknown date range"),
        "customerDomain": payload.get("customerDomain", ""),
        "competitors": payload.get("competitors", []),
        "customerKeywords": (payload.get("customerKeywords") or [])[:5],
        "customerPages": (payload.get("customerPages") or [])[:3],
        "customerBacklinks": payload.get("customerBacklinks", {}),
        "competitorSummaries": (payload.get("competitorSummaries") or [])[:3],
        "phraseInsights": (payload.get("phraseInsights") or [])[:5],
        "positionTracking": payload.get("positionTracking", {}),
        "periodSnapshots": payload.get("periodSnapshots", {}),
        "keywordCompetitiveMatrix": payload.get("keywordCompetitiveMatrix", {}),
    }
