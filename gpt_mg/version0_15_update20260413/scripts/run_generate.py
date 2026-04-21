#!/usr/bin/env python3
# Assumption: execute from anywhere; this script adds gpt_mg/version0_14 to sys.path and reads repo datasets without modifying them.
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from utils.local_llm_client import LocalLLMError, call as llm_call
from utils.pipeline_common import (
    DATASET_DEFAULT,
    DEFAULT_CANDIDATE_STRATEGIES,
    LOGS_DIR,
    RESULTS_DIR,
    SERVICE_SCHEMA_DEFAULT,
    append_jsonl,
    atomic_write_csv,
    build_prompt_values,
    dump_json,
    ensure_workspace,
    load_dataset_rows,
    load_genome,
    load_service_schema,
    make_run_id,
    normalize_candidate_json_text,
    render_blocks_for_genome,
    select_rows,
    slugify,
    unique_fieldnames,
)


GENERATION_EXTRA_FIELDS = [
    "row_no",
    "profile",
    "genome_id",
    "genome_seed",
    "run_id",
    "candidate_count",
    "candidates",
    "candidate_metadata",
    "prompt_log_paths",
    "generation_status",
    "llm_mode",
    "llm_model",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate JOI candidates for selected JOICommands-280 rows using a version0_14 genome.")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--genome-json", default=str(VERSION_ROOT / "genomes" / "example_genome.json"))
    parser.add_argument("--dataset", default=str(DATASET_DEFAULT))
    parser.add_argument("--service-schema", default=str(SERVICE_SCHEMA_DEFAULT))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--start-row", type=int, default=1)
    parser.add_argument("--end-row", type=int, default=None)
    parser.add_argument("--category", action="append", default=[], help="Filter by dataset category. Can be repeated or comma-separated.")
    parser.add_argument("--candidate-k", type=int, default=3)
    parser.add_argument("--seed", type=int, default=14)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--output-csv", default=None)
    parser.add_argument("--llm-mode", default=None)
    parser.add_argument("--llm-endpoint", default=None)
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--model", default=None, help="Override the model id while keeping the same prompt/genome.")
    return parser


def _candidate_strategies(genome: dict[str, Any], candidate_k: int) -> list[str]:
    strategies = list(genome.get("params", {}).get("candidate_strategies") or DEFAULT_CANDIDATE_STRATEGIES)
    if not strategies:
        strategies = list(DEFAULT_CANDIDATE_STRATEGIES)
    return [strategies[idx % len(strategies)] for idx in range(candidate_k)]


def _llm_settings(
    genome: dict[str, Any],
    cli_args: argparse.Namespace,
    *,
    model_override: str | None = None,
) -> tuple[float, int, str]:
    params = genome.get("params", {})
    block_02 = genome.get("block_params", {}).get("02", {})
    temperature = cli_args.temperature
    if temperature is None:
        temperature = block_02.get("temperature", params.get("temperature", 0.0))
    max_tokens = cli_args.max_tokens
    if max_tokens is None:
        max_tokens = block_02.get("max_tokens", params.get("max_tokens", 1024))
    model = str(model_override or params.get("model", "Qwen/Qwen2.5-Coder-7B-Instruct"))
    return float(temperature), int(max_tokens), str(model)


def _system_prompt() -> str:
    return "You are a deterministic JOILang generation engine. Follow the user instructions exactly and return only the requested JSON object."


