#!/usr/bin/env python3
# Assumption: this script performs category-guided prompt refinement and full reruns while only writing inside gpt_mg/version0_14/.
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from scripts.run_feedback_loop import evaluate_genome_on_rows, run_feedback_loop
from scripts.run_generate import _llm_settings, generate_candidates_for_rows
from scripts.run_rerank import rerank_candidates_csv
from utils.pipeline_common import (
    DATASET_DEFAULT,
    RESULTS_DIR,
    SERVICE_SCHEMA_DEFAULT,
    dump_json,
    ensure_workspace,
    load_dataset_rows,
    load_genome,
    load_service_schema,
    make_run_id,
    sample_rows,
    select_rows,
    slugify,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run category-wise refinement, then full-dataset GT-aware reruns for version0_14.")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--genome-json", default=str(VERSION_ROOT / "genomes" / "example_genome.json"))
    parser.add_argument("--dataset", default=str(DATASET_DEFAULT))
    parser.add_argument("--service-schema", default=str(SERVICE_SCHEMA_DEFAULT))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--start-row", type=int, default=1)
    parser.add_argument("--end-row", type=int, default=None)
    parser.add_argument("--category", action="append", default=[], help="Optional category filter. Can be repeated or comma-separated.")
    parser.add_argument("--category-sample-size", type=int, default=3)
    parser.add_argument("--category-attempts", type=int, default=2)
    parser.add_argument("--candidate-k", type=int, default=1)
    parser.add_argument("--full-failure-sample-size", type=int, default=16)
    parser.add_argument("--final-attempts", type=int, default=2)
    parser.add_argument("--repair-threshold", type=float, default=75.0)
    parser.add_argument("--repair-attempts", type=int, default=1)
    parser.add_argument("--skip-full-pass", action="store_true", help="Run only category-guided prompt refinement and skip the expensive full-dataset passes.")
    parser.add_argument("--llm-mode", default=None)
    parser.add_argument("--llm-endpoint", default=None)
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--seed", type=int, default=14)
    return parser


def _category_sort_key(value: str) -> tuple[int, str]:
    token = str(value)
    return (0, f"{int(token):08d}") if token.isdigit() else (1, token)


def _write_genome(path: Path, genome: dict[str, Any]) -> None:
    dump_json(path, genome)


def _rows_for_category(selected_rows: list[tuple[int, dict[str, str]]], category: str) -> list[tuple[int, dict[str, str]]]:
    return [item for item in selected_rows if str(item[1].get("category", "")) == str(category)]


