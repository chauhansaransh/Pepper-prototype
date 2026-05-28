from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Pepper-inspired palette
COLORS = {
    "primary": "#4255ff",
    "secondary": "#0f766e",
    "accent": "#f59e0b",
    "muted": "#64748b",
    "bg": "#f8fafc",
    "card": "#ffffff",
    "text": "#1e293b",
    "grid": "#e2e8f0",
}
BAR_GRADIENT = ["#3344db", "#4255ff", "#6366f1", "#818cf8"]

FIG_DPI = 200


def _safe_slug(customer_id: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in customer_id)


def _apply_theme(ax: plt.Axes) -> None:
    ax.set_facecolor(COLORS["card"])
    ax.tick_params(colors=COLORS["text"], labelsize=10)
    ax.title.set_color(COLORS["text"])
    ax.xaxis.label.set_color(COLORS["muted"])
    ax.yaxis.label.set_color(COLORS["muted"])
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(COLORS["grid"])


def _save_fig(fig: plt.Figure, output_path: Path) -> None:
    fig.patch.set_facecolor(COLORS["bg"])
    fig.savefig(
        output_path,
        dpi=FIG_DPI,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        edgecolor="none",
    )
    plt.close(fig)


def _format_compact(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.1f}"


def render_charts(
    customer_id: str, report_context: Dict[str, Any], output_dir: Path
) -> List[Dict[str, str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = _safe_slug(customer_id)
    charts: List[Dict[str, str]] = []

    # Backward-compatible: allow legacy callers to pass plain GSC normalized payload.
    if "totals" in report_context and "gsc" not in report_context:
        report_context = {"gsc": report_context}

    gsc = report_context.get("gsc") or report_context.get("gscFiltered") or {}
    ga4 = report_context.get("ga4") or {}
    semrush = report_context.get("semrush") or {}
    semrush_ai = report_context.get("semrushAi") or {}
    wordpress = report_context.get("wordpress") or {}
    webflow = report_context.get("webflow") or {}
    contentful = report_context.get("contentful") or {}

    totals = gsc.get("totals", {})
    if totals:
        kpi_path = output_dir / f"{slug}_kpi_summary.png"
        _render_kpi_cards(totals, kpi_path)
        charts.append(
            {
                "id": "kpi_summary",
                "title": "KPI Summary",
                "filename": kpi_path.name,
                "path": str(kpi_path),
            }
        )

    queries = gsc.get("topQueries", [])
    if queries:
        queries_path = output_dir / f"{slug}_top_queries.png"
        _render_ranked_bar_chart(
            items=[
                (q.get("query", "N/A"), int(q.get("clicks", 0)))
                for q in queries
            ],
            title="Top Queries by Clicks",
            xlabel="Clicks",
            output_path=queries_path,
            label_max_len=36,
        )
        charts.append(
            {
                "id": "top_queries",
                "title": "Top Queries by Clicks",
                "filename": queries_path.name,
                "path": str(queries_path),
            }
        )

    pages = gsc.get("topPages", [])
    if pages:
        pages_path = output_dir / f"{slug}_top_pages.png"
        _render_ranked_bar_chart(
            items=[
                (p.get("page", "N/A"), int(p.get("clicks", 0)))
                for p in pages
            ],
            title="Top Pages by Clicks",
            xlabel="Clicks",
            output_path=pages_path,
            label_max_len=42,
        )
        charts.append(
            {
                "id": "top_pages",
                "title": "Top Pages by Clicks",
                "filename": pages_path.name,
                "path": str(pages_path),
            }
        )

    ga4_pages = ga4.get("topLandingPages") or []
    if ga4_pages:
        ga4_pages_path = output_dir / f"{slug}_ga4_top_landing_pages.png"
        _render_ranked_bar_chart(
            items=[(p.get("pagePath", "N/A"), int(p.get("sessions", 0))) for p in ga4_pages],
            title="GA4 Top Landing Pages by Sessions",
            xlabel="Sessions",
            output_path=ga4_pages_path,
            label_max_len=42,
        )
        charts.append(
            {
                "id": "ga4_top_landing_pages",
                "title": "GA4 Top Landing Pages by Sessions",
                "filename": ga4_pages_path.name,
                "path": str(ga4_pages_path),
            }
        )

    competitor_summaries = semrush.get("competitorSummaries") or []
    if competitor_summaries:
        semrush_comp_path = output_dir / f"{slug}_semrush_competitor_authority.png"
        _render_ranked_bar_chart(
            items=[
                (c.get("label") or c.get("domain", "N/A"), int(c.get("authorityScore", 0)))
                for c in competitor_summaries
            ],
            title="Semrush Competitor Authority Score",
            xlabel="Authority Score",
            output_path=semrush_comp_path,
            label_max_len=36,
        )
        charts.append(
            {
                "id": "semrush_competitor_authority",
                "title": "Semrush Competitor Authority Score",
                "filename": semrush_comp_path.name,
                "path": str(semrush_comp_path),
            }
        )

    llm_rows = (semrush_ai.get("visibilityOverview") or {}).get("byLlm") or []
    if llm_rows:
        semrush_ai_path = output_dir / f"{slug}_ai_visibility_by_platform.png"
        _render_ranked_bar_chart(
            items=[
                (
                    r.get("platform", "N/A"),
                    int(float(r.get("visibilityShare", r.get("mentions", 0)))),
                )
                for r in llm_rows
            ],
            title="AI Visibility Share by Platform",
            xlabel="Visibility Share (%)",
            output_path=semrush_ai_path,
            label_max_len=30,
        )
        charts.append(
            {
                "id": "ai_visibility_by_platform",
                "title": "AI Visibility Share by Platform",
                "filename": semrush_ai_path.name,
                "path": str(semrush_ai_path),
            }
        )

    content_counts = [
        ("WordPress", len(wordpress.get("items") or [])),
        ("Webflow", len(webflow.get("items") or [])),
        ("Contentful", len(contentful.get("items") or [])),
    ]
    content_counts = [item for item in content_counts if item[1] > 0]
    if content_counts:
        cms_path = output_dir / f"{slug}_cms_content_counts.png"
        _render_ranked_bar_chart(
            items=content_counts,
            title="Published Content by CMS Source",
            xlabel="Items",
            output_path=cms_path,
            label_max_len=24,
        )
        charts.append(
            {
                "id": "cms_content_counts",
                "title": "Published Content by CMS Source",
                "filename": cms_path.name,
                "path": str(cms_path),
            }
        )

    return charts


def _render_kpi_cards(totals: Dict[str, Any], output_path: Path) -> None:
    cards = []
    if "clicks" in totals:
        cards.append(("Clicks", _format_compact(int(totals["clicks"])), COLORS["primary"]))
    if "impressions" in totals:
        cards.append(
            ("Impressions", _format_compact(int(totals["impressions"])), COLORS["secondary"])
        )
    if "ctr" in totals:
        cards.append(("CTR", f"{float(totals['ctr']) * 100:.2f}%", COLORS["accent"]))
    if "position" in totals:
        cards.append(("Avg Position", f"{float(totals['position']):.1f}", COLORS["muted"]))

    if not cards:
        return

    fig, axes = plt.subplots(1, len(cards), figsize=(2.8 * len(cards), 2.8))
    if len(cards) == 1:
        axes = [axes]
    fig.suptitle("KPI Snapshot", fontsize=14, fontweight="bold", color=COLORS["text"], y=1.02)

    for ax, (label, value, color) in zip(axes, cards):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        rect = plt.Rectangle(
            (0.05, 0.1),
            0.9,
            0.8,
            transform=ax.transAxes,
            facecolor=COLORS["card"],
            edgecolor=COLORS["grid"],
            linewidth=1.2,
            zorder=0,
        )
        ax.add_patch(rect)
        ax.text(
            0.5,
            0.62,
            value,
            ha="center",
            va="center",
            fontsize=20,
            fontweight="bold",
            color=color,
            transform=ax.transAxes,
        )
        ax.text(
            0.5,
            0.28,
            label,
            ha="center",
            va="center",
            fontsize=11,
            color=COLORS["muted"],
            transform=ax.transAxes,
        )

    fig.subplots_adjust(wspace=0.35)
    _save_fig(fig, output_path)


def _render_ranked_bar_chart(
    items: List[Tuple[str, int]],
    title: str,
    xlabel: str,
    output_path: Path,
    label_max_len: int = 40,
) -> None:
    sorted_items = sorted(items, key=lambda x: x[1], reverse=True)
    labels = [label[:label_max_len] + ("…" if len(label) > label_max_len else "") for label, _ in sorted_items]
    values = [v for _, v in sorted_items]
    n = len(values)

    fig_h = max(3.5, 0.55 * n + 1.5)
    fig, ax = plt.subplots(figsize=(9, fig_h))
    _apply_theme(ax)

    colors = [BAR_GRADIENT[min(i, len(BAR_GRADIENT) - 1)] for i in range(n)]
    y_pos = range(n)
    bars = ax.barh(list(y_pos), values, color=colors, height=0.65, zorder=2)

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: _format_compact(x)))
    ax.grid(axis="x", color=COLORS["grid"], linestyle="-", linewidth=0.8, alpha=0.9, zorder=0)
    ax.set_axisbelow(True)

    max_val = max(values) if values else 1
    for bar, val in zip(bars, values):
        ax.text(
            val + max_val * 0.02,
            bar.get_y() + bar.get_height() / 2,
            _format_compact(val),
            va="center",
            ha="left",
            fontsize=9,
            color=COLORS["text"],
            fontweight="600",
        )

    _save_fig(fig, output_path)
