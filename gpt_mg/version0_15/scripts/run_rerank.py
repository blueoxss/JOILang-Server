#!/usr/bin/env python3
# Assumption: this reranker reads candidate CSVs produced by version0_14/scripts/run_generate.py and writes all outputs inside gpt_mg/version0_14/results.
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from scripts.run_generate import _llm_settings
from utils.det_evaluator import evaluate_candidate, evaluate_candidates
from utils.local_llm_client import call as llm_call
from utils.pipeline_common import (
    LOGS_DIR,
    RESULTS_DIR,
    SERVICE_SCHEMA_DEFAULT,
    atomic_write_csv,
    build_prompt_values,
    dump_json,
    ensure_workspace,
    load_genome,
    load_json,
    load_service_schema,
    normalize_candidate_json_text,
    parse_connected_devices,
    read_csv_rows,
    render_blocks_for_genome,
    slugify,
    unique_fieldnames,
)


RERANK_EXTRA_FIELDS = [
    "output",
    "selected_candidate_index",
    "repair_applied",
    "repair_log_path",
    "det_valid_json",
    "det_schema_ok",
    "det_service_match",
    "det_arg_type_ok",
    "det_precondition_ok",
    "det_semantic_ok",
    "det_min_extraneous",
    "det_gt_exact",
    "det_gt_similarity",
    "det_score",
    "det_failure_reasons",
    "det_resolved_services",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rerank and repair JOI candidates using deterministic DET scoring.")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--genome-json", default=str(VERSION_ROOT / "genomes" / "example_genome.json"))
    parser.add_argument("--candidates-csv", required=True)
    parser.add_argument("--service-schema", default=str(SERVICE_SCHEMA_DEFAULT))
    parser.add_argument("--repair-threshold", type=float, default=70.0)
    parser.add_argument("--repair-attempts", type=int, default=2)
    parser.add_argument("--output-csv", default=None)
    parser.add_argument("--llm-mode", default=None)
    parser.add_argument("--llm-endpoint", default=None)
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--seed", type=int, default=14)
    return parser


def _system_prompt() -> str:
    return "You are a deterministic JOILang repair engine. Return exactly one repaired JSON object only."


