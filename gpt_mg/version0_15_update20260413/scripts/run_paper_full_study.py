#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from scripts.run_model_suite_benchmark import PAPER_LOCAL5_SUITE, _inspect_model_runtime
from utils.pipeline_common import RESULTS_DIR, atomic_write_csv, dump_json


DEFAULT_PROMPT_ASSETS_DIR = VERSION_ROOT.parent / "version0_13"
LOCAL_MODEL_KEYS = [entry["key"] for entry in PAPER_LOCAL5_SUITE]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run or schedule the final paper study pipeline for GPS/PromptOps experiments."
    )
    parser.add_argument("--suite", default="paper_local5")
    parser.add_argument("--include-cloud-ref", action="store_true")
    parser.add_argument("--models", action="append", default=[], help="Comma-separated or repeated model keys.")
    parser.add_argument("--categories", action="append", default=[], help="Comma-separated or repeated dataset categories.")
    parser.add_argument("--limit-per-category", type=int, default=None)
    parser.add_argument("--paper-fair-mode", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--quiet-final-summary", action="store_true")
    parser.add_argument("--progress", choices=["quiet", "minimal", "verbose"], default="minimal")
    parser.add_argument("--strict-availability", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--full-run", action="store_true")
    parser.add_argument("--output-root", default="")
    parser.add_argument("--prompt-assets-dir", default=str(DEFAULT_PROMPT_ASSETS_DIR))
    parser.add_argument("--retrieval-device", default="cpu")
    parser.add_argument("--retrieval-topk", type=int, default=10)
    parser.add_argument("--retrieval-mode", choices=["hybrid", "dense", "bm25"], default="hybrid")
    parser.add_argument("--candidate-k", type=int, default=1)
    parser.add_argument("--repair-attempts", type=int, default=0)
    parser.add_argument("--det-profile", choices=["legacy", "strict"], default="strict")
    parser.add_argument("--ga-population", type=int, default=4)
    parser.add_argument("--ga-gens", type=int, default=3)
    parser.add_argument("--ga-sample-size", type=int, default=4)
    parser.add_argument("--ga-validation-size", type=int, default=4)
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--llm-mode", default="")
    parser.add_argument("--llm-endpoint", default="")
    return parser


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _parse_multi(values: list[str]) -> list[str]:
    parsed: list[str] = []
    for value in values:
        for part in str(value).split(","):
            token = part.strip()
            if token:
                parsed.append(token)
    return parsed


def _study_root(args: argparse.Namespace) -> Path:
    if args.output_root:
        return Path(args.output_root).expanduser().resolve()
    return (RESULTS_DIR / f"paper_study_{_timestamp()}").resolve()


def _stage_path(root: Path, name: str) -> Path:
    return root / "stage_status" / f"{name}.json"


def _stage_completed(root: Path, name: str) -> bool:
    path = _stage_path(root, name)
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("status") == "pass"
    except Exception:
        return False


def _write_stage(
    root: Path,
    name: str,
    *,
    status: str,
    model_key: str,
    command: list[str] | None = None,
    output_paths: dict[str, str] | None = None,
    error_summary: str = "",
    start_time: str | None = None,
    end_time: str | None = None,
) -> None:
    payload = {
        "stage_name": name,
        "status": status,
        "start_time": start_time or datetime.now().isoformat(timespec="seconds"),
        "end_time": end_time or datetime.now().isoformat(timespec="seconds"),
        "model_key": model_key,
        "command": " ".join(command or []),
        "output_paths": output_paths or {},
        "error_summary": error_summary,
    }
    dump_json(_stage_path(root, name), payload)


def _run(command: list[str], *, quiet: bool) -> int:
    if quiet:
        proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        if proc.returncode != 0:
            sys.stderr.write(proc.stdout[-4000:])
        return int(proc.returncode)
    return int(subprocess.run(command, check=False).returncode)


def _selection_args(args: argparse.Namespace, categories: list[str]) -> list[str]:
    cli: list[str] = []
    for category in categories:
        cli += ["--category", str(category)]
    if args.limit_per_category is not None:
        cli += ["--limit-per-category", str(args.limit_per_category)]
    return cli


def _model_entries(model_keys: list[str]) -> list[dict[str, Any]]:
    wanted = set(model_keys or LOCAL_MODEL_KEYS)
    entries = [entry for entry in PAPER_LOCAL5_SUITE if entry["key"] in wanted]
    missing = sorted(wanted - {entry["key"] for entry in entries})
    if missing:
        raise SystemExit(f"Unknown model keys: {missing}. Available: {LOCAL_MODEL_KEYS}")
    return [json.loads(json.dumps(entry)) for entry in entries]


def _availability(args: argparse.Namespace, root: Path, entries: list[dict[str, Any]]) -> dict[str, str]:
    rows: list[dict[str, Any]] = []
    now = datetime.now().isoformat(timespec="seconds")
    inspect_args = argparse.Namespace(llm_mode=args.llm_mode or None, llm_endpoint=args.llm_endpoint or None)
    for entry in entries:
        if args.dry_run:
            runtime = {
                "status": "skipped",
                "message": "dry-run only",
                "cache_path": "",
                "model_label": entry.get("label", entry["key"]),
            }
        else:
            runtime = _inspect_model_runtime(entry, args=inspect_args, global_llm_extra={})
        status = runtime.get("status", "")
        paper_status = "runnable" if status == "ready" else ("skipped" if status == "skipped" else "blocked")
        rows.append(
            {
                "model_key": entry["key"],
                "model_name": entry.get("label", entry["key"]),
                "status": paper_status,
                "reason": runtime.get("message", status),
                "cache_path": runtime.get("cache_path", ""),
                "gated_access_required": str(entry["key"] in {"llama31_8b", "gemma2_9b_it"} and paper_status != "runnable"),
                "oom_observed": "false",
                "runtime_notes": json.dumps(runtime, ensure_ascii=False),
                "tested_command": "preflight via run_paper_full_study.py",
                "timestamp": now,
            }
        )
    headers = [
        "model_key",
        "model_name",
        "status",
        "reason",
        "cache_path",
        "gated_access_required",
        "oom_observed",
        "runtime_notes",
        "tested_command",
        "timestamp",
    ]
    atomic_write_csv(root / "availability_summary.csv", headers, rows)
    dump_json(root / "availability_summary.json", {"rows": rows})
    return {"csv": str(root / "availability_summary.csv"), "json": str(root / "availability_summary.json")}


def _write_command(root: Path, name: str, command: list[str]) -> Path:
    path = root / "commands" / f"{name}.sh"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + " ".join(command) + "\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def _benchmark_command(
    args: argparse.Namespace,
    *,
    root: Path,
    stage: str,
    models: list[str],
    categories: list[str],
    prompt_render_mode: str,
) -> list[str]:
    output_dir = root / stage
    cli = [
        sys.executable,
        str(VERSION_ROOT / "scripts" / "run_benchmark.py"),
        "--suite",
        args.suite,
        "--candidate-k",
        str(args.candidate_k),
        "--repair-attempts",
        str(args.repair_attempts),
        "--det-profile",
        args.det_profile,
        "--prompt-render-mode",
        prompt_render_mode,
        "--prompt-assets-dir",
        str(Path(args.prompt_assets_dir).expanduser().resolve()),
        "--enable-retrieval-premapping",
        "--retrieval-topk",
        str(args.retrieval_topk),
        "--retrieval-mode",
        args.retrieval_mode,
        "--retrieval-device",
        args.retrieval_device,
        "--timeout-sec",
        str(args.timeout_sec),
        "--output-dir",
        str(output_dir),
        "--print-mode",
        "paths",
        "--skip-unavailable",
    ]
    if args.paper_fair_mode:
        cli += ["--paper-fair-mode", "--export-paper-artifacts"]
    if args.strict_availability:
        cli += ["--strict-availability"]
    for model in models:
        cli += ["--model-key", model]
    return cli + _selection_args(args, categories)


def _ga_command(args: argparse.Namespace, *, root: Path, models: list[str], categories: list[str]) -> list[str]:
    cli = [
        sys.executable,
        str(VERSION_ROOT / "scripts" / "run_local_prompt_ga_study.py"),
        "--output-root",
        str(root / "B6_full_gps_ga"),
        "--prompt-assets-dir",
        str(Path(args.prompt_assets_dir).expanduser().resolve()),
        "--population",
        str(args.ga_population),
        "--gens",
        str(args.ga_gens),
        "--sample-size",
        str(args.ga_sample_size),
        "--validation-size",
        str(args.ga_validation_size),
        "--candidate-k",
        str(args.candidate_k),
        "--det-profile",
        args.det_profile,
        "--service-context-mode",
        "retrieval_fallback",
        "--retrieval-topk",
        str(args.retrieval_topk),
        "--retrieval-mode",
        args.retrieval_mode,
        "--retrieval-device",
        args.retrieval_device,
        "--timeout-sec",
        str(args.timeout_sec),
    ]
    if args.strict_availability:
        cli += ["--strict-availability"]
    else:
        cli += ["--skip-unavailable"]
    for model in models:
        cli += ["--model-key", model]
    for category in categories:
        cli += ["--category", category]
    if args.limit_per_category is not None:
        cli += ["--limit-per-category", str(args.limit_per_category)]
    return cli


def _cloud_equivalence_command(args: argparse.Namespace, *, root: Path, categories: list[str]) -> list[str]:
    cli = [
        sys.executable,
        str(VERSION_ROOT / "scripts" / "run_cloud_blocks_equivalence.py"),
        "--output-dir",
        str(root / "cloud_to_blocks_equivalence"),
        "--candidate-k",
        str(args.candidate_k),
        "--repair-attempts",
        str(args.repair_attempts),
        "--det-profile",
        args.det_profile,
        "--prompt-assets-dir",
        str(Path(args.prompt_assets_dir).expanduser().resolve()),
        "--service-context-mode",
        "retrieval_fallback",
        "--retrieval-topk",
        str(args.retrieval_topk),
        "--retrieval-mode",
        args.retrieval_mode,
        "--retrieval-device",
        args.retrieval_device,
        "--quiet-final-summary",
    ]
    if args.llm_endpoint:
        cli += ["--llm-endpoint", args.llm_endpoint]
    if args.dry_run:
        cli += ["--dry-run"]
    return cli + _selection_args(args, categories)


def _export_command(args: argparse.Namespace, *, root: Path, availability: dict[str, str]) -> list[str]:
    cli = [
        sys.executable,
        str(VERSION_ROOT / "scripts" / "export_paper_final_artifacts.py"),
        "--study-root",
        str(root),
        "--suite",
        args.suite,
        "--availability-csv",
        availability["csv"],
        "--availability-json",
        availability["json"],
        "--cloud-equivalence-dir",
        str(root / "cloud_to_blocks_equivalence"),
        "--ga-study-dir",
        str(root / "B6_full_gps_ga"),
        "--command-used",
        " ".join(sys.argv),
        "--quiet-final-summary",
        "--result-dir",
        f"B2={root / 'B2_direct_cloud_to_local'}",
        "--result-dir",
        f"B3={root / 'B3_fixed_block'}",
        "--result-dir",
        f"B6={root / 'B6_full_gps_eval'}",
    ]
    if args.include_cloud_ref:
        cli += ["--result-dir", f"B1={root / 'B1_cloud_reference'}"]
    return cli


def _write_final_manifest_alias(root: Path) -> None:
    paper_manifest = root / "paper" / "final_artifacts_manifest.json"
    if not paper_manifest.exists():
        return
    payload = json.loads(paper_manifest.read_text(encoding="utf-8"))
    dump_json(root / "paper" / "final_artifacts_manifest.json", payload)


def main() -> int:
    args = build_parser().parse_args()
    if not args.full_run and not args.smoke and not args.dry_run:
        args.smoke = True
    root = _study_root(args)
    root.mkdir(parents=True, exist_ok=True)

    models = _parse_multi(args.models) or LOCAL_MODEL_KEYS
    categories = _parse_multi(args.categories)
    if args.smoke:
        models = models or ["qwen25_coder_7b"]
        categories = categories or ["1"]
        if args.limit_per_category is None:
            args.limit_per_category = 1
        if not _parse_multi(args.models):
            models = ["qwen25_coder_7b"]
    entries = _model_entries(models)
    model_label = ",".join(models)
    if args.progress != "quiet":
        print("[RUN]")
        print(f"command={' '.join(sys.argv)}")
        print(f"model={model_label}")
        print(f"suite={args.suite}")
        print(f"categories={','.join(categories) if categories else 'all'}")
        print(f"limit_per_category={args.limit_per_category if args.limit_per_category is not None else 'N/A'}")
        print(f"output_root={root}")

    availability = _availability(args, root, entries)
    _write_stage(root, "preflight", status="pass", model_key=model_label, output_paths=availability)

    planned: dict[str, str] = {}
    stages: list[tuple[str, list[str], bool]] = []
    if args.include_cloud_ref:
        stages.append(("cloud_to_blocks_equivalence", _cloud_equivalence_command(args, root=root, categories=categories), True))
    stages.append(("B2_direct_cloud_to_local", _benchmark_command(args, root=root, stage="B2_direct_cloud_to_local", models=models, categories=categories, prompt_render_mode="legacy_v13_monolith"), True))
    stages.append(("B3_fixed_block", _benchmark_command(args, root=root, stage="B3_fixed_block", models=models, categories=categories, prompt_render_mode="blocks"), True))
    stages.append(("B6_full_gps_ga", _ga_command(args, root=root, models=models, categories=categories), bool(args.full_run or args.smoke)))
    # Accepted-prompt evaluation is a placeholder until a promoted B6 prompt path exists.
    stages.append(("B6_full_gps_eval", _benchmark_command(args, root=root, stage="B6_full_gps_eval", models=models, categories=categories, prompt_render_mode="blocks"), False))
    stages.append(("B4_random_search", [], False))
    stages.append(("B5_ga_benchmark_only", [], False))

    for stage, command, runnable in stages:
        if command:
            planned[stage] = str(_write_command(root, stage, command))
        if args.resume and not args.force and _stage_completed(root, stage):
            continue
        if args.progress == "minimal":
            print(f"[STAGE] {stage}: RUNNING")
        start_time = datetime.now().isoformat(timespec="seconds")
        if args.dry_run and stage == "cloud_to_blocks_equivalence" and command:
            code = _run(command, quiet=args.quiet_final_summary)
            _write_stage(root, stage, status="pass" if code == 0 else "fail", model_key=model_label, command=command, start_time=start_time)
            if args.progress == "minimal":
                print(f"[STAGE] {stage}: {'PASS' if code == 0 else 'FAIL'}")
            continue
        if args.dry_run or not runnable:
            _write_stage(root, stage, status="pending" if not runnable else "skipped", model_key=model_label, command=command, start_time=start_time)
            if args.progress == "minimal":
                print(f"[STAGE] {stage}: {'PENDING' if not runnable else 'SKIPPED'}")
            continue
        code = _run(command, quiet=args.quiet_final_summary)
        _write_stage(root, stage, status="pass" if code == 0 else "fail", model_key=model_label, command=command, start_time=start_time)
        if args.progress == "minimal":
            print(f"[STAGE] {stage}: {'PASS' if code == 0 else 'FAIL'}")
        if code != 0 and args.strict_availability:
            return code

    export_command = _export_command(args, root=root, availability=availability)
    planned["export_paper_final_artifacts"] = str(_write_command(root, "export_paper_final_artifacts", export_command))
    code = _run(export_command, quiet=args.quiet_final_summary)
    _write_stage(root, "artifact_export", status="pass" if code == 0 else "fail", model_key=model_label, command=export_command)

    dump_json(root / "study_plan.json", {"root": str(root), "commands": planned, "dry_run": args.dry_run, "smoke": args.smoke, "full_run": args.full_run})
    manifest = root / "paper" / "final_artifacts_manifest.json"
    if args.quiet_final_summary:
        print("Paper study completed.")
        print()
        print("Artifacts:")
        print(f"- manifest: {manifest}")
        print(f"- cloud/block equivalence: {root / 'cloud_to_blocks_equivalence'}")
        print(f"- figure1: {root / 'paper' / 'figures' / 'figure1_prompt_search_dynamics_across_model_scales.png'}")
        print(f"- figure2: {root / 'paper' / 'figures' / 'figure2_deployment_aware_pareto_frontier_final.png'}")
        print(f"- table3: {root / 'paper' / 'tables' / 'table3_main_results.csv'}")
        print(f"- table4: {root / 'paper' / 'tables' / 'table4_ablation_qwen14.csv'}")
        print(f"- model availability: {availability['csv']}")
        print(f"- promotion decisions: {root / 'paper' / 'promotion' / 'promotion_decisions.csv'}")
        print(f"- structured feedback: {root / 'structured_feedback.jsonl'}")
        print()
        print("Notes:")
        print("- Full five-model execution is scheduled but not run in dry-run mode.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
