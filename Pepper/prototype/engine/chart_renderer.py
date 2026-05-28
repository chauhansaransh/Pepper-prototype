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
    customer_id: str,
    report_context: Dict[str, Any],
    output_dir: Path,
    cadence: str = "weekly",
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
    cadence_key = cadence.strip().lower()
    comparison_specs = [
        (
            "gsc",
            f"gsc_period_comparison_{cadence_key}",
            f"GSC {cadence_key.title()} Comparison (Clicks)",
            gsc.get("periodSnapshots") or {},
            ("totals", "clicks"),
            "Clicks",
        ),
        (
            "ga4",
            f"ga4_period_comparison_{cadence_key}",
            f"GA4 {cadence_key.title()} Comparison (Sessions)",
            ga4.get("periodSnapshots") or {},
            ("totals", "sessions"),
            "Sessions",
        ),
        (
            "semrush",
            f"semrush_period_comparison_{cadence_key}",
            f"Semrush {cadence_key.title()} Comparison (Tracked Keywords)",
            semrush.get("periodSnapshots") or {},
            ("trackedKeywordsTop20",),
            "Tracked Keywords",
        ),
        (
            "semrush_ai",
            f"semrush_ai_period_comparison_{cadence_key}",
            f"Semrush AI {cadence_key.title()} Comparison (Estimated Mentions)",
            semrush_ai.get("periodSnapshots") or {},
            ("estimatedAiMentions",),
            "Estimated Mentions",
        ),
    ]

    for prefix, chart_id, title, snapshots, metric_path, ylabel in comparison_specs:
        cadence_values = _extract_cadence_comparisons(
            snapshots, metric_path, cadence_key
        )
        if not cadence_values:
            continue
        chart_path = output_dir / f"{slug}_{prefix}_period_comparison_{cadence_key}.png"
        _render_period_comparison_chart(cadence_values, title, ylabel, chart_path)
        charts.append(
            {
                "id": chart_id,
                "title": title,
                "filename": chart_path.name,
                "path": str(chart_path),
            }
        )

    return charts


def _nested_metric(snapshot: Dict[str, Any], path: Tuple[str, ...]) -> float:
    value: Any = snapshot
    for key in path:
        if not isinstance(value, dict):
            return 0.0
        value = value.get(key)
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _extract_cadence_comparisons(
    snapshots: Dict[str, Any],
    metric_path: Tuple[str, ...],
    cadence: str,
) -> Dict[str, Dict[str, float]]:
    cadence_map = {
        "weekly": ("Week", "currentWeek", "lastWeek", "bestWeek"),
        "monthly": ("Month", "currentMonth", "lastMonth", "bestMonth"),
        "quarterly": ("Quarter", "currentQuarter", "lastQuarter", "bestQuarter"),
    }
    selected = cadence_map.get(cadence, cadence_map["weekly"])
    result: Dict[str, Dict[str, float]] = {}
    label, current_key, last_key, best_key = selected
    current = _nested_metric(snapshots.get(current_key) or {}, metric_path)
    last = _nested_metric(snapshots.get(last_key) or {}, metric_path)
    best = _nested_metric(snapshots.get(best_key) or {}, metric_path)
    if any(v > 0 for v in (current, last, best)):
        result[label] = {"Current": current, "Last": last, "Best": best}
    return result


def _pct_change(current: float, reference: float) -> str:
    if reference == 0:
        return "n/a"
    delta = ((current - reference) / reference) * 100.0
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.1f}%"


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


def _render_period_comparison_chart(
    cadence_values: Dict[str, Dict[str, float]],
    title: str,
    ylabel: str,
    output_path: Path,
) -> None:
    cadences = list(cadence_values.keys())
    current_vals = [cadence_values[c]["Current"] for c in cadences]
    last_vals = [cadence_values[c]["Last"] for c in cadences]
    best_vals = [cadence_values[c]["Best"] for c in cadences]

    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    _apply_theme(ax)

    x = list(range(len(cadences)))
    width = 0.23
    bars_current = ax.bar(
        [i - width for i in x],
        current_vals,
        width=width,
        color=COLORS["primary"],
        label="Current",
    )
    bars_last = ax.bar(
        x,
        last_vals,
        width=width,
        color=COLORS["secondary"],
        label="Last",
    )
    bars_best = ax.bar(
        [i + width for i in x],
        best_vals,
        width=width,
        color=COLORS["accent"],
        label="Best",
    )

    ax.set_xticks(x)
    ax.set_xticklabels(cadences)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10.5, fontweight="bold", pad=8)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _format_compact(v)))
    ax.legend(frameon=False, loc="upper left", fontsize=8)

    current = current_vals[0] if current_vals else 0.0
    last = last_vals[0] if last_vals else 0.0
    best = best_vals[0] if best_vals else 0.0
    subtitle = (
        f"% change vs Last: {_pct_change(current, last)} | "
        f"vs Best: {_pct_change(current, best)}"
    )
    ax.text(
        0.0,
        1.02,
        subtitle,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.5,
        color=COLORS["muted"],
    )

    all_values = current_vals + last_vals + best_vals
    max_val = max(all_values) if any(all_values) else 1.0
    for bars in (bars_current, bars_last, bars_best):
        for bar in bars:
            value = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + max_val * 0.015,
                _format_compact(value),
                ha="center",
                va="bottom",
                fontsize=7,
                color=COLORS["text"],
            )

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
