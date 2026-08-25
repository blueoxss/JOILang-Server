#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _category_sort_key(value: str) -> tuple[int, Any]:
    text = _safe_text(value)
    if text.isdigit():
        return (0, int(text))
    return (1, text.casefold())


def _ordered_unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = _safe_text(raw)
        if not token:
            continue
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(token)
    return ordered


def _group_rows_by_category(rows: list[dict[str, str]]) -> tuple[list[str], dict[str, list[dict[str, str]]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        category = _safe_text(row.get("category"))
        if not category:
            continue
        grouped.setdefault(category, []).append(row)
    categories = sorted(grouped.keys(), key=_category_sort_key)
    return categories, grouped


def _pareto_mask(rows: list[dict[str, str]], *, x_key: str, y_key: str) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    for row in rows:
        model_key = str(row.get("model_key", ""))
        x_value = _safe_float(row.get(x_key))
        y_value = _safe_float(row.get(y_key))
        dominated = False
        for other in rows:
            if other is row:
                continue
            other_x = _safe_float(other.get(x_key))
            other_y = _safe_float(other.get(y_key))
            if other_y >= y_value and other_x <= x_value and (other_y > y_value or other_x < x_value):
                dominated = True
                break
        flags[model_key] = not dominated
    return flags


def _plot_tradeoff_scatter(
    rows: list[dict[str, str]],
    *,
    x_key: str,
    y_key: str,
    x_label: str,
    y_label: str,
    title: str,
    png_path: Path,
    pdf_path: Path,
) -> dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pareto = _pareto_mask(rows, x_key=x_key, y_key=y_key)
    figure, axis = plt.subplots(figsize=(9, 6), constrained_layout=True)
    for row in rows:
        model_key = str(row.get("model_key", ""))
        label = str(row.get("model_label", model_key))
        x_value = _safe_float(row.get(x_key))
        y_value = _safe_float(row.get(y_key))
        axis.scatter(
            [x_value],
            [y_value],
            s=90 if pareto.get(model_key, False) else 55,
            marker="D" if pareto.get(model_key, False) else "o",
            alpha=0.9,
        )
        axis.annotate(label, (x_value, y_value), textcoords="offset points", xytext=(6, 5), fontsize=9)
    axis.set_xlabel(x_label)
    axis.set_ylabel(y_label)
    axis.set_title(title)
    axis.grid(alpha=0.25)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(png_path, dpi=180)
    figure.savefig(pdf_path)
    plt.close(figure)
    return {
        "png": str(png_path),
        "pdf": str(pdf_path),
        "pareto_models": [row.get("model_key", "") for row in rows if pareto.get(str(row.get("model_key", "")), False)],
    }


def _plot_summary_bars(rows: list[dict[str, str]], *, png_path: Path, pdf_path: Path) -> dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [str(row.get("model_key", "")) for row in rows]
    det_pass = [_safe_float(row.get("det_pass_rate")) for row in rows]
    warm_latency = [_safe_float(row.get("warm_latency_p50")) for row in rows]
    cold_load = [_safe_float(row.get("cold_load_sec")) for row in rows]
    prompt_tokens = [_safe_float(row.get("avg_prompt_tokens")) for row in rows]
    peak_vram = [_safe_float(row.get("peak_vram_gb_max")) for row in rows]

    figure, axes = plt.subplots(3, 2, figsize=(12, 11), constrained_layout=True)
    plots = [
        (axes[0][0], det_pass, "det_pass_rate"),
        (axes[0][1], warm_latency, "warm_latency_p50"),
        (axes[1][0], cold_load, "cold_load_sec"),
        (axes[1][1], prompt_tokens, "avg_prompt_tokens"),
        (axes[2][0], peak_vram, "peak_vram_gb_max"),
    ]
    for axis, values, title in plots:
        axis.bar(labels, values)
        axis.set_title(title)
        axis.tick_params(axis="x", rotation=25)
        axis.grid(axis="y", alpha=0.2)
    axes[2][1].axis("off")
    png_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(png_path, dpi=180)
    figure.savefig(pdf_path)
    plt.close(figure)
    return {"png": str(png_path), "pdf": str(pdf_path)}


def _plot_category_tradeoff_grid(
    rows: list[dict[str, str]],
    *,
    x_key: str,
    y_key: str,
    x_label: str,
    y_label: str,
    title: str,
    png_path: Path,
    pdf_path: Path,
) -> dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    categories, grouped = _group_rows_by_category(rows)
    if not categories:
        return {"png": "", "pdf": "", "categories": [], "models": []}

    model_keys = _ordered_unique([_safe_text(row.get("model_key")) for row in rows])
    model_labels = {
        _safe_text(row.get("model_key")): _safe_text(row.get("model_label")) or _safe_text(row.get("model_key"))
        for row in rows
    }
    color_map = {}
    palette = list(plt.get_cmap("tab10").colors) + list(plt.get_cmap("tab20").colors)
    for index, model_key in enumerate(model_keys):
        color_map[model_key] = palette[index % len(palette)]

    column_count = min(3, max(1, len(categories)))
    row_count = int(math.ceil(len(categories) / column_count))
    figure, axes = plt.subplots(row_count, column_count, figsize=(6 * column_count, 4.8 * row_count), constrained_layout=False)
    if hasattr(axes, "flat"):
        flat_axes = list(axes.flat)
    else:
        flat_axes = [axes]

    legend_handles = {}
    category_pareto: dict[str, list[str]] = {}
    for axis, category in zip(flat_axes, categories):
        category_rows = grouped[category]
        pareto = _pareto_mask(category_rows, x_key=x_key, y_key=y_key)
        category_pareto[category] = [row.get("model_key", "") for row in category_rows if pareto.get(_safe_text(row.get("model_key")), False)]
        for row in category_rows:
            model_key = _safe_text(row.get("model_key"))
            x_value = _safe_float(row.get(x_key))
            y_value = _safe_float(row.get(y_key))
            scatter = axis.scatter(
                [x_value],
                [y_value],
                s=95 if pareto.get(model_key, False) else 58,
                marker="D" if pareto.get(model_key, False) else "o",
                color=color_map.get(model_key),
                alpha=0.92,
            )
            axis.annotate(model_key, (x_value, y_value), textcoords="offset points", xytext=(5, 4), fontsize=8)
            legend_handles.setdefault(model_key, scatter)
        axis.set_title(f"Category {category}")
        axis.set_xlabel(x_label)
        axis.set_ylabel(y_label)
        axis.grid(alpha=0.25)

    for axis in flat_axes[len(categories):]:
        axis.axis("off")

    if legend_handles:
        handles = [legend_handles[key] for key in model_keys if key in legend_handles]
        labels = [model_labels.get(key, key) for key in model_keys if key in legend_handles]
        figure.legend(
            handles,
            labels,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.945),
            ncol=min(3, max(1, len(labels))),
            frameon=False,
        )
    figure.suptitle(title, fontsize=14, y=0.985)
    figure.tight_layout(rect=(0.02, 0.02, 0.98, 0.86))

    png_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(png_path, dpi=180, bbox_inches="tight")
    figure.savefig(pdf_path, bbox_inches="tight")
    plt.close(figure)
    return {
        "png": str(png_path),
        "pdf": str(pdf_path),
        "categories": categories,
        "models": model_keys,
        "pareto_by_category": category_pareto,
    }


def _plot_category_metric_panels(
    rows: list[dict[str, str]],
    *,
    png_path: Path,
    pdf_path: Path,
) -> dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    categories, grouped = _group_rows_by_category(rows)
    if not categories:
        return {"png": "", "pdf": "", "categories": [], "models": []}

    model_keys = _ordered_unique([_safe_text(row.get("model_key")) for row in rows])
    model_labels = {
        _safe_text(row.get("model_key")): _safe_text(row.get("model_label")) or _safe_text(row.get("model_key"))
        for row in rows
    }
    palette = list(plt.get_cmap("tab10").colors) + list(plt.get_cmap("tab20").colors)
    width = 0.78 / max(1, len(model_keys))
    category_positions = list(range(len(categories)))

    metrics = [
        ("avg_det_score", "Average DET score"),
        ("det_pass_rate", "DET pass rate"),
        ("warm_latency_p50", "Warm latency p50 (sec)"),
        ("avg_prompt_tokens", "Average prompt tokens"),
    ]

    figure, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=False)
    legend_handles = []
    legend_labels = []
    for axis, (metric_key, metric_title) in zip(list(axes.flat), metrics):
        for model_index, model_key in enumerate(model_keys):
            values = []
            for category in categories:
                category_rows = grouped[category]
                row = next((item for item in category_rows if _safe_text(item.get("model_key")) == model_key), None)
                values.append(_safe_float(row.get(metric_key)) if row is not None else 0.0)
            offset = (model_index - (len(model_keys) - 1) / 2.0) * width
            bars = axis.bar(
                [position + offset for position in category_positions],
                values,
                width=width,
                color=palette[model_index % len(palette)],
                alpha=0.9,
            )
            if metric_key == metrics[0][0]:
                legend_handles.append(bars[0])
                legend_labels.append(model_labels.get(model_key, model_key))
        axis.set_title(metric_title)
        axis.set_xticks(category_positions)
        axis.set_xticklabels([f"Cat {category}" for category in categories])
        axis.grid(axis="y", alpha=0.2)

    if legend_handles:
        figure.legend(
            legend_handles,
            legend_labels,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.945),
            ncol=min(3, max(1, len(legend_labels))),
            frameon=False,
        )
    figure.suptitle("Category-wise performance comparison", fontsize=14, y=0.985)
    figure.tight_layout(rect=(0.02, 0.02, 0.98, 0.86))

    png_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(png_path, dpi=180, bbox_inches="tight")
    figure.savefig(pdf_path, bbox_inches="tight")
    plt.close(figure)
    return {
        "png": str(png_path),
        "pdf": str(pdf_path),
        "categories": categories,
        "models": model_keys,
        "metrics": [metric_key for metric_key, _metric_title in metrics],
    }


