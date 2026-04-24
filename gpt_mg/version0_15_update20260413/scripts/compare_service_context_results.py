#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from utils.pipeline_common import RESULTS_DIR, atomic_write_csv, dump_json


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _index_rows(rows: list[dict[str, str]], keys: list[str]) -> dict[tuple[str, ...], dict[str, str]]:
    indexed: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        indexed[tuple(str(row.get(key, "") or "") for key in keys)] = row
    return indexed


def _delta_row(
    baseline: dict[str, str],
    experiment: dict[str, str],
    *,
    keys: list[str],
) -> dict[str, Any]:
    row: dict[str, Any] = {key: str(experiment.get(key, baseline.get(key, "")) or "") for key in keys}
    metrics = [
        "avg_det_score",
        "det_pass_rate",
        "gt_exact_rate",
        "warm_latency_p50",
        "warm_latency_mean",
        "avg_prompt_tokens",
        "peak_vram_gb_max",
    ]
    for metric in metrics:
        base = _safe_float(baseline.get(metric))
        exp = _safe_float(experiment.get(metric))
        row[f"baseline_{metric}"] = round(base, 4)
        row[f"retrieval_{metric}"] = round(exp, 4)
        row[f"delta_{metric}"] = round(exp - base, 4)
        if metric in {"avg_prompt_tokens", "warm_latency_p50", "warm_latency_mean", "peak_vram_gb_max"} and base > 0:
            row[f"reduction_pct_{metric}"] = round((base - exp) / base * 100.0, 2)
    return row


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare schema-fallback and retrieval-fallback benchmark result directories.")
    parser.add_argument("--baseline-dir", required=True, help="Usually schema-fallback result dir.")
    parser.add_argument("--retrieval-dir", required=True, help="Usually retrieval-fallback result dir.")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    baseline_dir = Path(args.baseline_dir).resolve()
    retrieval_dir = Path(args.retrieval_dir).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else RESULTS_DIR / f"context_compare_{baseline_dir.name}__vs__{retrieval_dir.name}"
    output_dir.mkdir(parents=True, exist_ok=True)

    baseline_suite = _read_csv(baseline_dir / "suite_summary.csv")
    retrieval_suite = _read_csv(retrieval_dir / "suite_summary.csv")
    baseline_cat = _read_csv(baseline_dir / "category_summary.csv")
    retrieval_cat = _read_csv(retrieval_dir / "category_summary.csv")

    suite_rows: list[dict[str, Any]] = []
    base_suite_idx = _index_rows(baseline_suite, ["model_key"])
    ret_suite_idx = _index_rows(retrieval_suite, ["model_key"])
    for key in sorted(set(base_suite_idx) | set(ret_suite_idx)):
        suite_rows.append(_delta_row(base_suite_idx.get(key, {}), ret_suite_idx.get(key, {}), keys=["model_key"]))

    category_rows: list[dict[str, Any]] = []
    base_cat_idx = _index_rows(baseline_cat, ["model_key", "category"])
    ret_cat_idx = _index_rows(retrieval_cat, ["model_key", "category"])
    for key in sorted(set(base_cat_idx) | set(ret_cat_idx)):
        category_rows.append(_delta_row(base_cat_idx.get(key, {}), ret_cat_idx.get(key, {}), keys=["model_key", "category"]))

    suite_fieldnames = list(suite_rows[0].keys()) if suite_rows else ["model_key"]
    category_fieldnames = list(category_rows[0].keys()) if category_rows else ["model_key", "category"]
    atomic_write_csv(output_dir / "suite_context_comparison.csv", suite_fieldnames, suite_rows)
    atomic_write_csv(output_dir / "category_context_comparison.csv", category_fieldnames, category_rows)

    summary = {
        "baseline_dir": str(baseline_dir),
        "retrieval_dir": str(retrieval_dir),
        "output_dir": str(output_dir),
        "suite_rows": suite_rows,
        "category_rows": category_rows,
    }
    dump_json(output_dir / "context_comparison_summary.json", summary)

    if args.print_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Suite comparison CSV: {output_dir / 'suite_context_comparison.csv'}")
        print(f"Category comparison CSV: {output_dir / 'category_context_comparison.csv'}")
        print(f"Summary JSON: {output_dir / 'context_comparison_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
