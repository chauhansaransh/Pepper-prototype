import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


class UrlInspectionClient(Protocol):
    def inspect(
        self,
        site_url: str,
        inspection_url: str,
        language_code: str = "en-US",
    ) -> Dict[str, Any]:
        ...


class MockUrlInspectionClient:
    """Mock for urlInspection.index.inspect — reads canned responses from disk."""

    def __init__(self, fixtures_dir: Path) -> None:
        self._fixtures_dir = fixtures_dir
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _load_customer_fixture(self, customer_id: str) -> Dict[str, Any]:
        if customer_id not in self._cache:
            path = self._fixtures_dir / f"{customer_id}.json"
            if not path.exists():
                raise ValueError(f"No URL Inspection fixture for customer '{customer_id}'.")
            with path.open("r", encoding="utf-8") as f:
                self._cache[customer_id] = json.load(f)
        return self._cache[customer_id]

    def inspect(
        self,
        site_url: str,
        inspection_url: str,
        language_code: str = "en-US",
        *,
        customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        cid = customer_id
        if not cid:
            for path in self._fixtures_dir.glob("*.json"):
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("siteUrl") == site_url:
                    cid = path.stem
                    break
        if not cid:
            raise ValueError(f"No URL Inspection fixture for site '{site_url}'.")

        fixture = self._load_customer_fixture(cid)
        if fixture.get("siteUrl") != site_url:
            raise ValueError(f"site_url '{site_url}' does not match fixture for '{cid}'.")

        inspections = fixture.get("inspections") or {}
        if inspection_url not in inspections:
            raise ValueError(
                f"No inspection mock for URL '{inspection_url}' (customer '{cid}')."
            )

        return inspections[inspection_url]

    def list_inspection_urls(self, customer_id: str) -> List[str]:
        fixture = self._load_customer_fixture(customer_id)
        return list((fixture.get("inspections") or {}).keys())

    def list_inspections(self, customer_id: str) -> Dict[str, Dict[str, Any]]:
        fixture = self._load_customer_fixture(customer_id)
        return dict(fixture.get("inspections") or {})
