#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from utils.pipeline_common import DATASET_DEFAULT, RESULTS_DIR, atomic_write_csv, dump_json, load_json


RELEVANT_SUITE_METRICS = [
    "avg_det_score",
    "det_pass_rate",
    "gt_exact_rate",
    "warm_latency_p50",
    "warm_latency_mean",
    "avg_prompt_tokens",
    "avg_completion_tokens",
    "avg_total_tokens",
    "peak_vram_gb_max",
    "generation_error_rate",
    "failure_rate",
    "row_success_rate",
    "cold_load_sec",
]

RELEVANT_CATEGORY_METRICS = [
    "avg_det_score",
    "det_pass_rate",
    "gt_exact_rate",
    "warm_latency_p50",
    "avg_prompt_tokens",
    "avg_total_tokens",
    "peak_vram_gb_max",
    "generation_error_rate",
    "failure_rate",
    "row_success_rate",
]

RELEVANT_ROW_METRICS = [
    "det_score",
    "det_pass",
    "det_gt_exact",
    "det_gt_similarity",
    "det_gt_service_coverage",
    "det_gt_receiver_coverage",
    "det_dataflow_score",
    "det_numeric_grounding",
    "det_enum_grounding",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "llm_latency_sec",
    "total_pipeline_sec",
    "tokens_per_sec",
    "peak_vram_gb",
    "generation_error_type",
    "oom_flag",
    "service_list_snippet_source",
    "service_list_device_count",
    "service_list_retrieval_status",
    "service_list_retrieval_mode",
    "service_list_retrieval_topk",
    "service_list_retrieval_categories",
]


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _safe_bool(value: Any) -> bool:
    text = _safe_text(value).casefold()
    return text in {"1", "true", "yes", "y"}


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return pd.read_csv(path).fillna("").to_dict("records")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    atomic_write_csv(path, fieldnames, rows)


def _condition_sort_key(value: str) -> tuple[int, str]:
    if value == "baseline":
        return (0, value)
    if value == "retrieval":
        return (1, value)
    return (2, value)


def _parse_blocked_entry(raw: str) -> dict[str, str]:
    if "=" not in raw:
        return {"model_key": _safe_text(raw), "status": "blocked", "note": ""}
    model_key, rest = raw.split("=", 1)
    status, note = (rest.split("|", 1) + [""])[:2]
    return {
        "model_key": _safe_text(model_key),
        "status": _safe_text(status) or "blocked",
        "note": _safe_text(note),
    }


def _extract_row_metrics(result_dir: Path, model_key: str, condition: str) -> list[dict[str, Any]]:
    rows = _read_csv(result_dir / "row_comparison.csv")
    prefix = f"{model_key}__"
    extracted: list[dict[str, Any]] = []
    for row in rows:
        payload: dict[str, Any] = {
            "condition": condition,
            "model_key": model_key,
            "result_dir": str(result_dir),
            "row_no": row.get("row_no", ""),
            "category": row.get("category", "") or row.get("row_category", ""),
            "command_eng": row.get("command_eng", ""),
            "command_kor": row.get("command_kor", ""),
            "gt_name": row.get("gt_name", ""),
            "gt_code": row.get("gt_code", ""),
            "warmup_excluded": _safe_bool(row.get("warmup_excluded")) or _safe_bool(row.get(f"{prefix}warmup_excluded")),
        }
        for metric in RELEVANT_ROW_METRICS:
            payload[metric] = row.get(f"{prefix}{metric}", "")
        extracted.append(payload)
    return extracted


def _load_condition_rows(result_dirs: list[Path], condition: str) -> dict[str, list[dict[str, Any]]]:
    suite_rows: list[dict[str, Any]] = []
    category_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    row_rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []

    for result_dir in result_dirs:
        manifest_path = result_dir / "suite_manifest.json"
        manifest = load_json(manifest_path) if manifest_path.exists() else {}
        manifests.append({"condition": condition, "result_dir": str(result_dir), **manifest})
        suite = _read_csv(result_dir / "suite_summary.csv")
        categories = _read_csv(result_dir / "category_summary.csv")
        failures = _read_csv(result_dir / "failure_reason_summary.csv")

        for row in suite:
            suite_rows.append({"condition": condition, "result_dir": str(result_dir), **row})
            model_key = _safe_text(row.get("model_key"))
            if model_key:
                row_rows.extend(_extract_row_metrics(result_dir, model_key, condition))
        for row in categories:
            category_rows.append({"condition": condition, "result_dir": str(result_dir), **row})
        for row in failures:
            failure_rows.append({"condition": condition, "result_dir": str(result_dir), **row})

    return {
        "suite": suite_rows,
        "category": category_rows,
        "failure": failure_rows,
        "row": row_rows,
        "manifest": manifests,
    }


