import json
from pathlib import Path
from typing import Any, Dict, List

from .adapter import build_legacy_customer_payload
from .run_report import MockRunReportClient


class Ga4MockService:
    """Orchestrates mock GA4 Data API runReport responses."""

    def __init__(self, mock_root: Path) -> None:
        self._mock_root = mock_root
        self._customers = self._load_customers()
        self._run_report = MockRunReportClient(mock_root / "run_reports")

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

    def run_report(self, customer_id: str, report_key: str) -> Dict[str, Any]:
        customer = self.get_customer(customer_id)
        return self._run_report.run_report(
            property_id=customer["propertyId"],
            report_key=report_key,
            customer_id=customer_id,
        )

    def build_legacy_payload(self, customer_id: str) -> Dict[str, Any]:
        customer = self.get_customer(customer_id)
        meta = self._run_report.get_fixture_metadata(customer_id)
        property_totals = self._run_report.run_report(
            property_id=customer["propertyId"],
            report_key="propertyTotals",
            customer_id=customer_id,
        )
        by_channel = self._run_report.run_report(
            property_id=customer["propertyId"],
            report_key="byChannel",
            customer_id=customer_id,
        )
        by_landing_page = self._run_report.run_report(
            property_id=customer["propertyId"],
            report_key="byLandingPage",
            customer_id=customer_id,
        )
        return build_legacy_customer_payload(
            property_totals,
            by_channel,
            by_landing_page,
            meta["dateRangeLabel"],
        )
