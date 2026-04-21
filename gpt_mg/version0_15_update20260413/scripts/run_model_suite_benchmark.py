#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import concurrent.futures
import json
import os
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import fmean
from textwrap import indent
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from scripts.run_generate import _llm_settings, generate_candidates_for_rows
from scripts.run_rerank import rerank_candidates_csv
from utils.local_llm_client import close_persistent_worker, describe_worker_runtime
from utils.pipeline_common import (
    DATASET_DEFAULT,
    RESULTS_DIR,
    SERVICE_SCHEMA_DEFAULT,
    atomic_write_csv,
    dump_json,
    load_dataset_rows,
    load_genome,
    load_service_schema,
    parse_connected_devices,
    read_csv_rows,
    select_rows,
    slugify,
)


DEFAULT_GENOME_JSON = VERSION_ROOT / "results" / "best_genome.json"

PAPER_LOCAL5_SUITE = [
    {
        "key": "phi35_mini",
        "label": "Phi-3.5-mini-instruct",
        "model": "microsoft/Phi-3.5-mini-instruct",
        "mode": "worker",
        "llm_extra_payload": {
            "local_trust_remote_code": True,
        },
    },
    {
        "key": "qwen25_coder_7b",
        "label": "Qwen2.5-Coder-7B-Instruct",
        "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "mode": "worker",
    },
    {
        "key": "llama31_8b",
        "label": "Llama-3.1-8B-Instruct",
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "mode": "worker",
    },
    {
        "key": "gemma2_9b_it",
        "label": "Gemma-2-9B-it",
        "model": "google/gemma-2-9b-it",
        "mode": "worker",
    },
    {
        "key": "qwen25_coder_14b",
        "label": "Qwen2.5-Coder-14B-Instruct",
        "model": "Qwen/Qwen2.5-Coder-14B-Instruct",
        "mode": "worker",
    },
]

PAPER_WITH_CLOUD_REF_SUITE = PAPER_LOCAL5_SUITE + [
    {
        "key": "gpt41_mini",
        "label": "GPT-4.1-mini",
        "model": "gpt-4.1-mini",
        "mode": "openai",
    }
]

MODEL_SUITES = {
    "paper_local5": PAPER_LOCAL5_SUITE,
    "paper_with_cloud_ref": PAPER_WITH_CLOUD_REF_SUITE,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark the same version0_15 prompt/genome across a fixed model suite."
    )
    parser.add_argument(
        "--suite",
        choices=sorted(MODEL_SUITES.keys()),
        default="paper_local5",
        help="Built-in model suite. Default: paper_local5",
    )
    parser.add_argument(
        "--model-key",
        action="append",
        default=[],
        help="Subset the suite by key. Can be repeated.",
    )
    parser.add_argument(
        "--genome-json",
        default=str(DEFAULT_GENOME_JSON if DEFAULT_GENOME_JSON.exists() else VERSION_ROOT / "genomes" / "example_genome.json"),
        help="Genome to keep fixed across models. Default: results/best_genome.json when available.",
    )
    parser.add_argument("--dataset", default=str(DATASET_DEFAULT))
    parser.add_argument("--service-schema", default=str(SERVICE_SCHEMA_DEFAULT))
    parser.add_argument("--row-no", action="append", type=int, default=[], help="Select explicit dataset row numbers.")
    parser.add_argument("--query", default=None, help="Filter dataset rows by substring in command_eng/command_kor.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--limit-per-category",
        type=int,
        default=None,
        help="Optional balanced cap applied independently to each category after filtering. Example: --category 1 --category 2 --limit-per-category 10 selects up to 10 rows from each category.",
    )
    parser.add_argument("--start-row", type=int, default=1)
    parser.add_argument("--end-row", type=int, default=None)
    parser.add_argument("--category", action="append", default=[], help="Optional category filter. Can be repeated.")
    parser.add_argument(
        "--category-file",
        action="append",
        default=[],
        help="Optional path to a newline- or comma-separated category list file. Can be repeated.",
    )
    parser.add_argument("--list-categories", action="store_true", help="Print available dataset categories and exit.")
    parser.add_argument("--command-eng", default=None, help="Ad-hoc command text. Bypasses dataset selection.")
    parser.add_argument("--command-kor", default=None, help="Optional Korean command text for ad-hoc mode.")
    parser.add_argument("--connected-devices-json", default="", help="Inline JSON or file path for ad-hoc connected_devices.")
    parser.add_argument("--gt-json", default="", help="Inline JSON or file path for ad-hoc GT.")
    parser.add_argument("--cron", default="")
    parser.add_argument("--period", type=int, default=0)
    parser.add_argument("--manual-category", default="manual")
    parser.add_argument("--candidate-k", type=int, default=1, help="Candidates per row/model. Default: 1")
    parser.add_argument("--repair-threshold", type=float, default=70.0)
    parser.add_argument(
        "--repair-attempts",
        type=int,
        default=0,
        help="Repair attempts during rerank. Use 0 for raw same-prompt comparison first.",
    )
    parser.add_argument("--temperature", type=float, default=None, help="Optional temperature override for all models.")
    parser.add_argument("--max-tokens", type=int, default=None, help="Optional max token override for all models.")
    parser.add_argument("--measure-latency", action="store_true", help="Collect and summarize latency-oriented metrics.")
    parser.add_argument("--measure-vram", action="store_true", help="Collect and summarize VRAM-oriented metrics when supported.")
    parser.add_argument(
        "--warmup-row-no",
        action="append",
        type=int,
        default=[],
        help="Optional dedicated warmup row number. Can be repeated. Warmup rows are run before evaluation and excluded from summaries.",
    )
    parser.add_argument("--warmup-start-row", type=int, default=None, help="Optional warmup row start (inclusive).")
    parser.add_argument("--warmup-end-row", type=int, default=None, help="Optional warmup row end (inclusive).")
    parser.add_argument(
        "--paper-fair-mode",
        action="store_true",
        help="Sequential fresh-worker mode for fair paper-grade latency comparison. Implies isolated warmup and paper artifact export compatibility.",
    )
    parser.add_argument(
        "--latency-isolation-mode",
        choices=("inherit", "fresh_worker"),
        default="inherit",
        help="How to isolate worker-backed model latency measurement. Default: inherit current worker behavior.",
    )
    parser.add_argument("--llm-mode", default=None, help="Global runtime override. Example: worker, openai, mock")
    parser.add_argument("--llm-endpoint", default=None, help="Endpoint for non-worker modes.")
    parser.add_argument(
        "--llm-extra-json",
        default="",
        help="Inline JSON or file path for extra worker/http payload fields applied to every model.",
    )
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--seed", type=int, default=15)
    parser.add_argument("--output-dir", default=None, help="Optional output directory. Default: results/model_suite_<timestamp>")
    parser.add_argument("--preflight", action="store_true", help="Inspect local model availability before running the benchmark.")
    parser.add_argument("--preflight-only", action="store_true", help="Print local model availability and exit without running generation.")
    parser.add_argument(
        "--strict-availability",
        action="store_true",
        help="Abort if any selected model is unavailable for the configured runtime.",
    )
    parser.add_argument(
        "--skip-unavailable",
        action="store_true",
        help="Skip models that are not currently runnable instead of attempting generation and logging failures.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="Max model-level parallel workers. Worker-backed local models fall back to sequential execution by default.",
    )
    parser.add_argument(
        "--debug-runtime",
        action="store_true",
        help="Collect extra runtime diagnostics for the selected worker environment and write them into summary artifacts.",
    )
    parser.add_argument(
        "--print-worker-info",
        action="store_true",
        help="Print worker python / torch / CUDA details alongside preflight output.",
    )
    parser.add_argument(
        "--export-paper-artifacts",
        action="store_true",
        help="Write paper-oriented CSV summaries and attempt figure export into the result directory.",
    )
    parser.add_argument(
        "--print-mode",
        choices=("paths", "summary", "compare"),
        default="paths",
        help="Console output style. 'compare' prints row-wise GT vs generated code.",
    )
    parser.add_argument(
        "--print-limit",
        type=int,
        default=None,
        help="Optional max rows to print when --print-mode compare is used. Default: print all selected rows.",
    )
    parser.add_argument("--print-json", action="store_true")
    return parser


def _read_inline_or_file(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    candidate = Path(text).expanduser()
    if candidate.exists() and candidate.is_file():
        return candidate.read_text(encoding="utf-8").strip()
    return text


def _parse_json_object(value: str) -> dict[str, Any]:
    text = _read_inline_or_file(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception as exc:
        raise SystemExit(f"Failed to parse JSON payload: {text[:200]}") from exc
    if not isinstance(parsed, dict):
        raise SystemExit("Expected a JSON object payload.")
    return parsed


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _unique_preserve(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw or "").strip()
        if not token:
            continue
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(token)
    return ordered


def _load_category_filters(args: argparse.Namespace) -> list[str]:
    categories: list[str] = []
    for raw in args.category or []:
        categories.extend(token.strip() for token in str(raw).split(",") if token.strip())
    for raw_path in args.category_file or []:
        path = Path(str(raw_path)).expanduser()
        if not path.exists():
            raise SystemExit(f"Category file does not exist: {path}")
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            for token in line.split(","):
                cleaned = token.strip()
                if cleaned:
                    categories.append(cleaned)
    return _unique_preserve(categories)


def _print_available_categories(dataset_path: str | Path) -> None:
    rows = load_dataset_rows(dataset_path)
    counter: Counter[str] = Counter(str(row.get("category", "")).strip() for row in rows if str(row.get("category", "")).strip())
    print("Available categories:")
    for category, count in sorted(counter.items(), key=lambda item: item[0]):
        print(f" - {category}: {count}")


def _mean(values: list[float]) -> float:
    return round(fmean(values), 4) if values else 0.0


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return round(float(values[0]), 4)
    ordered = sorted(float(value) for value in values)
    q = max(0.0, min(1.0, float(q)))
    index = (len(ordered) - 1) * q
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return round(ordered[lower], 4)
    weight = index - lower
    return round(ordered[lower] * (1.0 - weight) + ordered[upper] * weight, 4)


def _first_nonempty(items: list[str]) -> str:
    for item in items:
        token = str(item or "").strip()
        if token:
            return token
    return ""


def _warmup_enabled(args: argparse.Namespace) -> bool:
    return bool(
        args.paper_fair_mode
        or args.measure_latency
        or args.warmup_row_no
        or args.warmup_start_row is not None
        or args.warmup_end_row is not None
    )


def _resolve_latency_isolation_mode(args: argparse.Namespace) -> str:
    if args.paper_fair_mode:
        return "fresh_worker"
    return str(args.latency_isolation_mode or "inherit")


def _normalize_gt_text(value: str) -> str:
    text = _read_inline_or_file(value)
    if not text:
        return ""
    try:
        parsed = json.loads(text)
    except Exception:
        return text
    if isinstance(parsed, dict):
        return json.dumps(parsed, ensure_ascii=False)
    return text


def _contains_hangul(value: str) -> bool:
    return any("\uac00" <= ch <= "\ud7a3" for ch in str(value or ""))


def _load_failure_reasons(row: dict[str, str]) -> list[str]:
    value = str(row.get("det_failure_reasons", "") or "").strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except Exception:
        return [value]
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item).strip()]
    return [str(parsed)]