def _merge_conditions(
    baseline_rows: list[dict[str, Any]],
    retrieval_rows: list[dict[str, Any]],
    *,
    keys: list[str],
    metrics: list[str],
) -> list[dict[str, Any]]:
    base_df = pd.DataFrame(baseline_rows)
    ret_df = pd.DataFrame(retrieval_rows)
    if base_df.empty or ret_df.empty:
        return []
    merged = base_df.merge(ret_df, on=keys, how="outer", suffixes=("_baseline", "_retrieval"))
    records: list[dict[str, Any]] = []
    for _, row in merged.iterrows():
        payload: dict[str, Any] = {key: row.get(key, "") for key in keys}
        for metric in metrics:
            base_key = f"{metric}_baseline"
            ret_key = f"{metric}_retrieval"
            base_val = _safe_float(row.get(base_key))
            ret_val = _safe_float(row.get(ret_key))
            payload[f"baseline_{metric}"] = base_val
            payload[f"retrieval_{metric}"] = ret_val
            payload[f"delta_{metric}"] = ret_val - base_val
            if metric in {"avg_prompt_tokens", "warm_latency_p50", "warm_latency_mean", "peak_vram_gb_max", "prompt_tokens", "llm_latency_sec", "total_pipeline_sec"} and base_val > 0:
                payload[f"reduction_pct_{metric}"] = (base_val - ret_val) / base_val * 100.0
        records.append(payload)
    return records


def _json_load_maybe(raw: Any) -> Any:
    text = _safe_text(raw)
    if not text:
        return []
    try:
        return json.loads(text)
    except Exception:
        return text


def _is_connected_devices_empty(raw: Any) -> bool:
    text = _safe_text(raw)
    if not text or text in {"{}", "[]", "null", "None"}:
        return True
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return len(payload) == 0
        if isinstance(payload, list):
            return len(payload) == 0
        return False
    except Exception:
        return False


def _build_dataset_context_summary(dataset_path: Path) -> list[dict[str, Any]]:
    if not dataset_path.exists():
        return []
    rows = pd.read_csv(dataset_path).fillna("").to_dict("records")
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        category = _safe_text(row.get("category"))
        bucket = grouped.setdefault(
            category,
            {
                "category": category,
                "row_count": 0,
                "empty_connected_devices_count": 0,
                "nonempty_connected_devices_count": 0,
            },
        )
        bucket["row_count"] += 1
        if _is_connected_devices_empty(row.get("connected_devices")):
            bucket["empty_connected_devices_count"] += 1
        else:
            bucket["nonempty_connected_devices_count"] += 1
    results = []
    for category, bucket in sorted(grouped.items(), key=lambda item: int(item[0]) if _safe_text(item[0]).isdigit() else item[0]):
        row_count = max(1, int(bucket["row_count"]))
        bucket["empty_connected_devices_ratio"] = round(bucket["empty_connected_devices_count"] / row_count, 4)
        results.append(bucket)
    return results


def _plot_tradeoff(df: pd.DataFrame, *, x_key: str, y_key: str, title: str, png_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(9.5, 6.2), constrained_layout=True)
    colors = {"baseline": "#1f77b4", "retrieval": "#d62728"}
    markers = {"qwen25_coder_7b": "o", "qwen25_coder_14b": "D"}
    for _, row in df.iterrows():
        condition = _safe_text(row.get("condition"))
        model_key = _safe_text(row.get("model_key"))
        x_val = _safe_float(row.get(x_key))
        y_val = _safe_float(row.get(y_key))
        label = f"{model_key} · {condition}"
        ax.scatter(
            [x_val],
            [y_val],
            s=95,
            color=colors.get(condition, "#555555"),
            marker=markers.get(model_key, "o"),
            alpha=0.9,
        )
        ax.annotate(label, (x_val, y_val), textcoords="offset points", xytext=(6, 5), fontsize=9)
    ax.set_xlabel(x_key)
    ax.set_ylabel(y_key)
    ax.set_title(title)
    ax.grid(alpha=0.25)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=180)
    plt.close(fig)


def _plot_condition_bars(df: pd.DataFrame, *, png_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if df.empty:
        return
    models = sorted(df["model_key"].dropna().astype(str).unique())
    conditions = sorted(df["condition"].dropna().astype(str).unique(), key=_condition_sort_key)
    metrics = [
        "avg_det_score",
        "det_pass_rate",
        "warm_latency_p50",
        "avg_prompt_tokens",
        "peak_vram_gb_max",
        "failure_rate",
    ]
    titles = {
        "avg_det_score": "Avg Strict DET",
        "det_pass_rate": "DET Pass Rate",
        "warm_latency_p50": "Warm Latency p50 (s)",
        "avg_prompt_tokens": "Avg Prompt Tokens",
        "peak_vram_gb_max": "Peak VRAM (GB)",
        "failure_rate": "Failure Rate",
    }
    width = 0.36
    fig, axes = plt.subplots(3, 2, figsize=(13, 11), constrained_layout=True)
    colors = {"baseline": "#4c78a8", "retrieval": "#f58518"}
    for ax, metric in zip(axes.flat, metrics):
        xs = list(range(len(models)))
        for idx, condition in enumerate(conditions):
            offsets = [x + (idx - (len(conditions) - 1) / 2) * width for x in xs]
            values = []
            for model_key in models:
                row = df[(df["model_key"] == model_key) & (df["condition"] == condition)]
                values.append(_safe_float(row.iloc[0][metric]) if not row.empty else 0.0)
            ax.bar(offsets, values, width=width, label=condition, color=colors.get(condition))
        ax.set_xticks(xs)
        ax.set_xticklabels(models, rotation=20)
        ax.set_title(titles[metric])
        ax.grid(axis="y", alpha=0.2)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=max(1, len(labels)), frameon=False)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=180)
    plt.close(fig)


