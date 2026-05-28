# Report data contract

## Wizard flow (2 steps)

1. **Configure** — customer, report template (`weekly` | `monthly` | `quarterly`), optional instructions
2. **Report** — `POST /api/reports/generate` then preview / PDF

Step 2 data review (manual source selection) is **not used** by the wizard. Templates define included data automatically.

## Generate request (`POST /api/reports/generate`)

```json
{
  "customerId": "acme-health",
  "reportType": "weekly",
  "instructions": "optional CSM notes"
}
```

- `reportType` — template id: `weekly`, `monthly`, or `quarterly`
- `includedItemIds` — optional dev override; ignored by default wizard

## Generate response

- `reportHtml`, `reportMarkdown`
- `charts[]`: `{ id, title, filename }`
- `usedLlm`, `llmProvider`, `llmError`
- `customerId`, `customerName`
- `reportType` — template id
- `reportTypeLabel` — human label (e.g. "Weekly Report")
- `templateId`, `sourcesUsed[]`, `dataSourcesUsed[]` (from section `data_sources` in YAML)

## Report templates API (debug)

- `GET /api/report-templates` — list metadata
- `GET /api/report-templates/{id}` — full template definition

See [`report-templates.md`](report-templates.md).

## Extract (`POST /api/extract`) — debug only

Still available; not used by the 2-step wizard. Returns `sources`, `items`, `reportOutline`.

### Item ID conventions

See existing docs: GSC, GA4, Semrush, Semrush AI, CMS item id patterns in prior sections of this file and linked `*-api-mocks.md` files.

## PDF export (`POST /api/reports/pdf`)

Unchanged — see README.

## Environment

- `GEMINI_API_KEY`, `GEMINI_MODEL`
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, etc.
