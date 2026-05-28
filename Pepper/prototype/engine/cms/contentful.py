import json
from pathlib import Path
from typing import Any, Dict, Protocol


class ContentfulClient(Protocol):
    def list_entries(
        self, customer_id: str, space: str, environment: str
    ) -> Dict[str, Any]:
        ...


class MockContentfulClient:
    """Mock for Content Delivery API GET .../spaces/{space}/environments/{env}/entries."""

    def __init__(self, fixtures_dir: Path) -> None:
        self._fixtures_dir = fixtures_dir
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _load(self, customer_id: str) -> Dict[str, Any]:
        if customer_id not in self._cache:
            path = self._fixtures_dir / f"{customer_id}.json"
            if not path.exists():
                raise ValueError(f"No Contentful fixture for customer '{customer_id}'.")
            with path.open("r", encoding="utf-8") as f:
                self._cache[customer_id] = json.load(f)
        return self._cache[customer_id]

    def list_entries(
        self, customer_id: str, space: str, environment: str
    ) -> Dict[str, Any]:
        data = self._load(customer_id)
        if data.get("space") != space:
            raise ValueError(f"space '{space}' does not match fixture space '{data.get('space')}'.")
        if data.get("environment") != environment:
            raise ValueError(
                f"environment '{environment}' does not match fixture "
                f"'{data.get('environment')}'."
            )
        return {
            "endpoint": data.get("endpoint"),
            "space": data.get("space"),
            "environment": data.get("environment"),
            "dateRangeLabel": data.get("dateRangeLabel", "CDA entries (published)"),
            "sys": data.get("sys", {"type": "Array"}),
            "total": int(data.get("total", 0)),
            "skip": int(data.get("skip", 0)),
            "limit": int(data.get("limit", 100)),
            "items": list(data.get("items") or []),
        }
