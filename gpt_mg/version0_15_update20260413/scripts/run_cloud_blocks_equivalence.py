#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
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

from utils.pipeline_common import RESULTS_DIR, atomic_write_csv, dump_json


DEFAULT_PROMPT_ASSETS_DIR = VERSION_ROOT.parent / "version0_13"
MODEL_KEY = "gpt41_mini"
MODEL_PREFIX = f"{MODEL_KEY}__"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare GPT-4.1-mini legacy_v13_monolith rendering with block rendering. "
            "This is the paper sanity check that prompt decomposition itself does not "
            "degrade the cloud reference behavior."
        )
    )
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--dataset", default="")
    parser.add_argument("--service-schema", default="")
    parser.add_argument("--row-no", action="append", type=int, default=[])
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--limit-per-category", type=int, default=None)
    parser.add_argument("--candidate-k", type=int, default=1)
    parser.add_argument("--repair-attempts", type=int, default=0)
    parser.add_argument("--det-profile", choices=["legacy", "strict"], default="strict")
    parser.add_argument("--llm-endpoint", default="")
    parser.add_argument("--prompt-assets-dir", default=str(DEFAULT_PROMPT_ASSETS_DIR))
    parser.add_argument("--service-context-mode", choices=["retrieval_fallback", "schema_fallback"], default="retrieval_fallback")
    parser.add_argument("--retrieval-topk", type=int, default=10)
    parser.add_argument("--retrieval-mode", choices=["hybrid", "dense", "bm25"], default="hybrid")
    parser.add_argument("--retrieval-device", default="cpu")
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quiet-final-summary", action="store_true")
    return parser


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _resolve_output_dir(raw: str) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    return (RESULTS_DIR / f"cloud_to_blocks_equivalence_{_timestamp()}").resolve()


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _endpoint(args: argparse.Namespace) -> str:
    return (
        args.llm_endpoint
        or os.getenv("JOI_V15_OPENAI_ENDPOINT", "").strip()
        or os.getenv("JOI_V14_OPENAI_ENDPOINT", "").strip()
        or "https://api.openai.com/v1/chat/completions"
    )


def _selection_args(args: argparse.Namespace) -> list[str]:
    cli: list[str] = []
    for row_no in args.row_no:
        cli += ["--row-no", str(row_no)]
    for category in args.category:
        cli += ["--category", str(category)]
    if args.limit is not None:
        cli += ["--limit", str(args.limit)]
    if args.limit_per_category is not None:
        cli += ["--limit-per-category", str(args.limit_per_category)]
    if args.dataset:
        cli += ["--dataset", args.dataset]
    if args.service_schema:
        cli += ["--service-schema", args.service_schema]
    return cli


def _benchmark_command(args: argparse.Namespace, *, mode: str, output_dir: Path) -> list[str]:
    cli = [
        sys.executable,
        str(VERSION_ROOT / "scripts" / "run_benchmark.py"),
        "--suite",
        "paper_with_cloud_ref",
        "--model-key",
        MODEL_KEY,
        "--llm-mode",
        "openai",
        "--llm-endpoint",
        _endpoint(args),
        "--candidate-k",
        str(args.candidate_k),
        "--repair-attempts",
        str(args.repair_attempts),
        "--det-profile",
        args.det_profile,
        "--prompt-render-mode",
        mode,
        "--prompt-assets-dir",
        str(Path(args.prompt_assets_dir).expanduser().resolve()),
        "--service-context-mode",
        args.service_context_mode,
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
        "--skip-row-report",
    ]
    return cli + _selection_args(args)


def _run_command(command: list[str], *, quiet: bool) -> int:
    if quiet:
        proc = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        if proc.returncode != 0:
            sys.stderr.write(proc.stdout[-4000:])
        return int(proc.returncode)
    return int(subprocess.run(command, check=False).returncode)


def _index_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {str(row.get("row_no", "")).strip(): row for row in rows if str(row.get("row_no", "")).strip()}


