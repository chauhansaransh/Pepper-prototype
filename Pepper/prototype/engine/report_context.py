from typing import Any, Dict, List, Optional

try:
    from data_extractor import extract_customer_data, filter_normalized_by_selection
    from report_templates import (
        DATA_SOURCE_SPECS,
        ReportTemplate,
        resolve_included_item_ids,
    )
    from sources import (
        ContentfulSource,
        GA4Source,
        GSCSource,
        SemrushSource,
        WebflowSource,
        WordPressSource,
    )
except ImportError:
    from .data_extractor import extract_customer_data, filter_normalized_by_selection
    from .report_templates import (
        DATA_SOURCE_SPECS,
        ReportTemplate,
        resolve_included_item_ids,
    )
    from .sources import (
        ContentfulSource,
        GA4Source,
        GSCSource,
        SemrushSource,
        WebflowSource,
        WordPressSource,
    )


SOURCE_NORMALIZED_KEYS = {
    "gsc": "normalized",
    "ga4": "ga4Normalized",
    "semrush": "semrushNormalized",
    "semrush-ai": "semrushAiNormalized",
    "wordpress": "wordpressNormalized",
    "webflow": "webflowNormalized",
    "contentful": "contentfulNormalized",
}

CONTEXT_KEY_BY_SOURCE = {
    "gsc": "gsc",
    "ga4": "ga4",
    "semrush": "semrush",
    "semrush-ai": "semrushAi",
    "wordpress": "wordpress",
    "webflow": "webflow",
    "contentful": "contentful",
}


def normalize_url_inspections(
    inspections: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Compact rows for LLM from GSC URL Inspection mock payloads."""
    rows: List[Dict[str, Any]] = []
    for url, payload in inspections.items():
        result = payload.get("inspectionResult") or {}
        index_status = result.get("indexStatusResult") or {}
        mobile = result.get("mobileUsabilityResult") or {}
        rich = result.get("richResultsResult") or {}
        verdict = index_status.get("verdict", "UNKNOWN")
        coverage = index_status.get("coverageState", "")
        severity = "low"
        if verdict == "NEEDS_IMPROVEMENT":
            severity = "medium"
        if "not indexed" in coverage.lower():
            severity = "high"
        rows.append(
            {
                "url": url,
                "verdict": verdict,
                "coverageState": coverage,
                "indexingState": index_status.get("indexingState"),
                "lastCrawlTime": index_status.get("lastCrawlTime"),
                "mobileUsability": mobile.get("verdict"),
                "richResults": rich.get("verdict"),
                "issue": coverage if verdict != "PASS" else None,
                "severity": severity if verdict != "PASS" else "none",
                "recommendation": _url_inspection_recommendation(verdict, coverage),
            }
        )
    return rows


def _url_inspection_recommendation(verdict: str, coverage: str) -> Optional[str]:
    if verdict == "PASS":
        return None
    if "not indexed" in coverage.lower():
        return "Investigate indexing blockers and internal links to this URL."
    if verdict == "NEEDS_IMPROVEMENT":
        return "Review crawl/index signals and compare canonical URLs."
    return "Monitor and re-request indexing after fixes."


def build_section_data(
    template: ReportTemplate,
    extracted: Dict[str, Any],
    url_inspection_rows: Optional[List[Dict[str, Any]]],
    included_ids: List[str],
) -> List[Dict[str, Any]]:
    """Per-template-section view of which APIs/data apply for the LLM."""
    included = set(included_ids)
    section_payloads: List[Dict[str, Any]] = []

    for section in template.structured_sections:
        entry: Dict[str, Any] = {
            "id": section.id,
            "title": section.title,
            "type": section.section_type,
            "dataSources": list(section.data_sources),
            "generatedBy": section.generated_by,
            "data": {},
        }
        if section.generated_by == "llm" and not section.data_sources:
            section_payloads.append(entry)
            continue

        for ds in section.data_sources:
            if ds == "gsc.url_inspection" and url_inspection_rows is not None:
                entry["data"]["gscUrlInspection"] = url_inspection_rows
                continue

            spec = DATA_SOURCE_SPECS.get(ds)
            if not spec:
                continue
            source_id = spec["sourceId"]
            extracted_key = SOURCE_NORMALIZED_KEYS.get(source_id)
            if not extracted_key:
                continue
            payload = extracted.get(extracted_key)
            if payload is None:
                continue
            context_key = CONTEXT_KEY_BY_SOURCE.get(source_id, source_id)
            if context_key not in entry["data"]:
                entry["data"][context_key] = _slice_payload_for_section(
                    payload, source_id, included
                )

        section_payloads.append(entry)

    return section_payloads


def _slice_payload_for_section(
    payload: Dict[str, Any],
    source_id: str,
    included_ids: set,
) -> Dict[str, Any]:
    """Return a smaller payload when GSC items are filtered; other sources pass through."""
    if source_id != "gsc":
        return payload
    return filter_normalized_by_selection(payload, list(included_ids))


def build_report_context(
    customer_id: str,
    template: ReportTemplate,
    gsc_source: GSCSource,
    ga4_source: Optional[GA4Source],
    semrush_source: Optional[SemrushSource],
    wordpress_source: Optional[WordPressSource],
    webflow_source: Optional[WebflowSource],
    contentful_source: Optional[ContentfulSource],
) -> Dict[str, Any]:
    extracted = extract_customer_data(
        customer_id,
        gsc_source,
        ga4_source,
        semrush_source,
        wordpress_source,
        webflow_source,
        contentful_source,
    )

    included_ids = resolve_included_item_ids(template, extracted["items"])
    selected_items = [i for i in extracted["items"] if i["id"] in included_ids]

    url_inspection_rows: Optional[List[Dict[str, Any]]] = None
    if template.requires_url_inspection:
        raw_inspections = gsc_source.list_url_inspections(customer_id)
        url_inspection_rows = normalize_url_inspections(raw_inspections)

    section_data = build_section_data(
        template, extracted, url_inspection_rows, included_ids
    )

    context: Dict[str, Any] = {
        "template": {
            "id": template.id,
            "label": template.label,
            "periodLabel": template.period_label,
            "sections": template.sections,
            "structuredSections": [s.to_dict() for s in template.structured_sections],
            "metadata": template.metadata,
            "dataSources": template.data_sources,
            "llmGuide": template.llm_guide,
            "apis": template.apis,
            "sources": template.sources,
        },
        "customerId": customer_id,
        "selectedItemIds": included_ids,
        "selectedItems": [
            {
                "id": i["id"],
                "sourceId": i["sourceId"],
                "type": i["type"],
                "label": i["label"],
                "summary": i["summary"],
                "metrics": i.get("metrics", {}),
            }
            for i in selected_items
        ],
        "sectionData": section_data,
    }

    for source_id in template.sources:
        extracted_key = SOURCE_NORMALIZED_KEYS.get(source_id)
        if not extracted_key:
            continue
        payload = extracted.get(extracted_key)
        if payload is not None:
            context_key = CONTEXT_KEY_BY_SOURCE.get(source_id, source_id)
            if source_id == "gsc":
                context[context_key] = filter_normalized_by_selection(
                    payload, included_ids
                )
            else:
                context[context_key] = payload

    if url_inspection_rows is not None:
        context["gscUrlInspection"] = url_inspection_rows

    gsc_full = extracted.get("normalized") or {}
    context["gscFiltered"] = filter_normalized_by_selection(gsc_full, included_ids)

    return context


def get_gsc_normalized_for_charts(context: Dict[str, Any]) -> Dict[str, Any]:
    return context.get("gscFiltered") or context.get("gsc") or {}
