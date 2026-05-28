import json
from pathlib import Path
from typing import Any, Dict, Protocol


class WebflowClient(Protocol):
    def list_live_items(self, customer_id: str, collection_id: str) -> Dict[str, Any]:
        ...


class MockWebflowClient:
    """Mock for GET /v2/collections/{collection_id}/items/live."""

    def __init__(self, fixtures_dir: Path) -> None:
        self._fixtures_dir = fixtures_dir
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _load(self, customer_id: str) -> Dict[str, Any]:
        if customer_id not in self._cache:
            path = self._fixtures_dir / f"{customer_id}.json"
            if not path.exists():
                raise ValueError(f"No Webflow fixture for customer '{customer_id}'.")
            with path.open("r", encoding="utf-8") as f:
                self._cache[customer_id] = json.load(f)
        return self._cache[customer_id]

    def list_live_items(self, customer_id: str, collection_id: str) -> Dict[str, Any]:
        data = self._load(customer_id)
        fixture_collection = data.get("collectionId")
        if collection_id and fixture_collection != collection_id:
            raise ValueError(
                f"collection_id '{collection_id}' does not match fixture '{fixture_collection}'."
            )
        return {
            "endpoint": data.get("endpoint"),
            "collectionId": fixture_collection,
            "siteId": data.get("siteId"),
            "dateRangeLabel": data.get("dateRangeLabel", "Live CMS items"),
            "items": list(data.get("items") or []),
            "pagination": dict(data.get("pagination") or {}),
        }
