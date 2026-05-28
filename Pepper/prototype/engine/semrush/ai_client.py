import json
from pathlib import Path
from typing import Any, Dict, Optional, Protocol


AI_REPORT_TYPES = (
    "ai_visibility_overview",
    "ai_prompt_mentions",
    "ai_citation_tracking",
)


class SemrushAiClient(Protocol):
    def fetch_report(
        self,
        report_type: str,
        *,
        customer_id: str,
    ) -> Dict[str, Any]:
        ...


class MockSemrushAiClient:
    """Mock Semrush AI Visibility API reports."""

    def __init__(self, fixtures_dir: Path) -> None:
        self._fixtures_dir = fixtures_dir
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _load_customer_fixture(self, customer_id: str) -> Dict[str, Any]:
        if customer_id not in self._cache:
            path = self._fixtures_dir / f"{customer_id}.json"
            if not path.exists():
                raise ValueError(
                    f"No Semrush AI fixture for customer '{customer_id}'."
                )
            with path.open("r", encoding="utf-8") as f:
                self._cache[customer_id] = json.load(f)
        return self._cache[customer_id]

    def get_fixture_metadata(self, customer_id: str) -> Dict[str, Any]:
        fixture = self._load_customer_fixture(customer_id)
        return {
            "customerDomain": fixture.get("customerDomain"),
            "dateRangeLabel": fixture.get("dateRangeLabel", "Unknown date range"),
            "periodSnapshots": fixture.get("periodSnapshots", {}),
            "aiPerformanceMatrix": fixture.get("aiPerformanceMatrix", {}),
        }

    def fetch_report(
        self,
        report_type: str,
        *,
        customer_id: str,
    ) -> Dict[str, Any]:
        if report_type not in AI_REPORT_TYPES:
            supported = ", ".join(AI_REPORT_TYPES)
            raise ValueError(
                f"Unsupported report_type '{report_type}'. Supported: {supported}"
            )

        fixture = self._load_customer_fixture(customer_id)
        reports = fixture.get("reports") or {}
        body = reports.get(report_type)
        if not body:
            raise ValueError(
                f"No '{report_type}' AI report for customer '{customer_id}'."
            )
        return dict(body)