def _plot_category_heatmap(delta_df: pd.DataFrame, *, value_key: str, title: str, png_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    if delta_df.empty:
        return
    pivot = (
        delta_df.pivot_table(index="model_key", columns="category", values=value_key, aggfunc="mean")
        .sort_index()
        .reindex(sorted(delta_df["model_key"].astype(str).unique()))
    )
    values = pivot.to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(11, 4.8), constrained_layout=True)
    image = ax.imshow(values, aspect="auto", cmap="coolwarm")
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels([str(col) for col in pivot.columns], rotation=0)
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels([str(idx) for idx in pivot.index])
    ax.set_xlabel("Category")
    ax.set_ylabel("Model")
    ax.set_title(title)
    for row_idx in range(values.shape[0]):
        for col_idx in range(values.shape[1]):
            ax.text(col_idx, row_idx, f"{values[row_idx, col_idx]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax, shrink=0.85)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=180)
    plt.close(fig)


def _plot_delta_histograms(delta_df: pd.DataFrame, *, value_key: str, title: str, png_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if delta_df.empty:
        return
    models = sorted(delta_df["model_key"].dropna().astype(str).unique())
    fig, axes = plt.subplots(len(models), 1, figsize=(10, max(4, 3.2 * len(models))), constrained_layout=True)
    if not hasattr(axes, "__iter__") or isinstance(axes, plt.Axes):
        axes = [axes]
    for ax, model_key in zip(axes, models):
        values = delta_df[delta_df["model_key"] == model_key][value_key].astype(float)
        ax.hist(values, bins=18, alpha=0.85, color="#4c78a8")
        ax.axvline(values.mean(), color="#d62728", linestyle="--", linewidth=1.5, label=f"mean={values.mean():.2f}")
        ax.set_title(f"{title} · {model_key}")
        ax.set_xlabel(value_key)
        ax.set_ylabel("Rows")
        ax.grid(alpha=0.2)
        ax.legend(frameon=False)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=180)
    plt.close(fig)


def _plot_failure_reason_heatmap(df: pd.DataFrame, *, png_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    if df.empty:
        return
    labels = df["condition"].astype(str) + " · " + df["model_key"].astype(str)
    top_reasons = (
        df.groupby("failure_reason", as_index=False)["count"]
        .sum()
        .sort_values("count", ascending=False)
        .head(10)["failure_reason"]
        .tolist()
    )
    matrix = (
        df[df["failure_reason"].isin(top_reasons)]
        .pivot_table(index=labels, columns="failure_reason", values="count", aggfunc="sum", fill_value=0)
        .reindex(columns=top_reasons)
    )
    values = matrix.to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(12, 4.8), constrained_layout=True)
    image = ax.imshow(values, aspect="auto", cmap="magma")
    ax.set_xticks(np.arange(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns.tolist(), rotation=35, ha="right")
    ax.set_yticks(np.arange(len(matrix.index)))
    ax.set_yticklabels(matrix.index.tolist())
    ax.set_title("Top Failure Reasons by Condition/Model")
    for r in range(values.shape[0]):
        for c in range(values.shape[1]):
            ax.text(c, r, f"{int(values[r, c])}", ha="center", va="center", fontsize=8, color="white")
    fig.colorbar(image, ax=ax, shrink=0.85)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=180)
    plt.close(fig)


def _plot_dataset_context(dataset_rows: list[dict[str, Any]], *, png_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not dataset_rows:
        return
    df = pd.DataFrame(dataset_rows)
    fig, ax = plt.subplots(figsize=(10.5, 4.8), constrained_layout=True)
    xs = range(len(df))
    empty = df["empty_connected_devices_ratio"].astype(float).tolist()
    counts = df["row_count"].astype(float).tolist()
    ax.bar(xs, empty, color="#2a9d8f", alpha=0.9)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(df["category"].astype(str).tolist())
    ax.set_xlabel("Category")
    ax.set_ylabel("Empty connected_devices ratio")
    ax.set_ylim(0, 1.05)
    ax.set_title("Dataset Context Regime by Category")
    ax.grid(axis="y", alpha=0.2)
    for x, ratio, count in zip(xs, empty, counts):
        ax.text(x, min(1.02, ratio + 0.03), f"n={int(count)}", ha="center", va="bottom", fontsize=8)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=180)
    plt.close(fig)


def _build_findings(
    combined_suite: pd.DataFrame,
    delta_suite: pd.DataFrame,
    delta_category: pd.DataFrame,
    availability_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    findings: dict[str, Any] = {}
    if not combined_suite.empty:
        best_row = combined_suite.sort_values("avg_det_score", ascending=False).iloc[0]
        fastest_row = combined_suite.sort_values("warm_latency_p50", ascending=True).iloc[0]
        findings["best_quality"] = {
            "model_key": _safe_text(best_row.get("model_key")),
            "condition": _safe_text(best_row.get("condition")),
            "avg_det_score": _safe_float(best_row.get("avg_det_score")),
        }
        findings["fastest"] = {
            "model_key": _safe_text(fastest_row.get("model_key")),
            "condition": _safe_text(fastest_row.get("condition")),
            "warm_latency_p50": _safe_float(fastest_row.get("warm_latency_p50")),
        }
    if not delta_suite.empty:
        best_gain = delta_suite.sort_values("delta_avg_det_score", ascending=False).iloc[0]
        best_reduction = delta_suite.sort_values("reduction_pct_avg_prompt_tokens", ascending=False).iloc[0]
        findings["best_det_gain_from_retrieval"] = {
            "model_key": _safe_text(best_gain.get("model_key")),
            "delta_avg_det_score": _safe_float(best_gain.get("delta_avg_det_score")),
        }
        findings["largest_prompt_reduction"] = {
            "model_key": _safe_text(best_reduction.get("model_key")),
            "reduction_pct_avg_prompt_tokens": _safe_float(best_reduction.get("reduction_pct_avg_prompt_tokens")),
        }
    if not delta_category.empty:
        gain_row = delta_category.sort_values("delta_avg_det_score", ascending=False).iloc[0]
        loss_row = delta_category.sort_values("delta_avg_det_score", ascending=True).iloc[0]
        findings["strongest_category_gain"] = {
            "model_key": _safe_text(gain_row.get("model_key")),
            "category": _safe_text(gain_row.get("category")),
            "delta_avg_det_score": _safe_float(gain_row.get("delta_avg_det_score")),
        }
        findings["largest_category_drop"] = {
            "model_key": _safe_text(loss_row.get("model_key")),
            "category": _safe_text(loss_row.get("category")),
            "delta_avg_det_score": _safe_float(loss_row.get("delta_avg_det_score")),
        }
    blocked = [row for row in availability_rows if _safe_text(row.get("status")) not in {"ran_both", "ran_baseline_only", "ran_retrieval_only"}]
    findings["blocked_models"] = blocked
    return findings


def _study_assessment(findings: dict[str, Any], availability_rows: list[dict[str, Any]]) -> dict[str, Any]:
    runnable = [row for row in availability_rows if _safe_text(row.get("status")) == "ran_both"]
    blocked = [row for row in availability_rows if _safe_text(row.get("status")) not in {"ran_both", "ran_baseline_only", "ran_retrieval_only"}]
    assessment = {
        "runnable_model_count": len(runnable),
        "blocked_model_count": len(blocked),
        "publication_readiness": "partial",
        "strengths": [],
        "limitations": [],
    }
    if len(runnable) >= 2:
        assessment["strengths"].append("At least two deployment-relevant local models completed both baseline and retrieval conditions.")
    if findings.get("largest_prompt_reduction", {}).get("reduction_pct_avg_prompt_tokens", 0.0) > 30.0:
        assessment["strengths"].append("Prompt compression effect is large enough to support a token-efficiency claim.")
    if findings.get("best_det_gain_from_retrieval", {}).get("delta_avg_det_score", 0.0) > 0.0:
        assessment["strengths"].append("Retrieval premapping improves strict DET for at least one strong local model.")
    if blocked:
        assessment["limitations"].append("The intended five-model local suite is not fully executable under the current environment; blocked models must be reported transparently.")
    assessment["limitations"].append("The strongest claim should be framed around the runnable Qwen local subset unless the blocked models are fixed and rerun.")
    return assessment


def _render_html_report(
    out_path: Path,
    *,
    title: str,
    findings: dict[str, Any],
    assessment: dict[str, Any],
    combined_suite: pd.DataFrame,
    delta_suite: pd.DataFrame,
    availability_rows: list[dict[str, Any]],
    dataset_context_df: pd.DataFrame,
    figures: list[dict[str, str]],
) -> None:
    def _table(df: pd.DataFrame, columns: list[str]) -> str:
        if df.empty:
            return "<p class='muted'>No rows available.</p>"
        subset = df.loc[:, [col for col in columns if col in df.columns]].copy()
        return subset.to_html(index=False, classes="table", border=0, justify="left")

    strengths = "".join(f"<li>{item}</li>" for item in assessment.get("strengths", []))
    limitations = "".join(f"<li>{item}</li>" for item in assessment.get("limitations", []))
    availability_df = pd.DataFrame(availability_rows)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{
      font-family: 'Segoe UI', 'Noto Sans KR', sans-serif;
      margin: 0 auto;
      max-width: 1280px;
      padding: 28px 34px 80px;
      color: #1f2937;
      background: #f7f8fa;
      line-height: 1.55;
    }}
    h1, h2, h3 {{ color: #102a43; }}
    .hero {{
      background: linear-gradient(135deg, #0f4c81, #2d6a4f);
      color: white;
      padding: 22px 24px;
      border-radius: 18px;
      box-shadow: 0 16px 35px rgba(16, 42, 67, 0.18);
      margin-bottom: 20px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin: 18px 0 24px;
    }}
    .card {{
      background: white;
      border-radius: 16px;
      padding: 16px 18px;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
      border: 1px solid #e7edf5;
    }}
    .metric {{
      font-size: 1.6rem;
      font-weight: 700;
      margin-top: 4px;
      color: #0f172a;
    }}
    .label {{
      font-size: 0.9rem;
      color: #52606d;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .section {{
      background: white;
      border-radius: 18px;
      padding: 20px 22px;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.07);
      margin-bottom: 18px;
      border: 1px solid #e7edf5;
    }}
    .table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.93rem;
    }}
    .table th, .table td {{
      border-bottom: 1px solid #e5e7eb;
      padding: 8px 10px;
      vertical-align: top;
      text-align: left;
    }}
    .table th {{
      background: #f8fafc;
    }}
    .figure-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 16px;
    }}
    .figure-card img {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid #d7dee8;
      background: white;
    }}
    .muted {{ color: #6b7280; }}
    .two-col {{
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 16px;
    }}
    @media (max-width: 980px) {{
      .two-col {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="hero">
    <h1>{title}</h1>
    <p>This report aggregates full-dataset benchmark runs for baseline full-schema prompting and retrieval-premapped prompting under the same version0_15 prompt/search pipeline.</p>
  </div>

  <div class="cards">
    <div class="card"><div class="label">Runnable Models</div><div class="metric">{assessment.get("runnable_model_count", 0)}</div></div>
    <div class="card"><div class="label">Blocked Models</div><div class="metric">{assessment.get("blocked_model_count", 0)}</div></div>
    <div class="card"><div class="label">Best Quality</div><div class="metric">{findings.get("best_quality", {}).get("model_key", "-")}</div><div class="muted">{findings.get("best_quality", {}).get("condition", "-")} · DET {findings.get("best_quality", {}).get("avg_det_score", 0):.2f}</div></div>
    <div class="card"><div class="label">Largest Prompt Reduction</div><div class="metric">{findings.get("largest_prompt_reduction", {}).get("model_key", "-")}</div><div class="muted">{findings.get("largest_prompt_reduction", {}).get("reduction_pct_avg_prompt_tokens", 0):.2f}% vs baseline</div></div>
  </div>

  <div class="section two-col">
    <div>
      <h2>Main Findings</h2>
      <ul>
        <li>Best quality condition: <strong>{findings.get("best_quality", {}).get("model_key", "-")}</strong> under <strong>{findings.get("best_quality", {}).get("condition", "-")}</strong>.</li>
        <li>Fastest condition: <strong>{findings.get("fastest", {}).get("model_key", "-")}</strong> under <strong>{findings.get("fastest", {}).get("condition", "-")}</strong>.</li>
        <li>Largest strict DET gain from retrieval: <strong>{findings.get("best_det_gain_from_retrieval", {}).get("model_key", "-")}</strong> ({findings.get("best_det_gain_from_retrieval", {}).get("delta_avg_det_score", 0):.2f}).</li>
        <li>Strongest category-level gain: model <strong>{findings.get("strongest_category_gain", {}).get("model_key", "-")}</strong>, category <strong>{findings.get("strongest_category_gain", {}).get("category", "-")}</strong>.</li>
        <li>Largest category-level drop: model <strong>{findings.get("largest_category_drop", {}).get("model_key", "-")}</strong>, category <strong>{findings.get("largest_category_drop", {}).get("category", "-")}</strong>.</li>
      </ul>
    </div>
    <div>
      <h2>Readiness Assessment</h2>
      <p><strong>Publication readiness:</strong> {assessment.get("publication_readiness", "partial")}</p>
      <h3>Strengths</h3>
      <ul>{strengths}</ul>
      <h3>Limitations</h3>
      <ul>{limitations}</ul>
    </div>
  </div>

  <div class="section">
    <h2>Availability Summary</h2>
    {_table(availability_df, ["model_key", "status", "note", "resolved_model_path"])}
  </div>

  <div class="section">
    <h2>Dataset Context Summary</h2>
    <p class="muted">This table explains where retrieval premapping can matter most. Categories with many rows that have empty <code>connected_devices</code> are the categories most exposed to full-schema fallback under the baseline condition.</p>
    {_table(dataset_context_df, ["category", "row_count", "empty_connected_devices_count", "nonempty_connected_devices_count", "empty_connected_devices_ratio"])}
  </div>

  <div class="section">
    <h2>Condition Summary</h2>
    {_table(combined_suite.sort_values(["model_key", "condition"]), ["model_key", "condition", "avg_det_score", "det_pass_rate", "warm_latency_p50", "avg_prompt_tokens", "peak_vram_gb_max", "failure_rate"])}
  </div>

  <div class="section">
    <h2>Retrieval vs Baseline Deltas</h2>
    {_table(delta_suite.sort_values("model_key"), ["model_key", "delta_avg_det_score", "delta_det_pass_rate", "reduction_pct_avg_prompt_tokens", "reduction_pct_warm_latency_p50", "reduction_pct_peak_vram_gb_max", "delta_failure_rate"])}
  </div>

  <div class="section">
    <h2>Figures</h2>
    <div class="figure-grid">
      {''.join(f"<div class='figure-card'><h3>{item['title']}</h3><img src='{Path(item['path']).name}' alt='{item['title']}' /></div>" for item in figures)}
    </div>
  </div>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aggregate multiple baseline/retrieval benchmark result directories into paper-ready study outputs.")
    parser.add_argument("--baseline-dir", action="append", default=[], help="Benchmark result dir for baseline schema-fallback runs. Can be repeated.")
    parser.add_argument("--retrieval-dir", action="append", default=[], help="Benchmark result dir for retrieval-premapping runs. Can be repeated.")
    parser.add_argument("--blocked-model", action="append", default=[], help="Explicit blocked/unrun model entry. Format: model_key=status|note")
    parser.add_argument("--study-title", default="JOILang Prompt Context Study")
    parser.add_argument("--out-dir", default="", help="Default: results/paper_study_<timestamp>/paper")
    parser.add_argument("--print-json", action="store_true")
    return parser


def aggregate_paper_study(
    *,
    baseline_dirs: list[str | Path],
    retrieval_dirs: list[str | Path],
    blocked_models: list[str] | None = None,
    study_title: str = "JOILang Prompt Context Study",
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    baseline_paths = [Path(path).resolve() for path in baseline_dirs]
    retrieval_paths = [Path(path).resolve() for path in retrieval_dirs]
    out_dir = Path(out_dir).resolve() if out_dir else RESULTS_DIR / "paper_study_outputs" / "paper"
    out_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = out_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    baseline_payload = _load_condition_rows(baseline_paths, "baseline")
    retrieval_payload = _load_condition_rows(retrieval_paths, "retrieval")

    combined_suite_rows = baseline_payload["suite"] + retrieval_payload["suite"]
    combined_category_rows = baseline_payload["category"] + retrieval_payload["category"]
    combined_failure_rows = baseline_payload["failure"] + retrieval_payload["failure"]
    combined_row_rows = baseline_payload["row"] + retrieval_payload["row"]
    manifests = baseline_payload["manifest"] + retrieval_payload["manifest"]

    combined_suite_df = pd.DataFrame(combined_suite_rows)
    combined_category_df = pd.DataFrame(combined_category_rows)
    combined_failure_df = pd.DataFrame(combined_failure_rows)
    combined_row_df = pd.DataFrame(combined_row_rows)

    delta_suite_rows = _merge_conditions(baseline_payload["suite"], retrieval_payload["suite"], keys=["model_key"], metrics=RELEVANT_SUITE_METRICS)
    delta_category_rows = _merge_conditions(
        baseline_payload["category"],
        retrieval_payload["category"],
        keys=["model_key", "category"],
        metrics=RELEVANT_CATEGORY_METRICS,
    )
    delta_row_rows = _merge_conditions(
        baseline_payload["row"],
        retrieval_payload["row"],
        keys=["model_key", "row_no", "category", "command_eng", "command_kor", "gt_name", "gt_code"],
        metrics=[
            "det_score",
            "det_gt_similarity",
            "det_gt_service_coverage",
            "det_gt_receiver_coverage",
            "det_dataflow_score",
            "det_numeric_grounding",
            "det_enum_grounding",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "llm_latency_sec",
            "total_pipeline_sec",
            "peak_vram_gb",
        ],
    )

    delta_suite_df = pd.DataFrame(delta_suite_rows)
    delta_category_df = pd.DataFrame(delta_category_rows)
    delta_row_df = pd.DataFrame(delta_row_rows)

    dataset_path = Path(DATASET_DEFAULT)
    if manifests:
        for manifest in manifests:
            dataset_value = _safe_text(manifest.get("dataset"))
            if dataset_value:
                candidate = Path(dataset_value)
                if not candidate.is_absolute():
                    candidate = (VERSION_ROOT / dataset_value).resolve()
                if candidate.exists():
                    dataset_path = candidate
                    break
    dataset_context_rows = _build_dataset_context_summary(dataset_path)
    dataset_context_df = pd.DataFrame(dataset_context_rows)

    availability_rows: list[dict[str, Any]] = []
    if not combined_suite_df.empty:
        by_model: dict[str, set[str]] = {}
        for _, row in combined_suite_df.iterrows():
            by_model.setdefault(_safe_text(row.get("model_key")), set()).add(_safe_text(row.get("condition")))
        resolved_path_by_model = (
            combined_suite_df.groupby("model_key")["resolved_model_path"].first().to_dict()
            if "resolved_model_path" in combined_suite_df.columns
            else {}
        )
        for model_key, conditions in sorted(by_model.items()):
            if conditions == {"baseline", "retrieval"}:
                status = "ran_both"
            elif conditions == {"baseline"}:
                status = "ran_baseline_only"
            elif conditions == {"retrieval"}:
                status = "ran_retrieval_only"
            else:
                status = "ran_partial"
            availability_rows.append(
                {
                    "model_key": model_key,
                    "status": status,
                    "note": "",
                    "resolved_model_path": resolved_path_by_model.get(model_key, ""),
                }
            )
    for raw in blocked_models or []:
        entry = _parse_blocked_entry(raw)
        if not any(_safe_text(row.get("model_key")) == entry["model_key"] for row in availability_rows):
            availability_rows.append({**entry, "resolved_model_path": ""})

    figures: list[dict[str, str]] = []
    if not combined_suite_df.empty:
        for x_key, title, filename in [
            ("warm_latency_p50", "Strict DET vs Warm Latency", "det_vs_warm_latency_by_condition.png"),
            ("avg_prompt_tokens", "Strict DET vs Prompt Tokens", "det_vs_prompt_tokens_by_condition.png"),
            ("peak_vram_gb_max", "Strict DET vs Peak VRAM", "det_vs_peak_vram_by_condition.png"),
        ]:
            path = figure_dir / filename
            _plot_tradeoff(combined_suite_df, x_key=x_key, y_key="avg_det_score", title=title, png_path=path)
            figures.append({"title": title, "path": str(path)})
        bar_path = figure_dir / "condition_metric_bars.png"
        _plot_condition_bars(combined_suite_df, png_path=bar_path)
        figures.append({"title": "Condition Metric Bars", "path": str(bar_path)})
    if not delta_category_df.empty:
        path = figure_dir / "category_det_delta_heatmap.png"
        _plot_category_heatmap(delta_category_df, value_key="delta_avg_det_score", title="Retrieval - Baseline Strict DET by Category", png_path=path)
        figures.append({"title": "Category DET Delta Heatmap", "path": str(path)})
        path = figure_dir / "category_prompt_reduction_heatmap.png"
        _plot_category_heatmap(delta_category_df, value_key="reduction_pct_avg_prompt_tokens", title="Prompt Reduction % by Category", png_path=path)
        figures.append({"title": "Category Prompt Reduction Heatmap", "path": str(path)})
    if not delta_row_df.empty:
        path = figure_dir / "row_det_delta_hist.png"
        _plot_delta_histograms(delta_row_df, value_key="delta_det_score", title="Per-row Strict DET Delta", png_path=path)
        figures.append({"title": "Row DET Delta Histogram", "path": str(path)})
        if "reduction_pct_prompt_tokens" in delta_row_df.columns:
            path = figure_dir / "row_prompt_reduction_hist.png"
            _plot_delta_histograms(delta_row_df, value_key="reduction_pct_prompt_tokens", title="Per-row Prompt Reduction %", png_path=path)
            figures.append({"title": "Row Prompt Reduction Histogram", "path": str(path)})
    if not combined_failure_df.empty:
        path = figure_dir / "failure_reason_heatmap.png"
        combined_failure_df["count"] = combined_failure_df["count"].apply(_safe_float)
        _plot_failure_reason_heatmap(combined_failure_df, png_path=path)
        figures.append({"title": "Failure Reason Heatmap", "path": str(path)})
    if dataset_context_rows:
        path = figure_dir / "dataset_context_regime.png"
        _plot_dataset_context(dataset_context_rows, png_path=path)
        figures.append({"title": "Dataset Context Regime", "path": str(path)})

    findings = _build_findings(combined_suite_df, delta_suite_df, delta_category_df, availability_rows)
    assessment = _study_assessment(findings, availability_rows)

    _write_csv(out_dir / "combined_suite_condition.csv", combined_suite_rows)
    _write_csv(out_dir / "combined_category_condition.csv", combined_category_rows)
    _write_csv(out_dir / "combined_failure_reason_condition.csv", combined_failure_rows)
    _write_csv(out_dir / "combined_row_condition.csv", combined_row_rows)
    _write_csv(out_dir / "condition_delta_by_model.csv", delta_suite_rows)
    _write_csv(out_dir / "condition_delta_by_category.csv", delta_category_rows)
    _write_csv(out_dir / "condition_delta_by_row.csv", delta_row_rows)
    _write_csv(out_dir / "availability_summary.csv", availability_rows)
    _write_csv(out_dir / "dataset_context_summary.csv", dataset_context_rows)
    dump_json(out_dir / "study_manifest_rows.json", manifests)

    report_lines = [
        f"# {study_title}",
        "",
        "## Study Scope",
        "",
        f"- Baseline result dirs: {len(baseline_paths)}",
        f"- Retrieval result dirs: {len(retrieval_paths)}",
        f"- Runnable models in both conditions: {assessment['runnable_model_count']}",
        f"- Blocked or unrun models: {assessment['blocked_model_count']}",
        "",
        "## Main Findings",
        "",
        f"- Best quality condition: `{findings.get('best_quality', {}).get('model_key', '-')}` under `{findings.get('best_quality', {}).get('condition', '-')}` with strict DET `{findings.get('best_quality', {}).get('avg_det_score', 0):.2f}`.",
        f"- Fastest condition: `{findings.get('fastest', {}).get('model_key', '-')}` under `{findings.get('fastest', {}).get('condition', '-')}` with warm latency p50 `{findings.get('fastest', {}).get('warm_latency_p50', 0):.2f}` s.",
        f"- Largest strict DET gain from retrieval: `{findings.get('best_det_gain_from_retrieval', {}).get('model_key', '-')}` (`{findings.get('best_det_gain_from_retrieval', {}).get('delta_avg_det_score', 0):.2f}`).",
        f"- Largest prompt reduction: `{findings.get('largest_prompt_reduction', {}).get('model_key', '-')}` (`{findings.get('largest_prompt_reduction', {}).get('reduction_pct_avg_prompt_tokens', 0):.2f}%`).",
        "",
        "## Category Findings",
        "",
        f"- Strongest category gain: model `{findings.get('strongest_category_gain', {}).get('model_key', '-')}`, category `{findings.get('strongest_category_gain', {}).get('category', '-')}`, delta DET `{findings.get('strongest_category_gain', {}).get('delta_avg_det_score', 0):.2f}`.",
        f"- Largest category drop: model `{findings.get('largest_category_drop', {}).get('model_key', '-')}`, category `{findings.get('largest_category_drop', {}).get('category', '-')}`, delta DET `{findings.get('largest_category_drop', {}).get('delta_avg_det_score', 0):.2f}`.",
        "",
        "## Strengths",
        "",
        *[f"- {item}" for item in assessment.get("strengths", [])],
        "",
        "## Limitations",
        "",
        *[f"- {item}" for item in assessment.get("limitations", [])],
        "",
        "## Output Files",
        "",
        "- `combined_suite_condition.csv`",
        "- `combined_category_condition.csv`",
        "- `condition_delta_by_model.csv`",
        "- `condition_delta_by_category.csv`",
        "- `condition_delta_by_row.csv`",
        "- `availability_summary.csv`",
    ]
    report_md = "\n".join(report_lines).strip() + "\n"
    (out_dir / "paper_findings.md").write_text(report_md, encoding="utf-8")
    _render_html_report(
        out_dir / "paper_findings.html",
        title=study_title,
        findings=findings,
        assessment=assessment,
        combined_suite=combined_suite_df,
        delta_suite=delta_suite_df,
        availability_rows=availability_rows,
        dataset_context_df=dataset_context_df,
        figures=figures,
    )

    summary = {
        "study_title": study_title,
        "out_dir": str(out_dir),
        "baseline_dirs": [str(path) for path in baseline_paths],
        "retrieval_dirs": [str(path) for path in retrieval_paths],
        "findings": findings,
        "assessment": assessment,
        "figures": figures,
        "combined_suite_csv": str(out_dir / "combined_suite_condition.csv"),
        "combined_category_csv": str(out_dir / "combined_category_condition.csv"),
        "delta_model_csv": str(out_dir / "condition_delta_by_model.csv"),
        "delta_category_csv": str(out_dir / "condition_delta_by_category.csv"),
        "delta_row_csv": str(out_dir / "condition_delta_by_row.csv"),
        "availability_csv": str(out_dir / "availability_summary.csv"),
        "dataset_context_csv": str(out_dir / "dataset_context_summary.csv"),
        "paper_findings_md": str(out_dir / "paper_findings.md"),
        "paper_findings_html": str(out_dir / "paper_findings.html"),
    }
    dump_json(out_dir / "paper_summary.json", summary)
    return summary


def main() -> int:
    args = build_parser().parse_args()
    summary = aggregate_paper_study(
        baseline_dirs=args.baseline_dir,
        retrieval_dirs=args.retrieval_dir,
        blocked_models=args.blocked_model,
        study_title=args.study_title,
        out_dir=args.out_dir or None,
    )
    if args.print_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Paper out dir: {summary['out_dir']}")
        print(f"Summary JSON: {Path(summary['out_dir']) / 'paper_summary.json'}")
        print(f"Findings HTML: {Path(summary['out_dir']) / 'paper_findings.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
