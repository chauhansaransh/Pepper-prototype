# Semrush API mocks (competitor analysis)

The prototype models six Semrush surfaces used for **competitor analysis**, complementing GSC (search performance) and GA4 (on-site behavior).

## Endpoints mocked

| Report key | Semrush API `type` | Role |
|------------|-------------------|------|
| `domain_organic` | `domain_organic` | Organic keywords a domain ranks for |
| `domain_organic_pages` | `domain_organic_pages` | Top organic landing URLs |
| `phrase_organic` | `phrase_organic` | SERP leaders for a keyword |
| `phrase_kdi` | `phrase_kdi` | Keyword difficulty (Kd) |
| `backlinks_overview` | `backlinks_overview` | Backlink / authority summary |
| `position_tracking` | Position Tracking API | Campaign keyword ranks vs competitors |

Fixtures use a **parsed CSV shape** (`columns` + `rows` with Semrush column codes such as `Ph`, `Po`, `Nq`, `Kd`) instead of raw CSV strings.

## Fixture layout

```
data/mock_inputs/semrush/
  customers.json
  reports/
    acme-health.json
    northstar-finance.json
```

Each customer file defines:

- `customerDomain` and two `competitors`
- Per-domain buckets for `domain_organic`, `domain_organic_pages`, `backlinks_overview`
- Per-phrase buckets for `phrase_organic` / `phrase_kdi` (aligned with GSC top queries)
- A single `position_tracking` campaign snapshot

## Python modules

| Module | Role |
|--------|------|
| [`engine/semrush/client.py`](../engine/semrush/client.py) | `MockSemrushClient.fetch_report(...)` |
| [`engine/semrush/adapter.py`](../engine/semrush/adapter.py) | Aggregates reports → legacy extract payload |
| [`engine/semrush/service.py`](../engine/semrush/service.py) | `SemrushMockService` |
| [`engine/sources.py`](../engine/sources.py) | `SemrushSource` |

## Extract item IDs

- `semrush.kpi.authority-score`, `semrush.kpi.organic-keywords`
- `semrush.competitor.<domain-slug>`
- `semrush.keyword.<phrase-slug>`, `semrush.page.<url-slug>`
- `semrush.phrase.<phrase-slug>` (KDI + SERP leaders)
- `semrush.backlinks.overview`
- `semrush.position.<phrase-slug>`

Report generation remains **GSC-only**; Semrush feeds Step 2 review and outline bullets.

## HTTP debug route

`GET /api/semrush/report?customerId=acme-health&type=domain_organic&domain=acmehealth.com`

| `type` | Extra query params |
|--------|-------------------|
| `domain_organic`, `domain_organic_pages`, `backlinks_overview` | `domain` (required) |
| `phrase_organic`, `phrase_kdi` | `phrase` (required) |
| `position_tracking` | none |

Examples:

```bash
curl "http://127.0.0.1:8000/api/semrush/report?customerId=acme-health&type=phrase_kdi&phrase=best%20protein%20for%20women"
curl "http://127.0.0.1:8000/api/semrush/report?customerId=acme-health&type=position_tracking"
```

## Semrush AI Data

AI Visibility mocks live under `ai_reports/` and surface in extract as source **Semrush AI Visibility** (`semrush-ai`).

| Report key | Purpose |
|------------|---------|
| `ai_visibility_overview` | Visibility score, mentions, citations, LLM breakdown, competitor benchmark |
| `ai_prompt_mentions` | Per-prompt brand mention vs competitors |
| `ai_citation_tracking` | Cited URLs, counts, avg citation position |

Debug route: `GET /api/semrush-ai/report?customerId=acme-health&type=ai_visibility_overview`

Extract item IDs: `semrush-ai.kpi.visibility-score`, `semrush-ai.competitor.*`, `semrush-ai.prompt.*`, `semrush-ai.citation.*`

See also [Semrush AI Visibility Toolkit](https://www.semrush.com/kb/1493-ai-visibility-toolkit).

## Official references

- [Semrush SEO API overview](https://developer.semrush.com/api/seo/overview/)
- [Keyword reports](https://developer.semrush.com/api/seo/keyword-reports/) (`phrase_organic`, `phrase_kdi`)
- [Backlinks](https://developer.semrush.com/api/seo/backlinks/) (`backlinks_overview`)
- [Position Tracking API](https://developer.semrush.com/api/projects/position-tracking/)
