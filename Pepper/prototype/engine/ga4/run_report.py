import json
from pathlib import Path
from typing import Any, Dict, Optional, Protocol


REPORT_BUCKETS = {
    "propertyTotals": "propertyTotals",
    "byChannel": "byChannel",
    "byLandingPage": "byLandingPage",
}


class RunReportClient(Protocol):
    def run_report(
        self,
        property_id: str,
        report_key: str,
        *,
        customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        ...


class MockRunReportClient:
    """Mock for analyticsdata.properties.runReport — reads canned responses from disk."""

    def __init__(self, fixtures_dir: Path) -> None:
        self._fixtures_dir = fixtures_dir
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _load_customer_fixture(self, customer_id: str) -> Dict[str, Any]:
        if customer_id not in self._cache:
            path = self._fixtures_dir / f"{customer_id}.json"
            if not path.exists():
                raise ValueError(f"No GA4 runReport fixture for customer '{customer_id}'.")
            with path.open("r", encoding="utf-8") as f:
                self._cache[customer_id] = json.load(f)
        return self._cache[customer_id]

    def _resolve_customer_id(self, property_id: str) -> str:
        for path in self._fixtures_dir.glob("*.json"):
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("propertyId") == property_id:
                return path.stem
        raise ValueError(f"No GA4 runReport fixture for property '{property_id}'.")

    def run_report(
        self,
        property_id: str,
        report_key: str,
        *,
        customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        bucket = REPORT_BUCKETS.get(report_key)
        if not bucket:
            supported = ", ".join(REPORT_BUCKETS.keys())
            raise ValueError(
                f"Unsupported report_key '{report_key}'. Supported: {supported}"
            )

        cid = customer_id or self._resolve_customer_id(property_id)
        fixture = self._load_customer_fixture(cid)

        if fixture.get("propertyId") != property_id:
            raise ValueError(
                f"property_id '{property_id}' does not match fixture for '{cid}'."
            )

        reports = fixture.get("reports") or {}
        if bucket not in reports:
            raise ValueError(f"No '{bucket}' report in fixture for customer '{cid}'.")
        return dict(reports[bucket])

    def get_fixture_metadata(self, customer_id: str) -> Dict[str, Any]:
        fixture = self._load_customer_fixture(customer_id)
        return {
            "propertyId": fixture.get("propertyId"),
            "startDate": fixture.get("startDate"),
            "endDate": fixture.get("endDate"),
            "dateRangeLabel": fixture.get("dateRangeLabel", "Unknown date range"),
        }