def export_paper_figures(results_dir: str | Path) -> dict[str, Any]:
    results_path = Path(results_dir).expanduser().resolve()
    comparison_rows = _read_csv(results_path / "main_model_comparison.csv")
    category_rows = _read_csv(results_path / "category_summary.csv")
    if not comparison_rows:
        raise SystemExit(f"No main_model_comparison.csv rows found under {results_path}")

    output_dir = results_path / "paper_figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "results_dir": str(results_path),
        "output_dir": str(output_dir),
        "figures": {},
    }
    try:
        summary["figures"]["det_vs_warm_latency"] = _plot_tradeoff_scatter(
            comparison_rows,
            x_key="warm_latency_p50",
            y_key="avg_det_score",
            x_label="Warm latency p50 (sec)",
            y_label="Average DET score",
            title="DET vs Warm Latency",
            png_path=output_dir / "det_vs_warm_latency.png",
            pdf_path=output_dir / "det_vs_warm_latency.pdf",
        )
        summary["figures"]["det_vs_prompt_tokens"] = _plot_tradeoff_scatter(
            comparison_rows,
            x_key="avg_prompt_tokens",
            y_key="avg_det_score",
            x_label="Average prompt tokens",
            y_label="Average DET score",
            title="DET vs Prompt Tokens",
            png_path=output_dir / "det_vs_prompt_tokens.png",
            pdf_path=output_dir / "det_vs_prompt_tokens.pdf",
        )
        summary["figures"]["det_vs_peak_vram"] = _plot_tradeoff_scatter(
            comparison_rows,
            x_key="peak_vram_gb_max",
            y_key="avg_det_score",
            x_label="Peak VRAM (GB)",
            y_label="Average DET score",
            title="DET vs Peak VRAM",
            png_path=output_dir / "det_vs_peak_vram.png",
            pdf_path=output_dir / "det_vs_peak_vram.pdf",
        )
        summary["figures"]["summary_bars"] = _plot_summary_bars(
            comparison_rows,
            png_path=output_dir / "paper_summary_bars.png",
            pdf_path=output_dir / "paper_summary_bars.pdf",
        )
        if category_rows:
            summary["figures"]["category_det_vs_warm_latency"] = _plot_category_tradeoff_grid(
                category_rows,
                x_key="warm_latency_p50",
                y_key="avg_det_score",
                x_label="Warm latency p50 (sec)",
                y_label="Average DET score",
                title="Category-wise DET vs Warm Latency",
                png_path=output_dir / "category_det_vs_warm_latency.png",
                pdf_path=output_dir / "category_det_vs_warm_latency.pdf",
            )
            summary["figures"]["category_det_vs_prompt_tokens"] = _plot_category_tradeoff_grid(
                category_rows,
                x_key="avg_prompt_tokens",
                y_key="avg_det_score",
                x_label="Average prompt tokens",
                y_label="Average DET score",
                title="Category-wise DET vs Prompt Tokens",
                png_path=output_dir / "category_det_vs_prompt_tokens.png",
                pdf_path=output_dir / "category_det_vs_prompt_tokens.pdf",
            )
            summary["figures"]["category_metric_panels"] = _plot_category_metric_panels(
                category_rows,
                png_path=output_dir / "category_metric_panels.png",
                pdf_path=output_dir / "category_metric_panels.pdf",
            )
        else:
            summary["category_figures_skipped"] = "category_summary.csv is missing or empty."
        summary["status"] = "ok"
    except Exception as exc:
        summary["status"] = "plotting_failed"
        summary["error"] = str(exc)
    summary_path = output_dir / "paper_figures_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export paper-ready figures from a run_model_suite_benchmark result directory.")
    parser.add_argument("--results-dir", required=True, help="Path to a benchmark output directory containing main_model_comparison.csv.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = export_paper_figures(args.results_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
