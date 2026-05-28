import json
from typing import Any, Dict, List


def build_storytelling_prompt(
    customer_name: str,
    report_type: str,
    instructions: str,
    normalized: Dict[str, Any],
) -> str:
    """Legacy GSC-only prompt (kept for backward compatibility)."""
    safe_instructions = instructions.strip() or "No additional CSM instructions."
    metrics_json = json.dumps(normalized, indent=2)

    return f"""You are a senior Customer Success analyst at Pepper Atlas.
Write a customer-facing SEO performance report in markdown.

Customer: {customer_name}
Report type: {report_type}
CSM instructions: {safe_instructions}

Use ONLY the metrics below. Do not invent numbers.

GSC metrics (JSON):
{metrics_json}

Requirements:
1. Tell a clear story: context -> what happened -> why it matters -> recommended next steps.
2. Use these sections with markdown headings:
   - Executive Summary
   - Performance Story
   - Key Wins
   - Areas to Improve
   - Recommended Actions (3-5 bullets)
3. Keep tone professional, concise, and client-ready.
4. Reference specific queries/pages from the data when relevant.
5. Do not include chart images or placeholders; charts are added separately in PDF export.
6. Output markdown only, no preamble.
"""


def _format_section_instructions(structured_sections: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for section in structured_sections:
        title = section.get("title", "Section")
        stype = section.get("type", "")
        generated = section.get("generatedBy")
        data_sources = section.get("dataSources") or []
        if generated == "llm":
            lines.append(
                f"   - ## {title} (type: {stype}) — synthesize from prior sections; no new metrics"
            )
        elif data_sources:
            ds = ", ".join(data_sources)
            lines.append(f"   - ## {title} (type: {stype}) — data: {ds}")
        else:
            lines.append(f"   - ## {title} (type: {stype})")
    return "\n".join(lines) if lines else "   (use template.sections headings)"


def build_template_storytelling_prompt(
    customer_name: str,
    template: Dict[str, Any],
    report_context: Dict[str, Any],
    instructions: str,
) -> str:
    safe_instructions = instructions.strip() or "No additional CSM instructions."
    structured = template.get("structuredSections") or []
    if structured:
        sections_block = _format_section_instructions(structured)
    else:
        sections_list = template.get("sections") or []
        sections_block = "\n".join(f"   - ## {s}" for s in sections_list)

    context_for_llm = {
        "customerId": report_context.get("customerId"),
        "selectedItems": report_context.get("selectedItems"),
        "sectionData": report_context.get("sectionData"),
        "gsc": report_context.get("gsc"),
        "ga4": report_context.get("ga4"),
        "semrush": report_context.get("semrush"),
        "semrushAi": report_context.get("semrushAi"),
        "wordpress": report_context.get("wordpress"),
        "webflow": report_context.get("webflow"),
        "contentful": report_context.get("contentful"),
        "gscUrlInspection": report_context.get("gscUrlInspection"),
    }
    context_json = json.dumps(
        {k: v for k, v in context_for_llm.items() if v is not None},
        indent=2,
    )

    metadata = template.get("metadata") or {}
    objective = metadata.get("objective", "")

    return f"""You are a senior Customer Success analyst at Pepper Atlas.
Write a customer-facing report in markdown using the template sections and data below.

Customer: {customer_name}
Report type: {template.get('label', template.get('id', 'Report'))}
Reporting period: {template.get('periodLabel', 'Unknown')}
Objective: {objective or 'See template guidance.'}
CSM instructions: {safe_instructions}

Template guidance:
{template.get('llmGuide', 'Follow standard SEO storytelling best practices.')}

Required markdown sections (use ## headings exactly as titled):
{sections_block}

Section layout hints:
- kpi_grid: bullet KPIs with values from sectionData
- table / dual_table / multi_table: markdown tables using columns implied by section type
- ai_signal_summary / trend_analysis / competitive_analysis / geo_analysis: short narrative + bullets
- grouped_list / grouped_summary: subheadings per group with bullet lists
- llm_summary / llm_analysis / priority_table: your synthesis only from provided data
- goal_tracking_table: table with goal, target, actual, status when data supports it

Data context (JSON) — use ONLY these numbers and labels; do not invent metrics:
{context_json}

Requirements:
1. Follow section order and titles from the template.
2. For each section, prefer metrics in sectionData[].data for that section's dataSources.
3. Top-level payloads (gsc, ga4, semrush, semrushAi, wordpress, webflow, contentful, gscUrlInspection) are authoritative.
4. Reference specific queries, pages, competitors, prompts, or URLs from selectedItems when relevant.
5. Keep tone professional, concise, and client-ready.
6. Do not include chart images or placeholders.
7. Output markdown only, no preamble.
"""
