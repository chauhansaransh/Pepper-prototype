from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from cms.service import CmsMockService
    from ga4.service import Ga4MockService
    from gsc.service import GscMockService
    from semrush.service import SemrushMockService
except ImportError:
    from .cms.service import CmsMockService
    from .ga4.service import Ga4MockService
    from .gsc.service import GscMockService
    from .semrush.service import SemrushMockService


class GSCSource:
    """Loads GSC data via mock Search Analytics + URL Inspection clients."""

    def __init__(self, mock_root: Path) -> None:
        self._service = GscMockService(mock_root)

    def list_customers(self) -> List[Dict[str, str]]:
        return self._service.list_customers()

    def get_customer_payload(self, customer_id: str) -> Dict[str, Any]:
        try:
            return self._service.build_legacy_payload(customer_id)
        except ValueError as exc:
            raise ValueError(f"No GSC payload found for customer '{customer_id}'.") from exc

    def search_analytics_query(
        self,
        customer_id: str,
        dimensions: Optional[List[str]] = None,
        row_limit: int = 1000,
    ) -> Dict[str, Any]:
        return self._service.search_analytics_query(
            customer_id, dimensions=dimensions, row_limit=row_limit
        )

    def get_url_inspection(self, customer_id: str, inspection_url: str) -> Dict[str, Any]:
        return self._service.url_inspection_inspect(customer_id, inspection_url)

    def list_url_inspections(self, customer_id: str) -> Dict[str, Dict[str, Any]]:
        return self._service.list_url_inspections(customer_id)

    def list_url_inspection_urls(self, customer_id: str) -> List[str]:
        return self._service.list_url_inspection_urls(customer_id)


class GA4Source:
    """Loads GA4 data via mock Data API runReport client."""

    def __init__(self, mock_root: Path) -> None:
        self._service = Ga4MockService(mock_root)

    def list_customers(self) -> List[Dict[str, str]]:
        return self._service.list_customers()

    def get_customer_payload(self, customer_id: str) -> Dict[str, Any]:
        try:
            return self._service.build_legacy_payload(customer_id)
        except ValueError as exc:
            raise ValueError(f"No GA4 payload found for customer '{customer_id}'.") from exc

    def run_report(self, customer_id: str, report_key: str) -> Dict[str, Any]:
        return self._service.run_report(customer_id, report_key)


class SemrushSource:
    """Loads Semrush data via mock SEO API + Position Tracking clients."""

    def __init__(self, mock_root: Path) -> None:
        self._service = SemrushMockService(mock_root)

    def list_customers(self) -> List[Dict[str, str]]:
        return self._service.list_customers()

    def get_customer_payload(self, customer_id: str) -> Dict[str, Any]:
        try:
            return self._service.build_legacy_payload(customer_id)
        except ValueError as exc:
            raise ValueError(
                f"No Semrush payload found for customer '{customer_id}'."
            ) from exc

    def fetch_report(
        self,
        customer_id: str,
        report_type: str,
        *,
        domain: Optional[str] = None,
        phrase: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._service.fetch_report(
            customer_id,
            report_type,
            domain=domain,
            phrase=phrase,
        )

    def get_ai_payload(self, customer_id: str) -> Dict[str, Any]:
        try:
            return self._service.build_ai_legacy_payload(customer_id)
        except ValueError as exc:
            raise ValueError(
                f"No Semrush AI payload found for customer '{customer_id}'."
            ) from exc

    def fetch_ai_report(self, customer_id: str, report_type: str) -> Dict[str, Any]:
        return self._service.fetch_ai_report(customer_id, report_type)


class WordPressSource:
    def __init__(self, mock_root: Path) -> None:
        self._service = CmsMockService(mock_root)

    def get_customer_payload(self, customer_id: str) -> Dict[str, Any]:
        try:
            return self._service.build_wordpress_payload(customer_id)
        except ValueError as exc:
            raise ValueError(
                f"No WordPress payload found for customer '{customer_id}'."
            ) from exc

    def list_posts(self, customer_id: str) -> Dict[str, Any]:
        return self._service.list_posts_wordpress(customer_id)


class WebflowSource:
    def __init__(self, mock_root: Path) -> None:
        self._service = CmsMockService(mock_root)

    def get_customer_payload(self, customer_id: str) -> Dict[str, Any]:
        try:
            return self._service.build_webflow_payload(customer_id)
        except ValueError as exc:
            raise ValueError(
                f"No Webflow payload found for customer '{customer_id}'."
            ) from exc

    def list_live_items(self, customer_id: str) -> Dict[str, Any]:
        return self._service.list_items_webflow(customer_id)


class ContentfulSource:
    def __init__(self, mock_root: Path) -> None:
        self._service = CmsMockService(mock_root)

    def get_customer_payload(self, customer_id: str) -> Dict[str, Any]:
        try:
            return self._service.build_contentful_payload(customer_id)
        except ValueError as exc:
            raise ValueError(
                f"No Contentful payload found for customer '{customer_id}'."
            ) from exc

    def list_entries(self, customer_id: str) -> Dict[str, Any]:
        return self._service.list_entries_contentful(customer_id)
