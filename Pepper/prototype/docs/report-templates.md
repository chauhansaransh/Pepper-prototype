# Report templates (code-defined)

Report types are configured as YAML files under [`config/report_templates/`](../config/report_templates/). The wizard uses template **id** values (`weekly`, `monthly`, `quarterly`). Each file defines **sections** with `data_sources` that drive which mocks are loaded for generation.

## Files

| File | Root key | Primary data sources |
|------|----------|----------------------|
| `weekly.yaml` | `weekly_report` | GSC, GA4, Semrush, Semrush AI, CMS, URL Inspection |
| `monthly.yaml` | `monthly_report` | GSC, GA4, Semrush, Semrush AI |
| `quarterly.yaml` | `quarterly_report` | GSC, GA4, Semrush, Semrush AI |

## Section schema

```yaml
weekly_report:
  metadata:
    report_type: "Weekly Report"
    audience: ["Analyst", "CSM"]
    objective: "Operational monitoring..."
  sections:
    - id: executive_snapshot
      title: "Executive Snapshot"
      type: kpi_grid
      data_sources:
        - gsc.search_analytics
        - ga4.run_report
      metrics: [...]          # layout hint for LLM
    - id: next_actions
      title: "Recommended Next Actions"
      type: priority_table
      generated_by: llm       # no data_sources — LLM synthesizes
```

### Supported `data_sources` keys

| Key | Extract source | Mock API |
|-----|----------------|----------|
| `gsc.search_analytics` | `gsc` | Search Analytics |
| `gsc.url_inspection` | `gsc` | URL Inspection (all fixture URLs) |
| `ga4.run_report` | `ga4` | GA4 Data API runReport |
| `semrush.report` | `semrush` | Semrush SEO reports |
| `semrush_ai.ai_visibility_overview` | `semrush-ai` | AI visibility overview |
| `semrush_ai.ai_prompt_mentions` | `semrush-ai` | AI prompt mentions |
| `semrush_ai.ai_citation_tracking` | `semrush-ai` | AI citation tracking |
| `wordpress.posts` | `wordpress` | WordPress posts |
| `webflow.items` | `webflow` | Webflow live items |
| `contentful.entries` | `contentful` | Contentful CDA entries |

Registry: [`DATA_SOURCE_SPECS`](../engine/report_templates.py).

## How generation uses templates

1. [`load_template()`](../engine/report_templates.py) parses `{weekly|monthly|quarterly}_report` and derives `sources`, `includeItemPatterns`, and `dataSources` from all section `data_sources`.
2. [`extract_customer_data()`](../engine/data_extractor.py) pulls normalized payloads for required sources.
3. [`resolve_included_item_ids()`](../engine/report_templates.py) filters extract items by source + glob patterns.
4. [`build_report_context()`](../engine/report_context.py) builds `sectionData` (per-section data slices), top-level source JSON, and `gscUrlInspection` when `gsc.url_inspection` is referenced.
5. [`generate_template_narrative_report()`](../engine/llm_client.py) sends structured sections + context to the LLM.

Charts still use **GSC** metrics from the filtered template selection.

## Legacy schema (still supported)

```yaml
id: weekly
sources: [gsc, ga4]
includeItemPatterns: ["gsc.*"]
sections: ["Executive Summary"]
llmGuide: |
  ...
```

## Editing templates

1. Change YAML in `config/report_templates/`.
2. Restart the API server.
3. Inspect: `GET /api/report-templates` or `GET /api/report-templates/weekly`.

## Wizard flow

**Configure → Report** (no manual source selection). `POST /api/extract` remains for debugging.
