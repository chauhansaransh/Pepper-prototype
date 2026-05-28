import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .adapter import build_legacy_customer_payload
from .ai_adapter import build_ai_legacy_payload
from .ai_client import MockSemrushAiClient
from .client import MockSemrushClient


class SemrushMockService:
    """Orchestrates mock Semrush SEO + Position Tracking API responses."""

    def __init__(self, mock_root: Path) -> None:
        self._mock_root = mock_root
        self._customers = self._load_customers()
        self._client = MockSemrushClient(mock_root / "reports")
        self._ai_client = MockSemrushAiClient(mock_root / "ai_reports")

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

    def fetch_report(
        self,
        customer_id: str,
        report_type: str,
        *,
        domain: Optional[str] = None,
        phrase: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.get_customer(customer_id)
        return self._client.fetch_report(
            report_type,
            customer_id=customer_id,
            domain=domain,
            phrase=phrase,
        )

    def build_legacy_payload(self, customer_id: str) -> Dict[str, Any]:
        meta = self._client.get_fixture_metadata(customer_id)
        customer_domain = meta["customerDomain"]
        competitors = meta.get("competitors") or []
        all_domains = [customer_domain] + [c["domain"] for c in competitors]

        domain_organic_by_domain = {
            d: self._client.fetch_report(
                "domain_organic", customer_id=customer_id, domain=d
            )
            for d in all_domains
        }
        domain_organic_pages_by_domain = {
            d: self._client.fetch_report(
                "domain_organic_pages", customer_id=customer_id, domain=d
            )
            for d in [customer_domain] + [c["domain"] for c in competitors[:1]]
        }
        backlinks_by_domain = {
            d: self._client.fetch_report(
                "backlinks_overview", customer_id=customer_id, domain=d
            )
            for d in all_domains
        }

        phrase_organic_by_phrase = {
            p: self._client.fetch_report(
                "phrase_organic", customer_id=customer_id, phrase=p
            )
            for p in meta.get("phraseOrganicPhrases") or []
        }
        phrase_kdi_by_phrase = {
            p: self._client.fetch_report(
                "phrase_kdi", customer_id=customer_id, phrase=p
            )
            for p in meta.get("phraseKdiPhrases") or []
        }

        position_tracking = self._client.fetch_report(
            "position_tracking", customer_id=customer_id
        )

        payload = build_legacy_customer_payload(
            customer_domain=customer_domain,
            competitors=competitors,
            domain_organic_by_domain=domain_organic_by_domain,
            domain_organic_pages_by_domain=domain_organic_pages_by_domain,
            phrase_organic_by_phrase=phrase_organic_by_phrase,
            phrase_kdi_by_phrase=phrase_kdi_by_phrase,
            backlinks_by_domain=backlinks_by_domain,
            position_tracking=position_tracking,
            date_range_label=meta["dateRangeLabel"],
        )
        payload["periodSnapshots"] = meta.get("periodSnapshots", {})
        payload["keywordCompetitiveMatrix"] = meta.get("keywordCompetitiveMatrix", {})
        return payload

    def fetch_ai_report(self, customer_id: str, report_type: str) -> Dict[str, Any]:
        self.get_customer(customer_id)
        return self._ai_client.fetch_report(report_type, customer_id=customer_id)

    def build_ai_legacy_payload(self, customer_id: str) -> Dict[str, Any]:
        self.get_customer(customer_id)
        ai_meta = self._ai_client.get_fixture_metadata(customer_id)
        visibility = self._ai_client.fetch_report(
            "ai_visibility_overview", customer_id=customer_id
        )
        prompts = self._ai_client.fetch_report(
            "ai_prompt_mentions", customer_id=customer_id
        )
        citations = self._ai_client.fetch_report(
            "ai_citation_tracking", customer_id=customer_id
        )
        payload = build_ai_legacy_payload(
            visibility,
            prompts,
            citations,
            ai_meta["dateRangeLabel"],
            ai_meta["customerDomain"],
        )
        payload["periodSnapshots"] = ai_meta.get("periodSnapshots", {})
        payload["aiPerformanceMatrix"] = ai_meta.get("aiPerformanceMatrix", {})
        return payload
