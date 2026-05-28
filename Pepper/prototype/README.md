# Pepper AI Builder Prototype

## What it does
1. **Configure** — Select customer, report template (Weekly / Monthly / Quarterly), and optional instructions
2. **Report** — Auto-pulls data per template, generates HTML report with charts and OpenRouter narrative; edit or download PDF

Report templates live in [`config/report_templates/`](config/report_templates/) (YAML). Each template defines which sources and APIs to use—no manual data selection in the UI.

## Setup
```bash
cd /Users/saranshchauhan/Documents/Pepper/prototype
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENROUTER_API_KEY="sk-or-v1-your-key-here"
export OPENROUTER_MODEL="openai/gpt-oss-120b:free"   # optional
```

Copy `.env.example` to `.env` for local reference (do not commit `.env`).

## Run
```bash
python engine/api_server.py
```

Open: http://127.0.0.1:8000

For production / sharing on the internet, see **[Deploy guide](docs/deploy.md)** (Render, Railway, Docker).

## API

### `GET /api/customers`
Returns customer list.

### `GET /api/report-templates`
List report template metadata (`weekly`, `monthly`, `quarterly`).

### `GET /api/report-templates/{id}`
Full template definition. See [`docs/report-templates.md`](docs/report-templates.md).

### `POST /api/reports/generate`
Generate HTML + markdown report (wizard Step 1 → 2).
```json
{
  "customerId": "acme-health",
  "reportType": "weekly",
  "instructions": "Focus on blog growth"
}
```

`reportType` is a template id: `weekly`, `monthly`, or `quarterly`.

Response includes `usedLlm`, `llmProvider`, `reportTypeLabel`, `sourcesUsed`, and `llmError`.

### `POST /api/reports/pdf`
Download PDF from final report.

### `POST /api/extract` (debug)
Returns all extract items; not used by the 2-step wizard.

### Source debug routes
GSC, GA4, Semrush, Semrush AI, WordPress, Webflow, Contentful — see [`docs/`](docs/).

### `GET /outputs/charts/<filename>`
Serves chart PNGs for HTML report preview.

## Outputs
- `outputs/sample_report.md`
- `outputs/sample_report.html`
- `outputs/sample_report.pdf`
- `outputs/charts/*.png`

## Environment variables
- `OPENROUTER_API_KEY` — required for LLM narratives and insights
- `OPENROUTER_MODEL` — default `openai/gpt-oss-120b:free`
- `OPENROUTER_HTTP_REFERER`, `OPENROUTER_APP_TITLE` — optional OpenRouter metadata headers
