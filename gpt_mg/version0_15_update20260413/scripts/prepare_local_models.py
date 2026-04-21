#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from scripts.run_model_suite_benchmark import (
    MODEL_SUITES,
    _inspect_model_runtime,
)
from utils.local_llm_client import DEFAULT_WORKER_PYTHON, describe_worker_runtime
from utils.pipeline_common import RESULTS_DIR, atomic_write_csv, dump_json


BENCHMARK_SCRIPT = VERSION_ROOT / "scripts" / "run_model_suite_benchmark.py"
DEFAULT_GENOME_JSON = VERSION_ROOT / "results" / "best_genome.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare Hugging Face cache snapshots and worker smoke checks for the paper local model suite."
    )
    parser.add_argument(
        "--suite",
        choices=sorted(MODEL_SUITES.keys()),
        default="paper_local5",
        help="Model suite to prepare. Default: paper_local5",
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
        help="Genome used for one-row smoke tests.",
    )
    parser.add_argument(
        "--download-missing",
        action="store_true",
        help="Attempt Hugging Face downloads for missing public models.",
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Do not run one-row smoke tests after preflight/download.",
    )
    parser.add_argument(
        "--smoke-row",
        type=int,
        default=1,
        help="Dataset row number used for smoke tests. Default: 1",
    )
    parser.add_argument("--candidate-k", type=int, default=1)
    parser.add_argument("--repair-attempts", type=int, default=0)
    parser.add_argument("--llm-mode", default=None)
    parser.add_argument("--llm-endpoint", default=None)
    parser.add_argument(
        "--llm-extra-json",
        default="",
        help="Inline JSON or file path for extra worker/http payload fields applied to every model.",
    )
    parser.add_argument(
        "--worker-python",
        default="",
        help="Optional explicit worker python override. Default: auto-detected worker python.",
    )
    parser.add_argument(
        "--huggingface-cli",
        default="huggingface-cli",
        help="Hugging Face CLI executable used for downloads. Default: huggingface-cli",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Optional output directory. Default: results/model_prep_<timestamp>",
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
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise SystemExit("Expected a JSON object payload for --llm-extra-json.")
    return parsed


def _resolved_output_dir(raw: str) -> Path:
    if raw:
        path = Path(raw)
        if not path.is_absolute():
            path = (VERSION_ROOT / raw).resolve()
        return path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return RESULTS_DIR / f"model_prep_{timestamp}"


def _resolve_suite_entries(args: argparse.Namespace) -> list[dict[str, Any]]:
    selected = MODEL_SUITES[args.suite]
    if not args.model_key:
        return [dict(item) for item in selected]
    wanted = {str(item).strip() for item in args.model_key if str(item).strip()}
    resolved = [dict(item) for item in selected if item["key"] in wanted]
    if not resolved:
        raise SystemExit(f"No suite entries matched --model-key values: {sorted(wanted)}")
    return resolved


def _inspect(entry: dict[str, Any], *, args: argparse.Namespace, global_llm_extra: dict[str, Any]) -> dict[str, Any]:
    runtime_args = argparse.Namespace(
        llm_mode=args.llm_mode,
        llm_endpoint=args.llm_endpoint,
    )
    return _inspect_model_runtime(entry, args=runtime_args, global_llm_extra=global_llm_extra)


def _run_download(model_name: str, cli_name: str) -> dict[str, Any]:
    completed = subprocess.run(
        [cli_name, "download", model_name],
        text=True,
        capture_output=True,
        check=False,
    )
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    combined = f"{stdout}\n{stderr}".strip().lower()
    result = {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "snapshot_path": stdout.splitlines()[-1].strip() if stdout.splitlines() else "",
        "status": "downloaded" if completed.returncode == 0 else "failed",
        "reason": "",
    }
    if completed.returncode == 0:
        return result
    if "gated" in combined or "401" in combined or "access to model" in combined:
        result["status"] = "gated"
        result["reason"] = stderr or stdout or "gated repository"
        return result
    if "not logged in" in combined or "authentication" in combined:
        result["status"] = "auth_required"
        result["reason"] = stderr or stdout or "authentication required"
        return result
    result["reason"] = stderr or stdout or f"download failed with exit code {completed.returncode}"
    return result


def _run_smoke(
    entry: dict[str, Any],
    *,
    args: argparse.Namespace,
    env: dict[str, str],
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(BENCHMARK_SCRIPT),
        "--suite",
        args.suite,
        "--model-key",
        str(entry["key"]),
        "--genome-json",
        str(Path(args.genome_json).resolve()),
        "--row-no",
        str(int(args.smoke_row)),
        "--candidate-k",
        str(int(args.candidate_k)),
        "--repair-attempts",
        str(int(args.repair_attempts)),
        "--strict-availability",
        "--print-json",
        "--debug-runtime",
    ]
    if args.llm_mode:
        command.extend(["--llm-mode", str(args.llm_mode)])
    if args.llm_endpoint:
        command.extend(["--llm-endpoint", str(args.llm_endpoint)])
    if args.llm_extra_json:
        command.extend(["--llm-extra-json", _read_inline_or_file(args.llm_extra_json)])
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if completed.returncode != 0:
        return {
            "ok": False,
            "status": "failed",
            "reason": stderr or stdout or f"smoke test failed with exit code {completed.returncode}",
            "stdout": stdout,
            "stderr": stderr,
        }
    try:
        payload = json.loads(stdout)
    except Exception as exc:
        return {
            "ok": False,
            "status": "failed",
            "reason": f"failed to parse benchmark JSON: {exc}",
            "stdout": stdout,
            "stderr": stderr,
        }
    model_summaries = payload.get("models") or []
    model_summary = model_summaries[0] if model_summaries else {}
    usage = model_summary.get("usage") or {}
    metrics = model_summary.get("metrics") or {}
    errors = usage.get("top_errors") or []
    return {
        "ok": int(usage.get("error_count") or 0) == 0,
        "status": "ok" if int(usage.get("error_count") or 0) == 0 else "runtime_error",
        "reason": "" if int(usage.get("error_count") or 0) == 0 else str(errors[0][0]),
        "summary": payload,
        "output_dir": payload.get("output_dir", ""),
        "avg_det_score": metrics.get("avg_det_score", 0.0),
        "stdout": stdout,
        "stderr": stderr,
    }


def _final_preparation_status(runtime: dict[str, Any], smoke: dict[str, Any] | None, download: dict[str, Any] | None) -> tuple[str, str]:
    status = str(runtime.get("status", "unknown"))
    if download and download.get("status") in {"gated", "auth_required"}:
        return download["status"], str(download.get("reason", ""))
    if status == "worker_env_broken":
        return "runtime_broken", str(runtime.get("message", ""))
    if smoke:
        if smoke.get("ok"):
            return "ready_and_smoke_tested", ""
        return "runtime_broken", str(smoke.get("reason", ""))
    if status == "ready":
        return "ready_not_smoke_tested", str(runtime.get("message", ""))
    if status == "missing_cache":
        return "missing_cache", str(runtime.get("message", ""))
    if status == "incomplete_cache":
        return "incomplete_cache", str(runtime.get("message", ""))
    if status == "download_required":
        return "download_required", str(runtime.get("message", ""))
    return status, str(runtime.get("message", ""))


def _write_text_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Local Model Preparation Report",
        "",
        f"- created_at: {summary['created_at']}",
        f"- suite: {summary['suite']}",
        f"- worker_python: {summary['worker_runtime'].get('python_path', '')}",
        f"- torch: {summary['worker_runtime'].get('torch_version', '')}",
        f"- transformers: {summary['worker_runtime'].get('transformers_version', '')}",
        f"- cuda_available: {summary['worker_runtime'].get('cuda_available', False)}",
        f"- cuda_devices: {', '.join(summary['worker_runtime'].get('cuda_devices', [])) if summary['worker_runtime'].get('cuda_devices') else '-'}",
        "",
        "## Models",
    ]
    for item in summary["models"]:
        lines.extend(
            [
                f"- {item['model_key']} ({item['model_label']}): {item['preparation_status']}",
                f"  configured_model: {item['configured_model']}",
                f"  resolved_model_path: {item['resolved_model_path']}",
                f"  cache_path: {item['cache_path']}",
                f"  snapshot_count: {item['snapshot_count']}",
                f"  smoke_output_dir: {item['smoke_output_dir'] or '-'}",
                f"  note: {item['note'] or '-'}",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()
    global_llm_extra = _parse_json_object(args.llm_extra_json) if args.llm_extra_json else {}
    output_dir = _resolved_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    suite_entries = _resolve_suite_entries(args)

    worker_python = str(args.worker_python or DEFAULT_WORKER_PYTHON)
    env = os.environ.copy()
    env["JOI_V15_WORKER_PYTHON"] = worker_python

    prepared_rows: list[dict[str, Any]] = []
    for entry in suite_entries:
        runtime_before = _inspect(entry, args=args, global_llm_extra=global_llm_extra)
        download_result: dict[str, Any] | None = None
        runtime_after = runtime_before
        if (
            args.download_missing
            and runtime_before.get("mode") == "worker"
            and runtime_before.get("status") in {"missing_cache", "download_required", "incomplete_cache"}
            and "/" in str(entry.get("model", ""))
        ):
            download_result = _run_download(str(entry["model"]), args.huggingface_cli)
            runtime_after = _inspect(entry, args=args, global_llm_extra=global_llm_extra)

        smoke_result: dict[str, Any] | None = None
        if not args.skip_smoke and runtime_after.get("status") == "ready":
            smoke_result = _run_smoke(entry, args=args, env=env)

        preparation_status, note = _final_preparation_status(runtime_after, smoke_result, download_result)
        prepared_rows.append(
            {
                "model_key": str(entry["key"]),
                "model_label": str(entry["label"]),
                "configured_model": str(entry["model"]),
                "mode": str(runtime_after.get("mode", "")),
                "status_before": str(runtime_before.get("status", "")),
                "status_after": str(runtime_after.get("status", "")),
                "preparation_status": preparation_status,
                "download_status": str(download_result.get("status", "")) if download_result else "",
                "downloaded_now": bool(download_result and download_result.get("ok")),
                "resolved_model_path": str(runtime_after.get("resolved_local_model_name", "")),
                "cache_path": str(runtime_after.get("cache_path", "")),
                "snapshot_count": int(runtime_after.get("snapshot_count", 0) or 0),
                "worker_python": str(runtime_after.get("worker_python", worker_python)),
                "worker_path": str(runtime_after.get("worker_path", "")),
                "local_device": str(runtime_after.get("local_device", "")),
                "local_dtype": str(runtime_after.get("local_dtype", "")),
                "local_load_in_4bit": bool(runtime_after.get("local_load_in_4bit", False)),
                "local_files_only": bool(runtime_after.get("local_files_only", False)),
                "smoke_status": str(smoke_result.get("status", "")) if smoke_result else "",
                "smoke_output_dir": str(smoke_result.get("output_dir", "")) if smoke_result else "",
                "smoke_avg_det_score": smoke_result.get("avg_det_score", 0.0) if smoke_result else 0.0,
                "note": note or str(runtime_after.get("message", "")),
                "runtime_before": runtime_before,
                "runtime_after": runtime_after,
                "download_result": download_result,
                "smoke_result": smoke_result,
            }
        )

    summary = {
        "created_at": datetime.now().isoformat(),
        "suite": args.suite,
        "genome_json": str(Path(args.genome_json).resolve()),
        "worker_runtime": describe_worker_runtime(worker_python),
        "models": prepared_rows,
        "ready_models": [row["model_key"] for row in prepared_rows if row["preparation_status"] == "ready_and_smoke_tested"],
        "ready_without_smoke": [row["model_key"] for row in prepared_rows if row["preparation_status"] == "ready_not_smoke_tested"],
        "downloaded_now": [row["model_key"] for row in prepared_rows if row["downloaded_now"]],
        "blocked_models": [
            {"model_key": row["model_key"], "status": row["preparation_status"], "note": row["note"]}
            for row in prepared_rows
            if row["preparation_status"] not in {"ready_and_smoke_tested", "ready_not_smoke_tested"}
        ],
        "output_dir": str(output_dir),
    }
    dump_json(output_dir / "model_readiness.json", summary)

    csv_headers = [
        "model_key",
        "model_label",
        "configured_model",
        "mode",
        "status_before",
        "status_after",
        "preparation_status",
        "download_status",
        "downloaded_now",
        "resolved_model_path",
        "cache_path",
        "snapshot_count",
        "worker_python",
        "worker_path",
        "local_device",
        "local_dtype",
        "local_load_in_4bit",
        "local_files_only",
        "smoke_status",
        "smoke_output_dir",
        "smoke_avg_det_score",
        "note",
    ]
    atomic_write_csv(
        output_dir / "model_readiness.csv",
        csv_headers,
        [{key: row.get(key, "") for key in csv_headers} for row in prepared_rows],
    )
    _write_text_report(output_dir / "model_readiness.txt", summary)

    if args.print_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            json.dumps(
                {
                    "output_dir": str(output_dir),
                    "model_readiness_json": str(output_dir / "model_readiness.json"),
                    "model_readiness_csv": str(output_dir / "model_readiness.csv"),
                    "model_readiness_txt": str(output_dir / "model_readiness.txt"),
                    "ready_models": summary["ready_models"],
                    "downloaded_now": summary["downloaded_now"],
                    "blocked_models": summary["blocked_models"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
