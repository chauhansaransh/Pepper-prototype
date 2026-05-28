import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .adapter import build_legacy_customer_payload
from .search_analytics import MockSearchAnalyticsClient
from .url_inspection import MockUrlInspectionClient


class GscMockService:
    """Orchestrates mock Search Analytics and URL Inspection clients."""

    def __init__(self, mock_root: Path) -> None:
        self._mock_root = mock_root
        self._customers = self._load_customers()
        self._search_analytics = MockSearchAnalyticsClient(
            mock_root / "search_analytics"
        )
        self._url_inspection = MockUrlInspectionClient(mock_root / "url_inspection")

    def _load_customers(self) -> List[Dict[str, str]]:
        path = self._mock_root / "customers.json"
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("customers", [])

    def list_customers(self) -> List[Dict[str, str]]:
        return list(self._customers)

    def get_customer(self, customer_id: str) -> Dict[str, str]:
        for customer in self._customers:
            if customer["id"] == customer_id:
                return customer
        raise ValueError(f"Unknown customer '{customer_id}'.")

    def search_analytics_query(
        self,
        customer_id: str,
        dimensions: Optional[List[str]] = None,
        row_limit: int = 1000,
    ) -> Dict[str, Any]:
        customer = self.get_customer(customer_id)
        meta = self._search_analytics.get_fixture_metadata(customer_id)
        return self._search_analytics.query(
            site_url=customer["property"],
            start_date=meta["startDate"],
            end_date=meta["endDate"],
            dimensions=dimensions,
            row_limit=row_limit,
            customer_id=customer_id,
        )

    def build_legacy_payload(self, customer_id: str) -> Dict[str, Any]:
        customer = self.get_customer(customer_id)
        meta = self._search_analytics.get_fixture_metadata(customer_id)
        property_response = self._search_analytics.query(
            site_url=customer["property"],
            start_date=meta["startDate"],
            end_date=meta["endDate"],
            dimensions=[],
            customer_id=customer_id,
        )
        query_response = self._search_analytics.query(
            site_url=customer["property"],
            start_date=meta["startDate"],
            end_date=meta["endDate"],
            dimensions=["query"],
            customer_id=customer_id,
        )
        page_response = self._search_analytics.query(
            site_url=customer["property"],
            start_date=meta["startDate"],
            end_date=meta["endDate"],
            dimensions=["page"],
            customer_id=customer_id,
        )
        payload = build_legacy_customer_payload(
            property_response,
            query_response,
            page_response,
            meta["dateRangeLabel"],
        )
        payload["periodSnapshots"] = meta.get("periodSnapshots", {})
        return payload

    def url_inspection_inspect(self, customer_id: str, inspection_url: str) -> Dict[str, Any]:
        customer = self.get_customer(customer_id)
        return self._url_inspection.inspect(
            site_url=customer["property"],
            inspection_url=inspection_url,
            customer_id=customer_id,
        )

    def list_url_inspections(self, customer_id: str) -> Dict[str, Dict[str, Any]]:
        self.get_customer(customer_id)
        return self._url_inspection.list_inspections(customer_id)

    def list_url_inspection_urls(self, customer_id: str) -> List[str]:
        self.get_customer(customer_id)
        return self._url_inspection.list_inspection_urls(customer_id)
