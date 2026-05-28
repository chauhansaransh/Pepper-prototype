from typing import Any, Dict, List, Optional


def _metric_index(headers: List[Dict[str, Any]]) -> Dict[str, int]:
    return {h["name"]: i for i, h in enumerate(headers)}


def _row_metrics(row: Dict[str, Any], headers: List[Dict[str, Any]]) -> Dict[str, float]:
    idx = _metric_index(headers)
    values = row.get("metricValues") or []
    out: Dict[str, float] = {}
    for name, i in idx.items():
        if i >= len(values):
            continue
        raw = values[i].get("value", "0")
        if name in ("engagementRate", "bounceRate"):
            out[name] = float(raw)
        else:
            out[name] = float(raw) if "." in str(raw) else float(int(raw))
    return out


def _first_row_metrics(response: Dict[str, Any]) -> Dict[str, float]:
    rows = response.get("rows") or []
    headers = response.get("metricHeaders") or []
    if not rows:
        return {}
    return _row_metrics(rows[0], headers)


def _find_channel_row(response: Dict[str, Any], channel: str) -> Optional[Dict[str, float]]:
    headers = response.get("metricHeaders") or []
    for row in response.get("rows") or []:
        dims = row.get("dimensionValues") or []
        if dims and dims[0].get("value") == channel:
            metrics = _row_metrics(row, headers)
            metrics["channel"] = channel
            return metrics
    return None


def _landing_pages_from_response(response: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    headers = response.get("metricHeaders") or []
    pages: List[Dict[str, Any]] = []
    for row in response.get("rows") or []:
        dims = row.get("dimensionValues") or []
        path = dims[0].get("value", "N/A") if dims else "N/A"
        metrics = _row_metrics(row, headers)
        pages.append(
            {
                "pagePath": path,
                "sessions": int(metrics.get("sessions", 0)),
                "activeUsers": int(metrics.get("activeUsers", 0)),
                "bounceRate": float(metrics.get("bounceRate", 0.0)),
                "averageSessionDuration": float(
                    metrics.get("averageSessionDuration", 0.0)
                ),
            }
        )
    pages.sort(key=lambda p: p["sessions"], reverse=True)
    return pages[:limit]


def build_legacy_customer_payload(
    property_totals: Dict[str, Any],
    by_channel: Dict[str, Any],
    by_landing_page: Dict[str, Any],
    date_range_label: str,
) -> Dict[str, Any]:
    """Map runReport bodies to a compact shape for extract / normalize."""
    totals_raw = _first_row_metrics(property_totals)
    organic = _find_channel_row(by_channel, "Organic Search") or {}

    return {
        "dateRange": date_range_label,
        "totals": {
            "sessions": int(totals_raw.get("sessions", 0)),
            "activeUsers": int(totals_raw.get("activeUsers", 0)),
            "engagedSessions": int(totals_raw.get("engagedSessions", 0)),
            "engagementRate": float(totals_raw.get("engagementRate", 0.0)),
            "conversions": int(totals_raw.get("conversions", 0)),
        },
        "organicChannel": {
            "channel": "Organic Search",
            "sessions": int(organic.get("sessions", 0)),
            "activeUsers": int(organic.get("activeUsers", 0)),
        },
        "topLandingPages": _landing_pages_from_response(by_landing_page),
    }


def normalize_ga4_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Trim legacy GA4 payload for downstream use."""
    totals = payload.get("totals", {})
    return {
        "dateRange": payload.get("dateRange", "Unknown date range"),
        "totals": {
            "sessions": int(totals.get("sessions", 0)),
            "activeUsers": int(totals.get("activeUsers", 0)),
            "engagedSessions": int(totals.get("engagedSessions", 0)),
            "engagementRate": float(totals.get("engagementRate", 0.0)),
            "conversions": int(totals.get("conversions", 0)),
        },
        "organicChannel": payload.get("organicChannel", {}),
        "topLandingPages": (payload.get("topLandingPages") or [])[:3],
        "lastWeekSegments": payload.get("lastWeekSegments", {}),
        "periodSnapshots": payload.get("periodSnapshots", {}),
    }