def _rerank_row_threshold(row: dict[str, str], *, default_threshold: float) -> float:
    if row.get("gt"):
        return default_threshold
    text = str(row.get("command_eng", "") or row.get("command_kor", "") or "")
    if _contains_hangul(text):
        return min(default_threshold, 60.0)
    return default_threshold


def _row_passed(row: dict[str, str], *, default_threshold: float) -> bool:
    if str(row.get("det_gt_exact", "")).lower() == "true":
        return True
    try:
        score = float(row.get("det_score") or 0.0)
    except Exception:
        score = 0.0
    return score >= _rerank_row_threshold(row, default_threshold=default_threshold)


def _summarize_rerank_rows(rows: list[dict[str, str]], *, default_threshold: float) -> dict[str, Any]:
    scores = [float(row.get("det_score") or 0.0) for row in rows]
    gt_sims = [float(row.get("det_gt_similarity") or 0.0) for row in rows]
    exact_count = sum(1 for row in rows if str(row.get("det_gt_exact", "")).lower() == "true")
    pass_count = 0
    fail_count = 0
    failure_counter: Counter[str] = Counter()
    failed_row_nos: list[int] = []
    failed_cases: list[dict[str, Any]] = []

    for row in rows:
        if _row_passed(row, default_threshold=default_threshold):
            pass_count += 1
            continue
        fail_count += 1
        row_no = int(row.get("row_no") or 0)
        reasons = _load_failure_reasons(row)
        failure_counter.update(reasons)
        failed_row_nos.append(row_no)
        failed_cases.append(
            {
                "row_no": row_no,
                "command_eng": row.get("command_eng", ""),
                "det_score": float(row.get("det_score") or 0.0),
                "threshold": _rerank_row_threshold(row, default_threshold=default_threshold),
                "failure_reasons": reasons,
                "output": row.get("output", ""),
                "gt": row.get("gt", ""),
            }
        )

    return {
        "row_count": len(rows),
        "avg_det_score": round(fmean(scores), 4) if scores else 0.0,
        "avg_gt_similarity": round(fmean(gt_sims), 4) if gt_sims else 0.0,
        "gt_exact_count": exact_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "top_failure_types": failure_counter.most_common(12),
        "failed_row_nos": failed_row_nos,
        "failed_cases": failed_cases,
    }