def _parse_candidates(value: str) -> list[Any]:
    text = (value or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [text]
    if isinstance(parsed, list):
        return parsed
    return [parsed]


def _repair_genome(base_genome: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": base_genome.get("id", "repair"),
        "seed": base_genome.get("seed", 0),
        "blocks": ["04", "05", "06"],
        "params": dict(base_genome.get("params", {})),
        "block_params": dict(base_genome.get("block_params", {})),
    }


def _compact_det_diagnostics(det: dict[str, Any]) -> str:
    compact = {
        "det_score": det.get("det_score", 0.0),
        "det_gt_exact": det.get("det_gt_exact", False),
        "det_gt_similarity": det.get("det_gt_similarity", 0.0),
        "failure_reasons": det.get("failure_reasons", []),
        "resolved_services": det.get("resolved_services", []),
        "gt_script": det.get("gt_script", ""),
    }
    return json.dumps(compact, ensure_ascii=False, indent=2)


def rerank_candidates_csv(
    *,
    profile: str,
    genome: dict[str, Any],
    candidates_csv: str | Path,
    service_schema: dict[str, dict[str, Any]],
    repair_threshold: float,
    repair_attempts: int,
    output_csv: str | Path,
    llm_mode: str | None,
    llm_endpoint: str | None,
    timeout_sec: int,
    retries: int,
    seed: int,
) -> dict[str, Any]:
    ensure_workspace()
    input_rows = read_csv_rows(candidates_csv)
    if not input_rows:
        raise SystemExit(f"No rows found in candidates CSV: {candidates_csv}")

    repair_genome = _repair_genome(genome)
    temperature, max_tokens, model = _llm_settings(genome, argparse.Namespace(temperature=None, max_tokens=None))
    rerank_logs_dir = LOGS_DIR / f"rerank_{slugify(genome.get('id', 'genome'))}"
    rerank_logs_dir.mkdir(parents=True, exist_ok=True)

    output_rows: list[dict[str, Any]] = []
    fieldnames: list[str] | None = None
    repaired_count = 0

    for row in input_rows:
        row_no = int(row.get("row_no") or 0)
        command_eng = row.get("command_eng", "")
        connected_devices = row.get("connected_devices", "")
        candidates = _parse_candidates(row.get("candidates", ""))
        scored = evaluate_candidates(
            command_eng,
            candidates,
            service_schema,
            connected_devices=connected_devices,
            ground_truth=row.get("gt", ""),
        )
        best = scored[0] if scored else evaluate_candidate(
            command_eng,
            "",
            service_schema,
            connected_devices=connected_devices,
            ground_truth=row.get("gt", ""),
        )
        selected_candidate = best.get("candidate", "") if scored else ""
        repair_applied = False
        repair_log_path = ""

        if float(best.get("det_score", 0.0)) < repair_threshold:
            current_best_candidate = selected_candidate
            current_best_det = best
            for attempt in range(repair_attempts):
                values = build_prompt_values(
                    row_no,
                    row,
                    service_schema,
                    candidate_strategy="repair",
                    det_diagnostics=_compact_det_diagnostics(current_best_det),
                    best_candidate=current_best_candidate if isinstance(current_best_candidate, str) else json.dumps(current_best_candidate, ensure_ascii=False),
                    failure_summary=", ".join(current_best_det.get("failure_reasons", [])),
                )
                rendered_prompt, manifest = render_blocks_for_genome(repair_genome, values=values)
                repair_log = rerank_logs_dir / f"row_{row_no:03d}_repair_{attempt + 1}.json"
                repair_log_path = str(repair_log)
                try:
                    response = llm_call(
                        _system_prompt(),
                        rendered_prompt + "\n\nReturn the repaired JSON object now.",
                        temperature=temperature,
                        max_tokens=max_tokens,
                        mode=llm_mode,
                        model=model,
                        endpoint=llm_endpoint,
                        timeout_sec=timeout_sec,
                        retries=retries,
                        seed=seed + row_no + attempt,
                        log_path=repair_log,
                    )
                    repaired_candidate = normalize_candidate_json_text(
                        str(response.get("content", "")).strip(),
                        default_cron=str(values.get("optional_cron", "") or ""),
                        default_period=int(str(values.get("optional_period", "0") or "0")),
                    )
                except Exception as exc:
                    dump_json(repair_log, {"error": str(exc), "prompt": rendered_prompt, "manifest": manifest})
                    continue
                repaired_det = evaluate_candidate(
                    command_eng,
                    repaired_candidate,
                    service_schema,
                    connected_devices=connected_devices,
                    ground_truth=row.get("gt", ""),
                )
                if float(repaired_det.get("det_score", 0.0)) > float(current_best_det.get("det_score", 0.0)):
                    current_best_candidate = repaired_candidate
                    current_best_det = repaired_det
                    repair_applied = True
                if float(current_best_det.get("det_score", 0.0)) >= repair_threshold:
                    break
            if repair_applied:
                repaired_count += 1
                selected_candidate = current_best_candidate
                best = current_best_det

        result_row = dict(row)
        result_row.update(
            {
                "output": selected_candidate if isinstance(selected_candidate, str) else json.dumps(selected_candidate, ensure_ascii=False),
                "selected_candidate_index": best.get("candidate_index", 0),
                "repair_applied": repair_applied,
                "repair_log_path": repair_log_path,
                "det_valid_json": best.get("det_valid_json", False),
                "det_schema_ok": best.get("det_schema_ok", False),
                "det_service_match": best.get("det_service_match", 0.0),
                "det_arg_type_ok": best.get("det_arg_type_ok", 0.0),
                "det_precondition_ok": best.get("det_precondition_ok", False),
                "det_semantic_ok": best.get("det_semantic_ok", 0.0),
                "det_min_extraneous": best.get("det_min_extraneous", 0.0),
                "det_gt_exact": best.get("det_gt_exact", False),
                "det_gt_similarity": best.get("det_gt_similarity", 0.0),
                "det_score": best.get("det_score", 0.0),
                "det_failure_reasons": json.dumps(best.get("failure_reasons", []), ensure_ascii=False),
                "det_resolved_services": json.dumps(best.get("resolved_services", []), ensure_ascii=False),
            }
        )
        output_rows.append(result_row)
        fieldnames = unique_fieldnames(output_rows, RERANK_EXTRA_FIELDS)
        atomic_write_csv(output_csv, fieldnames, output_rows)

    return {
        "output_csv": str(output_csv),
        "row_count": len(output_rows),
        "repaired_count": repaired_count,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    genome = load_genome(args.genome_json)
    service_schema = load_service_schema(args.service_schema)
    output_csv = args.output_csv or RESULTS_DIR / f"rerank_{slugify(genome.get('id', 'genome'))}.csv"
    summary = rerank_candidates_csv(
        profile=args.profile,
        genome=genome,
        candidates_csv=args.candidates_csv,
        service_schema=service_schema,
        repair_threshold=args.repair_threshold,
        repair_attempts=args.repair_attempts,
        output_csv=output_csv,
        llm_mode=args.llm_mode,
        llm_endpoint=args.llm_endpoint,
        timeout_sec=args.timeout_sec,
        retries=args.retries,
        seed=args.seed,
    )
    print("Rerank completed")
    print(f"- output_csv: {summary['output_csv']}")
    print(f"- rows: {summary['row_count']}")
    print(f"- repaired_rows: {summary['repaired_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
