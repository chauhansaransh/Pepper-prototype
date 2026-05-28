import os
from typing import Any, Dict, Optional, Tuple

try:
    from prompts import build_storytelling_prompt, build_template_storytelling_prompt
except ImportError:
    from .prompts import build_storytelling_prompt, build_template_storytelling_prompt


GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
OPENROUTER_REFERER = os.environ.get("OPENROUTER_HTTP_REFERER", "http://localhost:8000")
OPENROUTER_APP_TITLE = os.environ.get("OPENROUTER_APP_TITLE", "Pepper AI Builder Prototype")


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


def _run_llm(prompt: str) -> Tuple[Optional[str], Optional[str], str]:
    """Returns (markdown, error_message, llm_provider)."""
    errors: list[str] = []
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()

    if gemini_key:
        narrative, err = _call_gemini(prompt, gemini_key)
        if narrative:
            return narrative, None, "gemini"
        if err:
            errors.append(err)

    if openrouter_key:
        narrative, err = _call_openrouter(prompt, openrouter_key)
        if narrative:
            return narrative, None, "openrouter"
        if err:
            errors.append(err)

    if not gemini_key and not openrouter_key:
        return (
            None,
            "No LLM API keys configured. Set GEMINI_API_KEY and/or OPENROUTER_API_KEY.",
            "none",
        )

    combined = " | ".join(errors) if errors else "All LLM providers failed."
    return None, combined, "none"


def _call_gemini(prompt: str, api_key: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        narrative = (response.text or "").strip()
        if not narrative:
            return None, "Gemini returned an empty response."
        return narrative, None
    except Exception as exc:
        return None, f"Gemini API error: {exc}"


def _call_openrouter(prompt: str, api_key: str) -> Tuple[Optional[str], Optional[str]]:
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
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}],
        )
        narrative = (completion.choices[0].message.content or "").strip()
        if not narrative:
            return None, "OpenRouter returned an empty response."
        return narrative, None
    except Exception as exc:
        return None, f"OpenRouter API error: {exc}"
