# GA4 API mocks (Data API runReport)

The prototype models the [GA4 Data API `runReport`](https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/properties/runReport) method with JSON fixtures. GA4 **complements GSC** in Step 2 extract: search clicks and rankings from GSC, site sessions and engagement from GA4 (aligned landing paths and date range).

## Fixture layout

```
data/mock_inputs/ga4/
  customers.json
  run_reports/
    acme-health.json
    northstar-finance.json
```

| Fixture key | Typical request | Purpose |
|-------------|-----------------|--------|
| `propertyTotals` | No dimensions; property KPIs | Sessions, users, engagement, conversions |
| `byChannel` | `sessionDefaultChannelGroup` | Organic Search vs other channels (vs GSC clicks) |
| `byLandingPage` | `landingPage` | Same paths as GSC top pages; sessions, bounce, duration |

## Python modules

| Module | Role |
|--------|------|
| [`engine/ga4/run_report.py`](../engine/ga4/run_report.py) | `MockRunReportClient.run_report(...)` |
| [`engine/ga4/adapter.py`](../engine/ga4/adapter.py) | Maps runReport bodies → compact legacy payload for extract |
| [`engine/ga4/service.py`](../engine/ga4/service.py) | `Ga4MockService` orchestrator |
| [`engine/sources.py`](../engine/sources.py) | `GA4Source` facade |

### Example (in-process)

```python
from pathlib import Path
from engine.ga4.service import Ga4MockService

svc = Ga4MockService(Path("data/mock_inputs/ga4"))
organic = svc.run_report("acme-health", "byChannel")
legacy = svc.build_legacy_payload("acme-health")
```

## Extract item IDs

- `ga4.kpi.sessions`, `ga4.kpi.activeUsers`, `ga4.kpi.engagedSessions`, `ga4.kpi.engagementRate`, `ga4.kpi.conversions`
- `ga4.channel.organic-search` — complements `gsc.kpi.clicks`
- `ga4.page.<slug>` — complements `gsc.page.<slug>` (same paths)

Included by default: sessions, active users, organic channel, top landing pages. Engagement KPIs and conversions are opt-in.

## HTTP debug route

`GET /api/ga4/run-report?customerId=acme-health&report=byChannel`

`report` values: `propertyTotals`, `byChannel`, `byLandingPage`.

## Report generation

Final report generation still uses **GSC-only** normalized data. GA4 items appear in Step 2 for CSM review; wiring GA4 into narrative/charts is a follow-up.

## Swapping in the real API

Implement `RunReportClient` against `analyticsdata.properties.runReport` with the same `report_key` buckets and keep `build_legacy_customer_payload` as the adapter boundary.
