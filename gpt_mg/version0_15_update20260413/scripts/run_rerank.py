#!/usr/bin/env python3
# Assumption: this reranker reads candidate CSVs produced by version0_14/scripts/run_generate.py and writes all outputs inside gpt_mg/version0_14/results.
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from scripts.run_generate import _llm_settings
from utils.det_evaluator import evaluate_candidate, evaluate_candidates
from utils.local_llm_client import (
    LocalLLMError,
    call as llm_call,
    classify_error_text,
    is_oom_error_type,
)
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
    "repair_metadata",
    "repair_call_count",
    "repair_error_count",
    "repair_error_type",
    "repair_error_types",
    "repair_oom_flag",
    "repair_prompt_chars_total",
    "repair_prompt_tokens_total",
    "repair_completion_tokens_total",
    "repair_total_tokens_total",
    "repair_llm_latency_sec",
    "repair_peak_vram_gb",
    "repair_total_pipeline_sec",
    "det_profile",
    "det_valid_json",
    "det_schema_ok",
    "det_service_match",
    "det_arg_type_ok",
    "det_precondition_ok",
    "det_semantic_ok",
    "det_min_extraneous",
    "det_gt_service_coverage",
    "det_gt_service_precision",
    "det_gt_receiver_coverage",
    "det_dataflow_score",
    "det_numeric_grounding",
    "det_enum_grounding",
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
    parser.add_argument("--det-profile", choices=["legacy", "strict"], default="legacy")
    parser.add_argument("--output-csv", default=None)
    parser.add_argument("--llm-mode", default=None)
    parser.add_argument("--llm-endpoint", default=None)
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--seed", type=int, default=14)
    parser.add_argument("--model", default=None, help="Override the repair model id while keeping the same prompt/genome.")
    parser.add_argument("--service-context-mode", default=None, choices=["auto", "retrieval_fallback", "schema_fallback"])
    parser.add_argument("--enable-retrieval-premapping", action="store_true", help="Shortcut for --service-context-mode retrieval_fallback.")
    parser.add_argument("--disable-retrieval-premapping", action="store_true", help="Shortcut for --service-context-mode schema_fallback.")
    parser.add_argument("--retrieval-topk", type=int, default=None)
    parser.add_argument("--retrieval-mode", default=None, choices=["hybrid", "dense", "bm25"])
    parser.add_argument("--retrieval-json", default=None)
    parser.add_argument("--retrieval-bundle-dir", default=None)
    parser.add_argument("--retrieval-model-dir", default=None)
    parser.add_argument("--retrieval-device", default=None)
    return parser


def _service_context_mode(args: argparse.Namespace) -> str | None:
    if args.enable_retrieval_premapping:
        return "retrieval_fallback"
    if args.disable_retrieval_premapping:
        return "schema_fallback"
    return args.service_context_mode


def _system_prompt() -> str:
    return "You are a deterministic JOILang repair engine. Return exactly one repaired JSON object only."


def _error_type_from_exception(exc: Exception) -> str:
    if isinstance(exc, LocalLLMError):
        return str(exc.error_type or classify_error_text(str(exc)))
    return classify_error_text(str(exc))


