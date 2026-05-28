import json
from pathlib import Path
from typing import Any, Dict, Protocol


class WordPressClient(Protocol):
    def list_posts(self, customer_id: str) -> Dict[str, Any]:
        ...


class MockWordPressClient:
    """Mock for GET /wp-json/wp/v2/posts."""

    def __init__(self, fixtures_dir: Path) -> None:
        self._fixtures_dir = fixtures_dir
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _load(self, customer_id: str) -> Dict[str, Any]:
        if customer_id not in self._cache:
            path = self._fixtures_dir / f"{customer_id}.json"
            if not path.exists():
                raise ValueError(f"No WordPress fixture for customer '{customer_id}'.")
            with path.open("r", encoding="utf-8") as f:
                self._cache[customer_id] = json.load(f)
        return self._cache[customer_id]

    def list_posts(self, customer_id: str) -> Dict[str, Any]:
        data = self._load(customer_id)
        return {
            "endpoint": data.get("endpoint", "/wp-json/wp/v2/posts"),
            "siteUrl": data.get("siteUrl"),
            "dateRangeLabel": data.get("dateRangeLabel", "Published content (live)"),
            "items": list(data.get("items") or []),
            "totalItems": int(data.get("totalItems", len(data.get("items") or []))),
        }
