from typing import Any, Dict, List


def _row_to_query(row: Dict[str, Any]) -> Dict[str, Any]:
    keys = row.get("keys") or []
    return {
        "query": keys[0] if keys else "N/A",
        "clicks": int(row.get("clicks", 0)),
        "impressions": int(row.get("impressions", 0)),
        "ctr": float(row.get("ctr", 0.0)),
        "position": float(row.get("position", 0.0)),
    }


def _row_to_page(row: Dict[str, Any]) -> Dict[str, Any]:
    keys = row.get("keys") or []
    return {
        "page": keys[0] if keys else "N/A",
        "clicks": int(row.get("clicks", 0)),
        "impressions": int(row.get("impressions", 0)),
        "ctr": float(row.get("ctr", 0.0)),
        "position": float(row.get("position", 0.0)),
    }


def _top_rows_by_clicks(rows: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda r: int(r.get("clicks", 0)), reverse=True)
    return sorted_rows[:limit]


def build_legacy_customer_payload(
    property_response: Dict[str, Any],
    query_response: Dict[str, Any],
    page_response: Dict[str, Any],
    date_range_label: str,
) -> Dict[str, Any]:
    """Map Search Analytics API bodies to the legacy gscResponseByCustomer shape."""
    property_rows = property_response.get("rows") or []
    if not property_rows:
        totals = {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0}
    else:
        row = property_rows[0]
        totals = {
            "clicks": int(row.get("clicks", 0)),
            "impressions": int(row.get("impressions", 0)),
            "ctr": float(row.get("ctr", 0.0)),
            "position": float(row.get("position", 0.0)),
        }

    query_rows = _top_rows_by_clicks(query_response.get("rows") or [])
    page_rows = _top_rows_by_clicks(page_response.get("rows") or [])

    return {
        "dateRange": date_range_label,
        "totals": totals,
        "topQueries": [_row_to_query(r) for r in query_rows],
        "topPages": [_row_to_page(r) for r in page_rows],
    }
