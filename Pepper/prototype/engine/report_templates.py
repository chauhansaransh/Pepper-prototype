import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT_DIR / "config" / "report_templates"

REPORT_TYPE_OPTIONS = [
    {"id": "weekly", "label": "Weekly Report"},
    {"id": "monthly", "label": "Monthly Report"},
    {"id": "quarterly", "label": "Quarterly Report"},
]

# Maps template data_sources keys (from YAML) to extract source ids and item globs.
DATA_SOURCE_SPECS: Dict[str, Dict[str, Any]] = {
    "gsc.search_analytics": {
        "sourceId": "gsc",
        "api": "search_analytics",
        "itemPatterns": ["gsc.*"],
    },
    "gsc.url_inspection": {
        "sourceId": "gsc",
        "api": "url_inspection",
        "itemPatterns": [],
        "requiresUrlInspection": True,
    },
    "ga4.run_report": {
        "sourceId": "ga4",
        "api": "run_report",
        "itemPatterns": ["ga4.*"],
    },
    "semrush.report": {
        "sourceId": "semrush",
        "api": "report",
        "itemPatterns": ["semrush.*"],
    },
    "semrush_ai.ai_visibility_overview": {
        "sourceId": "semrush-ai",
        "api": "ai_visibility_overview",
        "itemPatterns": [
            "semrush-ai.kpi.*",
            "semrush-ai.competitor.*",
            "semrush-ai.llm.*",
        ],
    },
    "semrush_ai.ai_prompt_mentions": {
        "sourceId": "semrush-ai",
        "api": "ai_prompt_mentions",
        "itemPatterns": ["semrush-ai.prompt.*", "semrush-ai.llm.*"],
    },
    "semrush_ai.ai_citation_tracking": {
        "sourceId": "semrush-ai",
        "api": "ai_citation_tracking",
        "itemPatterns": ["semrush-ai.citation.*"],
    },
    "wordpress.posts": {
        "sourceId": "wordpress",
        "api": "posts",
        "itemPatterns": ["wordpress.*"],
    },
    "webflow.items": {
        "sourceId": "webflow",
        "api": "items",
        "itemPatterns": ["webflow.*"],
    },
    "contentful.entries": {
        "sourceId": "contentful",
        "api": "entries",
        "itemPatterns": ["contentful.*"],
    },
}


@dataclass
class TemplateSection:
    id: str
    title: str
    section_type: str
    data_sources: List[str] = field(default_factory=list)
    generated_by: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "type": self.section_type,
        }
        if self.data_sources:
            out["dataSources"] = list(self.data_sources)
        if self.generated_by:
            out["generatedBy"] = self.generated_by
        out.update(self.extra)
        return out


@dataclass
class ReportTemplate:
    id: str
    label: str
    period_label: str
    sources: List[str]
    include_item_patterns: List[str]
    apis: Dict[str, List[str]]
    sections: List[str]
    llm_guide: str
    structured_sections: List[TemplateSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    data_sources: List[str] = field(default_factory=list)
    requires_url_inspection: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "periodLabel": self.period_label,
            "sources": list(self.sources),
            "dataSources": list(self.data_sources),
            "includeItemPatterns": list(self.include_item_patterns),
            "apis": self.apis,
            "sections": list(self.sections),
            "structuredSections": [s.to_dict() for s in self.structured_sections],
            "metadata": dict(self.metadata),
            "llmGuide": self.llm_guide,
            "requiresUrlInspection": self.requires_url_inspection,
        }

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "periodLabel": self.period_label,
            "sources": list(self.sources),
            "dataSources": list(self.data_sources),
            "sections": list(self.sections),
            "objective": self.metadata.get("objective"),
            "audience": self.metadata.get("audience"),
        }


def _normalize_template_id(report_type_id: str) -> str:
    normalized = report_type_id.strip().lower().replace(" ", "-")
    aliases = {
        "weekly-report": "weekly",
        "monthly-report": "monthly",
        "quarterly-report": "quarterly",
        "weekly-seo-summary": "weekly",
        "monthly-performance-review": "monthly",
    }
    return aliases.get(normalized, normalized)


def _collect_data_sources_from_sections(
    structured_sections: List[TemplateSection],
) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for section in structured_sections:
        for ds in section.data_sources:
            if ds not in seen:
                seen.add(ds)
                ordered.append(ds)
    return ordered


def _derive_from_data_sources(data_sources: List[str]) -> tuple:
    sources: List[str] = []
    patterns: List[str] = []
    apis: Dict[str, List[str]] = {}
    requires_url_inspection = False
    seen_sources: Set[str] = set()
    seen_patterns: Set[str] = set()

    for ds in data_sources:
        spec = DATA_SOURCE_SPECS.get(ds)
        if not spec:
            continue
        source_id = spec["sourceId"]
        if source_id not in seen_sources:
            seen_sources.add(source_id)
            sources.append(source_id)
        for pattern in spec.get("itemPatterns") or []:
            if pattern not in seen_patterns:
                seen_patterns.add(pattern)
                patterns.append(pattern)
        api_name = spec.get("api")
        if api_name:
            apis.setdefault(source_id, [])
            if api_name not in apis[source_id]:
                apis[source_id].append(api_name)
        if spec.get("requiresUrlInspection"):
            requires_url_inspection = True

    return sources, patterns, apis, requires_url_inspection


def _parse_structured_section(raw: Dict[str, Any]) -> TemplateSection:
    known_keys = {"id", "title", "type", "data_sources", "generated_by"}
    extra = {k: v for k, v in raw.items() if k not in known_keys}
    return TemplateSection(
        id=raw.get("id", ""),
        title=raw.get("title", ""),
        section_type=raw.get("type", "unknown"),
        data_sources=list(raw.get("data_sources") or []),
        generated_by=raw.get("generated_by"),
        extra=extra,
    )


