# GSC API mocks (Search Analytics + URL Inspection)

The prototype models two [Google Search Console APIs](https://developers.google.com/webmaster-tools) with JSON fixtures and mock clients. Report and extract flows still consume a **legacy aggregated payload** built only from Search Analytics; URL Inspection is mock-ready for future use.

## Fixture layout

```
data/mock_inputs/gsc/
  customers.json
  search_analytics/
    acme-health.json
    northstar-finance.json
  url_inspection/
    acme-health.json
    northstar-finance.json
```

| File | Maps to API method |
|------|-------------------|
| `search_analytics/<customer>.json` | [`searchanalytics.query`](https://developers.google.com/webmaster-tools/v1/searchanalytics/query) |
| `url_inspection/<customer>.json` | [`urlInspection.index.inspect`](https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect) |

## Python modules

| Module | Role |
|--------|------|
| [`engine/gsc/search_analytics.py`](../engine/gsc/search_analytics.py) | `MockSearchAnalyticsClient.query(...)` |
| [`engine/gsc/url_inspection.py`](../engine/gsc/url_inspection.py) | `MockUrlInspectionClient.inspect(...)` |
| [`engine/gsc/adapter.py`](../engine/gsc/adapter.py) | Maps Search Analytics rows → legacy `totals` / `topQueries` / `topPages` |
| [`engine/gsc/service.py`](../engine/gsc/service.py) | `GscMockService` orchestrator |
| [`engine/sources.py`](../engine/sources.py) | `GSCSource` facade used by extract/report |

### Example (in-process)

```python
from pathlib import Path
from engine.gsc.service import GscMockService

root = Path("data/mock_inputs/gsc")
svc = GscMockService(root)

# Raw Search Analytics body (by query)
rows = svc.search_analytics_query("acme-health", dimensions=["query"])

# Legacy shape for normalize_gsc_payload / data_extractor
legacy = svc.build_legacy_payload("acme-health")

# URL Inspection (not wired to extract yet)
result = svc.url_inspection_inspect(
    "acme-health",
    "https://acmehealth.com/blog/protein-guide",
)
```

### Dimensions → fixture bucket

| `dimensions` | Fixture key |
|--------------|-------------|
| `[]` (omit) | `byProperty` |
| `["query"]` | `byQuery` |
| `["page"]` | `byPage` |

## HTTP debug routes

| Route | Query params |
|-------|----------------|
| `GET /api/gsc/search-analytics` | `customerId` (required), `dimensions` optional: `query`, `page`, or omit for property totals |
| `GET /api/gsc/url-inspection` | `customerId`, `url` (full canonical URL as in fixtures) |

Examples:

```bash
curl "http://127.0.0.1:8000/api/gsc/search-analytics?customerId=acme-health&dimensions=query"
curl "http://127.0.0.1:8000/api/gsc/url-inspection?customerId=acme-health&url=https://acmehealth.com/blog/protein-guide"
```

## URL Inspection scope

Fixtures include index status, mobile usability, and rich results per top landing page. At least one URL per customer uses `NEEDS_IMPROVEMENT` / `Crawled - currently not indexed` for contrast. This data is **not** merged into `POST /api/extract` or report generation yet.

## Swapping in real APIs

Implement `SearchAnalyticsClient` and `UrlInspectionClient` protocols (same method signatures as the mock classes) and inject them into `GscMockService` or a future `GscLiveService`. Keep `build_legacy_customer_payload` as the adapter boundary so `pipeline.py` and `data_extractor.py` stay unchanged.
