#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import concurrent.futures
import json
import os
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
from utils.local_llm_client import describe_worker_runtime
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
    parser.add_argument("--start-row", type=int, default=1)
    parser.add_argument("--end-row", type=int, default=None)
    parser.add_argument("--category", action="append", default=[], help="Optional category filter. Can be repeated.")
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
        error_suffix = ""
        if int(usage.get("error_count") or 0) > 0:
            error_suffix = f", gen_errors={usage['error_count']}"
        print(
            " - "
            f"{model_summary['model_key']} ({model_summary['model_label']}): "
            f"avg_det={metrics['avg_det_score']:.4f}, "
            f"gt_exact={metrics['gt_exact_count']}/{metrics['row_count']}, "
            f"pass={metrics['pass_count']}/{metrics['row_count']}, "
            f"avg_latency={usage['avg_latency_sec']:.4f}s"
            f"{error_suffix}"
        )
        if usage.get("top_errors"):
            first_error = str(usage["top_errors"][0][0]).splitlines()[0]
            print(f"   top_generation_error: {first_error}")
    print(f"Suite summary CSV: {summary['suite_summary_csv']}")
    print(f"Row comparison CSV: {summary['row_comparison_csv']}")
    print(f"Failure reason CSV: {summary.get('failure_reason_summary_csv', '')}")
    print(f"Category summary CSV: {summary.get('category_summary_csv', '')}")


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
            det_exact = str(row.get(f"{model_key}__det_gt_exact", "") or "False")
            det_similarity = str(row.get(f"{model_key}__det_gt_similarity", "") or "0")
            failure_reasons_raw = str(row.get(f"{model_key}__failure_reasons", "") or "")
            failures = _pretty_json_list(failure_reasons_raw)
            output_view = _parse_program_view(row.get(f"{model_key}__output", ""))
            output_period = str(output_view.get("period", "") or "0")
            print("")
            print(
                f"[{model_key}] {model_summary['model_label']} | "
                f"det={det_score} | exact={det_exact} | sim={det_similarity}"
            )
            print(f"Generated schedule: cron=\"{output_view.get('cron', '')}\" period={output_period}")
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
    rows = load_dataset_rows(args.dataset)
    selected = select_rows(
        rows,
        start_row=args.start_row,
        end_row=args.end_row,
        limit=args.limit,
        categories=args.category,
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
        raise SystemExit("No dataset rows selected. Check --row-no/--query/--limit/--category.")
    return selected


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
    llm_extra_payload = _merge_llm_extra(entry, global_llm_extra)

    label = slugify(entry["key"])
    candidates_csv = output_dir / f"{label}_candidates.csv"
    rerank_csv = output_dir / f"{label}_rerank.csv"
    run_id = f"suite_{label}_{slugify(genome.get('id', 'genome'))}_{args.seed}"

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
    metrics = _summarize_rerank_rows(rerank_rows, default_threshold=args.repair_threshold)
    usage = _summarize_generation_usage(generation["rows"])

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
        "generation": generation,
        "rerank": rerank,
        "metrics": metrics,
        "usage": usage,
    }
    dump_json(output_dir / f"{label}_summary.json", summary)
    return summary