def _summarize_repair_meta(repair_meta: list[dict[str, Any]]) -> dict[str, Any]:
    error_types: list[str] = []
    prompt_chars = 0
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    llm_latency_sec = 0.0
    peak_vram_gb = 0.0
    for meta in repair_meta:
        prompt_chars += int(meta.get("prompt_chars") or 0)
        prompt_tokens += int(meta.get("prompt_tokens") or 0)
        completion_tokens += int(meta.get("completion_tokens") or 0)
        total_tokens += int(meta.get("total_tokens") or 0)
        llm_latency_sec += float(meta.get("latency_sec") or 0.0)
        peak_vram_gb = max(peak_vram_gb, float(meta.get("peak_vram_gb") or 0.0))
        error_type = str(meta.get("error_type", "") or "").strip()
        if error_type:
            error_types.append(error_type)
    primary_error = error_types[0] if error_types else ""
    return {
        "repair_call_count": len(repair_meta),
        "repair_error_count": len(error_types),
        "repair_error_type": primary_error,
        "repair_error_types": json.dumps(error_types, ensure_ascii=False),
        "repair_oom_flag": any(is_oom_error_type(item) for item in error_types),
        "repair_prompt_chars_total": prompt_chars,
        "repair_prompt_tokens_total": prompt_tokens,
        "repair_completion_tokens_total": completion_tokens,
        "repair_total_tokens_total": total_tokens,
        "repair_llm_latency_sec": round(llm_latency_sec, 4),
        "repair_peak_vram_gb": round(peak_vram_gb, 4),
    }


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
    det_profile: str,
    output_csv: str | Path,
    llm_mode: str | None,
    llm_endpoint: str | None,
    timeout_sec: int,
    retries: int,
    seed: int,
    model_override: str | None = None,
    llm_extra_payload: dict[str, Any] | None = None,
    service_context_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_workspace()
    input_rows = read_csv_rows(candidates_csv)
    if not input_rows:
        raise SystemExit(f"No rows found in candidates CSV: {candidates_csv}")

    repair_genome = _repair_genome(genome)
    temperature, max_tokens, model = _llm_settings(
        genome,
        argparse.Namespace(temperature=None, max_tokens=None),
        model_override=model_override,
    )
    rerank_logs_dir = LOGS_DIR / f"rerank_{slugify(genome.get('id', 'genome'))}"
    rerank_logs_dir.mkdir(parents=True, exist_ok=True)

    output_rows: list[dict[str, Any]] = []
    fieldnames: list[str] | None = None
    repaired_count = 0
    system_prompt = _system_prompt()

    for row in input_rows:
        row_started = time.perf_counter()
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
            profile=det_profile,
        )
        best = scored[0] if scored else evaluate_candidate(
            command_eng,
            "",
            service_schema,
            connected_devices=connected_devices,
            ground_truth=row.get("gt", ""),
            profile=det_profile,
        )
        selected_candidate = best.get("candidate", "") if scored else ""
        repair_applied = False
        repair_log_path = ""
        repair_meta: list[dict[str, Any]] = []

        if float(best.get("det_score", 0.0)) < repair_threshold:
            current_best_candidate = selected_candidate
            current_best_det = best
            for attempt in range(repair_attempts):
                values = build_prompt_values(
                    row_no,
                    row,
                    service_schema,
                    candidate_strategy="repair",
                    **(service_context_kwargs or {}),
                    det_diagnostics=_compact_det_diagnostics(current_best_det),
                    best_candidate=current_best_candidate if isinstance(current_best_candidate, str) else json.dumps(current_best_candidate, ensure_ascii=False),
                    failure_summary=", ".join(current_best_det.get("failure_reasons", [])),
                )
                rendered_prompt, manifest = render_blocks_for_genome(repair_genome, values=values)
                repair_prompt = rendered_prompt + "\n\nReturn the repaired JSON object now."
                prompt_chars = len(system_prompt) + len(repair_prompt)
                repair_log = rerank_logs_dir / f"row_{row_no:03d}_repair_{attempt + 1}.json"
                repair_log_path = str(repair_log)
                try:
                    response = llm_call(
                        system_prompt,
                        repair_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        mode=llm_mode,
                        model=model,
                        endpoint=llm_endpoint,
                        timeout_sec=timeout_sec,
                        retries=retries,
                        seed=seed + row_no + attempt,
                        log_path=repair_log,
                        extra_payload=llm_extra_payload,
                    )
                    repair_meta.append(
                        {
                            "attempt": attempt + 1,
                            "prompt_chars": prompt_chars,
                            "prompt_tokens": response.get("prompt_tokens", 0),
                            "completion_tokens": response.get("completion_tokens", 0),
                            "total_tokens": response.get("total_tokens", 0),
                            "latency_sec": response.get("latency_sec", 0.0),
                            "peak_vram_gb": response.get("peak_vram_gb", 0.0),
                            "load_sec": response.get("load_sec", 0.0),
                            "generate_sec": response.get("generate_sec", 0.0),
                            "prompt_prep_sec": response.get("prompt_prep_sec", 0.0),
                            "decode_sec": response.get("decode_sec", 0.0),
                            "worker_pid": response.get("worker_pid", 0),
                            "error_type": "",
                            "oom_flag": False,
                            "manifest": manifest,
                        }
                    )
                    repaired_candidate = normalize_candidate_json_text(
                        str(response.get("content", "")).strip(),
                        default_cron=str(values.get("optional_cron", "") or ""),
                        default_period=int(str(values.get("optional_period", "0") or "0")),
                    )
                except Exception as exc:
                    error_type = _error_type_from_exception(exc)
                    repair_meta.append(
                        {
                            "attempt": attempt + 1,
                            "prompt_chars": prompt_chars,
                            "error": str(exc),
                            "error_type": error_type,
                            "oom_flag": is_oom_error_type(error_type),
                            "manifest": manifest,
                        }
                    )
                    dump_json(repair_log, {"error": str(exc), "prompt": rendered_prompt, "manifest": manifest})
                    continue
                repaired_det = evaluate_candidate(
                    command_eng,
                    repaired_candidate,
                    service_schema,
                    connected_devices=connected_devices,
                    ground_truth=row.get("gt", ""),
                    profile=det_profile,
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

        repair_summary = _summarize_repair_meta(repair_meta)
        result_row = dict(row)
        result_row.update(
            {
                "output": selected_candidate if isinstance(selected_candidate, str) else json.dumps(selected_candidate, ensure_ascii=False),
                "selected_candidate_index": best.get("candidate_index", 0),
                "repair_applied": repair_applied,
                "repair_log_path": repair_log_path,
                "repair_metadata": json.dumps(repair_meta, ensure_ascii=False),
                "repair_total_pipeline_sec": round(time.perf_counter() - row_started, 4),
                "det_valid_json": best.get("det_valid_json", False),
                "det_profile": best.get("det_profile", det_profile),
                "det_schema_ok": best.get("det_schema_ok", False),
                "det_service_match": best.get("det_service_match", 0.0),
                "det_arg_type_ok": best.get("det_arg_type_ok", 0.0),
                "det_precondition_ok": best.get("det_precondition_ok", False),
                "det_semantic_ok": best.get("det_semantic_ok", 0.0),
                "det_min_extraneous": best.get("det_min_extraneous", 0.0),
                "det_gt_service_coverage": best.get("det_gt_service_coverage", 1.0),
                "det_gt_service_precision": best.get("det_gt_service_precision", 1.0),
                "det_gt_receiver_coverage": best.get("det_gt_receiver_coverage", 1.0),
                "det_dataflow_score": best.get("det_dataflow_score", 1.0),
                "det_numeric_grounding": best.get("det_numeric_grounding", 1.0),
                "det_enum_grounding": best.get("det_enum_grounding", 1.0),
                "det_gt_exact": best.get("det_gt_exact", False),
                "det_gt_similarity": best.get("det_gt_similarity", 0.0),
                "det_score": best.get("det_score", 0.0),
                "det_failure_reasons": json.dumps(best.get("failure_reasons", []), ensure_ascii=False),
                "det_resolved_services": json.dumps(best.get("resolved_services", []), ensure_ascii=False),
            }
        )
        result_row.update(repair_summary)
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
        det_profile=args.det_profile,
        output_csv=output_csv,
        llm_mode=args.llm_mode,
        llm_endpoint=args.llm_endpoint,
        timeout_sec=args.timeout_sec,
        retries=args.retries,
        seed=args.seed,
        model_override=args.model,
        service_context_kwargs={
            "service_context_mode": _service_context_mode(args),
            "retrieval_topk": args.retrieval_topk,
            "retrieval_mode": args.retrieval_mode,
            "retrieval_json_path": args.retrieval_json,
            "retrieval_bundle_dir": args.retrieval_bundle_dir,
            "retrieval_model_dir": args.retrieval_model_dir,
            "retrieval_device": args.retrieval_device,
        },
    )
    print("Rerank completed")
    print(f"- output_csv: {summary['output_csv']}")
    print(f"- rows: {summary['row_count']}")
    print(f"- repaired_rows: {summary['repaired_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