def _parse_candidate_metadata(value: str) -> list[dict[str, Any]]:
    text = str(value or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return []
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def _summarize_generation_usage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    prompt_tokens: list[int] = []
    completion_tokens: list[int] = []
    total_tokens: list[int] = []
    latency_sec: list[float] = []
    candidate_count = 0
    error_count = 0
    error_counter: Counter[str] = Counter()
    for row in rows:
        for meta in _parse_candidate_metadata(str(row.get("candidate_metadata", ""))):
            error_text = str(meta.get("error", "") or "").strip()
            if error_text:
                error_count += 1
                error_counter.update([error_text])
            if "prompt_tokens" not in meta:
                continue
            candidate_count += 1
            prompt_tokens.append(int(meta.get("prompt_tokens") or 0))
            completion_tokens.append(int(meta.get("completion_tokens") or 0))
            total_tokens.append(int(meta.get("total_tokens") or 0))
            latency_sec.append(float(meta.get("latency_sec") or 0.0))
    return {
        "candidate_count": candidate_count,
        "avg_prompt_tokens": round(fmean(prompt_tokens), 4) if prompt_tokens else 0.0,
        "avg_completion_tokens": round(fmean(completion_tokens), 4) if completion_tokens else 0.0,
        "avg_total_tokens": round(fmean(total_tokens), 4) if total_tokens else 0.0,
        "avg_latency_sec": round(fmean(latency_sec), 4) if latency_sec else 0.0,
        "error_count": error_count,
        "top_errors": error_counter.most_common(5),
    }


def _parse_json_list(value: str) -> list[Any]:
    text = str(value or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return []
    if isinstance(parsed, list):
        return parsed
    return []


def _normalize_error_types(value: str | list[Any]) -> list[str]:
    if isinstance(value, list):
        items = value
    else:
        items = _parse_json_list(str(value or ""))
    return _unique_preserve([str(item).strip() for item in items if str(item).strip()])


def _primary_error_type(error_types: list[str]) -> str:
    priority = [
        "cuda_oom",
        "worker_crash",
        "incompatible_runtime",
        "gated_model",
        "missing_cache",
        "cpu_fallback_timeout",
        "invalid_json",
        "local_llm_error",
    ]
    normalized = [str(item).strip() for item in error_types if str(item).strip()]
    if not normalized:
        return ""
    for candidate in priority:
        if candidate in normalized:
            return candidate
    return normalized[0]


def _build_model_row_metrics(
    *,
    model_key: str,
    model_label: str,
    generation_rows: list[dict[str, Any]],
    rerank_rows: list[dict[str, Any]],
    runtime_info: dict[str, Any],
    default_threshold: float,
) -> list[dict[str, Any]]:
    generation_by_row = {int(row.get("row_no") or 0): row for row in generation_rows}
    metrics_rows: list[dict[str, Any]] = []
    for rerank_row in rerank_rows:
        row_no = int(rerank_row.get("row_no") or 0)
        generation_row = generation_by_row.get(row_no, {})
        failure_reasons = _load_failure_reasons(rerank_row)
        generation_error_types = _normalize_error_types(generation_row.get("generation_error_types", ""))
        repair_error_types = _normalize_error_types(rerank_row.get("repair_error_types", ""))
        all_error_types = _unique_preserve(generation_error_types + repair_error_types)
        det_pass = _row_passed(rerank_row, default_threshold=default_threshold)
        llm_latency_sec = _safe_float(generation_row.get("generation_llm_latency_sec")) + _safe_float(
            rerank_row.get("repair_llm_latency_sec")
        )
        total_pipeline_sec = _safe_float(generation_row.get("generation_total_pipeline_sec")) + _safe_float(
            rerank_row.get("repair_total_pipeline_sec")
        )
        prompt_chars = _safe_int(generation_row.get("generation_prompt_chars_total")) + _safe_int(
            rerank_row.get("repair_prompt_chars_total")
        )
        prompt_tokens = _safe_int(generation_row.get("generation_prompt_tokens_total")) + _safe_int(
            rerank_row.get("repair_prompt_tokens_total")
        )
        completion_tokens = _safe_int(generation_row.get("generation_completion_tokens_total")) + _safe_int(
            rerank_row.get("repair_completion_tokens_total")
        )
        total_tokens = _safe_int(generation_row.get("generation_total_tokens_total")) + _safe_int(
            rerank_row.get("repair_total_tokens_total")
        )
        peak_vram_gb = max(
            _safe_float(generation_row.get("generation_peak_vram_gb")),
            _safe_float(rerank_row.get("repair_peak_vram_gb")),
        )
        primary_error = _primary_error_type(all_error_types)
        metrics_rows.append(
            {
                "model_key": model_key,
                "model_label": model_label,
                "row_no": row_no,
                "row_category": str(rerank_row.get("category", "") or generation_row.get("category", "") or ""),
                "category": str(rerank_row.get("category", "") or generation_row.get("category", "") or ""),
                "command_eng": str(rerank_row.get("command_eng", "") or generation_row.get("command_eng", "") or ""),
                "command_kor": str(rerank_row.get("command_kor", "") or generation_row.get("command_kor", "") or ""),
                "gt": str(rerank_row.get("gt", "") or generation_row.get("gt", "") or ""),
                "output": str(rerank_row.get("output", "") or ""),
                "det_score": _safe_float(rerank_row.get("det_score")),
                "det_pass": det_pass,
                "gt_exact": _coerce_bool(rerank_row.get("det_gt_exact")),
                "det_valid_json": _coerce_bool(rerank_row.get("det_valid_json")),
                "det_gt_similarity": _safe_float(rerank_row.get("det_gt_similarity")),
                "failure_reasons": failure_reasons,
                "failure_reasons_json": json.dumps(failure_reasons, ensure_ascii=False),
                "prompt_chars": prompt_chars,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "llm_latency_sec": round(llm_latency_sec, 4),
                "total_pipeline_sec": round(total_pipeline_sec, 4),
                "peak_vram_gb": round(peak_vram_gb, 4),
                "generation_error_type": primary_error,
                "generation_error_types": json.dumps(all_error_types, ensure_ascii=False),
                "oom_flag": any(item == "cuda_oom" for item in all_error_types),
                "worker_python": str(runtime_info.get("worker_python", "")),
                "resolved_model_path": str(
                    runtime_info.get("resolved_local_model_name", runtime_info.get("local_model_name", ""))
                ),
                "warmup_excluded": False,
                "selected_candidate_index": _safe_int(rerank_row.get("selected_candidate_index")),
                "repair_applied": _coerce_bool(rerank_row.get("repair_applied")),
                "candidate_count": _safe_int(generation_row.get("candidate_count")),
                "generation_call_count": _safe_int(generation_row.get("generation_call_count")),
                "repair_call_count": _safe_int(rerank_row.get("repair_call_count")),
                "row_success": det_pass and not primary_error,
                "tokens_per_sec": round((float(total_tokens) / llm_latency_sec), 4) if llm_latency_sec > 0 else 0.0,
            }
        )
    return metrics_rows


def _summarize_model_row_metrics(
    row_metrics: list[dict[str, Any]],
    *,
    cold_load_sec: float = 0.0,
    warmup_row_count: int = 0,
) -> dict[str, Any]:
    effective_rows = [row for row in row_metrics if not _coerce_bool(row.get("warmup_excluded"))]
    if not effective_rows:
        return {
            "row_count": 0,
            "det_pass_rate": 0.0,
            "gt_exact_rate": 0.0,
            "warm_latency_mean": 0.0,
            "warm_latency_p50": 0.0,
            "warm_latency_p95": 0.0,
            "cold_load_sec": round(float(cold_load_sec or 0.0), 4),
            "avg_prompt_chars": 0.0,
            "avg_prompt_tokens": 0.0,
            "avg_completion_tokens": 0.0,
            "avg_total_tokens": 0.0,
            "avg_tokens_per_sec": 0.0,
            "peak_vram_gb_max": 0.0,
            "oom_count": 0,
            "generation_error_rate": 0.0,
            "failure_rate": 0.0,
            "row_success_rate": 0.0,
            "failure_reason_topk": [],
            "warmup_row_count": warmup_row_count,
        }
    row_count = len(effective_rows)
    latencies = [float(row.get("llm_latency_sec") or 0.0) for row in effective_rows]
    prompt_chars = [float(row.get("prompt_chars") or 0.0) for row in effective_rows]
    prompt_tokens = [float(row.get("prompt_tokens") or 0.0) for row in effective_rows]
    completion_tokens = [float(row.get("completion_tokens") or 0.0) for row in effective_rows]
    total_tokens = [float(row.get("total_tokens") or 0.0) for row in effective_rows]
    tokens_per_sec = [float(row.get("tokens_per_sec") or 0.0) for row in effective_rows if float(row.get("tokens_per_sec") or 0.0) > 0]
    det_pass_count = sum(1 for row in effective_rows if _coerce_bool(row.get("det_pass")))
    gt_exact_count = sum(1 for row in effective_rows if _coerce_bool(row.get("gt_exact")))
    generation_error_count = sum(1 for row in effective_rows if str(row.get("generation_error_type", "")).strip())
    row_success_count = sum(1 for row in effective_rows if _coerce_bool(row.get("row_success")))
    oom_count = sum(1 for row in effective_rows if _coerce_bool(row.get("oom_flag")))
    failure_counter: Counter[str] = Counter()
    for row in effective_rows:
        failure_counter.update(row.get("failure_reasons") or [])
    return {
        "row_count": row_count,
        "det_pass_rate": round(det_pass_count / row_count, 4),
        "gt_exact_rate": round(gt_exact_count / row_count, 4),
        "warm_latency_mean": _mean(latencies),
        "warm_latency_p50": _percentile(latencies, 0.5),
        "warm_latency_p95": _percentile(latencies, 0.95),
        "cold_load_sec": round(float(cold_load_sec or 0.0), 4),
        "avg_prompt_chars": _mean(prompt_chars),
        "avg_prompt_tokens": _mean(prompt_tokens),
        "avg_completion_tokens": _mean(completion_tokens),
        "avg_total_tokens": _mean(total_tokens),
        "avg_tokens_per_sec": _mean(tokens_per_sec),
        "peak_vram_gb_max": round(max(float(row.get("peak_vram_gb") or 0.0) for row in effective_rows), 4),
        "oom_count": oom_count,
        "generation_error_rate": round(generation_error_count / row_count, 4),
        "failure_rate": round((row_count - det_pass_count) / row_count, 4),
        "row_success_rate": round(row_success_count / row_count, 4),
        "failure_reason_topk": failure_counter.most_common(8),
        "warmup_row_count": warmup_row_count,
    }


def _pareto_flags(rows: list[dict[str, Any]], *, x_key: str, y_key: str) -> dict[str, bool]:
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


def _parse_program_view(value: Any) -> dict[str, str | bool]:
    text = str(value or "").strip()
    result: dict[str, str | bool] = {
        "raw": text,
        "name": "",
        "cron": "",
        "period": "",
        "code": "",
        "valid_json": False,
    }
    if not text:
        return result
    try:
        parsed = json.loads(text)
    except Exception:
        return result
    if not isinstance(parsed, dict):
        return result
    result["valid_json"] = True
    result["name"] = str(parsed.get("name", "") or "")
    result["cron"] = str(parsed.get("cron", "") or "")
    period = parsed.get("period", "")
    result["period"] = "" if period in (None, "") else str(period)
    result["code"] = str(parsed.get("code") or parsed.get("script") or "")
    return result


def _pretty_json_list(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "-"
    try:
        parsed = json.loads(text)
    except Exception:
        return text
    if isinstance(parsed, list):
        items = [str(item).strip() for item in parsed if str(item).strip()]
        return ", ".join(items) if items else "-"
    return str(parsed)


def _display_code(view: dict[str, str | bool], *, empty_label: str = "<empty>") -> str:
    code = str(view.get("code", "") or "").strip()
    if code:
        return code
    if bool(view.get("valid_json")):
        return empty_label
    raw = str(view.get("raw", "") or "").strip()
    if raw:
        return raw
    return empty_label


def _diff_summary(
    gt_view: dict[str, str | bool],
    output_view: dict[str, str | bool],
    *,
    det_exact: str,
    failure_reasons: str,
) -> str:
    if str(det_exact).strip().lower() == "true":
        return "exact match"
    parts: list[str] = []
    gt_cron = str(gt_view.get("cron", "") or "")
    out_cron = str(output_view.get("cron", "") or "")
    gt_period = str(gt_view.get("period", "") or "")
    out_period = str(output_view.get("period", "") or "")
    if gt_cron != out_cron or gt_period != out_period:
        parts.append("schedule differs")
    gt_code = str(gt_view.get("code", "") or "").strip()
    out_code = str(output_view.get("code", "") or "").strip()
    if gt_code != out_code:
        if not out_code:
            parts.append("code missing")
        elif not gt_code:
            parts.append("unexpected code")
        else:
            parts.append("code differs")
    reasons_text = _pretty_json_list(failure_reasons)
    if reasons_text != "-":
        parts.append(f"det={reasons_text}")
    if not parts and not bool(output_view.get("valid_json")):
        return "invalid json or unparsable output"
    return ", ".join(parts) if parts else "non-exact mismatch"


def _print_paths_summary(summary: dict[str, Any]) -> None:
    manifest = summary["manifest"]
    print(
        json.dumps(
            {
                "output_dir": summary["output_dir"],
                "suite_summary_csv": summary["suite_summary_csv"],
                "row_comparison_csv": summary["row_comparison_csv"],
                "failure_reason_summary_csv": summary.get("failure_reason_summary_csv", ""),
                "category_summary_csv": summary.get("category_summary_csv", ""),
                "main_model_comparison_csv": summary.get("main_model_comparison_csv", ""),
                "tradeoff_summary_csv": summary.get("tradeoff_summary_csv", ""),
                "model_keys": manifest["model_keys"],
                "row_count": manifest["row_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _print_suite_summary(summary: dict[str, Any]) -> None:
    manifest = summary["manifest"]
    print(f"Output directory: {summary['output_dir']}")
    print(f"Rows: {manifest['row_count']} | Models: {', '.join(manifest['model_keys'])}")
    if manifest.get("skipped_models"):
        skipped = ", ".join(f"{item['model_key']}({item['status']})" for item in manifest["skipped_models"])
        print(f"Skipped models: {skipped}")
    for model_summary in summary["models"]:
        metrics = model_summary["metrics"]
        usage = model_summary["usage"]
        paper_metrics = model_summary.get("paper_metrics") or {}
        error_suffix = ""
        if int(usage.get("error_count") or 0) > 0:
            error_suffix = f", gen_errors={usage['error_count']}"
        print(
            " - "
            f"{model_summary['model_key']} ({model_summary['model_label']}): "
            f"avg_det={metrics['avg_det_score']:.4f}, "
            f"gt_exact={metrics['gt_exact_count']}/{metrics['row_count']}, "
            f"pass={metrics['pass_count']}/{metrics['row_count']}, "
            f"avg_latency={usage['avg_latency_sec']:.4f}s, "
            f"warm_p50={paper_metrics.get('warm_latency_p50', 0.0):.4f}s, "
            f"cold_load={paper_metrics.get('cold_load_sec', 0.0):.4f}s, "
            f"avg_prompt_tokens={paper_metrics.get('avg_prompt_tokens', 0.0):.1f}, "
            f"peak_vram={paper_metrics.get('peak_vram_gb_max', 0.0):.4f}GB"
            f"{error_suffix}"
        )
        if usage.get("top_errors"):
            first_error = str(usage["top_errors"][0][0]).splitlines()[0]
            print(f"   top_generation_error: {first_error}")
    print(f"Suite summary CSV: {summary['suite_summary_csv']}")
    print(f"Row comparison CSV: {summary['row_comparison_csv']}")
    print(f"Failure reason CSV: {summary.get('failure_reason_summary_csv', '')}")
    print(f"Category summary CSV: {summary.get('category_summary_csv', '')}")
    if summary.get("main_model_comparison_csv"):
        print(f"Main model comparison CSV: {summary['main_model_comparison_csv']}")
    if summary.get("tradeoff_summary_csv"):
        print(f"Tradeoff summary CSV: {summary['tradeoff_summary_csv']}")


def _print_row_comparisons(
    summary: dict[str, Any],
    row_rows: list[dict[str, Any]],
    *,
    print_limit: int | None = None,
) -> None:
    if not row_rows:
        print("No row comparison data available.")
        return

    _print_suite_summary(summary)
    model_summaries = summary["models"]
    rows_to_print = row_rows[: max(0, int(print_limit))] if print_limit else row_rows
    print("")
    for row in rows_to_print:
        row_no = int(row.get("row_no") or 0)
        print("=" * 88)
        print(f"[Row {row_no}] {row.get('command_eng', '')}")
        if row.get("command_kor"):
            print(f"KOR: {row['command_kor']}")
        if row.get("category"):
            print(f"Category: {row['category']}")

        gt_view = _parse_program_view(row.get("gt", ""))
        gt_period = str(gt_view.get("period", "") or "0")
        print(f"GT schedule: cron=\"{gt_view.get('cron', '')}\" period={gt_period}")
        print("GT code:")
        print(indent(_display_code(gt_view), "  "))

        for model_summary in model_summaries:
            model_key = str(model_summary["model_key"])
            det_score = str(row.get(f"{model_key}__det_score", "") or "0")
            det_pass = str(row.get(f"{model_key}__det_pass", "") or "False")
            det_exact = str(row.get(f"{model_key}__det_gt_exact", "") or "False")
            det_similarity = str(row.get(f"{model_key}__det_gt_similarity", "") or "0")
            failure_reasons_raw = str(row.get(f"{model_key}__failure_reasons", "") or "")
            failures = _pretty_json_list(failure_reasons_raw)
            output_view = _parse_program_view(row.get(f"{model_key}__output", ""))
            output_period = str(output_view.get("period", "") or "0")
            prompt_tokens = str(row.get(f"{model_key}__prompt_tokens", "") or "0")
            llm_latency = str(row.get(f"{model_key}__llm_latency_sec", "") or "0")
            peak_vram = str(row.get(f"{model_key}__peak_vram_gb", "") or "0")
            generation_error_type = str(row.get(f"{model_key}__generation_error_type", "") or "")
            print("")
            print(
                f"[{model_key}] {model_summary['model_label']} | "
                f"det={det_score} | pass={det_pass} | exact={det_exact} | sim={det_similarity}"
            )
            print(f"Generated schedule: cron=\"{output_view.get('cron', '')}\" period={output_period}")
            print(f"Prompt tokens: {prompt_tokens} | LLM latency: {llm_latency}s | Peak VRAM: {peak_vram}GB")
            if generation_error_type:
                print(f"Generation error type: {generation_error_type}")
            print(
                "Diff summary: "
                + _diff_summary(
                    gt_view,
                    output_view,
                    det_exact=det_exact,
                    failure_reasons=failure_reasons_raw,
                )
            )
            print(f"Failure reasons: {failures}")
            print("Generated code:")
            print(indent(_display_code(output_view), "  "))

    if print_limit and len(row_rows) > print_limit:
        print("")
        print(f"... printed {print_limit} of {len(row_rows)} rows. See CSV for the full dataset comparison.")


def _resolved_output_dir(raw: str | None) -> Path:
    if raw:
        path = Path(raw)
        if not path.is_absolute():
            path = (VERSION_ROOT / raw).resolve()
        return path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return RESULTS_DIR / f"model_suite_{timestamp}"


def _env_text(name_v15: str, name_v14: str, default: str = "") -> str:
    value = os.getenv(name_v15, "").strip()
    if value:
        return value
    value = os.getenv(name_v14, "").strip()
    if value:
        return value
    return default


def _env_bool(name_v15: str, name_v14: str, default: bool) -> bool:
    text = _env_text(name_v15, name_v14, "")
    if not text:
        return default
    return text.lower() in {"1", "true", "yes", "y", "on"}


def _hf_cache_root() -> Path:
    explicit = os.getenv("HF_HUB_CACHE", "").strip() or os.getenv("HUGGINGFACE_HUB_CACHE", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    transformers_cache = os.getenv("TRANSFORMERS_CACHE", "").strip()
    if transformers_cache:
        return Path(transformers_cache).expanduser()
    return Path.home() / ".cache" / "huggingface" / "hub"


def _hf_repo_cache_dir(model_name: str) -> Path:
    return _hf_cache_root() / f"models--{model_name.replace('/', '--')}"


def _snapshot_has_model_artifacts(snapshot_path: Path) -> bool:
    path = Path(snapshot_path).expanduser()
    if not path.exists() or not path.is_dir():
        return False
    has_config = (path / "config.json").exists()
    weight_patterns = (
        "*.safetensors",
        "*.bin",
        "*.pth",
        "*.pt",
        "*.gguf",
        "*.ckpt",
        "*.msgpack",
        "*.onnx",
    )
    has_weights = any(path.glob(pattern) for pattern in weight_patterns)
    if not has_weights and (path / "model.safetensors.index.json").exists():
        has_weights = True
    if not has_weights and (path / "pytorch_model.bin.index.json").exists():
        has_weights = True
    return has_config and has_weights


def _inspect_model_runtime(
    entry: dict[str, Any],
    *,
    args: argparse.Namespace,
    global_llm_extra: dict[str, Any],
) -> dict[str, Any]:
    llm_mode = _suite_mode(entry, args) or "worker"
    llm_extra_payload = _merge_llm_extra(entry, global_llm_extra) or {}
    runtime: dict[str, Any] = {
        "model_key": entry["key"],
        "model_label": entry["label"],
        "mode": llm_mode,
        "backend": "transformers_worker" if llm_mode == "worker" else llm_mode,
        "configured_model": entry["model"],
        "status": "unknown",
        "message": "",
        "ollama_used": False,
    }
    if llm_mode != "worker":
        if llm_mode == "mock":
            runtime["status"] = "ready"
            runtime["message"] = "mock mode"
            return runtime
        endpoint = _suite_endpoint(entry, args)
        runtime["status"] = "ready" if endpoint else "missing_endpoint"
        runtime["message"] = (
            f"endpoint={endpoint}" if endpoint else "This model requires --llm-endpoint or an endpoint env var."
        )
        return runtime

    worker_runtime = describe_worker_runtime()
    worker_ok = bool(worker_runtime.get("ok"))
    local_model_name = str(
        llm_extra_payload.get("local_model_name")
        or _env_text("JOI_V15_LOCAL_MODEL_NAME", "JOI_V14_LOCAL_MODEL_NAME", entry["model"])
    )
    local_files_only = bool(
        llm_extra_payload.get(
            "local_files_only",
            _env_bool("JOI_V15_LOCAL_FILES_ONLY", "JOI_V14_LOCAL_FILES_ONLY", True),
        )
    )
    local_device = str(
        llm_extra_payload.get(
            "local_device",
            _env_text("JOI_V15_LOCAL_DEVICE", "JOI_V14_LOCAL_DEVICE", "cuda:1"),
        )
    )
    local_dtype = str(
        llm_extra_payload.get(
            "local_dtype",
            _env_text("JOI_V15_LOCAL_DTYPE", "JOI_V14_LOCAL_DTYPE", "bf16"),
        )
    )
    local_load_in_4bit = bool(
        llm_extra_payload.get(
            "local_load_in_4bit",
            _env_bool("JOI_V15_LOCAL_LOAD_IN_4BIT", "JOI_V14_LOCAL_LOAD_IN_4BIT", False),
        )
    )
    local_attn_implementation = str(
        llm_extra_payload.get(
            "local_attn_implementation",
            _env_text("JOI_V15_LOCAL_ATTN_IMPLEMENTATION", "JOI_V14_LOCAL_ATTN_IMPLEMENTATION", ""),
        )
    )
    cache_path = _hf_repo_cache_dir(local_model_name)
    if Path(local_model_name).expanduser().exists():
        cache_kind = "local_path"
        cache_exists = True
        snapshot_count = 1
        resolved_cache_path = str(Path(local_model_name).expanduser().resolve())
    else:
        cache_kind = "hf_cache"
        cache_exists = cache_path.exists()
        snapshots = sorted((cache_path / "snapshots").glob("*")) if cache_exists else []
        snapshot_count = len(snapshots)
        resolved_cache_path = str((snapshots[-1] if snapshots else cache_path).resolve()) if cache_exists else str(cache_path)

    runtime.update(
        {
            "local_model_name": local_model_name,
            "resolved_local_model_name": (
                str(Path(local_model_name).expanduser().resolve()) if Path(local_model_name).expanduser().exists() else resolved_cache_path
            ),
            "local_files_only": local_files_only,
            "local_device": local_device,
            "local_dtype": local_dtype,
            "local_load_in_4bit": local_load_in_4bit,
            "local_attn_implementation": local_attn_implementation,
            "cache_kind": cache_kind,
            "cache_path": resolved_cache_path,
            "cache_exists": cache_exists,
            "snapshot_count": snapshot_count,
            "cache_complete": _snapshot_has_model_artifacts(Path(resolved_cache_path)) if cache_exists else False,
            "worker_python": worker_runtime.get("python_path", ""),
            "worker_path": worker_runtime.get("worker_path", ""),
            "persistent_worker_path": worker_runtime.get("persistent_worker_path", ""),
            "persistent_worker": worker_runtime.get("persistent_worker", False),
            "worker_runtime": worker_runtime,
        }
    )
    if not worker_ok:
        runtime["status"] = "worker_env_broken"
        runtime["message"] = f"worker python probe failed: {worker_runtime.get('error', 'unknown error')}"
    elif cache_exists and not bool(runtime.get("cache_complete")):
        runtime["status"] = "incomplete_cache"
        runtime["message"] = "Local cache snapshot exists but required model artifacts are missing."
    elif cache_exists:
        runtime["status"] = "ready"
        runtime["message"] = f"cached locally ({cache_kind}, snapshots={snapshot_count})"
    elif local_files_only:
        runtime["status"] = "missing_cache"
        runtime["message"] = "local_files_only=true and the model is not cached locally."
    else:
        runtime["status"] = "download_required"
        runtime["message"] = "The model is not cached locally; this runtime would try Hugging Face download."
    return runtime


def _print_preflight(
    runtime_rows: list[dict[str, Any]],
    *,
    print_worker_info: bool = False,
    debug_runtime: bool = False,
) -> None:
    print("Preflight:")
    for row in runtime_rows:
        header = (
            f" - {row['model_key']} ({row['model_label']}): "
            f"backend={row['backend']}, status={row['status']}"
        )
        print(header)
        if row["mode"] == "worker":
            print(f"   local_model_name: {row.get('local_model_name', '')}")
            print(f"   resolved_model_path: {row.get('resolved_local_model_name', '')}")
            print(
                f"   device={row.get('local_device', '')} "
                f"dtype={row.get('local_dtype', '')} "
                f"load_in_4bit={row.get('local_load_in_4bit', False)} "
                f"local_files_only={row.get('local_files_only', False)} "
                f"attn={row.get('local_attn_implementation', '') or '-'}"
            )
            print(f"   cache_path: {row.get('cache_path', '')}")
            if print_worker_info or debug_runtime:
                worker_runtime = row.get("worker_runtime") or {}
                print(f"   worker_python: {row.get('worker_python', '')}")
                print(
                    f"   torch={worker_runtime.get('torch_version', '')} "
                    f"transformers={worker_runtime.get('transformers_version', '')} "
                    f"cuda_available={worker_runtime.get('cuda_available', False)} "
                    f"device_count={worker_runtime.get('device_count', 0)}"
                )
                if worker_runtime.get("cuda_devices"):
                    print(f"   cuda_devices: {', '.join(str(item) for item in worker_runtime['cuda_devices'])}")
                if worker_runtime.get("warnings") and debug_runtime:
                    print(f"   warnings: {json.dumps(worker_runtime['warnings'], ensure_ascii=False)}")
        if row.get("message"):
            print(f"   note: {row['message']}")


def _resolve_suite(args: argparse.Namespace) -> list[dict[str, Any]]:
    selected = MODEL_SUITES[args.suite]
    if not args.model_key:
        return [copy.deepcopy(item) for item in selected]
    wanted = {str(item).strip() for item in args.model_key if str(item).strip()}
    filtered = [copy.deepcopy(item) for item in selected if item["key"] in wanted]
    if not filtered:
        raise SystemExit(f"No suite entries matched --model-key values: {sorted(wanted)}")
    return filtered


def _select_dataset_rows(args: argparse.Namespace) -> list[tuple[int, dict[str, str]]]:
    if args.limit_per_category is not None and int(args.limit_per_category) < 1:
        raise SystemExit("--limit-per-category must be >= 1.")
    rows = load_dataset_rows(args.dataset)
    categories = _load_category_filters(args)
    selected = select_rows(
        rows,
        start_row=args.start_row,
        end_row=args.end_row,
        limit=args.limit,
        limit_per_category=args.limit_per_category,
        categories=categories,
    )
    if args.row_no:
        wanted = {int(value) for value in args.row_no}
        selected = [item for item in selected if item[0] in wanted]
    if args.query:
        query = str(args.query).strip().lower()
        selected = [
            item
            for item in selected
            if query in str(item[1].get("command_eng", "")).lower()
            or query in str(item[1].get("command_kor", "")).lower()
        ]
    if not selected:
        raise SystemExit("No dataset rows selected. Check --row-no/--query/--limit/--limit-per-category/--category.")
    return selected


def _select_warmup_rows(
    args: argparse.Namespace,
    *,
    selected_rows: list[tuple[int, dict[str, str]]],
) -> list[tuple[int, dict[str, str]]]:
    if not _warmup_enabled(args):
        return []
    if args.command_eng or args.command_kor:
        return []
    dataset_rows = load_dataset_rows(args.dataset)
    requested_row_nos = [int(value) for value in args.warmup_row_no]
    if args.warmup_start_row is not None or args.warmup_end_row is not None:
        warmup_rows = select_rows(
            dataset_rows,
            start_row=args.warmup_start_row or 1,
            end_row=args.warmup_end_row,
            limit=None,
            categories=[],
        )
        requested_row_nos.extend(row_no for row_no, _row in warmup_rows)
    if (
        not requested_row_nos
        and selected_rows
        and (args.paper_fair_mode or (args.measure_latency and _resolve_latency_isolation_mode(args) == "fresh_worker"))
    ):
        requested_row_nos.append(int(selected_rows[0][0]))
    if not requested_row_nos:
        return []
    wanted = {int(item) for item in requested_row_nos if int(item) >= 1}
    if not wanted:
        return []
    warmup_rows: list[tuple[int, dict[str, str]]] = []
    for row_no, row in enumerate(dataset_rows, start=1):
        if row_no in wanted:
            warmup_rows.append((row_no, row))
    return warmup_rows


def _build_manual_rows(args: argparse.Namespace) -> list[tuple[int, dict[str, str]]]:
    connected_devices = parse_connected_devices(_read_inline_or_file(args.connected_devices_json))
    row = {
        "index": "manual",
        "category": args.manual_category,
        "command_kor": str(args.command_kor or ""),
        "command_eng": str(args.command_eng or args.command_kor or ""),
        "connected_devices": json.dumps(connected_devices, ensure_ascii=False),
        "gt": _normalize_gt_text(args.gt_json),
        "cron": str(args.cron or ""),
        "period": str(int(args.period)),
    }
    return [(1, row)]


def _select_rows(args: argparse.Namespace) -> list[tuple[int, dict[str, str]]]:
    if args.command_eng or args.command_kor:
        return _build_manual_rows(args)
    return _select_dataset_rows(args)


def _genome_for_model(base_genome: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    genome = copy.deepcopy(base_genome)
    genome.setdefault("params", {})
    genome["params"]["model"] = entry["model"]
    base_id = str(base_genome.get("id", "genome"))
    genome["id"] = f"{base_id}__{slugify(entry['key'])}"
    return genome


def _merge_llm_extra(entry: dict[str, Any], global_extra: dict[str, Any]) -> dict[str, Any] | None:
    merged = dict(entry.get("llm_extra_payload") or {})
    merged.update(global_extra)
    return merged or None


def _suite_mode(entry: dict[str, Any], args: argparse.Namespace) -> str | None:
    if args.llm_mode:
        return args.llm_mode
    return entry.get("mode")


def _suite_endpoint(entry: dict[str, Any], args: argparse.Namespace) -> str | None:
    if args.llm_endpoint:
        return args.llm_endpoint
    endpoint = str(entry.get("endpoint", "") or "").strip()
    if endpoint:
        return endpoint
    env_name = str(entry.get("endpoint_env", "") or "").strip()
    if env_name:
        return os.getenv(env_name, "").strip() or None
    return None


def _run_single_model(
    *,
    args: argparse.Namespace,
    entry: dict[str, Any],
    runtime_info: dict[str, Any],
    base_genome: dict[str, Any],
    rows: list[tuple[int, dict[str, str]]],
    warmup_rows: list[tuple[int, dict[str, str]]],
    service_schema: dict[str, dict[str, Any]],
    output_dir: Path,
    global_llm_extra: dict[str, Any],
) -> dict[str, Any]:
    genome = _genome_for_model(base_genome, entry)
    cli_namespace = argparse.Namespace(temperature=args.temperature, max_tokens=args.max_tokens)
    temperature, max_tokens, resolved_model = _llm_settings(
        genome,
        cli_namespace,
        model_override=entry["model"],
    )
    llm_mode = _suite_mode(entry, args)
    llm_endpoint = _suite_endpoint(entry, args)
    if llm_mode in {"openai", "openai_compatible", "http"} and not llm_endpoint:
        raise SystemExit(f"Model {entry['key']} requires --llm-endpoint for mode={llm_mode}.")
    llm_extra_payload = dict(_merge_llm_extra(entry, global_llm_extra) or {})
    latency_isolation_mode = _resolve_latency_isolation_mode(args)
    if llm_mode == "worker" and latency_isolation_mode == "fresh_worker":
        llm_extra_payload["persistent_worker"] = True
    elif llm_mode == "worker" and max(1, int(args.max_workers or 1)) > 1:
        llm_extra_payload["persistent_worker"] = False

    label = slugify(entry["key"])
    candidates_csv = output_dir / f"{label}_candidates.csv"
    rerank_csv = output_dir / f"{label}_rerank.csv"
    run_id = f"suite_{label}_{slugify(genome.get('id', 'genome'))}_{args.seed}"
    warmup_summary: dict[str, Any] = {
        "row_count": 0,
        "row_nos": [],
        "candidate_count": 0,
        "cold_load_sec": 0.0,
        "output_csv": "",
    }

    if llm_mode == "worker" and latency_isolation_mode == "fresh_worker":
        close_persistent_worker()

    try:
        if warmup_rows:
            warmup_csv = output_dir / f"{label}_warmup_candidates.csv"
            warmup_generation = generate_candidates_for_rows(
                profile=VERSION_ROOT.name,
                genome=genome,
                dataset_rows=warmup_rows,
                service_schema=service_schema,
                candidate_k=1,
                llm_mode=llm_mode,
                llm_endpoint=llm_endpoint,
                timeout_sec=args.timeout_sec,
                retries=args.retries,
                run_id=f"{run_id}_warmup",
                output_csv=warmup_csv,
                seed=args.seed,
                temperature=temperature,
                max_tokens=max_tokens,
                model=resolved_model,
                llm_extra_payload=llm_extra_payload,
            )
            warmup_first_latency = 0.0
            if warmup_generation["rows"]:
                first_meta = _parse_candidate_metadata(str(warmup_generation["rows"][0].get("candidate_metadata", "")))
                if first_meta:
                    warmup_first_latency = _safe_float(first_meta[0].get("latency_sec"))
            warmup_summary = {
                "row_count": len(warmup_rows),
                "row_nos": [row_no for row_no, _row in warmup_rows],
                "candidate_count": sum(_safe_int(row.get("candidate_count")) for row in warmup_generation["rows"]),
                "cold_load_sec": round(warmup_first_latency, 4),
                "output_csv": str(warmup_csv),
            }
            dump_json(output_dir / f"{label}_warmup_summary.json", warmup_summary)

        generation = generate_candidates_for_rows(
            profile=VERSION_ROOT.name,
            genome=genome,
            dataset_rows=rows,
            service_schema=service_schema,
            candidate_k=args.candidate_k,
            llm_mode=llm_mode,
            llm_endpoint=llm_endpoint,
            timeout_sec=args.timeout_sec,
            retries=args.retries,
            run_id=run_id,
            output_csv=candidates_csv,
            seed=args.seed,
            temperature=temperature,
            max_tokens=max_tokens,
            model=resolved_model,
            llm_extra_payload=llm_extra_payload,
        )
        rerank = rerank_candidates_csv(
            profile=VERSION_ROOT.name,
            genome=genome,
            candidates_csv=candidates_csv,
            service_schema=service_schema,
            repair_threshold=args.repair_threshold,
            repair_attempts=max(0, int(args.repair_attempts)),
            output_csv=rerank_csv,
            llm_mode=llm_mode,
            llm_endpoint=llm_endpoint,
            timeout_sec=args.timeout_sec,
            retries=args.retries,
            seed=args.seed,
            model_override=resolved_model,
            llm_extra_payload=llm_extra_payload,
        )
        rerank_rows = read_csv_rows(rerank_csv)
    finally:
        if llm_mode == "worker" and latency_isolation_mode == "fresh_worker":
            close_persistent_worker()
    metrics = _summarize_rerank_rows(rerank_rows, default_threshold=args.repair_threshold)
    usage = _summarize_generation_usage(generation["rows"])
    row_metrics = _build_model_row_metrics(
        model_key=entry["key"],
        model_label=entry["label"],
        generation_rows=generation["rows"],
        rerank_rows=rerank_rows,
        runtime_info=runtime_info,
        default_threshold=args.repair_threshold,
    )
    paper_metrics = _summarize_model_row_metrics(
        row_metrics,
        cold_load_sec=_safe_float(warmup_summary.get("cold_load_sec")),
        warmup_row_count=_safe_int(warmup_summary.get("row_count")),
    )

    summary = {
        "model_key": entry["key"],
        "model_label": entry["label"],
        "mode": llm_mode or "worker",
        "model": resolved_model,
        "endpoint": llm_endpoint or "",
        "genome_id": genome.get("id", ""),
        "blocks": genome.get("blocks", []),
        "temperature": temperature,
        "max_tokens": max_tokens,
        "candidate_k": args.candidate_k,
        "repair_attempts": max(0, int(args.repair_attempts)),
        "llm_extra_payload": llm_extra_payload or {},
        "runtime": runtime_info,
        "resolved_model_path": runtime_info.get("resolved_local_model_name", runtime_info.get("local_model_name", "")),
        "worker_python": runtime_info.get("worker_python", ""),
        "worker_path": runtime_info.get("worker_path", ""),
        "persistent_worker_path": runtime_info.get("persistent_worker_path", ""),
        "persistent_worker": runtime_info.get("persistent_worker", False),
        "local_device": runtime_info.get("local_device", ""),
        "local_dtype": runtime_info.get("local_dtype", ""),
        "local_load_in_4bit": runtime_info.get("local_load_in_4bit", False),
        "local_attn_implementation": runtime_info.get("local_attn_implementation", ""),
        "local_files_only": runtime_info.get("local_files_only", False),
        "latency_isolation_mode": latency_isolation_mode,
        "paper_fair_mode": bool(args.paper_fair_mode),
        "generation": generation,
        "warmup": warmup_summary,
        "rerank": rerank,
        "metrics": metrics,
        "usage": usage,
        "row_metrics": row_metrics,
        "paper_metrics": paper_metrics,
    }
    dump_json(output_dir / f"{label}_summary.json", summary)
    return summary


def _build_overall_rows(model_summaries: list[dict[str, Any]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for summary in model_summaries:
        metrics = summary["metrics"]
        usage = summary["usage"]
        paper_metrics = summary.get("paper_metrics") or {}
        rows.append(
            [
                summary["model_key"],
                summary["model_label"],
                summary["mode"],
                summary["model"],
                str(summary.get("resolved_model_path", "")),
                str(summary.get("worker_python", "")),
                str(summary.get("local_device", "")),
                str(summary.get("local_dtype", "")),
                str(summary.get("local_attn_implementation", "")),
                str(summary.get("candidate_k", "")),
                str(summary.get("repair_attempts", "")),
                str(summary.get("genome_id", "")),
                str(summary.get("latency_isolation_mode", "")),
                str(summary.get("paper_fair_mode", False)),
                str((summary.get("warmup") or {}).get("row_count", 0)),
                str(metrics["row_count"]),
                f"{metrics['avg_det_score']:.4f}",
                f"{metrics['avg_gt_similarity']:.4f}",
                str(metrics["gt_exact_count"]),
                str(metrics["pass_count"]),
                str(metrics["fail_count"]),
                f"{paper_metrics.get('det_pass_rate', 0.0):.4f}",
                f"{paper_metrics.get('gt_exact_rate', 0.0):.4f}",
                f"{paper_metrics.get('warm_latency_mean', 0.0):.4f}",
                f"{paper_metrics.get('warm_latency_p50', 0.0):.4f}",
                f"{paper_metrics.get('warm_latency_p95', 0.0):.4f}",
                f"{paper_metrics.get('cold_load_sec', 0.0):.4f}",
                f"{paper_metrics.get('avg_prompt_chars', 0.0):.4f}",
                f"{paper_metrics.get('avg_prompt_tokens', 0.0):.4f}",
                f"{paper_metrics.get('avg_completion_tokens', 0.0):.4f}",
                f"{paper_metrics.get('avg_total_tokens', 0.0):.4f}",
                f"{paper_metrics.get('avg_tokens_per_sec', 0.0):.4f}",
                f"{usage['avg_prompt_tokens']:.4f}",
                f"{usage['avg_completion_tokens']:.4f}",
                f"{usage['avg_total_tokens']:.4f}",
                f"{usage['avg_latency_sec']:.4f}",
                f"{paper_metrics.get('peak_vram_gb_max', 0.0):.4f}",
                str(paper_metrics.get("oom_count", 0)),
                f"{paper_metrics.get('generation_error_rate', 0.0):.4f}",
                f"{paper_metrics.get('failure_rate', 0.0):.4f}",
                f"{paper_metrics.get('row_success_rate', 0.0):.4f}",
                json.dumps(paper_metrics.get("failure_reason_topk", []), ensure_ascii=False),
            ]
        )
    return rows


def _build_failure_reason_summary(model_summaries: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    for summary in model_summaries:
        counter: Counter[str] = Counter()
        rerank_csv = Path(summary["rerank"]["output_csv"])
        for row in read_csv_rows(rerank_csv):
            counter.update(_load_failure_reasons(row))
        for reason, count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
            rows.append(
                {
                    "model_key": str(summary["model_key"]),
                    "model_label": str(summary["model_label"]),
                    "failure_reason": str(reason),
                    "count": str(count),
                }
            )
    return ["model_key", "model_label", "failure_reason", "count"], rows


def _build_category_summary(
    model_summaries: list[dict[str, Any]],
    *,
    default_threshold: float,
) -> tuple[list[str], list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    for summary in model_summaries:
        by_category: dict[str, list[dict[str, Any]]] = {}
        for row in summary.get("row_metrics") or []:
            by_category.setdefault(str(row.get("row_category", "")), []).append(row)
        for category in sorted(by_category.keys()):
            category_rows = by_category[category]
            det_scores = [_safe_float(row.get("det_score")) for row in category_rows]
            similarities = [_safe_float(row.get("det_gt_similarity")) for row in category_rows]
            det_pass_count = sum(1 for row in category_rows if _coerce_bool(row.get("det_pass")))
            gt_exact_count = sum(1 for row in category_rows if _coerce_bool(row.get("gt_exact")))
            generation_error_count = sum(1 for row in category_rows if str(row.get("generation_error_type", "")).strip())
            row_success_count = sum(1 for row in category_rows if _coerce_bool(row.get("row_success")))
            oom_count = sum(1 for row in category_rows if _coerce_bool(row.get("oom_flag")))
            counter: Counter[str] = Counter()
            for row in category_rows:
                counter.update(row.get("failure_reasons") or [])
            row_count = len(category_rows)
            rows.append(
                {
                    "model_key": str(summary["model_key"]),
                    "model_label": str(summary["model_label"]),
                    "category": category,
                    "row_count": str(row_count),
                    "avg_det_score": f"{_mean(det_scores):.4f}",
                    "avg_gt_similarity": f"{_mean(similarities):.4f}",
                    "gt_exact_count": str(gt_exact_count),
                    "gt_exact_rate": f"{(gt_exact_count / row_count) if row_count else 0.0:.4f}",
                    "pass_count": str(det_pass_count),
                    "det_pass_rate": f"{(det_pass_count / row_count) if row_count else 0.0:.4f}",
                    "fail_count": str(row_count - det_pass_count),
                    "warm_latency_p50": f"{_percentile([_safe_float(row.get('llm_latency_sec')) for row in category_rows], 0.5):.4f}",
                    "avg_prompt_tokens": f"{_mean([_safe_float(row.get('prompt_tokens')) for row in category_rows]):.4f}",
                    "avg_total_tokens": f"{_mean([_safe_float(row.get('total_tokens')) for row in category_rows]):.4f}",
                    "peak_vram_gb_max": f"{max((_safe_float(row.get('peak_vram_gb')) for row in category_rows), default=0.0):.4f}",
                    "oom_count": str(oom_count),
                    "generation_error_rate": f"{(generation_error_count / row_count) if row_count else 0.0:.4f}",
                    "failure_rate": f"{((row_count - det_pass_count) / row_count) if row_count else 0.0:.4f}",
                    "row_success_rate": f"{(row_success_count / row_count) if row_count else 0.0:.4f}",
                    "top_failure_types": json.dumps(counter.most_common(6), ensure_ascii=False),
                }
            )
    return (
        [
            "model_key",
            "model_label",
            "category",
            "row_count",
            "avg_det_score",
            "avg_gt_similarity",
            "gt_exact_count",
            "gt_exact_rate",
            "pass_count",
            "det_pass_rate",
            "fail_count",
            "warm_latency_p50",
            "avg_prompt_tokens",
            "avg_total_tokens",
            "peak_vram_gb_max",
            "oom_count",
            "generation_error_rate",
            "failure_rate",
            "row_success_rate",
            "top_failure_types",
        ],
        rows,
    )


def _build_latency_breakdown_rows(model_summaries: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    fieldnames = [
        "model_key",
        "model_label",
        "row_no",
        "row_category",
        "command_eng",
        "command_kor",
        "det_score",
        "det_pass",
        "gt_exact",
        "failure_reasons",
        "prompt_chars",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "llm_latency_sec",
        "total_pipeline_sec",
        "tokens_per_sec",
        "peak_vram_gb",
        "generation_error_type",
        "generation_error_types",
        "oom_flag",
        "worker_python",
        "resolved_model_path",
        "warmup_excluded",
        "selected_candidate_index",
        "repair_applied",
        "candidate_count",
        "generation_call_count",
        "repair_call_count",
        "row_success",
    ]
    rows: list[dict[str, Any]] = []
    for summary in model_summaries:
        for row in summary.get("row_metrics") or []:
            payload = {key: row.get(key, "") for key in fieldnames}
            payload["failure_reasons"] = row.get("failure_reasons_json", "[]")
            rows.append(payload)
    return fieldnames, rows


def _build_main_model_comparison_rows(model_summaries: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    fieldnames = [
        "model_key",
        "model_label",
        "avg_det_score",
        "det_pass_rate",
        "gt_exact_rate",
        "warm_latency_mean",
        "warm_latency_p50",
        "warm_latency_p95",
        "cold_load_sec",
        "avg_prompt_tokens",
        "avg_completion_tokens",
        "avg_total_tokens",
        "peak_vram_gb_max",
        "oom_count",
        "generation_error_rate",
        "failure_rate",
        "row_success_rate",
        "resolved_model_path",
        "worker_python",
        "candidate_k",
        "repair_attempts",
        "latency_isolation_mode",
        "paper_fair_mode",
    ]
    rows: list[dict[str, Any]] = []
    for summary in model_summaries:
        metrics = summary.get("metrics") or {}
        paper_metrics = summary.get("paper_metrics") or {}
        rows.append(
            {
                "model_key": summary.get("model_key", ""),
                "model_label": summary.get("model_label", ""),
                "avg_det_score": f"{_safe_float(metrics.get('avg_det_score')):.4f}",
                "det_pass_rate": f"{_safe_float(paper_metrics.get('det_pass_rate')):.4f}",
                "gt_exact_rate": f"{_safe_float(paper_metrics.get('gt_exact_rate')):.4f}",
                "warm_latency_mean": f"{_safe_float(paper_metrics.get('warm_latency_mean')):.4f}",
                "warm_latency_p50": f"{_safe_float(paper_metrics.get('warm_latency_p50')):.4f}",
                "warm_latency_p95": f"{_safe_float(paper_metrics.get('warm_latency_p95')):.4f}",
                "cold_load_sec": f"{_safe_float(paper_metrics.get('cold_load_sec')):.4f}",
                "avg_prompt_tokens": f"{_safe_float(paper_metrics.get('avg_prompt_tokens')):.4f}",
                "avg_completion_tokens": f"{_safe_float(paper_metrics.get('avg_completion_tokens')):.4f}",
                "avg_total_tokens": f"{_safe_float(paper_metrics.get('avg_total_tokens')):.4f}",
                "peak_vram_gb_max": f"{_safe_float(paper_metrics.get('peak_vram_gb_max')):.4f}",
                "oom_count": str(paper_metrics.get("oom_count", 0)),
                "generation_error_rate": f"{_safe_float(paper_metrics.get('generation_error_rate')):.4f}",
                "failure_rate": f"{_safe_float(paper_metrics.get('failure_rate')):.4f}",
                "row_success_rate": f"{_safe_float(paper_metrics.get('row_success_rate')):.4f}",
                "resolved_model_path": summary.get("resolved_model_path", ""),
                "worker_python": summary.get("worker_python", ""),
                "candidate_k": str(summary.get("candidate_k", "")),
                "repair_attempts": str(summary.get("repair_attempts", "")),
                "latency_isolation_mode": summary.get("latency_isolation_mode", ""),
                "paper_fair_mode": str(summary.get("paper_fair_mode", False)),
            }
        )
    return fieldnames, rows


def _build_tradeoff_summary_rows(model_summaries: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    source_rows: list[dict[str, Any]] = []
    for summary in model_summaries:
        metrics = summary.get("metrics") or {}
        paper_metrics = summary.get("paper_metrics") or {}
        source_rows.append(
            {
                "model_key": summary.get("model_key", ""),
                "model_label": summary.get("model_label", ""),
                "avg_det_score": _safe_float(metrics.get("avg_det_score")),
                "warm_latency_p50": _safe_float(paper_metrics.get("warm_latency_p50")),
                "avg_prompt_tokens": _safe_float(paper_metrics.get("avg_prompt_tokens")),
                "peak_vram_gb_max": _safe_float(paper_metrics.get("peak_vram_gb_max")),
                "cold_load_sec": _safe_float(paper_metrics.get("cold_load_sec")),
                "oom_count": _safe_int(paper_metrics.get("oom_count")),
                "generation_error_rate": _safe_float(paper_metrics.get("generation_error_rate")),
                "failure_rate": _safe_float(paper_metrics.get("failure_rate")),
            }
        )
    latency_frontier = _pareto_flags(source_rows, x_key="warm_latency_p50", y_key="avg_det_score")
    prompt_frontier = _pareto_flags(source_rows, x_key="avg_prompt_tokens", y_key="avg_det_score")
    vram_frontier = _pareto_flags(source_rows, x_key="peak_vram_gb_max", y_key="avg_det_score")
    fieldnames = [
        "model_key",
        "model_label",
        "avg_det_score",
        "warm_latency_p50",
        "avg_prompt_tokens",
        "peak_vram_gb_max",
        "cold_load_sec",
        "oom_count",
        "generation_error_rate",
        "failure_rate",
        "det_per_latency",
        "det_per_prompt_token",
        "det_per_vram",
        "pareto_det_vs_warm_latency",
        "pareto_det_vs_prompt_tokens",
        "pareto_det_vs_peak_vram",
    ]
    rows: list[dict[str, Any]] = []
    for row in source_rows:
        model_key = str(row.get("model_key", ""))
        warm_latency = _safe_float(row.get("warm_latency_p50"))
        prompt_tokens = _safe_float(row.get("avg_prompt_tokens"))
        peak_vram = _safe_float(row.get("peak_vram_gb_max"))
        det_score = _safe_float(row.get("avg_det_score"))
        rows.append(
            {
                "model_key": model_key,
                "model_label": row.get("model_label", ""),
                "avg_det_score": f"{det_score:.4f}",
                "warm_latency_p50": f"{warm_latency:.4f}",
                "avg_prompt_tokens": f"{prompt_tokens:.4f}",
                "peak_vram_gb_max": f"{peak_vram:.4f}",
                "cold_load_sec": f"{_safe_float(row.get('cold_load_sec')):.4f}",
                "oom_count": str(_safe_int(row.get("oom_count"))),
                "generation_error_rate": f"{_safe_float(row.get('generation_error_rate')):.4f}",
                "failure_rate": f"{_safe_float(row.get('failure_rate')):.4f}",
                "det_per_latency": f"{(det_score / warm_latency) if warm_latency > 0 else 0.0:.4f}",
                "det_per_prompt_token": f"{(det_score / prompt_tokens) if prompt_tokens > 0 else 0.0:.6f}",
                "det_per_vram": f"{(det_score / peak_vram) if peak_vram > 0 else 0.0:.4f}",
                "pareto_det_vs_warm_latency": str(latency_frontier.get(model_key, False)),
                "pareto_det_vs_prompt_tokens": str(prompt_frontier.get(model_key, False)),
                "pareto_det_vs_peak_vram": str(vram_frontier.get(model_key, False)),
            }
        )
    return fieldnames, rows


def _build_latency_summary_rows(model_summaries: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    fieldnames = ["model_key", "model_label", "cold_load_sec", "warm_latency_mean", "warm_latency_p50", "warm_latency_p95", "row_success_rate"]
    rows: list[dict[str, Any]] = []
    for summary in model_summaries:
        paper_metrics = summary.get("paper_metrics") or {}
        rows.append(
            {
                "model_key": summary.get("model_key", ""),
                "model_label": summary.get("model_label", ""),
                "cold_load_sec": f"{_safe_float(paper_metrics.get('cold_load_sec')):.4f}",
                "warm_latency_mean": f"{_safe_float(paper_metrics.get('warm_latency_mean')):.4f}",
                "warm_latency_p50": f"{_safe_float(paper_metrics.get('warm_latency_p50')):.4f}",
                "warm_latency_p95": f"{_safe_float(paper_metrics.get('warm_latency_p95')):.4f}",
                "row_success_rate": f"{_safe_float(paper_metrics.get('row_success_rate')):.4f}",
            }
        )
    return fieldnames, rows


def _build_vram_summary_rows(model_summaries: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    fieldnames = ["model_key", "model_label", "peak_vram_gb_max", "oom_count", "cold_load_sec"]
    rows: list[dict[str, Any]] = []
    for summary in model_summaries:
        paper_metrics = summary.get("paper_metrics") or {}
        rows.append(
            {
                "model_key": summary.get("model_key", ""),
                "model_label": summary.get("model_label", ""),
                "peak_vram_gb_max": f"{_safe_float(paper_metrics.get('peak_vram_gb_max')):.4f}",
                "oom_count": str(_safe_int(paper_metrics.get("oom_count"))),
                "cold_load_sec": f"{_safe_float(paper_metrics.get('cold_load_sec')):.4f}",
            }
        )
    return fieldnames, rows


def _build_tokenizer_summary_rows(model_summaries: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    fieldnames = ["model_key", "model_label", "avg_prompt_chars", "avg_prompt_tokens", "avg_completion_tokens", "avg_total_tokens", "avg_tokens_per_sec"]
    rows: list[dict[str, Any]] = []
    for summary in model_summaries:
        paper_metrics = summary.get("paper_metrics") or {}
        rows.append(
            {
                "model_key": summary.get("model_key", ""),
                "model_label": summary.get("model_label", ""),
                "avg_prompt_chars": f"{_safe_float(paper_metrics.get('avg_prompt_chars')):.4f}",
                "avg_prompt_tokens": f"{_safe_float(paper_metrics.get('avg_prompt_tokens')):.4f}",
                "avg_completion_tokens": f"{_safe_float(paper_metrics.get('avg_completion_tokens')):.4f}",
                "avg_total_tokens": f"{_safe_float(paper_metrics.get('avg_total_tokens')):.4f}",
                "avg_tokens_per_sec": f"{_safe_float(paper_metrics.get('avg_tokens_per_sec')):.4f}",
            }
        )
    return fieldnames, rows


def _build_generation_error_summary(model_summaries: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    fieldnames = ["model_key", "model_label", "generation_error_type", "count"]
    rows: list[dict[str, Any]] = []
    for summary in model_summaries:
        counter: Counter[str] = Counter()
        for row in summary.get("row_metrics") or []:
            error_type = str(row.get("generation_error_type", "") or "").strip()
            if error_type:
                counter.update([error_type])
        for error_type, count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
            rows.append(
                {
                    "model_key": str(summary.get("model_key", "")),
                    "model_label": str(summary.get("model_label", "")),
                    "generation_error_type": error_type,
                    "count": str(count),
                }
            )
    return fieldnames, rows


def _build_row_comparison_rows(model_summaries: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    by_row: dict[int, dict[str, Any]] = {}
    model_keys: list[str] = []
    for summary in model_summaries:
        model_key = str(summary["model_key"])
        model_keys.append(model_key)
        for row in summary.get("row_metrics") or []:
            row_no = int(row.get("row_no") or 0)
            entry = by_row.setdefault(
                row_no,
                {
                    "row_no": row_no,
                    "category": row.get("row_category", ""),
                    "row_category": row.get("row_category", ""),
                    "command_eng": row.get("command_eng", ""),
                    "command_kor": row.get("command_kor", ""),
                    "gt": row.get("gt", ""),
                    "warmup_excluded": row.get("warmup_excluded", False),
                },
            )
            gt_view = _parse_program_view(row.get("gt", ""))
            entry["gt_name"] = gt_view.get("name", "")
            entry["gt_cron"] = gt_view.get("cron", "")
            entry["gt_period"] = gt_view.get("period", "")
            entry["gt_code"] = gt_view.get("code", "")
            output_view = _parse_program_view(row.get("output", ""))
            entry[f"{model_key}__det_score"] = row.get("det_score", "")
            entry[f"{model_key}__det_pass"] = row.get("det_pass", "")
            entry[f"{model_key}__det_gt_exact"] = row.get("gt_exact", "")
            entry[f"{model_key}__det_gt_similarity"] = row.get("det_gt_similarity", "")
            entry[f"{model_key}__failure_reasons"] = row.get("failure_reasons_json", "")
            entry[f"{model_key}__output"] = row.get("output", "")
            entry[f"{model_key}__output_name"] = output_view.get("name", "")
            entry[f"{model_key}__output_cron"] = output_view.get("cron", "")
            entry[f"{model_key}__output_period"] = output_view.get("period", "")
            entry[f"{model_key}__output_code"] = output_view.get("code", "")
            entry[f"{model_key}__prompt_chars"] = row.get("prompt_chars", "")
            entry[f"{model_key}__prompt_tokens"] = row.get("prompt_tokens", "")
            entry[f"{model_key}__completion_tokens"] = row.get("completion_tokens", "")
            entry[f"{model_key}__total_tokens"] = row.get("total_tokens", "")
            entry[f"{model_key}__llm_latency_sec"] = row.get("llm_latency_sec", "")
            entry[f"{model_key}__total_pipeline_sec"] = row.get("total_pipeline_sec", "")
            entry[f"{model_key}__tokens_per_sec"] = row.get("tokens_per_sec", "")
            entry[f"{model_key}__peak_vram_gb"] = row.get("peak_vram_gb", "")
            entry[f"{model_key}__generation_error_type"] = row.get("generation_error_type", "")
            entry[f"{model_key}__oom_flag"] = row.get("oom_flag", "")
            entry[f"{model_key}__worker_python"] = row.get("worker_python", "")
            entry[f"{model_key}__resolved_model_path"] = row.get("resolved_model_path", "")
            entry[f"{model_key}__warmup_excluded"] = row.get("warmup_excluded", "")
            entry[f"{model_key}__row_category"] = row.get("row_category", "")
    ordered_model_keys = sorted(dict.fromkeys(model_keys))
    fieldnames = [
        "row_no",
        "category",
        "row_category",
        "command_eng",
        "command_kor",
        "gt",
        "gt_name",
        "gt_cron",
        "gt_period",
        "gt_code",
        "warmup_excluded",
    ]
    for model_key in ordered_model_keys:
        fieldnames.extend(
            [
                f"{model_key}__det_score",
                f"{model_key}__det_pass",
                f"{model_key}__det_gt_exact",
                f"{model_key}__det_gt_similarity",
                f"{model_key}__failure_reasons",
                f"{model_key}__output",
                f"{model_key}__output_name",
                f"{model_key}__output_cron",
                f"{model_key}__output_period",
                f"{model_key}__output_code",
                f"{model_key}__prompt_chars",
                f"{model_key}__prompt_tokens",
                f"{model_key}__completion_tokens",
                f"{model_key}__total_tokens",
                f"{model_key}__llm_latency_sec",
                f"{model_key}__total_pipeline_sec",
                f"{model_key}__tokens_per_sec",
                f"{model_key}__peak_vram_gb",
                f"{model_key}__generation_error_type",
                f"{model_key}__oom_flag",
                f"{model_key}__worker_python",
                f"{model_key}__resolved_model_path",
                f"{model_key}__warmup_excluded",
                f"{model_key}__row_category",
            ]
        )
    rows = [by_row[row_no] for row_no in sorted(by_row.keys())]
    return fieldnames, rows


def _run_selected_models(
    *,
    args: argparse.Namespace,
    suite_entries: list[dict[str, Any]],
    preflight_by_key: dict[str, dict[str, Any]],
    base_genome: dict[str, Any],
    rows: list[tuple[int, dict[str, str]]],
    warmup_rows: list[tuple[int, dict[str, str]]],
    service_schema: dict[str, dict[str, Any]],
    output_dir: Path,
    global_llm_extra: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    requested_workers = max(1, int(args.max_workers or 1))
    effective_workers = requested_workers
    if args.paper_fair_mode or _resolve_latency_isolation_mode(args) == "fresh_worker":
        effective_workers = 1

    def _run(index_entry: tuple[int, dict[str, Any]]) -> tuple[int, dict[str, Any]]:
        index, entry = index_entry
        model_summary = _run_single_model(
            args=args,
            entry=entry,
            runtime_info=preflight_by_key.get(entry["key"], {}),
            base_genome=base_genome,
            rows=rows,
            warmup_rows=warmup_rows,
            service_schema=service_schema,
            output_dir=output_dir,
            global_llm_extra=global_llm_extra,
        )
        model_summary["suite_index"] = index
        return index, model_summary

    if effective_workers <= 1 or len(suite_entries) <= 1:
        model_summaries: list[dict[str, Any]] = []
        for index, entry in enumerate(suite_entries):
            _index, summary = _run((index, entry))
            model_summaries.append(summary)
        return model_summaries, effective_workers

    ordered: list[dict[str, Any] | None] = [None] * len(suite_entries)
    with concurrent.futures.ThreadPoolExecutor(max_workers=effective_workers) as executor:
        futures = [executor.submit(_run, item) for item in enumerate(suite_entries)]
        for future in concurrent.futures.as_completed(futures):
            index, summary = future.result()
            ordered[index] = summary
    return [item for item in ordered if item is not None], effective_workers


def main() -> int:
    args = build_parser().parse_args()
    if args.list_categories:
        _print_available_categories(args.dataset)
        return 0
    if args.paper_fair_mode:
        args.measure_latency = True
        args.measure_vram = True
    requested_suite_entries = _resolve_suite(args)
    global_llm_extra = _parse_json_object(args.llm_extra_json) if args.llm_extra_json else {}
    preflight = [_inspect_model_runtime(entry, args=args, global_llm_extra=global_llm_extra) for entry in requested_suite_entries]
    preflight_by_key = {str(item["model_key"]): item for item in preflight}
    if args.preflight or args.preflight_only:
        _print_preflight(
            preflight,
            print_worker_info=args.print_worker_info,
            debug_runtime=args.debug_runtime,
        )
    unavailable = [item for item in preflight if item.get("status") not in {"ready"}]
    if args.preflight_only:
        return 0
    if args.strict_availability and unavailable:
        names = ", ".join(str(item["model_key"]) for item in unavailable)
        raise SystemExit(f"Unavailable models for current runtime: {names}")
    suite_entries = list(requested_suite_entries)
    skipped_models: list[dict[str, Any]] = []
    if args.skip_unavailable and unavailable:
        runnable_keys = {str(item["model_key"]) for item in preflight if item.get("status") == "ready"}
        skipped_models = [item for item in preflight if item.get("status") != "ready"]
        suite_entries = [entry for entry in requested_suite_entries if entry["key"] in runnable_keys]
        if not suite_entries:
            names = ", ".join(str(item["model_key"]) for item in unavailable)
            raise SystemExit(f"No runnable models remain after --skip-unavailable filtering: {names}")

    output_dir = _resolved_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_genome = load_genome(args.genome_json)
    service_schema = load_service_schema(args.service_schema)
    rows = _select_rows(args)
    warmup_rows = _select_warmup_rows(args, selected_rows=rows)
    category_filters = _load_category_filters(args)
    latency_isolation_mode = _resolve_latency_isolation_mode(args)

    manifest = {
        "created_at": datetime.now().isoformat(),
        "suite": args.suite,
        "requested_model_keys": [entry["key"] for entry in requested_suite_entries],
        "model_keys": [entry["key"] for entry in suite_entries],
        "genome_json": str(Path(args.genome_json).resolve()),
        "genome_id": base_genome.get("id", ""),
        "blocks": base_genome.get("blocks", []),
        "candidate_strategies": base_genome.get("params", {}).get("candidate_strategies", []),
        "candidate_k": args.candidate_k,
        "repair_threshold": args.repair_threshold,
        "repair_attempts": args.repair_attempts,
        "category_filters": category_filters,
        "limit_per_category": args.limit_per_category,
        "row_count": len(rows),
        "row_nos": [row_no for row_no, _row in rows],
        "warmup_row_count": len(warmup_rows),
        "warmup_row_nos": [row_no for row_no, _row in warmup_rows],
        "preflight": preflight,
        "skipped_models": skipped_models,
        "skip_unavailable": bool(args.skip_unavailable),
        "requested_max_workers": max(1, int(args.max_workers or 1)),
        "debug_runtime": bool(args.debug_runtime),
        "measure_latency": bool(args.measure_latency),
        "measure_vram": bool(args.measure_vram),
        "latency_isolation_mode": latency_isolation_mode,
        "paper_fair_mode": bool(args.paper_fair_mode),
        "export_paper_artifacts": bool(args.export_paper_artifacts),
    }
    model_summaries, effective_max_workers = _run_selected_models(
        args=args,
        suite_entries=suite_entries,
        preflight_by_key=preflight_by_key,
        base_genome=base_genome,
        rows=rows,
        warmup_rows=warmup_rows,
        service_schema=service_schema,
        output_dir=output_dir,
        global_llm_extra=global_llm_extra,
    )
    manifest["effective_max_workers"] = effective_max_workers
    manifest["latency_comparison_fair"] = bool(effective_max_workers == 1 and latency_isolation_mode == "fresh_worker")
    dump_json(output_dir / "suite_manifest.json", manifest)

    overall_headers = [
        "model_key",
        "model_label",
        "mode",
        "model",
        "resolved_model_path",
        "worker_python",
        "local_device",
        "local_dtype",
        "local_attn_implementation",
        "candidate_k",
        "repair_attempts",
        "genome_id",
        "latency_isolation_mode",
        "paper_fair_mode",
        "warmup_row_count",
        "row_count",
        "avg_det_score",
        "avg_gt_similarity",
        "gt_exact_count",
        "pass_count",
        "fail_count",
        "det_pass_rate",
        "gt_exact_rate",
        "warm_latency_mean",
        "warm_latency_p50",
        "warm_latency_p95",
        "cold_load_sec",
        "avg_prompt_chars",
        "paper_avg_prompt_tokens",
        "paper_avg_completion_tokens",
        "paper_avg_total_tokens",
        "avg_tokens_per_sec",
        "avg_prompt_tokens",
        "avg_completion_tokens",
        "avg_total_tokens",
        "avg_latency_sec",
        "peak_vram_gb_max",
        "oom_count",
        "generation_error_rate",
        "failure_rate",
        "row_success_rate",
        "failure_reason_topk",
    ]
    overall_rows = _build_overall_rows(model_summaries)
    atomic_write_csv(output_dir / "suite_summary.csv", overall_headers, [dict(zip(overall_headers, row)) for row in overall_rows])

    row_fieldnames, row_rows = _build_row_comparison_rows(model_summaries)
    atomic_write_csv(output_dir / "row_comparison.csv", row_fieldnames, row_rows)
    failure_headers, failure_rows = _build_failure_reason_summary(model_summaries)
    atomic_write_csv(output_dir / "failure_reason_summary.csv", failure_headers, failure_rows)
    generation_error_headers, generation_error_rows = _build_generation_error_summary(model_summaries)
    atomic_write_csv(output_dir / "generation_error_summary.csv", generation_error_headers, generation_error_rows)
    category_headers, category_rows = _build_category_summary(
        model_summaries,
        default_threshold=args.repair_threshold,
    )
    atomic_write_csv(output_dir / "category_summary.csv", category_headers, category_rows)
    atomic_write_csv(output_dir / "category_model_comparison.csv", category_headers, category_rows)

    latency_breakdown_headers, latency_breakdown_rows = _build_latency_breakdown_rows(model_summaries)
    atomic_write_csv(output_dir / "latency_breakdown.csv", latency_breakdown_headers, latency_breakdown_rows)
    main_model_headers, main_model_rows = _build_main_model_comparison_rows(model_summaries)
    atomic_write_csv(output_dir / "main_model_comparison.csv", main_model_headers, main_model_rows)
    tradeoff_headers, tradeoff_rows = _build_tradeoff_summary_rows(model_summaries)
    atomic_write_csv(output_dir / "tradeoff_summary.csv", tradeoff_headers, tradeoff_rows)
    latency_headers, latency_rows = _build_latency_summary_rows(model_summaries)
    atomic_write_csv(output_dir / "latency_summary.csv", latency_headers, latency_rows)
    vram_headers, vram_rows = _build_vram_summary_rows(model_summaries)
    atomic_write_csv(output_dir / "vram_summary.csv", vram_headers, vram_rows)
    tokenizer_headers, tokenizer_rows = _build_tokenizer_summary_rows(model_summaries)
    atomic_write_csv(output_dir / "tokenizer_summary.csv", tokenizer_headers, tokenizer_rows)

    paper_artifacts: dict[str, Any] = {
        "main_model_comparison_csv": str(output_dir / "main_model_comparison.csv"),
        "tradeoff_summary_csv": str(output_dir / "tradeoff_summary.csv"),
        "category_model_comparison_csv": str(output_dir / "category_model_comparison.csv"),
        "latency_breakdown_csv": str(output_dir / "latency_breakdown.csv"),
        "latency_summary_csv": str(output_dir / "latency_summary.csv"),
        "vram_summary_csv": str(output_dir / "vram_summary.csv"),
        "tokenizer_summary_csv": str(output_dir / "tokenizer_summary.csv"),
        "generation_error_summary_csv": str(output_dir / "generation_error_summary.csv"),
    }
    if args.export_paper_artifacts or args.paper_fair_mode:
        try:
            from scripts.export_paper_figures import export_paper_figures

            paper_artifacts["figures"] = export_paper_figures(output_dir)
        except Exception as exc:
            paper_artifacts["figure_export_error"] = str(exc)
    dump_json(output_dir / "paper_metrics_summary.json", paper_artifacts)

    summary = {
        "output_dir": str(output_dir),
        "manifest": manifest,
        "models": model_summaries,
        "suite_summary_csv": str(output_dir / "suite_summary.csv"),
        "row_comparison_csv": str(output_dir / "row_comparison.csv"),
        "failure_reason_summary_csv": str(output_dir / "failure_reason_summary.csv"),
        "generation_error_summary_csv": str(output_dir / "generation_error_summary.csv"),
        "category_summary_csv": str(output_dir / "category_summary.csv"),
        "category_model_comparison_csv": str(output_dir / "category_model_comparison.csv"),
        "latency_breakdown_csv": str(output_dir / "latency_breakdown.csv"),
        "main_model_comparison_csv": str(output_dir / "main_model_comparison.csv"),
        "tradeoff_summary_csv": str(output_dir / "tradeoff_summary.csv"),
        "latency_summary_csv": str(output_dir / "latency_summary.csv"),
        "vram_summary_csv": str(output_dir / "vram_summary.csv"),
        "tokenizer_summary_csv": str(output_dir / "tokenizer_summary.csv"),
        "paper_metrics_summary_json": str(output_dir / "paper_metrics_summary.json"),
        "paper_artifacts": paper_artifacts,
    }
    dump_json(output_dir / "suite_summary.json", summary)

    if args.print_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.print_mode == "compare":
        _print_row_comparisons(summary, row_rows, print_limit=args.print_limit)
    elif args.print_mode == "summary":
        _print_suite_summary(summary)
    else:
        _print_paths_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
