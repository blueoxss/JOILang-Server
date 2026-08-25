#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from utils.pipeline_common import RESULTS_DIR, atomic_write_csv, dump_json


LOCAL_MODELS = ["phi35_mini", "qwen25_coder_7b", "llama31_8b", "gemma2_9b_it", "qwen25_coder_14b"]
TABLE3_VARIANTS = {"B1", "B2", "B6"}
TABLE4_VARIANTS = {
    "B6": "Full GPS",
    "B3": "Fixed block",
    "B4": "Random search",
    "B5": "GA + benchmark only",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export final paper-facing artifacts from available measured results.")
    parser.add_argument("--study-root", default="")
    parser.add_argument("--paper-dir", default="")
    parser.add_argument(
        "--result-dir",
        action="append",
        default=[],
        help="Measured benchmark result in VARIANT=PATH form, e.g. B1=/abs/cloud or B2=/abs/local.",
    )
    parser.add_argument("--ga-study-dir", default="")
    parser.add_argument("--cloud-equivalence-dir", default="")
    parser.add_argument("--availability-csv", default="")
    parser.add_argument("--availability-json", default="")
    parser.add_argument("--command-used", default="")
    parser.add_argument("--suite", default="paper_local5")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quiet-final-summary", action="store_true")
    return parser


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _resolve_study_root(raw: str) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    return (RESULTS_DIR / f"paper_study_{_timestamp()}").resolve()


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _detpass_percent(value: Any) -> float:
    rate = _float(value, 0.0)
    return rate * 100.0 if rate <= 1.000001 else rate


def _variant_specs(values: list[str]) -> dict[str, Path]:
    specs: dict[str, Path] = {}
    for raw in values:
        if "=" not in raw:
            continue
        key, path = raw.split("=", 1)
        key = key.strip()
        if key:
            specs[key] = Path(path).expanduser().resolve()
    return specs


def _read_suite_rows(specs: dict[str, Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant, path in specs.items():
        suite_csv = path / "suite_summary.csv"
        for row in _read_csv(suite_csv):
            model_key = row.get("model_key", "")
            rows.append(
                {
                    "variant": variant,
                    "variant_label": _variant_label(variant),
                    "source_dir": str(path),
                    "model_key": model_key,
                    "model_label": row.get("model_label") or model_key,
                    "detpass_percent": round(_detpass_percent(row.get("det_pass_rate")), 4),
                    "mean_sdet": round(_float(row.get("avg_det_score")), 4),
                    "avg_input_tokens": round(_float(row.get("avg_prompt_tokens") or row.get("paper_avg_prompt_tokens")), 4),
                    "latency_sec": round(_float(row.get("warm_latency_p50") or row.get("avg_latency_sec")), 4),
                    "mode": row.get("mode", ""),
                    "prompt_render_mode": row.get("prompt_render_mode", ""),
                    "row_count": row.get("row_count", ""),
                    "measured": True,
                }
            )
    return rows


def _variant_label(variant: str) -> str:
    labels = {
        "B0": "Hand-crafted local baseline",
        "B1": "Cloud reference",
        "B2": "Direct cloud-to-local transfer",
        "B3": "Fixed block",
        "B4": "Random search",
        "B5": "GA + benchmark only",
        "B6": "Full GPS / Ours",
    }
    return labels.get(variant, variant)


def _latex_escape(text: Any) -> str:
    return str(text).replace("_", r"\_").replace("%", r"\%")


def _write_latex_table(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    lines = ["\\begin{tabular}{" + "l" * len(headers) + "}", "\\toprule"]
    lines.append(" & ".join(_latex_escape(header) for header in headers) + r" \\")
    lines.append("\\midrule")
    for row in rows:
        lines.append(" & ".join(_latex_escape(row.get(header, "")) for header in headers) + r" \\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    _write_text(path, "\n".join(lines))


def _load_ga_progress(ga_dir: Path) -> list[dict[str, str]]:
    return _read_csv(ga_dir / "ga_progress_all.csv") if ga_dir else []


def _write_figure1(paper_dir: Path, ga_rows: list[dict[str, str]], missing_models: list[str]) -> dict[str, Any]:
    figure_data = paper_dir / "figure_data"
    figures = paper_dir / "figures"
    figure_data.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    generation_rows: list[dict[str, Any]] = []
    for row in ga_rows:
        generation_rows.append(
            {
                "model_key": row.get("model_key", ""),
                "category": row.get("category", ""),
                "generation": row.get("generation", ""),
                "DETPass": row.get("validation_det_pass_rate", ""),
                "SDET": row.get("validation_avg_det_score", ""),
                "fitness": row.get("fitness", ""),
                "prompt_tokens": row.get("prompt_tokens", ""),
                "latency_sec": row.get("llm_latency_sec", ""),
                "genome_id": row.get("genome_id", ""),
            }
        )
    fieldnames = ["model_key", "category", "generation", "DETPass", "SDET", "fitness", "prompt_tokens", "latency_sec", "genome_id"]
    atomic_write_csv(figure_data / "figure1_generation_dynamics.csv", fieldnames, generation_rows)

    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in generation_rows:
        grouped[(str(row["model_key"]), str(row["category"]), str(row["generation"]))].append(_float(row["DETPass"]))
    category_rows = [
        {
            "model_key": model,
            "category": category,
            "generation": generation,
            "mean_DETPass": round(sum(values) / len(values), 4) if values else "",
        }
        for (model, category, generation), values in sorted(grouped.items())
    ]
    atomic_write_csv(figure_data / "figure1_category_dynamics.csv", ["model_key", "category", "generation", "mean_DETPass"], category_rows)

    summary = {
        "status": "measured" if generation_rows else "pending",
        "description": "Prompt search dynamics across model scales.",
        "missing_models": missing_models,
        "row_count": len(generation_rows),
        "notes": [] if generation_rows else ["No GA progress rows were provided; figure is a pending placeholder."],
    }
    dump_json(figure_data / "figure1_summary.json", summary)

    _plot_figure1(figures, generation_rows, summary)
    return {
        "png": str(figures / "figure1_prompt_search_dynamics_across_model_scales.png"),
        "pdf": str(figures / "figure1_prompt_search_dynamics_across_model_scales.pdf"),
        "data": str(figure_data / "figure1_generation_dynamics.csv"),
        "summary": str(figure_data / "figure1_summary.json"),
    }


def _write_figure2(paper_dir: Path, suite_rows: list[dict[str, Any]]) -> dict[str, Any]:
    figure_data = paper_dir / "figure_data"
    figures = paper_dir / "figures"
    figure_data.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "model_key": row["model_key"],
            "model_label": row["model_label"],
            "variant": row["variant"],
            "variant_label": row["variant_label"],
            "DETPass": row["detpass_percent"],
            "SDET": row["mean_sdet"],
            "avg_prompt_tokens": row["avg_input_tokens"],
            "warm_latency_p50": row["latency_sec"],
            "deployment_point": str(row["variant"] != "B1"),
            "source_dir": row["source_dir"],
        }
        for row in suite_rows
    ]
    headers = ["model_key", "model_label", "variant", "variant_label", "DETPass", "SDET", "avg_prompt_tokens", "warm_latency_p50", "deployment_point", "source_dir"]
    atomic_write_csv(figure_data / "figure2_pareto_points.csv", headers, rows)
    summary = {
        "status": "measured" if rows else "pending",
        "description": "Deployment-aware Pareto frontier. GPT-4.1-mini is an upper cloud reference, not a local frontier point.",
        "point_count": len(rows),
        "notes": [] if rows else ["No measured suite rows were provided; figure is a pending placeholder."],
    }
    dump_json(figure_data / "figure2_frontier_summary.json", summary)
    _plot_figure2(figures, rows, summary)
    return {
        "png": str(figures / "figure2_deployment_aware_pareto_frontier_final.png"),
        "pdf": str(figures / "figure2_deployment_aware_pareto_frontier_final.pdf"),
        "data": str(figure_data / "figure2_pareto_points.csv"),
        "summary": str(figure_data / "figure2_frontier_summary.json"),
    }


def _plot_figure1(figures: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 5))
    if rows:
        grouped: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        for row in rows:
            grouped[str(row["model_key"])][int(float(row["generation"] or 0))].append(_float(row["DETPass"]))
        for model_key, by_gen in sorted(grouped.items()):
            xs = sorted(by_gen)
            ys = [sum(by_gen[x]) / len(by_gen[x]) for x in xs]
            ax.plot(xs, ys, marker="o", label=model_key)
        ax.set_xlabel("Generation")
        ax.set_ylabel("DETPass (%)")
        ax.legend(loc="best", fontsize=8)
    else:
        ax.text(0.5, 0.5, "Pending actual GA measurements", ha="center", va="center", fontsize=14)
        ax.set_axis_off()
    ax.set_title("Figure 1. Prompt search dynamics across model scales")
    fig.tight_layout()
    fig.savefig(figures / "figure1_prompt_search_dynamics_across_model_scales.png", dpi=180)
    fig.savefig(figures / "figure1_prompt_search_dynamics_across_model_scales.pdf")
    plt.close(fig)


def _plot_figure2(figures: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    if rows:
        for row in rows:
            label = f"{row['model_key']} {row['variant']}"
            marker = "x" if str(row["deployment_point"]).lower() == "false" else "o"
            axes[0].scatter(_float(row["avg_prompt_tokens"]), _float(row["DETPass"]), marker=marker)
            axes[0].annotate(label, (_float(row["avg_prompt_tokens"]), _float(row["DETPass"])), fontsize=7)
            axes[1].scatter(_float(row["warm_latency_p50"]), _float(row["DETPass"]), marker=marker)
            axes[1].annotate(label, (_float(row["warm_latency_p50"]), _float(row["DETPass"])), fontsize=7)
        axes[0].set_xlabel("Average input tokens")
        axes[0].set_ylabel("DETPass (%)")
        axes[1].set_xlabel("Warm latency p50 (s)")
        axes[1].set_ylabel("DETPass (%)")
    else:
        for ax in axes:
            ax.text(0.5, 0.5, "Pending actual measurements", ha="center", va="center", fontsize=12)
            ax.set_axis_off()
    axes[0].set_title("(a) DETPass vs prompt tokens")
    axes[1].set_title("(b) DETPass vs warm latency")
    fig.suptitle("Figure 2. Deployment-aware Pareto frontier")
    fig.tight_layout()
    fig.savefig(figures / "figure2_deployment_aware_pareto_frontier_final.png", dpi=180)
    fig.savefig(figures / "figure2_deployment_aware_pareto_frontier_final.pdf")
    plt.close(fig)


def _write_table3(paper_dir: Path, suite_rows: list[dict[str, Any]]) -> dict[str, str]:
    table_dir = paper_dir / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    b0_present = any(row["variant"] == "B0" for row in suite_rows)
    for row in suite_rows:
        if row["variant"] not in TABLE3_VARIANTS and row["variant"] != "B0":
            continue
        rows.append(
            {
                "Model": row["model_label"],
                "Variant": f"{row['variant']} {_variant_label(row['variant'])}",
                "DETPass (%)": row["detpass_percent"],
                "Mean SDET": row["mean_sdet"],
                "Avg Input Tokens": row["avg_input_tokens"],
                "Latency (s)": row["latency_sec"],
            }
        )
    if not b0_present:
        rows.append(
            {
                "Model": "B0 local baseline",
                "Variant": "N/A",
                "DETPass (%)": "N/A",
                "Mean SDET": "N/A",
                "Avg Input Tokens": "N/A",
                "Latency (s)": "N/A",
                "note": "B0 is reserved for a manually designed local baseline and was not executed in this run.",
            }
        )
    headers = ["Model", "Variant", "DETPass (%)", "Mean SDET", "Avg Input Tokens", "Latency (s)"]
    atomic_write_csv(table_dir / "table3_main_results.csv", headers, rows)
    dump_json(table_dir / "table3_main_results.json", {"rows": rows, "b0_note": rows[-1].get("note", "") if rows else ""})
    _write_latex_table(table_dir / "table3_main_results.tex", headers, rows)
    return {
        "csv": str(table_dir / "table3_main_results.csv"),
        "json": str(table_dir / "table3_main_results.json"),
        "tex": str(table_dir / "table3_main_results.tex"),
    }


def _write_table4(paper_dir: Path, suite_rows: list[dict[str, Any]]) -> dict[str, str]:
    table_dir = paper_dir / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for variant, label in TABLE4_VARIANTS.items():
        measured = next((row for row in suite_rows if row["variant"] == variant and row["model_key"] == "qwen25_coder_14b"), None)
        if measured:
            rows.append(
                {
                    "Variant": f"{variant} {label}",
                    "DETPass": measured["detpass_percent"],
                    "SDET": measured["mean_sdet"],
                    "Tokens": measured["avg_input_tokens"],
                }
            )
        else:
            rows.append({"Variant": f"{variant} {label}", "DETPass": "N/A", "SDET": "N/A", "Tokens": "N/A"})
    headers = ["Variant", "DETPass", "SDET", "Tokens"]
    atomic_write_csv(table_dir / "table4_ablation_qwen14.csv", headers, rows)
    dump_json(table_dir / "table4_ablation_qwen14.json", {"rows": rows, "notes": ["Only B3/B4/B5/B6 are paper-facing ablation rows."]})
    _write_latex_table(table_dir / "table4_ablation_qwen14.tex", headers, rows)
    return {
        "csv": str(table_dir / "table4_ablation_qwen14.csv"),
        "json": str(table_dir / "table4_ablation_qwen14.json"),
        "tex": str(table_dir / "table4_ablation_qwen14.tex"),
    }


def _failure_mapping(reason: str) -> tuple[str, str, str, str]:
    base = str(reason).split(":", 1)[0].strip()
    mapping = {
        "invalid_json": ("schema_violation", "output_format", "repair_clause_injection", "03"),
        "schema_missing_keys": ("schema_violation", "output_schema", "repair_clause_injection", "03"),
        "unknown_service": ("service_mapping", "service_mapping", "service_grounding_rule", "02"),
        "service_match": ("service_mapping", "service_mapping", "service_grounding_rule", "02"),
        "gt_service_coverage": ("service_mapping", "service_mapping", "coverage_rule", "02"),
        "arg_type": ("enum_type_mismatch", "schema_enum_grounding", "enum_type_rule", "02"),
        "enum_grounding": ("enum_type_mismatch", "schema_enum_grounding", "enum_type_rule", "02"),
        "numeric_grounding": ("numeric_or_temporal_error", "temporal_rule", "unit_grounding_rule", "06"),
        "dataflow": ("dataflow_error", "dataflow", "dataflow_rule", "06"),
        "gt_receiver_coverage": ("owner_device_mismatch", "owner_device_rule", "receiver_rule", "02"),
        "semantic": ("semantic_error", "skeleton", "skeleton_rule", "06"),
        "extraneous": ("extraneous_action", "skeleton", "minimality_rule", "06"),
        "gt_mismatch": ("gt_mismatch", "det_helper", "targeted_repair_hint", "06"),
    }
    return mapping.get(base, ("other", "det_helper", "targeted_repair_hint", "06"))


def _parse_failure_reasons(raw: Any) -> list[str]:
    text = str(raw or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text.replace("'", '"')) if text.startswith("[") else []
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except Exception:
        pass
    return [item.strip() for item in text.strip("[]").split(",") if item.strip()]


def _write_structured_feedback(study_root: Path, suite_specs: dict[str, Path]) -> dict[str, str]:
    records: list[dict[str, Any]] = []
    now = datetime.now().isoformat(timespec="seconds")
    for variant, path in suite_specs.items():
        for row in _read_csv(path / "row_comparison.csv"):
            model_keys = sorted({key.split("__", 1)[0] for key in row if key.endswith("__failure_reasons")})
            for model_key in model_keys:
                reasons = _parse_failure_reasons(row.get(f"{model_key}__failure_reasons"))
                if not reasons:
                    continue
                for reason in reasons:
                    failure_type, block_family, mutation_type, block_id = _failure_mapping(reason)
                    records.append(
                        {
                            "row_id": row.get("row_no", ""),
                            "model_key": model_key,
                            "genome_id": row.get(f"{model_key}__genome_id", ""),
                            "det_profile": row.get(f"{model_key}__det_profile", ""),
                            "failure_type": failure_type,
                            "original_failure_reasons": reason,
                            "affected_block_family": block_family,
                            "suggested_mutation_type": mutation_type,
                            "prompt_block_id": block_id,
                            "variant": variant,
                            "timestamp": now,
                        }
                    )
    jsonl_path = study_root / "structured_feedback.jsonl"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    counter = Counter((rec["failure_type"], rec["affected_block_family"], rec["suggested_mutation_type"]) for rec in records)
    summary_rows = [
        {
            "failure_type": key[0],
            "affected_block_family": key[1],
            "suggested_mutation_type": key[2],
            "count": count,
        }
        for key, count in counter.most_common()
    ]
    atomic_write_csv(
        study_root / "structured_feedback_summary.csv",
        ["failure_type", "affected_block_family", "suggested_mutation_type", "count"],
        summary_rows,
    )
    return {
        "jsonl": str(jsonl_path),
        "summary_csv": str(study_root / "structured_feedback_summary.csv"),
    }


def _write_promotion_outputs(study_root: Path, paper_dir: Path, suite_rows: list[dict[str, Any]]) -> dict[str, str]:
    promotion_dir = paper_dir / "promotion"
    promotion_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    now = datetime.now().isoformat(timespec="seconds")
    for row in suite_rows:
        if row["variant"] != "B6":
            continue
        rows.append(
            {
                "candidate_id": f"{row['model_key']}_{row['variant']}",
                "model_key": row["model_key"],
                "genome_id": "",
                "DETPass": row["detpass_percent"],
                "SDET": row["mean_sdet"],
                "avg_prompt_tokens": row["avg_input_tokens"],
                "warm_latency_p50": row["latency_sec"],
                "replay_gate_pass": "pending" if row["measured"] else "N/A",
                "regression_gate_pass": "pending" if row["measured"] else "N/A",
                "promoted": "false",
                "rejection_reason": "pending replay/regression acceptance audit",
                "previous_accepted_prompt": "",
                "accepted_prompt_path": "",
                "timestamp": now,
            }
        )
    if not rows:
        rows.append(
            {
                "candidate_id": "pending",
                "model_key": "",
                "genome_id": "",
                "DETPass": "N/A",
                "SDET": "N/A",
                "avg_prompt_tokens": "N/A",
                "warm_latency_p50": "N/A",
                "replay_gate_pass": "N/A",
                "regression_gate_pass": "N/A",
                "promoted": "false",
                "rejection_reason": "No B6 measured candidate available.",
                "previous_accepted_prompt": "",
                "accepted_prompt_path": "",
                "timestamp": now,
            }
        )
    headers = [
        "candidate_id",
        "model_key",
        "genome_id",
        "DETPass",
        "SDET",
        "avg_prompt_tokens",
        "warm_latency_p50",
        "replay_gate_pass",
        "regression_gate_pass",
        "promoted",
        "rejection_reason",
        "previous_accepted_prompt",
        "accepted_prompt_path",
        "timestamp",
    ]
    atomic_write_csv(promotion_dir / "promotion_decisions.csv", headers, rows)
    dump_json(promotion_dir / "promotion_decisions.json", {"rows": rows})
    _write_text(
        study_root / "PROMOTION.md",
        "# Promotion Decisions\n\n"
        "Acceptance gates block promotion, not candidate generation. "
        "Rejected candidates leave the previous accepted prompt active.\n",
    )
    return {
        "csv": str(promotion_dir / "promotion_decisions.csv"),
        "json": str(promotion_dir / "promotion_decisions.json"),
        "md": str(study_root / "PROMOTION.md"),
    }


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(VERSION_ROOT.parents[1]), text=True).strip()
    except Exception:
        return ""


def main() -> int:
    args = build_parser().parse_args()
    study_root = _resolve_study_root(args.study_root)
    study_root.mkdir(parents=True, exist_ok=True)
    paper_dir = Path(args.paper_dir).expanduser().resolve() if args.paper_dir else study_root / "paper"
    paper_dir.mkdir(parents=True, exist_ok=True)

    result_specs = _variant_specs(args.result_dir)
    suite_rows = _read_suite_rows(result_specs)
    ga_dir = Path(args.ga_study_dir).expanduser().resolve() if args.ga_study_dir else Path()
    ga_rows = _load_ga_progress(ga_dir) if ga_dir else []
    measured_models = {str(row.get("model_key", "")) for row in suite_rows} | {str(row.get("model_key", "")) for row in ga_rows}
    missing_models = [model for model in LOCAL_MODELS if model not in measured_models]

    figure1 = _write_figure1(paper_dir, ga_rows, missing_models)
    figure2 = _write_figure2(paper_dir, suite_rows)
    table3 = _write_table3(paper_dir, suite_rows)
    table4 = _write_table4(paper_dir, suite_rows)
    structured_feedback = _write_structured_feedback(study_root, result_specs)
    promotion = _write_promotion_outputs(study_root, paper_dir, suite_rows)

    availability_csv = args.availability_csv or str(study_root / "availability_summary.csv")
    availability_json = args.availability_json or str(study_root / "availability_summary.json")
    manifest = {
        "run_timestamp": datetime.now().isoformat(timespec="seconds"),
        "git_commit_sha": _git_sha(),
        "command_used": args.command_used or " ".join(sys.argv),
        "suite": args.suite,
        "model_availability_summary": {"csv": availability_csv, "json": availability_json},
        "cloud_block_equivalence_path": args.cloud_equivalence_dir,
        "figure1_path": figure1,
        "figure2_path": figure2,
        "table3_path": table3,
        "table4_path": table4,
        "main_result_csv": [str(path / "suite_summary.csv") for path in result_specs.values()],
        "ablation_csv": table4["csv"],
        "promotion_decisions_path": promotion,
        "structured_feedback_path": structured_feedback,
        "missing_unavailable_models": missing_models,
        "notes": [
            "Retrieval pre-mapping is fixed runtime context construction and is not a GA mutation target.",
            "Replay cases are operational feedback and acceptance gates, not a main leaderboard metric.",
        ],
    }
    dump_json(paper_dir / "final_artifacts_manifest.json", manifest)
    _write_text(
        paper_dir / "final_artifacts_manifest.md",
        "# Final Artifacts Manifest\n\n"
        + "\n".join(f"- {key}: {value}" for key, value in manifest.items()),
    )
    if args.quiet_final_summary:
        print(f"paper artifacts: {paper_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