def _parse_sectioned_report(
    template_id: str, report_block: Dict[str, Any]
) -> ReportTemplate:
    metadata = dict(report_block.get("metadata") or {})
    raw_sections = list(report_block.get("sections") or [])
    structured_sections = [_parse_structured_section(s) for s in raw_sections]
    section_titles = [s.title for s in structured_sections if s.title]

    data_sources = _collect_data_sources_from_sections(structured_sections)
    sources, patterns, apis, requires_url_inspection = _derive_from_data_sources(
        data_sources
    )

    report_type_label = metadata.get("report_type") or template_id.title()
    objective = metadata.get("objective", "")
    audience = metadata.get("audience") or []
    audience_str = ", ".join(audience) if isinstance(audience, list) else str(audience)

    llm_guide_parts = [
        f"Report: {report_type_label}.",
        f"Audience: {audience_str}." if audience_str else "",
        f"Objective: {objective}." if objective else "",
        "For each section, use the section type as a layout hint (kpi_grid, table, llm_summary, etc.).",
        "Sections marked generated_by=llm should be written from insights in other sections.",
        "Use only metrics present in sectionData and source payloads; do not invent numbers.",
    ]
    llm_guide = " ".join(p for p in llm_guide_parts if p).strip()

    period_defaults = {
        "weekly": "Last 7 days",
        "monthly": "Last 30 days",
        "quarterly": "Last quarter",
    }

    return ReportTemplate(
        id=template_id,
        label=report_type_label,
        period_label=period_defaults.get(template_id, "Reporting period"),
        sources=sources,
        include_item_patterns=patterns,
        apis=apis,
        sections=section_titles,
        llm_guide=llm_guide,
        structured_sections=structured_sections,
        metadata=metadata,
        data_sources=data_sources,
        requires_url_inspection=requires_url_inspection,
    )


def _parse_legacy_template(data: Dict[str, Any], template_id: str) -> ReportTemplate:
    structured_sections: List[TemplateSection] = []
    for title in data.get("sections") or []:
        if isinstance(title, str):
            structured_sections.append(
                TemplateSection(
                    id=_normalize_template_id(title),
                    title=title,
                    section_type="narrative",
                )
            )

    data_sources = list(data.get("dataSources") or [])
    if not data_sources and data.get("sources"):
        for source_id in data.get("sources") or []:
            for key, spec in DATA_SOURCE_SPECS.items():
                if spec["sourceId"] == source_id:
                    data_sources.append(key)
                    break

    sources = list(data.get("sources") or [])
    patterns = list(data.get("includeItemPatterns") or [])
    apis = dict(data.get("apis") or {})
    requires_url_inspection = "gsc.url_inspection" in data_sources

    if data_sources and not patterns:
        _, patterns, apis, requires_url_inspection = _derive_from_data_sources(
            data_sources
        )
        if not sources:
            sources, _, _, _ = _derive_from_data_sources(data_sources)

    return ReportTemplate(
        id=data.get("id", template_id),
        label=data.get("label", template_id.title()),
        period_label=data.get("periodLabel", "Unknown period"),
        sources=sources,
        include_item_patterns=patterns,
        apis=apis,
        sections=[s.title for s in structured_sections] or list(data.get("sections") or []),
        llm_guide=(data.get("llmGuide") or "").strip(),
        structured_sections=structured_sections,
        metadata=dict(data.get("metadata") or {}),
        data_sources=data_sources,
        requires_url_inspection=requires_url_inspection,
    )


def load_template(report_type_id: str) -> ReportTemplate:
    """Load template by id (weekly | monthly | quarterly)."""
    template_id = _normalize_template_id(report_type_id)
    path = TEMPLATES_DIR / f"{template_id}.yaml"
    if not path.exists():
        valid = ", ".join(o["id"] for o in REPORT_TYPE_OPTIONS)
        raise ValueError(
            f"Unknown report type '{report_type_id}'. Valid template ids: {valid}"
        )

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if "id" in data:
        template = _parse_legacy_template(data, template_id)
    else:
        report_key = f"{template_id}_report"
        report_block = data.get(report_key)
        if not report_block:
            raise ValueError(
                f"Template file '{path.name}' must contain '{report_key}' or legacy 'id' root."
            )
        template = _parse_sectioned_report(template_id, report_block)

    if template.id != template_id:
        template = ReportTemplate(
            id=template_id,
            label=template.label,
            period_label=template.period_label,
            sources=template.sources,
            include_item_patterns=template.include_item_patterns,
            apis=template.apis,
            sections=template.sections,
            llm_guide=template.llm_guide,
            structured_sections=template.structured_sections,
            metadata=template.metadata,
            data_sources=template.data_sources,
            requires_url_inspection=template.requires_url_inspection,
        )
    return template


def list_templates() -> List[ReportTemplate]:
    templates: List[ReportTemplate] = []
    for option in REPORT_TYPE_OPTIONS:
        templates.append(load_template(option["id"]))
    return templates


def resolve_included_item_ids(
    template: ReportTemplate, items: List[Dict[str, Any]]
) -> List[str]:
    """Match extract item ids against template patterns, filtered by source."""
    allowed_sources = set(template.sources)
    patterns = template.include_item_patterns
    if not patterns:
        return [
            i["id"]
            for i in items
            if i.get("sourceId", "") in allowed_sources
        ]

    selected: List[str] = []
    for item in items:
        source_id = item.get("sourceId", "")
        item_id = item.get("id", "")
        if source_id not in allowed_sources:
            continue
        if any(fnmatch.fnmatch(item_id, pattern) for pattern in patterns):
            selected.append(item_id)

    return selected
