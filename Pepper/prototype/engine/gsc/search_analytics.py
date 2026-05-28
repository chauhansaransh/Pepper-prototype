import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


DIMENSION_BUCKETS = {
    (): "byProperty",
    ("query",): "byQuery",
    ("page",): "byPage",
}


class SearchAnalyticsClient(Protocol):
    def query(
        self,
        site_url: str,
        start_date: str,
        end_date: str,
        dimensions: Optional[List[str]] = None,
        row_limit: int = 1000,
    ) -> Dict[str, Any]:
        ...


class MockSearchAnalyticsClient:
    """Mock for searchanalytics.query — reads canned API-shaped responses from disk."""

    def __init__(self, fixtures_dir: Path) -> None:
        self._fixtures_dir = fixtures_dir
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _load_customer_fixture(self, customer_id: str) -> Dict[str, Any]:
        if customer_id not in self._cache:
            path = self._fixtures_dir / f"{customer_id}.json"
            if not path.exists():
                raise ValueError(f"No Search Analytics fixture for customer '{customer_id}'.")
            with path.open("r", encoding="utf-8") as f:
                self._cache[customer_id] = json.load(f)
        return self._cache[customer_id]

    def _resolve_customer_id(self, site_url: str) -> str:
        for path in self._fixtures_dir.glob("*.json"):
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("siteUrl") == site_url:
                return path.stem
        raise ValueError(f"No Search Analytics fixture for site '{site_url}'.")

    def _bucket_key(self, dimensions: Optional[List[str]]) -> str:
        dims = tuple(dimensions or [])
        bucket = DIMENSION_BUCKETS.get(dims)
        if not bucket:
            raise ValueError(
                f"Unsupported dimensions {list(dims)}. "
                f"Supported: {list(DIMENSION_BUCKETS.keys())}"
            )
        return bucket

    def query(
        self,
        site_url: str,
        start_date: str,
        end_date: str,
        dimensions: Optional[List[str]] = None,
        row_limit: int = 1000,
        *,
        customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        cid = customer_id or self._resolve_customer_id(site_url)
        fixture = self._load_customer_fixture(cid)

        if fixture.get("siteUrl") != site_url:
            raise ValueError(f"site_url '{site_url}' does not match fixture for '{cid}'.")

        bucket = self._bucket_key(dimensions)
        response = fixture["responses"][bucket].copy()
        rows = response.get("rows") or []
        response["rows"] = rows[:row_limit]
        return response

    def get_fixture_metadata(self, customer_id: str) -> Dict[str, Any]:
        fixture = self._load_customer_fixture(customer_id)
        return {
            "startDate": fixture.get("startDate"),
            "endDate": fixture.get("endDate"),
            "dateRangeLabel": fixture.get("dateRangeLabel", "Unknown date range"),
            "siteUrl": fixture.get("siteUrl"),
            "periodSnapshots": fixture.get("periodSnapshots", {}),
        }
