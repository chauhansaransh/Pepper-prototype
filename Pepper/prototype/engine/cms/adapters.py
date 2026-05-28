import re
from typing import Any, Dict, List


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def normalize_wordpress_payload(
    api_response: Dict[str, Any], date_range_label: str
) -> Dict[str, Any]:
    posts: List[Dict[str, Any]] = []
    for item in api_response.get("items") or []:
        title = item.get("title") or {}
        excerpt = item.get("excerpt") or {}
        posts.append(
            {
                "id": item.get("id"),
                "slug": item.get("slug", ""),
                "title": _strip_html(title.get("rendered", "")),
                "excerpt": _strip_html(excerpt.get("rendered", "")),
                "link": item.get("link", ""),
                "status": item.get("status", ""),
                "date": item.get("date", ""),
                "modified": item.get("modified", ""),
            }
        )
    return {
        "dateRange": date_range_label,
        "siteUrl": api_response.get("siteUrl", ""),
        "endpoint": api_response.get("endpoint", "/wp-json/wp/v2/posts"),
        "totalItems": api_response.get("totalItems", len(posts)),
        "posts": posts,
        "periodSnapshots": api_response.get("periodSnapshots", {}),
    }


def normalize_webflow_payload(
    api_response: Dict[str, Any], date_range_label: str
) -> Dict[str, Any]:
    items_out: List[Dict[str, Any]] = []
    for item in api_response.get("items") or []:
        fields = item.get("fieldData") or {}
        items_out.append(
            {
                "id": item.get("id", ""),
                "name": fields.get("name", ""),
                "slug": fields.get("slug", ""),
                "urlPath": fields.get("url-path", ""),
                "metaDescription": fields.get("meta-description", ""),
                "lastPublished": item.get("lastPublished", ""),
                "isDraft": bool(item.get("isDraft", False)),
            }
        )
    pagination = api_response.get("pagination") or {}
    return {
        "dateRange": date_range_label,
        "collectionId": api_response.get("collectionId", ""),
        "siteId": api_response.get("siteId", ""),
        "endpoint": api_response.get("endpoint", ""),
        "totalItems": int(pagination.get("total", len(items_out))),
        "items": items_out,
        "periodSnapshots": api_response.get("periodSnapshots", {}),
    }


def normalize_contentful_payload(
    api_response: Dict[str, Any], date_range_label: str
) -> Dict[str, Any]:
    entries_out: List[Dict[str, Any]] = []
    for item in api_response.get("items") or []:
        sys = item.get("sys") or {}
        fields = item.get("fields") or {}
        content_type = (sys.get("contentType") or {}).get("sys") or {}
        entries_out.append(
            {
                "id": sys.get("id", ""),
                "contentType": content_type.get("id", ""),
                "title": fields.get("title", ""),
                "slug": fields.get("slug", ""),
                "path": fields.get("path", ""),
                "publishDate": fields.get("publishDate", ""),
                "seoDescription": fields.get("seoDescription", ""),
                "updatedAt": sys.get("updatedAt", ""),
            }
        )
    return {
        "dateRange": date_range_label,
        "space": api_response.get("space", ""),
        "environment": api_response.get("environment", "master"),
        "endpoint": api_response.get("endpoint", ""),
        "total": api_response.get("total", len(entries_out)),
        "entries": entries_out,
        "periodSnapshots": api_response.get("periodSnapshots", {}),
    }
