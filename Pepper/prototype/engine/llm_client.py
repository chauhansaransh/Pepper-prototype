import os
from typing import Any, Dict, Optional, Tuple

try:
    from prompts import build_storytelling_prompt, build_template_storytelling_prompt
except ImportError:
    from .prompts import build_storytelling_prompt, build_template_storytelling_prompt


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
OPENROUTER_REFERER = os.environ.get("OPENROUTER_HTTP_REFERER", "http://localhost:8000")
OPENROUTER_APP_TITLE = os.environ.get("OPENROUTER_APP_TITLE", "Pepper AI Builder Prototype")

_POINTER_WRITING_RULES = """
Writing rules (strict):
- Output markdown bullets only (- ), no headings or preamble.
- Each bullet is 1-2 complete sentences (about 25-50 words).
- Cite specific values from the table: metric names, numbers, % changes, page paths, queries, or statuses.
- Do not invent metrics, URLs, queries, or trends that are not in the table.
- Explain what the data shows and the recommended next step.
- Professional Customer Success tone; complete thoughts, not telegraphic fragments.
"""

_RECOMMENDATION_WRITING_RULES = """
Writing rules (strict):
- Output exactly 4 markdown bullets (- ), no headings or preamble.
- Each bullet is 1-2 complete sentences (about 30-55 words).
- Ground every recommendation in the weekly report tables (cite metrics, pages, queries, competitors, or URLs).
- Do not invent data; if something is unclear, recommend verifying it in the source tools.
- Prioritize highest-impact actions across SEO, content, technical, and competitive areas.
"""


def generate_narrative_report(
    customer_name: str,
    report_type: str,
    instructions: str,
    normalized: Dict[str, Any],
) -> Tuple[Optional[str], Optional[str], str]:
    """Legacy: GSC-only narrative."""
    prompt = build_storytelling_prompt(
        customer_name=customer_name,
        report_type=report_type,
        instructions=instructions,
        normalized=normalized,
    )
    return _run_llm(prompt)


def generate_template_narrative_report(
    customer_name: str,
    template: Dict[str, Any],
    report_context: Dict[str, Any],
    instructions: str,
) -> Tuple[Optional[str], Optional[str], str]:
    """Multi-source narrative driven by report template + context."""
    prompt = build_template_storytelling_prompt(
        customer_name=customer_name,
        template=template,
        report_context=report_context,
        instructions=instructions,
    )
    return _run_llm(prompt)


def _run_pointer_llm(prompt: str) -> Tuple[Optional[str], Optional[str], str]:
    return _run_llm(prompt, max_tokens=600)


def generate_executive_table_insights(
    customer_name: str,
    report_type: str,
    executive_table_markdown: str,
    instructions: str,
) -> Tuple[Optional[str], Optional[str], str]:
    safe_instructions = instructions.strip() or "No additional CSM instructions."
    prompt = f"""You are a senior Customer Success analyst.
Generate 2-3 insights for the Executive Summary section.

Customer: {customer_name}
Report type: {report_type}
CSM instructions: {safe_instructions}

Use ONLY the executive summary table below.
Each bullet must reference at least one metric with its current value and week-over-week % change.
{_POINTER_WRITING_RULES}

Executive Summary Table:
{executive_table_markdown}
"""
    return _run_pointer_llm(prompt)


def generate_deliverables_status_pointers(
    customer_name: str,
    report_type: str,
    deliverables_table_markdown: str,
    instructions: str,
) -> Tuple[Optional[str], Optional[str], str]:
    safe_instructions = instructions.strip() or "No additional CSM instructions."
    prompt = f"""You are a senior Customer Success analyst.
Generate 2-3 insights for the Deliverables section.

Customer: {customer_name}
Report type: {report_type}
CSM instructions: {safe_instructions}

Use ONLY the deliverables table below.
Each bullet must name a specific content item or CMS row and the action needed.
{_POINTER_WRITING_RULES}

Deliverables Table:
{deliverables_table_markdown}
"""
    return _run_pointer_llm(prompt)


def generate_top_pages_pointers(
    customer_name: str,
    report_type: str,
    top_pages_table_markdown: str,
    instructions: str,
) -> Tuple[Optional[str], Optional[str], str]:
    safe_instructions = instructions.strip() or "No additional CSM instructions."
    prompt = f"""You are a senior SEO and Customer Success analyst.
Generate 2-3 insights for the Top Pages section.

Customer: {customer_name}
Report type: {report_type}
CSM instructions: {safe_instructions}

Use ONLY the top pages table below.
Each bullet must name a page path and cite clicks, impressions, CTR, or position from the table.
{_POINTER_WRITING_RULES}

Top Pages Table:
{top_pages_table_markdown}
"""
    return _run_pointer_llm(prompt)


def generate_top_queries_pointers(
    customer_name: str,
    report_type: str,
    top_queries_table_markdown: str,
    instructions: str,
) -> Tuple[Optional[str], Optional[str], str]:
    safe_instructions = instructions.strip() or "No additional CSM instructions."
    prompt = f"""You are a senior SEO and Customer Success analyst.
Generate 2-3 insights for the Top Queries section.

Customer: {customer_name}
Report type: {report_type}
CSM instructions: {safe_instructions}

Use ONLY the top queries table below.
Each bullet must name a query and cite clicks, impressions, CTR, or average position from the table.
{_POINTER_WRITING_RULES}

Top Queries Table:
{top_queries_table_markdown}
"""
    return _run_pointer_llm(prompt)


def generate_weekly_recommendations(
    customer_name: str,
    report_type: str,
    report_markdown: str,
    instructions: str,
) -> Tuple[Optional[str], Optional[str], str]:
    safe_instructions = instructions.strip() or "No additional CSM instructions."
    prompt = f"""You are a senior Customer Success and SEO lead.
Write 4-5 recommendations for the final Recommendations section.

Customer: {customer_name}
Report type: {report_type}
CSM instructions: {safe_instructions}

Read the full weekly report below (all tables and section insights).
Prioritize the highest-impact next steps and cover different areas (SEO, content, technical, competitive) when the data supports it.
{_RECOMMENDATION_WRITING_RULES}

Report:
{report_markdown}
"""
    return _run_llm(prompt, max_tokens=1024)


def _run_llm(
    prompt: str, *, max_tokens: int = 2500
) -> Tuple[Optional[str], Optional[str], str]:
    """Returns (markdown, error_message, llm_provider). Uses OpenRouter only."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return (
            None,
            "No LLM API key configured. Set OPENROUTER_API_KEY.",
            "none",
        )

    narrative, err = _call_openrouter(prompt, api_key, max_tokens=max_tokens)
    if narrative:
        return narrative, None, "openrouter"
    return None, err or "OpenRouter request failed.", "none"


def _call_openrouter(
    prompt: str, api_key: str, *, max_tokens: int = 2500
) -> Tuple[Optional[str], Optional[str]]:
    try:
        from openai import OpenAI

        client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": OPENROUTER_REFERER,
                "X-Title": OPENROUTER_APP_TITLE,
            },
        )
        completion = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            max_tokens=max_tokens,
            temperature=0.35,
            messages=[{"role": "user", "content": prompt}],
        )
        narrative = (completion.choices[0].message.content or "").strip()
        if not narrative:
            return None, "OpenRouter returned an empty response."
        return narrative, None
    except Exception as exc:
        return None, f"OpenRouter API error: {exc}"
