import json
from pathlib import Path
from typing import Any, Dict, List

from .adapters import (
    normalize_contentful_payload,
    normalize_webflow_payload,
    normalize_wordpress_payload,
)
from .contentful import MockContentfulClient
from .webflow import MockWebflowClient
from .wordpress import MockWordPressClient


class CmsMockService:
    """Orchestrates WordPress, Webflow, and Contentful mock API clients."""

    def __init__(self, mock_root: Path) -> None:
        self._mock_root = mock_root
        self._customers = self._load_customers()
        self._wordpress = MockWordPressClient(mock_root / "wordpress")
        self._webflow = MockWebflowClient(mock_root / "webflow")
        self._contentful = MockContentfulClient(mock_root / "contentful")

    def _load_customers(self) -> List[Dict[str, Any]]:
        path = self._mock_root / "customers.json"
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("customers", [])

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        for customer in self._customers:
            if customer["id"] == customer_id:
                return customer
        raise ValueError(f"Unknown customer '{customer_id}'.")

    def list_posts_wordpress(self, customer_id: str) -> Dict[str, Any]:
        return self._wordpress.list_posts(customer_id)

    def list_items_webflow(self, customer_id: str) -> Dict[str, Any]:
        customer = self.get_customer(customer_id)
        collection_id = (customer.get("webflow") or {}).get("collectionId", "")
        return self._webflow.list_live_items(customer_id, collection_id)

    def list_entries_contentful(self, customer_id: str) -> Dict[str, Any]:
        customer = self.get_customer(customer_id)
        cfg = customer.get("contentful") or {}
        return self._contentful.list_entries(
            customer_id, cfg.get("space", ""), cfg.get("environment", "master")
        )

    def build_wordpress_payload(self, customer_id: str) -> Dict[str, Any]:
        raw = self.list_posts_wordpress(customer_id)
        return normalize_wordpress_payload(raw, raw.get("dateRangeLabel", "Live"))

    def build_webflow_payload(self, customer_id: str) -> Dict[str, Any]:
        raw = self.list_items_webflow(customer_id)
        return normalize_webflow_payload(raw, raw.get("dateRangeLabel", "Live"))

    def build_contentful_payload(self, customer_id: str) -> Dict[str, Any]:
        raw = self.list_entries_contentful(customer_id)
        return normalize_contentful_payload(raw, raw.get("dateRangeLabel", "Live"))