def generate_candidates_for_rows(
    *,
    profile: str,
    genome: dict[str, Any],
    dataset_rows: list[tuple[int, dict[str, str]]],
    service_schema: dict[str, dict[str, Any]],
    candidate_k: int,
    llm_mode: str | None,
    llm_endpoint: str | None,
    timeout_sec: int,
    retries: int,
    run_id: str,
    output_csv: str | Path,
    seed: int,
    temperature: float,
    max_tokens: int,
    model: str,
    llm_extra_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_workspace()
    output_csv = Path(output_csv)
    logs_dir = LOGS_DIR / run_id
    logs_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = RESULTS_DIR / f"candidates_{slugify(run_id)}.jsonl"

    output_rows: list[dict[str, Any]] = []
    fieldnames: list[str] | None = None
    strategies = _candidate_strategies(genome, candidate_k)

    for row_no, row in dataset_rows:
        candidates: list[str] = []
        candidate_meta: list[dict[str, Any]] = []
        prompt_log_paths: list[str] = []
        generation_status = "ok"
        for candidate_index in range(candidate_k):
            strategy = strategies[candidate_index]
            values = build_prompt_values(row_no, row, service_schema, candidate_strategy=strategy)
            rendered_prompt, manifest = render_blocks_for_genome(genome, values=values)
            user_prompt = rendered_prompt + "\n\nReturn the final JSON object now."
            log_path = logs_dir / f"row_{row_no:03d}_cand_{candidate_index + 1}.json"
            prompt_log_paths.append(str(log_path))
            try:
                response = llm_call(
                    _system_prompt(),
                    user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    mode=llm_mode,
                    model=model,
                    endpoint=llm_endpoint,
                    timeout_sec=timeout_sec,
                    retries=retries,
                    seed=seed + row_no + candidate_index,
                    log_path=log_path,
                    extra_payload=llm_extra_payload,
                )
                candidate_text = normalize_candidate_json_text(
                    str(response.get("content", "")).strip(),
                    default_cron=str(values.get("optional_cron", "") or ""),
                    default_period=int(str(values.get("optional_period", "0") or "0")),
                )
                candidates.append(candidate_text)
                candidate_meta.append(
                    {
                        "candidate_index": candidate_index,
                        "strategy": strategy,
                        "prompt_tokens": response.get("prompt_tokens", 0),
                        "completion_tokens": response.get("completion_tokens", 0),
                        "total_tokens": response.get("total_tokens", 0),
                        "latency_sec": response.get("latency_sec", 0.0),
                        "block_manifest": manifest,
                    }
                )
            except Exception as exc:
                generation_status = "partial_error"
                candidates.append("")
                candidate_meta.append(
                    {
                        "candidate_index": candidate_index,
                        "strategy": strategy,
                        "error": str(exc),
                        "block_manifest": manifest,
                    }
                )
                dump_json(log_path, {"error": str(exc), "block_manifest": manifest, "prompt": user_prompt})

        result_row = dict(row)
        result_row.update(
            {
                "row_no": row_no,
                "profile": profile,
                "genome_id": genome.get("id", "unknown"),
                "genome_seed": genome.get("seed", seed),
                "run_id": run_id,
                "candidate_count": len(candidates),
                "candidates": json.dumps(candidates, ensure_ascii=False),
                "candidate_metadata": json.dumps(candidate_meta, ensure_ascii=False),
                "prompt_log_paths": json.dumps(prompt_log_paths, ensure_ascii=False),
                "generation_status": generation_status,
                "llm_mode": llm_mode or "worker",
                "llm_model": model,
            }
        )
        output_rows.append(result_row)
        fieldnames = unique_fieldnames(output_rows, GENERATION_EXTRA_FIELDS)
        atomic_write_csv(output_csv, fieldnames, output_rows)
        append_jsonl(
            jsonl_path,
            {
                "row_no": row_no,
                "profile": profile,
                "genome_id": genome.get("id", "unknown"),
                "candidates": candidates,
                "candidate_metadata": candidate_meta,
            },
        )

    return {
        "run_id": run_id,
        "output_csv": str(output_csv),
        "jsonl_path": str(jsonl_path),
        "row_count": len(output_rows),
        "rows": output_rows,
        "fieldnames": fieldnames or [],
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

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

    temperature, max_tokens, model = _llm_settings(genome, args, model_override=args.model)
    run_id = args.run_id or make_run_id(f"generate_{args.profile}_{genome.get('id', 'genome')}", args.seed)
    output_csv = args.output_csv or RESULTS_DIR / f"candidates_{slugify(genome.get('id', 'genome'))}.csv"

    summary = generate_candidates_for_rows(
        profile=args.profile,
        genome=genome,
        dataset_rows=selected_rows,
        service_schema=service_schema,
        candidate_k=args.candidate_k,
        llm_mode=args.llm_mode,
        llm_endpoint=args.llm_endpoint,
        timeout_sec=args.timeout_sec,
        retries=args.retries,
        run_id=run_id,
        output_csv=output_csv,
        seed=args.seed,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
    )

    print("Generation completed")
    print(f"- run_id: {summary['run_id']}")
    print(f"- output_csv: {summary['output_csv']}")
    print(f"- jsonl_path: {summary['jsonl_path']}")
    print(f"- rows: {summary['row_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