def _summary_from_rerank_csv(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    scores = [float(row.get("det_score") or 0.0) for row in rows]
    gt_sims = [float(row.get("det_gt_similarity") or 0.0) for row in rows]
    exact = sum(1 for row in rows if str(row.get("det_gt_exact", "")).lower() == "true")
    return {
        "row_count": len(rows),
        "avg_det_score": round(statistics.fmean(scores), 4) if scores else 0.0,
        "avg_gt_similarity": round(statistics.fmean(gt_sims), 4) if gt_sims else 0.0,
        "gt_exact_count": exact,
        "rows_ge_70": sum(1 for score in scores if score >= 70.0),
    }


def _pick_full_failure_rows(rerank_csv: Path, selected_rows: list[tuple[int, dict[str, str]]], sample_size: int) -> list[tuple[int, dict[str, str]]]:
    row_map = {row_no: row for row_no, row in selected_rows}
    with rerank_csv.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    rows.sort(
        key=lambda row: (
            float(row.get("det_gt_similarity") or 0.0),
            float(row.get("det_score") or 0.0),
            int(row.get("row_no") or 0),
        )
    )
    picked: list[tuple[int, dict[str, str]]] = []
    seen: set[int] = set()
    for row in rows:
        row_no = int(row.get("row_no") or 0)
        if row_no <= 0 or row_no in seen or row_no not in row_map:
            continue
        seen.add(row_no)
        picked.append((row_no, row_map[row_no]))
        if len(picked) >= sample_size:
            break
    return picked


def _run_full_pass(
    *,
    profile: str,
    genome: dict[str, Any],
    selected_rows: list[tuple[int, dict[str, str]]],
    service_schema: dict[str, dict[str, Any]],
    llm_mode: str | None,
    llm_endpoint: str | None,
    timeout_sec: int,
    retries: int,
    seed: int,
    sweep_dir: Path,
    label: str,
    repair_threshold: float,
    repair_attempts: int,
) -> dict[str, Any]:
    temperature, max_tokens, model = _llm_settings(genome, argparse.Namespace(temperature=None, max_tokens=None))
    candidates_csv = sweep_dir / f"{label}_candidates.csv"
    rerank_csv = sweep_dir / f"{label}_rerank.csv"
    generate_candidates_for_rows(
        profile=profile,
        genome=genome,
        dataset_rows=selected_rows,
        service_schema=service_schema,
        candidate_k=1,
        llm_mode=llm_mode,
        llm_endpoint=llm_endpoint,
        timeout_sec=timeout_sec,
        retries=retries,
        run_id=make_run_id(label, seed),
        output_csv=candidates_csv,
        seed=seed,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
    )
    rerank_summary = rerank_candidates_csv(
        profile=profile,
        genome=genome,
        candidates_csv=candidates_csv,
        service_schema=service_schema,
        repair_threshold=repair_threshold,
        repair_attempts=repair_attempts,
        det_profile="legacy",
        output_csv=rerank_csv,
        llm_mode=llm_mode,
        llm_endpoint=llm_endpoint,
        timeout_sec=timeout_sec,
        retries=retries,
        seed=seed,
    )
    return {
        "candidates_csv": str(candidates_csv),
        "rerank_csv": str(rerank_csv),
        "rerank_summary": rerank_summary,
        "metrics": _summary_from_rerank_csv(rerank_csv),
    }


def run_category_sweep(args: argparse.Namespace) -> dict[str, Any]:
    ensure_workspace()
    genome = load_genome(args.genome_json)
    service_schema = load_service_schema(args.service_schema)
    rows = load_dataset_rows(args.dataset)
    selected_rows = select_rows(
        rows,
        start_row=args.start_row,
        end_row=args.end_row,
        limit=args.limit,
        categories=args.category,
    )
    if not selected_rows:
        raise SystemExit("No rows selected. Check --start-row/--end-row/--limit/--category.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sweep_dir = RESULTS_DIR / f"category_sweep_{timestamp}"
    sweep_dir.mkdir(parents=True, exist_ok=True)

    current_genome = genome
    category_reports: list[dict[str, Any]] = []
    categories = sorted({str(row.get("category", "")) for _, row in selected_rows}, key=_category_sort_key)

    for index, category in enumerate(categories, start=1):
        category_rows = _rows_for_category(selected_rows, category)
        sample_size = min(args.category_sample_size, len(category_rows))
        sampled_rows = sample_rows(category_rows, sample_size=sample_size, seed=args.seed + index)
        if not sampled_rows:
            continue
        before = evaluate_genome_on_rows(
            profile=args.profile,
            genome=current_genome,
            row_subset=sampled_rows,
            service_schema=service_schema,
            candidate_k=args.candidate_k,
            llm_mode=args.llm_mode,
            llm_endpoint=args.llm_endpoint,
            timeout_sec=args.timeout_sec,
            retries=args.retries,
            seed=args.seed + index,
            run_label=f"category_{category}_before",
        )
        feedback = run_feedback_loop(
            profile=args.profile,
            genome=current_genome,
            dataset_rows=sampled_rows,
            service_schema=service_schema,
            validation_size=len(sampled_rows),
            candidate_k=args.candidate_k,
            attempts=args.category_attempts,
            improvement_threshold=0.1,
            llm_mode=args.llm_mode,
            llm_endpoint=args.llm_endpoint,
            timeout_sec=args.timeout_sec,
            retries=args.retries,
            seed=args.seed + 1000 + index,
        )
        if feedback.get("improved"):
            current_genome = feedback["best_genome"]
        category_report = {
            "category": category,
            "sample_size": len(sampled_rows),
            "before_avg_det_score": before["avg_det_score"],
            "after_avg_det_score": feedback["best_metrics"]["avg_det_score"],
            "before_failures": before["failure_summary"],
            "after_failures": feedback["best_metrics"]["failure_summary"],
            "improved": feedback["improved"],
            "patch_dir": feedback["patch_dir"],
        }
        category_reports.append(category_report)
        dump_json(sweep_dir / f"category_{category}.json", category_report)
        _write_genome(sweep_dir / f"best_after_category_{category}.json", current_genome)

    if args.skip_full_pass:
        final_genome_path = sweep_dir / "final_best_genome.json"
        _write_genome(final_genome_path, current_genome)
        summary = {
            "sweep_dir": str(sweep_dir),
            "category_reports": category_reports,
            "pre_full": None,
            "final_feedback": None,
            "post_full": None,
            "final_best_genome": str(final_genome_path),
        }
        dump_json(sweep_dir / "summary.json", summary)
        return summary

    pre_full = _run_full_pass(
        profile=args.profile,
        genome=current_genome,
        selected_rows=selected_rows,
        service_schema=service_schema,
        llm_mode=args.llm_mode,
        llm_endpoint=args.llm_endpoint,
        timeout_sec=args.timeout_sec,
        retries=args.retries,
        seed=args.seed + 2000,
        sweep_dir=sweep_dir,
        label="full_before_patch",
        repair_threshold=args.repair_threshold,
        repair_attempts=args.repair_attempts,
    )

    worst_rows = _pick_full_failure_rows(Path(pre_full["rerank_csv"]), selected_rows, args.full_failure_sample_size)
    final_feedback = run_feedback_loop(
        profile=args.profile,
        genome=current_genome,
        dataset_rows=worst_rows or selected_rows,
        service_schema=service_schema,
        validation_size=len(worst_rows or selected_rows),
        candidate_k=args.candidate_k,
        attempts=args.final_attempts,
        improvement_threshold=0.1,
        llm_mode=args.llm_mode,
        llm_endpoint=args.llm_endpoint,
        timeout_sec=args.timeout_sec,
        retries=args.retries,
        seed=args.seed + 3000,
    )
    if final_feedback.get("improved"):
        current_genome = final_feedback["best_genome"]

    post_full = _run_full_pass(
        profile=args.profile,
        genome=current_genome,
        selected_rows=selected_rows,
        service_schema=service_schema,
        llm_mode=args.llm_mode,
        llm_endpoint=args.llm_endpoint,
        timeout_sec=args.timeout_sec,
        retries=args.retries,
        seed=args.seed + 4000,
        sweep_dir=sweep_dir,
        label="full_final",
        repair_threshold=args.repair_threshold,
        repair_attempts=args.repair_attempts,
    )

    final_genome_path = sweep_dir / "final_best_genome.json"
    _write_genome(final_genome_path, current_genome)
    summary = {
        "sweep_dir": str(sweep_dir),
        "category_reports": category_reports,
        "pre_full": pre_full,
        "final_feedback": {
            "patch_dir": final_feedback["patch_dir"],
            "improved": final_feedback["improved"],
            "baseline_avg_det_score": final_feedback["baseline"]["avg_det_score"],
            "best_avg_det_score": final_feedback["best_metrics"]["avg_det_score"],
        },
        "post_full": post_full,
        "final_best_genome": str(final_genome_path),
    }
    dump_json(sweep_dir / "summary.json", summary)
    return summary


def main() -> int:
    args = build_parser().parse_args()
    summary = run_category_sweep(args)
    print("Category sweep completed")
    print(f"- sweep_dir: {summary['sweep_dir']}")
    if summary["pre_full"] is not None and summary["post_full"] is not None:
        print(f"- pre_full_avg_det_score: {summary['pre_full']['metrics']['avg_det_score']}")
        print(f"- post_full_avg_det_score: {summary['post_full']['metrics']['avg_det_score']}")
        print(f"- post_full_avg_gt_similarity: {summary['post_full']['metrics']['avg_gt_similarity']}")
    else:
        print("- full_pass: skipped")
    print(f"- final_best_genome: {summary['final_best_genome']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
