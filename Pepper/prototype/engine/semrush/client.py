import json
from pathlib import Path
from typing import Any, Dict, Optional, Protocol


REPORT_TYPES = (
    "domain_organic",
    "domain_organic_pages",
    "phrase_organic",
    "phrase_kdi",
    "backlinks_overview",
    "position_tracking",
)


class SemrushClient(Protocol):
    def fetch_report(
        self,
        report_type: str,
        *,
        customer_id: str,
        domain: Optional[str] = None,
        phrase: Optional[str] = None,
    ) -> Dict[str, Any]:
        ...


class MockSemrushClient:
    """Mock Semrush SEO API reports (parsed CSV shape as JSON)."""

    def __init__(self, fixtures_dir: Path) -> None:
        self._fixtures_dir = fixtures_dir
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _load_customer_fixture(self, customer_id: str) -> Dict[str, Any]:
        if customer_id not in self._cache:
            path = self._fixtures_dir / f"{customer_id}.json"
            if not path.exists():
                raise ValueError(f"No Semrush fixture for customer '{customer_id}'.")
            with path.open("r", encoding="utf-8") as f:
                self._cache[customer_id] = json.load(f)
        return self._cache[customer_id]

    def get_fixture_metadata(self, customer_id: str) -> Dict[str, Any]:
        fixture = self._load_customer_fixture(customer_id)
        reports = fixture.get("reports") or {}
        return {
            "customerDomain": fixture.get("customerDomain"),
            "database": fixture.get("database", "us"),
            "dateRangeLabel": fixture.get("dateRangeLabel", "Unknown date range"),
            "competitors": fixture.get("competitors", []),
            "phraseOrganicPhrases": sorted((reports.get("phrase_organic") or {}).keys()),
            "phraseKdiPhrases": sorted((reports.get("phrase_kdi") or {}).keys()),
            "periodSnapshots": fixture.get("periodSnapshots", {}),
            "keywordCompetitiveMatrix": fixture.get("keywordCompetitiveMatrix", {}),
        }

    def fetch_report(
        self,
        report_type: str,
        *,
        customer_id: str,
        domain: Optional[str] = None,
        phrase: Optional[str] = None,
    ) -> Dict[str, Any]:
        if report_type not in REPORT_TYPES:
            supported = ", ".join(REPORT_TYPES)
            raise ValueError(
                f"Unsupported report_type '{report_type}'. Supported: {supported}"
            )

        fixture = self._load_customer_fixture(customer_id)
        reports = fixture.get("reports") or {}

        if report_type == "position_tracking":
            body = reports.get("position_tracking")
            if not body:
                raise ValueError(
                    f"No position_tracking report for customer '{customer_id}'."
                )
            return dict(body)

        bucket = reports.get(report_type)
        if bucket is None:
            raise ValueError(
                f"No '{report_type}' report for customer '{customer_id}'."
            )

        if report_type in ("domain_organic", "domain_organic_pages", "backlinks_overview"):
            if not domain:
                raise ValueError(f"domain is required for report_type '{report_type}'.")
            if domain not in bucket:
                raise ValueError(
                    f"No '{report_type}' data for domain '{domain}' (customer '{customer_id}')."
                )
            return dict(bucket[domain])

        if report_type in ("phrase_organic", "phrase_kdi"):
            if not phrase:
                raise ValueError(f"phrase is required for report_type '{report_type}'.")
            if phrase not in bucket:
                raise ValueError(
                    f"No '{report_type}' data for phrase '{phrase}' (customer '{customer_id}')."
                )
            return dict(bucket[phrase])

        raise ValueError(f"Unhandled report_type '{report_type}'.")