def _build_overall_rows(model_summaries: list[dict[str, Any]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for summary in model_summaries:
        metrics = summary["metrics"]
        usage = summary["usage"]
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
                str(metrics["row_count"]),
                f"{metrics['avg_det_score']:.4f}",
                f"{metrics['avg_gt_similarity']:.4f}",
                str(metrics["gt_exact_count"]),
                str(metrics["pass_count"]),
                str(metrics["fail_count"]),
                f"{usage['avg_prompt_tokens']:.4f}",
                f"{usage['avg_completion_tokens']:.4f}",
                f"{usage['avg_total_tokens']:.4f}",
                f"{usage['avg_latency_sec']:.4f}",
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
        by_category: dict[str, list[dict[str, str]]] = {}
        rerank_csv = Path(summary["rerank"]["output_csv"])
        for row in read_csv_rows(rerank_csv):
            by_category.setdefault(str(row.get("category", "")), []).append(row)
        for category in sorted(by_category.keys()):
            category_rows = by_category[category]
            metrics = _summarize_rerank_rows(category_rows, default_threshold=default_threshold)
            counter: Counter[str] = Counter()
            for row in category_rows:
                counter.update(_load_failure_reasons(row))
            rows.append(
                {
                    "model_key": str(summary["model_key"]),
                    "model_label": str(summary["model_label"]),
                    "category": category,
                    "row_count": str(metrics["row_count"]),
                    "avg_det_score": f"{metrics['avg_det_score']:.4f}",
                    "avg_gt_similarity": f"{metrics['avg_gt_similarity']:.4f}",
                    "gt_exact_count": str(metrics["gt_exact_count"]),
                    "pass_count": str(metrics["pass_count"]),
                    "fail_count": str(metrics["fail_count"]),
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
            "pass_count",
            "fail_count",
            "top_failure_types",
        ],
        rows,
    )


def _build_row_comparison_rows(model_summaries: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    by_row: dict[int, dict[str, Any]] = {}
    model_keys: list[str] = []
    for summary in model_summaries:
        model_key = str(summary["model_key"])
        model_keys.append(model_key)
        rerank_csv = Path(summary["rerank"]["output_csv"])
        for row in read_csv_rows(rerank_csv):
            row_no = int(row.get("row_no") or 0)
            entry = by_row.setdefault(
                row_no,
                {
                    "row_no": row_no,
                    "category": row.get("category", ""),
                    "command_eng": row.get("command_eng", ""),
                    "command_kor": row.get("command_kor", ""),
                    "gt": row.get("gt", ""),
                },
            )
            gt_view = _parse_program_view(row.get("gt", ""))
            entry["gt_name"] = gt_view.get("name", "")
            entry["gt_cron"] = gt_view.get("cron", "")
            entry["gt_period"] = gt_view.get("period", "")
            entry["gt_code"] = gt_view.get("code", "")
            output_view = _parse_program_view(row.get("output", ""))
            entry[f"{model_key}__det_score"] = row.get("det_score", "")
            entry[f"{model_key}__det_gt_exact"] = row.get("det_gt_exact", "")
            entry[f"{model_key}__det_gt_similarity"] = row.get("det_gt_similarity", "")
            entry[f"{model_key}__failure_reasons"] = row.get("det_failure_reasons", "")
            entry[f"{model_key}__output"] = row.get("output", "")
            entry[f"{model_key}__output_name"] = output_view.get("name", "")
            entry[f"{model_key}__output_cron"] = output_view.get("cron", "")
            entry[f"{model_key}__output_period"] = output_view.get("period", "")
            entry[f"{model_key}__output_code"] = output_view.get("code", "")
    ordered_model_keys = sorted(dict.fromkeys(model_keys))
    fieldnames = ["row_no", "category", "command_eng", "command_kor", "gt", "gt_name", "gt_cron", "gt_period", "gt_code"]
    for model_key in ordered_model_keys:
        fieldnames.extend(
            [
                f"{model_key}__det_score",
                f"{model_key}__det_gt_exact",
                f"{model_key}__det_gt_similarity",
                f"{model_key}__failure_reasons",
                f"{model_key}__output",
                f"{model_key}__output_name",
                f"{model_key}__output_cron",
                f"{model_key}__output_period",
                f"{model_key}__output_code",
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
    service_schema: dict[str, dict[str, Any]],
    output_dir: Path,
    global_llm_extra: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    requested_workers = max(1, int(args.max_workers or 1))
    effective_workers = requested_workers
    if requested_workers > 1 and any((_suite_mode(entry, args) or "worker") == "worker" for entry in suite_entries):
        effective_workers = 1

    def _run(index_entry: tuple[int, dict[str, Any]]) -> tuple[int, dict[str, Any]]:
        index, entry = index_entry
        model_summary = _run_single_model(
            args=args,
            entry=entry,
            runtime_info=preflight_by_key.get(entry["key"], {}),
            base_genome=base_genome,
            rows=rows,
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
        "row_count": len(rows),
        "row_nos": [row_no for row_no, _row in rows],
        "preflight": preflight,
        "skipped_models": skipped_models,
        "skip_unavailable": bool(args.skip_unavailable),
        "requested_max_workers": max(1, int(args.max_workers or 1)),
        "debug_runtime": bool(args.debug_runtime),
    }
    model_summaries, effective_max_workers = _run_selected_models(
        args=args,
        suite_entries=suite_entries,
        preflight_by_key=preflight_by_key,
        base_genome=base_genome,
        rows=rows,
        service_schema=service_schema,
        output_dir=output_dir,
        global_llm_extra=global_llm_extra,
    )
    manifest["effective_max_workers"] = effective_max_workers
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
        "row_count",
        "avg_det_score",
        "avg_gt_similarity",
        "gt_exact_count",
        "pass_count",
        "fail_count",
        "avg_prompt_tokens",
        "avg_completion_tokens",
        "avg_total_tokens",
        "avg_latency_sec",
    ]
    overall_rows = _build_overall_rows(model_summaries)
    atomic_write_csv(output_dir / "suite_summary.csv", overall_headers, [dict(zip(overall_headers, row)) for row in overall_rows])

    row_fieldnames, row_rows = _build_row_comparison_rows(model_summaries)
    atomic_write_csv(output_dir / "row_comparison.csv", row_fieldnames, row_rows)
    failure_headers, failure_rows = _build_failure_reason_summary(model_summaries)
    atomic_write_csv(output_dir / "failure_reason_summary.csv", failure_headers, failure_rows)
    category_headers, category_rows = _build_category_summary(
        model_summaries,
        default_threshold=args.repair_threshold,
    )
    atomic_write_csv(output_dir / "category_summary.csv", category_headers, category_rows)

    summary = {
        "output_dir": str(output_dir),
        "manifest": manifest,
        "models": model_summaries,
        "suite_summary_csv": str(output_dir / "suite_summary.csv"),
        "row_comparison_csv": str(output_dir / "row_comparison.csv"),
        "failure_reason_summary_csv": str(output_dir / "failure_reason_summary.csv"),
        "category_summary_csv": str(output_dir / "category_summary.csv"),
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