def _compare(monolith_dir: Path, blocks_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    mono_rows = _index_rows(_read_csv(monolith_dir / "row_comparison.csv"))
    block_rows = _index_rows(_read_csv(blocks_dir / "row_comparison.csv"))
    row_ids = sorted(set(mono_rows) | set(block_rows), key=lambda item: int(item) if item.isdigit() else item)
    rows: list[dict[str, Any]] = []
    mismatch_count = 0
    mono_pass = 0
    block_pass = 0
    for row_id in row_ids:
        mono = mono_rows.get(row_id, {})
        block = block_rows.get(row_id, {})
        mono_ok = _truthy(mono.get(f"{MODEL_PREFIX}det_pass", ""))
        block_ok = _truthy(block.get(f"{MODEL_PREFIX}det_pass", ""))
        mono_pass += int(mono_ok)
        block_pass += int(block_ok)
        mismatch = mono_ok != block_ok
        mismatch_count += int(mismatch)
        rows.append(
            {
                "row_no": row_id,
                "category": mono.get("category") or block.get("category", ""),
                "command_eng": mono.get("command_eng") or block.get("command_eng", ""),
                "monolith_det_pass": mono_ok,
                "blocks_det_pass": block_ok,
                "pass_mismatch": mismatch,
                "monolith_det_score": mono.get(f"{MODEL_PREFIX}det_score", ""),
                "blocks_det_score": block.get(f"{MODEL_PREFIX}det_score", ""),
                "monolith_output_name": mono.get(f"{MODEL_PREFIX}output_name", ""),
                "blocks_output_name": block.get(f"{MODEL_PREFIX}output_name", ""),
                "monolith_failure_reasons": mono.get(f"{MODEL_PREFIX}failure_reasons", ""),
                "blocks_failure_reasons": block.get(f"{MODEL_PREFIX}failure_reasons", ""),
            }
        )
    total = len(row_ids)
    summary = {
        "row_count": total,
        "monolithic_pass_count": mono_pass,
        "block_rendered_pass_count": block_pass,
        "monolithic_pass_rate": round((mono_pass / total) * 100.0, 4) if total else 0.0,
        "block_rendered_pass_rate": round((block_pass / total) * 100.0, 4) if total else 0.0,
        "mismatch_count": mismatch_count,
        "all_pass_equivalence": bool(total and mismatch_count == 0 and mono_pass == total and block_pass == total),
    }
    return rows, summary


def _write_readme(path: Path, summary: dict[str, Any]) -> None:
    text = f"""# Cloud-to-Block Prompt Equivalence

This verifies that prompt block decomposition itself does not degrade the cloud reference behavior.

## Result

- model backend: {summary.get("model_backend", "")}
- prompt modes compared: {", ".join(summary.get("prompt_modes_compared", []))}
- row/category scope: {summary.get("row_category_scope", "")}
- DET profile: {summary.get("det_profile", "")}
- monolithic pass rate: {summary.get("monolithic_pass_rate", "pending")}
- block-rendered pass rate: {summary.get("block_rendered_pass_rate", "pending")}
- mismatch count: {summary.get("mismatch_count", "pending")}
- all-pass equivalence: {summary.get("all_pass_equivalence", False)}

## Files

- `summary.json`
- `monolith_vs_blocks.csv`
- `command.txt`
"""
    path.write_text(text, encoding="utf-8")


def _scope_label(args: argparse.Namespace) -> str:
    pieces: list[str] = []
    if args.row_no:
        pieces.append("rows=" + ",".join(str(item) for item in args.row_no))
    if args.category:
        pieces.append("categories=" + ",".join(str(item) for item in args.category))
    if args.limit is not None:
        pieces.append(f"limit={args.limit}")
    if args.limit_per_category is not None:
        pieces.append(f"limit_per_category={args.limit_per_category}")
    return "; ".join(pieces) if pieces else "full selected dataset"


def main() -> int:
    args = build_parser().parse_args()
    output_dir = _resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    monolith_dir = output_dir / "monolith"
    blocks_dir = output_dir / "blocks"
    commands = {
        "monolith": _benchmark_command(args, mode="legacy_v13_monolith", output_dir=monolith_dir),
        "blocks": _benchmark_command(args, mode="blocks", output_dir=blocks_dir),
    }
    (output_dir / "command.txt").write_text(
        "\n\n".join(f"# {name}\n" + " ".join(cmd) for name, cmd in commands.items()) + "\n",
        encoding="utf-8",
    )

    if args.dry_run:
        summary = {
            "status": "pending_dry_run",
            "model_backend": "gpt-4.1-mini/openai-compatible",
            "prompt_modes_compared": ["legacy_v13_monolith", "blocks"],
            "row_category_scope": _scope_label(args),
            "det_profile": args.det_profile,
            "monolithic_pass_rate": None,
            "block_rendered_pass_rate": None,
            "mismatch_count": None,
            "all_pass_equivalence": False,
            "notes": ["Dry run only; no model calls were made."],
        }
        dump_json(output_dir / "summary.json", summary)
        atomic_write_csv(output_dir / "monolith_vs_blocks.csv", ["row_no", "status"], [])
        _write_readme(output_dir / "README.md", summary)
        if args.quiet_final_summary:
            print(f"cloud/block equivalence dry-run: {output_dir}")
        return 0

    failures: list[str] = []
    for name, command in commands.items():
        code = _run_command(command, quiet=args.quiet_final_summary)
        if code != 0:
            failures.append(f"{name} command failed with exit code {code}")

    rows, metric_summary = _compare(monolith_dir, blocks_dir)
    headers = [
        "row_no",
        "category",
        "command_eng",
        "monolith_det_pass",
        "blocks_det_pass",
        "pass_mismatch",
        "monolith_det_score",
        "blocks_det_score",
        "monolith_output_name",
        "blocks_output_name",
        "monolith_failure_reasons",
        "blocks_failure_reasons",
    ]
    atomic_write_csv(output_dir / "monolith_vs_blocks.csv", headers, rows)
    summary = {
        "status": "failed" if failures else "completed",
        "model_backend": "gpt-4.1-mini/openai-compatible",
        "prompt_modes_compared": ["legacy_v13_monolith", "blocks"],
        "row_category_scope": _scope_label(args),
        "det_profile": args.det_profile,
        "monolith_dir": str(monolith_dir),
        "blocks_dir": str(blocks_dir),
        "notes": failures,
        **metric_summary,
    }
    dump_json(output_dir / "summary.json", summary)
    _write_readme(output_dir / "README.md", summary)

    if args.quiet_final_summary:
        print(f"cloud/block equivalence: {output_dir}")
        print(f"all_pass_equivalence={summary['all_pass_equivalence']} mismatch_count={summary['mismatch_count']}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
