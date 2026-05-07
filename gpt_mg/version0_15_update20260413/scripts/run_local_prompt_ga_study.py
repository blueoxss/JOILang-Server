#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = VERSION_ROOT.parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from scripts.run_generate import generate_candidates_for_rows
from scripts.run_model_suite_benchmark import PAPER_LOCAL5_SUITE, _inspect_model_runtime, _print_preflight
from utils.det_evaluator import evaluate_candidates, summarize_failure_patterns
from utils.pipeline_common import (
    BLOCKS_DIR,
    DATASET_DEFAULT,
    RESULTS_DIR,
    SERVICE_SCHEMA_DEFAULT,
    atomic_write_csv,
    dump_json,
    ensure_workspace,
    load_dataset_rows,
    load_service_schema,
    sample_rows,
    select_rows,
    seeded_uuid,
    slugify,
)


DET_PASS_THRESHOLD = 70.0
DEFAULT_PROMPT_ASSETS_DIR = VERSION_ROOT.parent / "version0_13"

STRATEGY_POOL = [
    "direct",
    "minimal",
    "canonical_names_first",
    "explicit_preconditions",
    "compact_json",
]

BASE_MICRO_RULES = [
    "Return exactly one JSON object only with keys name, cron, period, code.",
    "Use value entries in conditions and function entries in actions.",
    "Emit lowercase service/value member tokens after the receiver dot.",
    "Never invent service names outside the provided service_list_snippet.",
]

FAILURE_FEEDBACK_RULES = {
    "invalid_json": "The final answer must be a raw JSON object only; no markdown, prose, or code fences.",
    "schema_missing_keys": "Always include exactly name, cron, period, and code.",
    "service_match": "Resolve every member token from service_list_snippet.service/canonical_name before emitting code.",
    "unknown_service": "Do not shorten canonical member names; use the provided category-prefixed service token, then lowercase it.",
    "arg_type": "Match argument count, type, unit, and enum values exactly from service_list_snippet.",
    "semantic": "Prefer the smallest action sequence that directly matches the natural command verb and target.",
    "extraneous": "Remove unrelated helper actions and duplicate service calls.",
    "gt_mismatch": "Preserve GT-style temporal structure, receiver tags, service ordering, and literals.",
    "gt_service_coverage": "Include every service family implied by the command, including both sensor reads and actuator effects.",
    "gt_receiver_coverage": "Preserve all receiver tags and all(...) group receivers when the command addresses groups.",
    "dataflow": "When a sensor value is read for a command, pass or use that value in the downstream action.",
    "numeric_grounding": "Copy numeric literals and units from the command exactly after unit conversion.",
    "enum_grounding": "Use only enum strings that appear in service_list_snippet for the selected service.",
}

BLOCK_FILE_MAP = {
    "01": "01_preamble.txt",
    "02": "02_generator_prompt.txt",
    "03": "03_postprocessor.txt",
    "06": "06_det_helper.txt",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a paper-oriented local prompt GA study. "
            "version0_13 prompt assets are split into version0_15 block genes, "
            "then crossed over and mutated per local model and category."
        )
    )
    parser.add_argument("--dataset", default=str(DATASET_DEFAULT))
    parser.add_argument("--service-schema", default=str(SERVICE_SCHEMA_DEFAULT))
    parser.add_argument("--prompt-assets-dir", default=str(DEFAULT_PROMPT_ASSETS_DIR))
    parser.add_argument("--output-root", default="")
    parser.add_argument("--profile", default=VERSION_ROOT.name)
    parser.add_argument("--model-key", action="append", default=[], help="Local model key. Can be repeated.")
    parser.add_argument("--category", action="append", default=[], help="Category filter. Can be repeated or comma-separated.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--limit-per-category", type=int, default=None)
    parser.add_argument("--population", type=int, default=4)
    parser.add_argument("--gens", type=int, default=3)
    parser.add_argument("--sample-size", type=int, default=4)
    parser.add_argument("--validation-size", type=int, default=4)
    parser.add_argument("--cheap-eval-limit", type=int, default=2)
    parser.add_argument("--candidate-k", type=int, default=1)
    parser.add_argument("--elites", type=int, default=1)
    parser.add_argument("--crossover-rate", type=float, default=0.65)
    parser.add_argument("--mutation-rate", type=float, default=0.35)
    parser.add_argument("--alpha", type=float, default=0.25, help="Variance penalty used in fitness.")
    parser.add_argument("--det-profile", choices=["legacy", "strict"], default="strict")
    parser.add_argument("--llm-mode", default="worker")
    parser.add_argument("--llm-endpoint", default=None)
    parser.add_argument("--preflight-only", action="store_true", help="Inspect selected local model availability and exit.")
    parser.add_argument("--skip-unavailable", action="store_true", help="Skip local models that are not ready in preflight.")
    parser.add_argument("--strict-availability", action="store_true", help="Abort when any selected local model is unavailable.")
    parser.add_argument("--print-worker-info", action="store_true")
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--service-context-mode", choices=["auto", "retrieval_fallback", "schema_fallback"], default="retrieval_fallback")
    parser.add_argument("--disable-retrieval-premapping", action="store_true")
    parser.add_argument("--retrieval-topk", type=int, default=10)
    parser.add_argument("--retrieval-mode", choices=["hybrid", "dense", "bm25"], default="hybrid")
    parser.add_argument("--retrieval-json", default=None)
    parser.add_argument("--retrieval-bundle-dir", default=None)
    parser.add_argument("--retrieval-model-dir", default=None)
    parser.add_argument("--retrieval-device", default="cpu")
    parser.add_argument("--v13-detail", choices=["compact", "mixed", "full"], default="mixed")
    parser.add_argument("--skip-final-eval", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Build gene pool and manifest only.")
    parser.add_argument("--seed", type=int, default=150413)
    return parser


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _copy_jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _parse_repeated(values: list[str]) -> list[str]:
    parsed: list[str] = []
    for value in values or []:
        for part in str(value).split(","):
            token = part.strip()
            if token:
                parsed.append(token)
    return parsed


def _categories_from_rows(rows: list[tuple[int, dict[str, str]]]) -> list[str]:
    categories = {str(row.get("category", "")).strip() for _row_no, row in rows if str(row.get("category", "")).strip()}
    return sorted(categories, key=lambda item: (int(item) if item.isdigit() else 10**9, item))


def _limit_rows_per_category(
    rows: list[tuple[int, dict[str, str]]],
    *,
    limit_per_category: int | None,
) -> list[tuple[int, dict[str, str]]]:
    if not limit_per_category or limit_per_category <= 0:
        return rows
    counts: dict[str, int] = defaultdict(int)
    kept: list[tuple[int, dict[str, str]]] = []
    for row_no, row in rows:
        category = str(row.get("category", "")).strip()
        if counts[category] >= limit_per_category:
            continue
        counts[category] += 1
        kept.append((row_no, row))
    return kept


def _load_v13_assets(prompt_assets_dir: Path) -> dict[str, str]:
    files = {
        "grammar": "grammar_ver1.5.10.md",
        "service": "service_prompt_10.md",
        "tempo": "tempo_prompt_9.md",
        "caution": "caution_prompt_8.md",
        "response": "response_prompt_baseline_cot.md",
    }
    assets: dict[str, str] = {}
    missing: list[str] = []
    for key, filename in files.items():
        path = prompt_assets_dir / filename
        if not path.exists():
            missing.append(str(path))
        else:
            assets[key] = _read_text(path)
    if missing:
        raise SystemExit("Missing version0_13 prompt assets:\n" + "\n".join(missing))
    return assets


def _compact_text(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text.strip()
    headings: list[str] = []
    bullets: list[str] = []
    examples: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if stripped.startswith("#"):
            headings.append(stripped)
        elif stripped.startswith(("-", "*", "1.", "2.", "3.", "4.", "5.")):
            if any(key in lower for key in ("must", "never", "service", "value", "function", "tag", "condition", "time", "json")):
                bullets.append(stripped)
        elif any(key in lower for key in ("correct", "incorrect", "example", "command")):
            examples.append(stripped)
    sections = []
    if headings:
        sections.append("\n".join(headings[:18]))
    if bullets:
        sections.append("\n".join(bullets[:80]))
    if examples:
        sections.append("\n".join(examples[:30]))
    compact = "\n".join(sections).strip()
    if len(compact) < max_chars * 0.35:
        compact = text[:max_chars].strip()
    return compact[:max_chars].rstrip() + "\n\n[Compact excerpt from version0_13 prompt assets]"


def _header(block_id: str, role: str, description: str) -> str:
    placeholders = "{command_eng}, {connected_devices}, {service_list_snippet}, {optional_cron}, {optional_period}, {candidate_strategy}"
    return (
        f"# id: {block_id}\n"
        f"# role: {role}\n"
        "# params: temperature, few_shot_count, max_tokens, micro_rules\n"
        f"# description: {description}\n"
        f"# placeholders: {placeholders}\n\n"
    )


def _adapter_intro() -> str:
    return """Version bridge:
- This gene is derived from version0_13 prompt assets, but it runs in the version0_15 block renderer.
- Treat [service_list_value] and [service_list_function] from version0_13 as the typed `services` entries inside {service_list_snippet}.
- Use only the device categories, selector tags, values, functions, argument types, and enum values present in {service_list_snippet}.
- In final JOILang code, keep receiver tags unchanged and lowercase only the service/value member token after the receiver dot.
"""


def _task_io_block() -> str:
    return """Current task inputs:
- command_eng: {command_eng}
- connected_devices: {connected_devices}
- optional_cron: {optional_cron}
- optional_period: {optional_period}
- candidate_strategy: {candidate_strategy}

Authoritative service_list_snippet:
{service_list_snippet}
"""


def _strict_json_contract() -> str:
    return """Output contract:
- Return exactly one raw JSON object and nothing else.
- Required keys are exactly: name, cron, period, code.
- For unscheduled commands, use cron "" and period 0.
- `code` must be valid JOILang and JSON-escaped.
- If schema-safe code cannot be produced, return an empty code string instead of inventing services.
"""


def _strict_det_helper() -> str:
    return """DET-aware generation targets:
- Service coverage: include every value/function implied by the command.
- Receiver coverage: preserve category tags, selector tags, locations, and all(...) groups.
- Dataflow: when reading a sensor value, use that value in the downstream condition/action.
- Numeric grounding: preserve numbers and convert only when service units require it.
- Enum grounding: use exact enum strings from the selected service entry.
- Minimality: avoid unrelated actions, duplicate calls, and helper methods outside the schema.
"""


def _source_rel(path: Path) -> str:
    try:
        return str(path.relative_to(BLOCKS_DIR))
    except ValueError:
        return str(path)


def build_gene_pool(
    *,
    prompt_assets_dir: Path,
    output_root: Path,
    detail: str,
) -> tuple[dict[str, list[dict[str, Any]]], Path]:
    assets = _load_v13_assets(prompt_assets_dir)
    pool_seed = hashlib.sha1(
        (str(prompt_assets_dir.resolve()) + "|" + detail + "|" + "|".join(f"{k}:{len(v)}" for k, v in assets.items())).encode("utf-8")
    ).hexdigest()[:10]
    generated_dir = BLOCKS_DIR / "generated" / f"v13_gene_pool_{pool_seed}"
    generated_dir.mkdir(parents=True, exist_ok=True)

    variants: dict[str, list[dict[str, Any]]] = {
        block_id: [
            {
                "variant": "v15_current",
                "source_file": BLOCK_FILE_MAP[block_id],
                "char_count": len(_read_text(BLOCKS_DIR / BLOCK_FILE_MAP[block_id])),
                "parent_assets": ["version0_15_current"],
                "generated": False,
            }
        ]
        for block_id in BLOCK_FILE_MAP
    }

    def add_variant(block_id: str, name: str, body: str, parent_assets: list[str]) -> None:
        role = {
            "01": "preprocessor",
            "02": "generator",
            "03": "postprocessor",
            "06": "helper",
        }.get(block_id, "prompt")
        path = generated_dir / f"{block_id}_{slugify(name)}.txt"
        text = _header(block_id, role, f"version0_13-derived gene variant: {name}") + body
        _write_text(path, text)
        variants[block_id].append(
            {
                "variant": name,
                "source_file": _source_rel(path),
                "char_count": len(text),
                "parent_assets": parent_assets,
                "generated": True,
            }
        )

    caution_compact = _compact_text(assets["caution"], max_chars=5200)
    service_compact = _compact_text(assets["service"], max_chars=5200)
    response_compact = _compact_text(assets["response"], max_chars=5200)
    grammar_compact = _compact_text(assets["grammar"], max_chars=6200)
    tempo_compact = _compact_text(assets["tempo"], max_chars=5200)

    add_variant(
        "01",
        "v13_caution_compact",
        "\n\n".join([
            "You are a deterministic JOILang programmer.",
            _adapter_intro(),
            "Version0_13 important cautions, compacted:",
            caution_compact,
        ]),
        ["caution_prompt_8.md"],
    )
    add_variant(
        "01",
        "v13_caution_schema_strict",
        "\n\n".join([
            "You are a schema-faithful JOILang generator.",
            _adapter_intro(),
            _strict_json_contract(),
            "Critical caution rules:",
            caution_compact,
        ]),
        ["caution_prompt_8.md"],
    )

    add_variant(
        "02",
        "v13_service_response_compact",
        "\n\n".join([
            "Generate one JOILang JSON object for the current command.",
            _task_io_block(),
            _adapter_intro(),
            "Version0_13 service separation rules:",
            service_compact,
            "Version0_13 response construction rules:",
            response_compact,
            _strict_json_contract(),
        ]),
        ["service_prompt_10.md", "response_prompt_baseline_cot.md"],
    )
    add_variant(
        "02",
        "v13_schema_first_compact",
        "\n\n".join([
            "Schema-first generation procedure:",
            _task_io_block(),
            "1. Select device categories and receiver tags only from service_list_snippet.",
            "2. Select condition values from type=value entries.",
            "3. Select actions from type=function entries.",
            "4. Emit lowercase canonical member names after the receiver dot.",
            "5. Return JSON only.",
            service_compact,
            _strict_det_helper(),
            _strict_json_contract(),
        ]),
        ["service_prompt_10.md"],
    )

    add_variant(
        "03",
        "v13_response_contract",
        "\n\n".join([
            "Final response scrubber derived from version0_13 response prompt.",
            response_compact,
            _strict_json_contract(),
            "Never expose chain-of-thought. Do not print internal extraction lists.",
        ]),
        ["response_prompt_baseline_cot.md"],
    )
    add_variant(
        "03",
        "json_case_guard",
        "\n\n".join([
            _strict_json_contract(),
            "Case guard:",
            "- Receiver tags after # keep original case.",
            "- Member tokens after the dot must be lowercase.",
            "- Example: (#Speaker).Speaker_SetVolume(30) -> (#Speaker).speaker_setvolume(30)",
            "- Do not rewrite category tags such as #DoorLock, #AirQualitySensor, or #RobotVacuumCleaner.",
        ]),
        ["version0_15_case_rules"],
    )

    add_variant(
        "06",
        "v13_grammar_tempo_compact",
        "\n\n".join([
            "Grammar and temporal helper rules derived from version0_13.",
            grammar_compact,
            tempo_compact,
            _strict_det_helper(),
        ]),
        ["grammar_ver1.5.10.md", "tempo_prompt_9.md"],
    )
    add_variant(
        "06",
        "det_strict_helper",
        "\n\n".join([
            "Use these evaluator-facing constraints before finalizing code.",
            _strict_det_helper(),
            "Temporal edge cases:",
            "- Repeated triggers such as whenever/every time/button pressed should usually use period 100 and state/edge guards.",
            "- One-shot when/until commands may use wait until if no repetition is implied.",
            "- Delayed follow-up actions should use the schema-supported delay form and preserve action order.",
        ]),
        ["strict_det_feedback"],
    )

    if detail in {"mixed", "full"}:
        add_variant(
            "01",
            "v13_caution_full",
            "\n\n".join([
                "You are a JOILang programmer. Follow these version0_13 caution rules in the version0_15 schema context.",
                _adapter_intro(),
                assets["caution"],
            ]),
            ["caution_prompt_8.md"],
        )
        add_variant(
            "02",
            "v13_service_response_full",
            "\n\n".join([
                _task_io_block(),
                _adapter_intro(),
                assets["service"],
                assets["response"],
                _strict_json_contract(),
            ]),
            ["service_prompt_10.md", "response_prompt_baseline_cot.md"],
        )
        add_variant(
            "06",
            "v13_grammar_tempo_full",
            "\n\n".join([
                assets["grammar"],
                assets["tempo"],
                _strict_det_helper(),
            ]),
            ["grammar_ver1.5.10.md", "tempo_prompt_9.md"],
        )

    manifest_path = output_root / "gene_pool_manifest.json"
    dump_json(
        manifest_path,
        {
            "prompt_assets_dir": str(prompt_assets_dir),
            "detail": detail,
            "generated_dir": str(generated_dir),
            "variants": variants,
        },
    )
    return variants, manifest_path


def _model_entries(model_keys: list[str]) -> list[dict[str, Any]]:
    requested = set(model_keys)
    if not requested:
        return [_copy_jsonable(entry) for entry in PAPER_LOCAL5_SUITE]
    entries = []
    available = {entry["key"]: entry for entry in PAPER_LOCAL5_SUITE}
    missing = sorted(requested - set(available.keys()))
    if missing:
        raise SystemExit(f"Unknown model keys: {missing}. Available: {sorted(available.keys())}")
    for entry in PAPER_LOCAL5_SUITE:
        if entry["key"] in requested:
            entries.append(_copy_jsonable(entry))
    return entries


def _service_context_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    mode = "schema_fallback" if args.disable_retrieval_premapping else args.service_context_mode
    return {
        "service_context_mode": mode,
        "retrieval_topk": args.retrieval_topk,
        "retrieval_mode": args.retrieval_mode,
        "retrieval_json_path": args.retrieval_json,
        "retrieval_bundle_dir": args.retrieval_bundle_dir,
        "retrieval_model_dir": args.retrieval_model_dir,
        "retrieval_device": args.retrieval_device,
    }


def _block_source(genome: dict[str, Any], block_id: str) -> str:
    return str(genome.get("block_params", {}).get(block_id, {}).get("source_file", BLOCK_FILE_MAP.get(block_id, "")))


def _make_genome(
    *,
    model_id: str,
    rng: random.Random,
    gene_pool: dict[str, list[dict[str, Any]]],
    fixed_variant: str | None = None,
    base_name: str = "gene",
) -> dict[str, Any]:
    block_params: dict[str, Any] = {}
    for block_id in ["01", "02", "03", "06"]:
        variants = gene_pool[block_id]
        selected = None
        if fixed_variant:
            selected = next((item for item in variants if item["variant"] == fixed_variant), None)
        if selected is None:
            selected = rng.choice(variants)
        block_params[block_id] = {"source_file": selected["source_file"]}
    block_params["02"]["few_shot_count"] = rng.choice([1, 2, 3])
    if rng.random() < 0.7:
        block_params["02"]["micro_rules"] = rng.sample(BASE_MICRO_RULES, k=rng.randint(1, min(3, len(BASE_MICRO_RULES))))
    genome = {
        "id": f"{base_name}-{seeded_uuid(rng)}",
        "seed": rng.randint(1, 10**9),
        "blocks": ["01", "02", "03", "06"],
        "params": {
            "model": model_id,
            "temperature": rng.choice([0.0, 0.0, 0.05]),
            "max_tokens": rng.choice([512, 768, 1024]),
            "candidate_strategies": rng.sample(STRATEGY_POOL, k=rng.randint(2, min(4, len(STRATEGY_POOL)))),
        },
        "block_params": block_params,
    }
    return genome


def _initial_population(
    *,
    model_id: str,
    rng: random.Random,
    gene_pool: dict[str, list[dict[str, Any]]],
    population_size: int,
) -> list[dict[str, Any]]:
    population: list[dict[str, Any]] = [
        _make_genome(model_id=model_id, rng=rng, gene_pool=gene_pool, fixed_variant="v15_current", base_name="v15"),
        _make_genome(model_id=model_id, rng=rng, gene_pool=gene_pool, fixed_variant=None, base_name="v13mix"),
    ]
    compact_variants = {
        "01": "v13_caution_compact",
        "02": "v13_service_response_compact",
        "03": "v13_response_contract",
        "06": "v13_grammar_tempo_compact",
    }
    compact = _make_genome(model_id=model_id, rng=rng, gene_pool=gene_pool, fixed_variant="v15_current", base_name="v13compact")
    for block_id, variant_name in compact_variants.items():
        selected = next((item for item in gene_pool[block_id] if item["variant"] == variant_name), None)
        if selected:
            compact["block_params"][block_id]["source_file"] = selected["source_file"]
    population.append(compact)
    while len(population) < max(1, population_size):
        population.append(_make_genome(model_id=model_id, rng=rng, gene_pool=gene_pool, base_name="gene"))
    return population[: max(1, population_size)]


def _mutate(
    genome: dict[str, Any],
    *,
    rng: random.Random,
    gene_pool: dict[str, list[dict[str, Any]]],
    failure_hints: list[str],
) -> dict[str, Any]:
    child = _copy_jsonable(genome)
    child["id"] = f"mut-{seeded_uuid(rng)}"
    child["seed"] = rng.randint(1, 10**9)
    child.setdefault("params", {})
    child.setdefault("block_params", {})
    choice = rng.choice(["swap_gene", "micro_rule", "strategy", "temperature", "max_tokens", "few_shot"])
    if choice == "swap_gene":
        block_id = rng.choice(["01", "02", "03", "06"])
        selected = rng.choice(gene_pool[block_id])
        child["block_params"].setdefault(block_id, {})["source_file"] = selected["source_file"]
    elif choice == "micro_rule":
        block_id = rng.choice(["02", "03", "06"])
        rules = list(child["block_params"].setdefault(block_id, {}).get("micro_rules") or [])
        feedback_rules = _rules_from_failures(failure_hints)
        candidate_rule = rng.choice(feedback_rules or BASE_MICRO_RULES)
        if candidate_rule not in rules:
            rules.append(candidate_rule)
        child["block_params"][block_id]["micro_rules"] = rules[-5:]
    elif choice == "strategy":
        child["params"]["candidate_strategies"] = rng.sample(STRATEGY_POOL, k=rng.randint(2, min(5, len(STRATEGY_POOL))))
    elif choice == "temperature":
        child["params"]["temperature"] = rng.choice([0.0, 0.0, 0.05, 0.1])
    elif choice == "max_tokens":
        child["params"]["max_tokens"] = rng.choice([512, 768, 1024, 1280])
    elif choice == "few_shot":
        child["block_params"].setdefault("02", {})["few_shot_count"] = rng.choice([1, 2, 3])
    return child


def _crossover(parent_a: dict[str, Any], parent_b: dict[str, Any], *, rng: random.Random) -> dict[str, Any]:
    child = _copy_jsonable(parent_a if rng.random() < 0.5 else parent_b)
    child["id"] = f"cross-{seeded_uuid(rng)}"
    child["seed"] = rng.randint(1, 10**9)
    child.setdefault("params", {})
    child.setdefault("block_params", {})
    for block_id in ["01", "02", "03", "06"]:
        owner = parent_a if rng.random() < 0.5 else parent_b
        if block_id in owner.get("block_params", {}):
            child["block_params"][block_id] = _copy_jsonable(owner["block_params"][block_id])
    for key in {"temperature", "max_tokens", "candidate_strategies", "model"}:
        owner = parent_a if rng.random() < 0.5 else parent_b
        if key in owner.get("params", {}):
            child["params"][key] = _copy_jsonable(owner["params"][key])
    child["blocks"] = ["01", "02", "03", "06"]
    return child


def _rules_from_failures(failure_hints: list[str]) -> list[str]:
    rules: list[str] = []
    for reason in failure_hints:
        normalized = str(reason).split(":", 1)[0]
        if normalized in FAILURE_FEEDBACK_RULES:
            rules.append(FAILURE_FEEDBACK_RULES[normalized])
        elif str(reason).startswith("unknown_service"):
            rules.append(FAILURE_FEEDBACK_RULES["unknown_service"])
    return list(dict.fromkeys(rules))


def _candidate_strategies(genome: dict[str, Any], candidate_k: int) -> list[str]:
    strategies = list(genome.get("params", {}).get("candidate_strategies") or STRATEGY_POOL)
    if not strategies:
        strategies = ["direct"]
    return [strategies[idx % len(strategies)] for idx in range(max(1, candidate_k))]


def _temperature_max_tokens(args: argparse.Namespace, genome: dict[str, Any]) -> tuple[float, int]:
    params = genome.get("params", {})
    temperature = args.temperature if args.temperature is not None else params.get("temperature", 0.0)
    max_tokens = args.max_tokens if args.max_tokens is not None else params.get("max_tokens", 768)
    return float(temperature), int(max_tokens)


def _metric_progress(metrics: dict[str, Any]) -> dict[str, Any]:
    rows = list(metrics.get("rows") or [])
    row_count = len(rows)
    scores = [float(row.get("det_score") or 0.0) for row in rows]
    gt_exact_count = sum(1 for row in rows if bool(row.get("det_gt_exact")))
    pass_count = sum(
        1
        for row in rows
        if bool(row.get("det_gt_exact")) or float(row.get("det_score") or 0.0) >= DET_PASS_THRESHOLD
    )
    return {
        "row_count": row_count,
        "avg_det_score": round(statistics.fmean(scores), 4) if scores else 0.0,
        "variance": round(statistics.pvariance(scores), 6) if len(scores) > 1 else 0.0,
        "det_pass_count": pass_count,
        "det_pass_rate": round((pass_count / row_count) * 100.0, 4) if row_count else 0.0,
        "gt_exact_count": gt_exact_count,
        "gt_exact_rate": round((gt_exact_count / row_count) * 100.0, 4) if row_count else 0.0,
    }


def _evaluate_genome(
    *,
    args: argparse.Namespace,
    genome: dict[str, Any],
    entry: dict[str, Any],
    row_subset: list[tuple[int, dict[str, str]]],
    service_schema: dict[str, dict[str, Any]],
    run_dir: Path,
    run_label: str,
    seed: int,
) -> dict[str, Any]:
    candidates_dir = run_dir / "candidates"
    evaluations_dir = run_dir / "evaluations"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    evaluations_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{slugify(run_label)}_{slugify(genome.get('id', 'genome'))}_{seed}"
    output_csv = candidates_dir / f"{run_id}.csv"
    temperature, max_tokens = _temperature_max_tokens(args, genome)
    started = time.perf_counter()
    generation_summary = generate_candidates_for_rows(
        profile=args.profile,
        genome=genome,
        dataset_rows=row_subset,
        service_schema=service_schema,
        candidate_k=args.candidate_k,
        llm_mode=args.llm_mode,
        llm_endpoint=args.llm_endpoint,
        timeout_sec=args.timeout_sec,
        retries=args.retries,
        run_id=run_id,
        output_csv=output_csv,
        seed=seed,
        temperature=temperature,
        max_tokens=max_tokens,
        model=entry["model"],
        llm_extra_payload=entry.get("llm_extra_payload") or {},
        service_context_kwargs=_service_context_kwargs(args),
        prompt_render_mode="blocks",
        prompt_assets_dir=None,
    )
    det_rows: list[dict[str, Any]] = []
    scores: list[float] = []
    failure_counter: Counter[str] = Counter()
    token_totals = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "llm_latency_sec": 0.0,
        "pipeline_sec": 0.0,
        "peak_vram_gb": 0.0,
    }
    for row in generation_summary.get("rows", []):
        command_eng = str(row.get("command_eng", "") or "")
        candidates = json.loads(row.get("candidates", "[]")) if row.get("candidates") else []
        scored = evaluate_candidates(
            command_eng,
            candidates,
            service_schema,
            connected_devices=row.get("connected_devices", ""),
            ground_truth=row.get("gt", ""),
            profile=args.det_profile,
        )
        best = scored[0] if scored else {
            "det_score": 0.0,
            "failure_reasons": ["no_candidates"],
            "candidate": "",
            "det_gt_exact": False,
            "det_gt_similarity": 0.0,
        }
        reasons = list(best.get("failure_reasons") or [])
        failure_counter.update(str(reason) for reason in reasons)
        scores.append(float(best.get("det_score", 0.0)))
        token_totals["prompt_tokens"] += int(float(row.get("generation_prompt_tokens_total") or 0))
        token_totals["completion_tokens"] += int(float(row.get("generation_completion_tokens_total") or 0))
        token_totals["total_tokens"] += int(float(row.get("generation_total_tokens_total") or 0))
        token_totals["llm_latency_sec"] += float(row.get("generation_llm_latency_sec") or 0.0)
        token_totals["pipeline_sec"] += float(row.get("generation_total_pipeline_sec") or 0.0)
        token_totals["peak_vram_gb"] = max(token_totals["peak_vram_gb"], float(row.get("generation_peak_vram_gb") or 0.0))
        det_rows.append(
            {
                "row_no": int(row.get("row_no") or 0),
                "category": str(row.get("category", "") or ""),
                "command_eng": command_eng,
                "det_score": float(best.get("det_score", 0.0)),
                "det_gt_exact": bool(best.get("det_gt_exact", False)),
                "det_gt_similarity": float(best.get("det_gt_similarity", 0.0)),
                "failure_reasons": reasons,
                "output": best.get("candidate", ""),
                "gt": row.get("gt", ""),
                "service_list_snippet_source": row.get("service_list_snippet_source", ""),
                "service_list_retrieval_status": row.get("service_list_retrieval_status", ""),
                "service_list_retrieval_categories": row.get("service_list_retrieval_categories", ""),
            }
        )
    metric = _metric_progress({"rows": det_rows})
    metric["elapsed_sec"] = round(time.perf_counter() - started, 4)
    metric["generation_output_csv"] = str(output_csv)
    metric["failure_summary"] = dict(failure_counter.most_common())
    metric["failure_patterns"] = summarize_failure_patterns(det_rows)
    metric.update({key: round(value, 4) if isinstance(value, float) else value for key, value in token_totals.items()})
    evaluation = {
        "run_label": run_label,
        "genome": genome,
        "metrics": metric,
        "rows": det_rows,
        "generation_summary": generation_summary,
    }
    dump_json(evaluations_dir / f"{run_id}.json", evaluation)
    return evaluation


def _fitness(metrics: dict[str, Any], *, alpha: float) -> float:
    return float(metrics.get("avg_det_score") or 0.0) - alpha * float(metrics.get("variance") or 0.0)


def _tournament(evaluated: list[dict[str, Any]], *, rng: random.Random, size: int = 3) -> dict[str, Any]:
    contenders = rng.sample(evaluated, k=min(size, len(evaluated)))
    contenders.sort(
        key=lambda item: (
            -float(item["fitness"]),
            -float(item["validation_metrics"].get("avg_det_score") or 0.0),
            str(item["genome"].get("id", "")),
        )
    )
    return contenders[0]["genome"]


def _failure_hints_from_evaluated(evaluated: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for item in evaluated[: max(1, min(3, len(evaluated)))]:
        counter.update((item.get("validation_metrics") or {}).get("failure_summary") or {})
        counter.update((item.get("train_metrics") or {}).get("failure_summary") or {})
    return [reason for reason, _count in counter.most_common(8)]


def run_one_model_category(
    *,
    args: argparse.Namespace,
    entry: dict[str, Any],
    category: str,
    selected_rows: list[tuple[int, dict[str, str]]],
    service_schema: dict[str, dict[str, Any]],
    gene_pool: dict[str, list[dict[str, Any]]],
    output_root: Path,
    seed: int,
) -> dict[str, Any]:
    rng = random.Random(seed)
    model_key = str(entry["key"])
    run_dir = output_root / "runs" / slugify(model_key) / f"cat{slugify(category)}"
    run_dir.mkdir(parents=True, exist_ok=True)

    validation_rows = sample_rows(selected_rows, sample_size=min(args.validation_size, len(selected_rows)), seed=seed + 9000)
    validation_row_nos = {row_no for row_no, _row in validation_rows}
    train_candidates = [item for item in selected_rows if item[0] not in validation_row_nos] or selected_rows

    population = _initial_population(
        model_id=entry["model"],
        rng=rng,
        gene_pool=gene_pool,
        population_size=args.population,
    )
    generation_progress: list[dict[str, Any]] = []
    population_records: list[dict[str, Any]] = []
    best_history: list[dict[str, Any]] = []
    global_best: dict[str, Any] | None = None
    failure_hints: list[str] = []

    for generation in range(1, max(1, args.gens) + 1):
        train_rows = sample_rows(
            train_candidates,
            sample_size=min(args.sample_size, len(train_candidates)),
            seed=seed + generation,
        ) or train_candidates
        if args.cheap_eval_limit > 0 and len(train_rows) > args.cheap_eval_limit:
            quick_rows = train_rows[: args.cheap_eval_limit]
        else:
            quick_rows = train_rows

        evaluated: list[dict[str, Any]] = []
        for genome in population:
            quick_eval = _evaluate_genome(
                args=args,
                genome=genome,
                entry=entry,
                row_subset=quick_rows,
                service_schema=service_schema,
                run_dir=run_dir,
                run_label=f"g{generation:03d}_quick",
                seed=seed + generation + int(genome.get("seed", 0)) % 10000,
            )
            train_eval = quick_eval
            if len(train_rows) > len(quick_rows) and float(quick_eval["metrics"].get("avg_det_score") or 0.0) > 0.0:
                train_eval = _evaluate_genome(
                    args=args,
                    genome=genome,
                    entry=entry,
                    row_subset=train_rows,
                    service_schema=service_schema,
                    run_dir=run_dir,
                    run_label=f"g{generation:03d}_train",
                    seed=seed + generation + int(genome.get("seed", 0)) % 10000 + 101,
                )
            validation_eval = _evaluate_genome(
                args=args,
                genome=genome,
                entry=entry,
                row_subset=validation_rows,
                service_schema=service_schema,
                run_dir=run_dir,
                run_label=f"g{generation:03d}_valid",
                seed=seed + generation + int(genome.get("seed", 0)) % 10000 + 500000,
            )
            train_metrics = train_eval["metrics"]
            validation_metrics = validation_eval["metrics"]
            record = {
                "model_key": model_key,
                "model_label": entry.get("label", model_key),
                "category": category,
                "generation": generation,
                "genome_id": genome.get("id", ""),
                "fitness": round(_fitness(train_metrics, alpha=args.alpha), 6),
                "train_avg_det_score": train_metrics.get("avg_det_score", 0.0),
                "train_variance": train_metrics.get("variance", 0.0),
                "train_det_pass_rate": train_metrics.get("det_pass_rate", 0.0),
                "train_gt_exact_rate": train_metrics.get("gt_exact_rate", 0.0),
                "validation_avg_det_score": validation_metrics.get("avg_det_score", 0.0),
                "validation_variance": validation_metrics.get("variance", 0.0),
                "validation_det_pass_rate": validation_metrics.get("det_pass_rate", 0.0),
                "validation_gt_exact_rate": validation_metrics.get("gt_exact_rate", 0.0),
                "prompt_tokens": validation_metrics.get("prompt_tokens", 0),
                "llm_latency_sec": validation_metrics.get("llm_latency_sec", 0.0),
                "peak_vram_gb": validation_metrics.get("peak_vram_gb", 0.0),
                "block_01": _block_source(genome, "01"),
                "block_02": _block_source(genome, "02"),
                "block_03": _block_source(genome, "03"),
                "block_06": _block_source(genome, "06"),
                "failure_summary": json.dumps(validation_metrics.get("failure_summary", {}), ensure_ascii=False),
            }
            population_records.append(record)
            evaluated.append(
                {
                    "genome": genome,
                    "fitness": record["fitness"],
                    "train_metrics": train_metrics,
                    "validation_metrics": validation_metrics,
                    "record": record,
                }
            )

        evaluated.sort(
            key=lambda item: (
                -float(item["fitness"]),
                -float(item["validation_metrics"].get("avg_det_score") or 0.0),
                str(item["genome"].get("id", "")),
            )
        )
        generation_best = evaluated[0]
        best_record = dict(generation_best["record"])
        best_record["rank_scope"] = "generation_best"
        generation_progress.append(best_record)
        best_history.append(
            {
                "generation": generation,
                "genome_id": generation_best["genome"].get("id", ""),
                "fitness": generation_best["fitness"],
                "train_metrics": generation_best["train_metrics"],
                "validation_metrics": generation_best["validation_metrics"],
                "genome": generation_best["genome"],
            }
        )

        if (
            global_best is None
            or float(generation_best["validation_metrics"].get("avg_det_score") or 0.0)
            > float(global_best["validation_metrics"].get("avg_det_score") or 0.0)
        ):
            global_best = generation_best

        failure_hints = _failure_hints_from_evaluated(evaluated)
        elites = [_copy_jsonable(item["genome"]) for item in evaluated[: max(1, args.elites)]]
        next_population: list[dict[str, Any]] = elites
        if failure_hints and len(next_population) < max(1, args.population):
            next_population.append(
                _mutate(
                    generation_best["genome"],
                    rng=rng,
                    gene_pool=gene_pool,
                    failure_hints=failure_hints,
                )
            )
        while len(next_population) < max(1, args.population):
            parent_a = _tournament(evaluated, rng=rng)
            if rng.random() < args.crossover_rate and len(evaluated) > 1:
                parent_b = _tournament(evaluated, rng=rng)
                child = _crossover(parent_a, parent_b, rng=rng)
            else:
                child = _copy_jsonable(parent_a)
                child["id"] = f"clone-{seeded_uuid(rng)}"
                child["seed"] = rng.randint(1, 10**9)
            if rng.random() < args.mutation_rate:
                child = _mutate(child, rng=rng, gene_pool=gene_pool, failure_hints=failure_hints)
            next_population.append(child)
        population = next_population[: max(1, args.population)]

        atomic_write_csv(run_dir / "ga_generation_progress.csv", list(generation_progress[0].keys()), generation_progress)
        atomic_write_csv(run_dir / "ga_population_evaluations.csv", list(population_records[0].keys()), population_records)
        dump_json(run_dir / "best_history.json", best_history)
        dump_json(run_dir / "best_genome.json", global_best["genome"] if global_best else generation_best["genome"])

        print(
            f"[{model_key} cat{category}] gen {generation}/{args.gens}: "
            f"valid_det={best_record['validation_avg_det_score']} "
            f"pass={best_record['validation_det_pass_rate']} "
            f"best={best_record['genome_id']}",
            flush=True,
        )

    final_eval: dict[str, Any] | None = None
    if global_best and not args.skip_final_eval:
        final_eval = _evaluate_genome(
            args=args,
            genome=global_best["genome"],
            entry=entry,
            row_subset=selected_rows,
            service_schema=service_schema,
            run_dir=run_dir,
            run_label="final_all_rows",
            seed=seed + 800000,
        )
        dump_json(run_dir / "final_all_rows_eval.json", final_eval)

    first = generation_progress[0] if generation_progress else {}
    best = max(
        generation_progress,
        key=lambda item: (
            float(item.get("validation_avg_det_score") or 0.0),
            float(item.get("validation_det_pass_rate") or 0.0),
        ),
    ) if generation_progress else {}
    final_metrics = final_eval["metrics"] if final_eval else (global_best or {}).get("validation_metrics", {})
    summary = {
        "model_key": model_key,
        "model_label": entry.get("label", model_key),
        "model_id": entry.get("model", ""),
        "category": category,
        "row_count": len(selected_rows),
        "validation_row_count": len(validation_rows),
        "generation_count": len(generation_progress),
        "first_generation_validation_det": first.get("validation_avg_det_score", 0.0),
        "best_generation": best.get("generation", ""),
        "best_genome_id": best.get("genome_id", ""),
        "best_validation_det": best.get("validation_avg_det_score", 0.0),
        "best_validation_pass_rate": best.get("validation_det_pass_rate", 0.0),
        "improvement_vs_generation1": round(
            float(best.get("validation_avg_det_score") or 0.0) - float(first.get("validation_avg_det_score") or 0.0),
            4,
        ),
        "final_all_avg_det": final_metrics.get("avg_det_score", 0.0),
        "final_all_pass_rate": final_metrics.get("det_pass_rate", 0.0),
        "final_all_gt_exact_rate": final_metrics.get("gt_exact_rate", 0.0),
        "final_all_prompt_tokens": final_metrics.get("prompt_tokens", 0),
        "final_all_llm_latency_sec": final_metrics.get("llm_latency_sec", 0.0),
        "final_all_peak_vram_gb": final_metrics.get("peak_vram_gb", 0.0),
        "run_dir": str(run_dir),
        "best_genome_path": str(run_dir / "best_genome.json"),
    }
    dump_json(run_dir / "run_summary.json", summary)
    return {
        "summary": summary,
        "progress": generation_progress,
        "population_records": population_records,
    }


def _plot_study(output_root: Path, progress_rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]]) -> dict[str, str]:
    figures_dir = output_root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    statuses: dict[str, str] = {}
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        return {"matplotlib": f"skipped: {exc}"}

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in progress_rows:
        grouped[f"{row.get('model_key')} cat{row.get('category')}"].append(row)

    fig, ax = plt.subplots(figsize=(13, 7), constrained_layout=True)
    for label, rows in sorted(grouped.items()):
        rows = sorted(rows, key=lambda item: int(item.get("generation") or 0))
        ax.plot(
            [int(row.get("generation") or 0) for row in rows],
            [float(row.get("validation_avg_det_score") or 0.0) for row in rows],
            marker="o",
            linewidth=1.8,
            label=label,
        )
    ax.set_title("Validation DET by GA generation")
    ax.set_xlabel("Generation")
    ax.set_ylabel("Validation DET")
    ax.grid(True, alpha=0.25)
    if len(grouped) <= 16:
        ax.legend(fontsize=8)
    det_path = figures_dir / "validation_det_by_generation.png"
    fig.savefig(det_path, dpi=180)
    plt.close(fig)
    statuses["validation_det_by_generation"] = str(det_path)

    fig, ax = plt.subplots(figsize=(13, 7), constrained_layout=True)
    for label, rows in sorted(grouped.items()):
        rows = sorted(rows, key=lambda item: int(item.get("generation") or 0))
        ax.plot(
            [int(row.get("generation") or 0) for row in rows],
            [float(row.get("validation_det_pass_rate") or 0.0) for row in rows],
            marker="s",
            linewidth=1.8,
            label=label,
        )
    ax.set_title("Validation DET pass rate by GA generation")
    ax.set_xlabel("Generation")
    ax.set_ylabel("Pass rate (%)")
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.25)
    if len(grouped) <= 16:
        ax.legend(fontsize=8)
    pass_path = figures_dir / "validation_pass_rate_by_generation.png"
    fig.savefig(pass_path, dpi=180)
    plt.close(fig)
    statuses["validation_pass_rate_by_generation"] = str(pass_path)

    models = sorted({str(row.get("model_key")) for row in summary_rows})
    categories = sorted(
        {str(row.get("category")) for row in summary_rows},
        key=lambda item: (int(item) if item.isdigit() else 10**9, item),
    )
    matrix = [[math.nan for _ in categories] for _ in models]
    for row in summary_rows:
        model_idx = models.index(str(row.get("model_key")))
        category_idx = categories.index(str(row.get("category")))
        matrix[model_idx][category_idx] = float(row.get("final_all_avg_det") or row.get("best_validation_det") or 0.0)
    fig, ax = plt.subplots(figsize=(max(8, len(categories) * 0.75), max(4, len(models) * 0.6)), constrained_layout=True)
    image = ax.imshow(matrix, aspect="auto", cmap="viridis", vmin=0, vmax=100)
    ax.set_xticks(range(len(categories)), [f"cat{cat}" for cat in categories], rotation=45, ha="right")
    ax.set_yticks(range(len(models)), models)
    ax.set_title("Best/final DET heatmap by local model and category")
    for row_idx, model in enumerate(models):
        for col_idx, category in enumerate(categories):
            value = matrix[row_idx][col_idx]
            if not math.isnan(value):
                ax.text(col_idx, row_idx, f"{value:.1f}", ha="center", va="center", color="white", fontsize=8)
    fig.colorbar(image, ax=ax, label="DET")
    heatmap_path = figures_dir / "best_det_heatmap.png"
    fig.savefig(heatmap_path, dpi=180)
    plt.close(fig)
    statuses["best_det_heatmap"] = str(heatmap_path)

    fig, ax = plt.subplots(figsize=(13, 7), constrained_layout=True)
    labels = [f"{row.get('model_key')} c{row.get('category')}" for row in summary_rows]
    values = [float(row.get("improvement_vs_generation1") or 0.0) for row in summary_rows]
    colors = ["#3b7ddd" if value >= 0 else "#d9534f" for value in values]
    ax.bar(range(len(labels)), values, color=colors)
    ax.axhline(0, color="#333", linewidth=0.8)
    ax.set_title("GA improvement over generation 1")
    ax.set_ylabel("Validation DET delta")
    ax.set_xticks(range(len(labels)), labels, rotation=60, ha="right", fontsize=8)
    ax.grid(True, axis="y", alpha=0.25)
    improvement_path = figures_dir / "improvement_vs_generation1.png"
    fig.savefig(improvement_path, dpi=180)
    plt.close(fig)
    statuses["improvement_vs_generation1"] = str(improvement_path)

    failure_counter: Counter[str] = Counter()
    for row in progress_rows:
        try:
            failure_summary = json.loads(str(row.get("failure_summary") or "{}"))
        except Exception:
            failure_summary = {}
        for reason, count in failure_summary.items():
            failure_counter[str(reason)] += int(count or 0)
    if failure_counter:
        top_items = failure_counter.most_common(14)
        fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True)
        ax.barh([item[0] for item in reversed(top_items)], [item[1] for item in reversed(top_items)], color="#8f6b43")
        ax.set_title("Failure reasons observed in generation-best prompts")
        ax.set_xlabel("Count")
        ax.grid(True, axis="x", alpha=0.25)
        failure_path = figures_dir / "failure_reason_counts.png"
        fig.savefig(failure_path, dpi=180)
        plt.close(fig)
        statuses["failure_reason_counts"] = str(failure_path)
    return statuses


def _failure_feedback_rows(progress_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in progress_rows:
        try:
            failure_summary = json.loads(str(row.get("failure_summary") or "{}"))
        except Exception:
            failure_summary = {}
        feedback_rules = _rules_from_failures(list(failure_summary.keys()))
        for reason, count in sorted(failure_summary.items(), key=lambda item: (-int(item[1] or 0), str(item[0]))):
            rows.append(
                {
                    "model_key": row.get("model_key", ""),
                    "category": row.get("category", ""),
                    "generation": row.get("generation", ""),
                    "genome_id": row.get("genome_id", ""),
                    "failure_reason": reason,
                    "failure_count": count,
                    "feedback_rule_candidates": " | ".join(feedback_rules),
                    "validation_avg_det_score": row.get("validation_avg_det_score", ""),
                    "validation_det_pass_rate": row.get("validation_det_pass_rate", ""),
                }
            )
    return rows


def _write_markdown_report(output_root: Path, summary_rows: list[dict[str, Any]], plot_status: dict[str, str]) -> Path:
    lines = [
        "# Local Prompt GA Study Report",
        "",
        f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"- result_dir: `{output_root}`",
        "",
        "## Figure Artifacts",
    ]
    for name, path in plot_status.items():
        lines.append(f"- {name}: `{path}`")
    failure_csv = output_root / "ga_failure_feedback_summary.csv"
    if failure_csv.exists():
        lines.append(f"- failure feedback summary: `{failure_csv}`")
    lines.extend(["", "## Best Results by Model and Category", ""])
    headers = [
        "model",
        "cat",
        "rows",
        "best_gen",
        "gen1_det",
        "best_valid_det",
        "delta",
        "final_det",
        "final_pass",
        "gt_exact",
    ]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in summary_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("model_key", "")),
                    str(row.get("category", "")),
                    str(row.get("row_count", "")),
                    str(row.get("best_generation", "")),
                    f"{float(row.get('first_generation_validation_det') or 0.0):.4f}",
                    f"{float(row.get('best_validation_det') or 0.0):.4f}",
                    f"{float(row.get('improvement_vs_generation1') or 0.0):+.4f}",
                    f"{float(row.get('final_all_avg_det') or 0.0):.4f}",
                    f"{float(row.get('final_all_pass_rate') or 0.0):.2f}%",
                    f"{float(row.get('final_all_gt_exact_rate') or 0.0):.2f}%",
                ]
            )
            + " |"
        )
    report_path = output_root / "paper_report.md"
    _write_text(report_path, "\n".join(lines))
    return report_path


def _write_html_report(output_root: Path, summary_rows: list[dict[str, Any]], plot_status: dict[str, str], markdown_path: Path) -> Path:
    def rel(path_value: str) -> str:
        try:
            return str(Path(path_value).relative_to(output_root))
        except Exception:
            return path_value

    rows_html = []
    for row in summary_rows:
        delta = float(row.get("improvement_vs_generation1") or 0.0)
        cls = "good" if delta >= 0 else "bad"
        rows_html.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('model_key', '')))}</td>"
            f"<td>cat{html.escape(str(row.get('category', '')))}</td>"
            f"<td>{html.escape(str(row.get('row_count', '')))}</td>"
            f"<td>{html.escape(str(row.get('best_generation', '')))}</td>"
            f"<td>{float(row.get('first_generation_validation_det') or 0.0):.4f}</td>"
            f"<td>{float(row.get('best_validation_det') or 0.0):.4f}</td>"
            f"<td class='{cls}'>{delta:+.4f}</td>"
            f"<td>{float(row.get('final_all_avg_det') or 0.0):.4f}</td>"
            f"<td>{float(row.get('final_all_pass_rate') or 0.0):.2f}%</td>"
            f"<td>{float(row.get('final_all_gt_exact_rate') or 0.0):.2f}%</td>"
            f"<td><code>{html.escape(str(row.get('run_dir', '')))}</code></td>"
            "</tr>"
        )
    figure_cards = []
    for name, path_value in plot_status.items():
        if not str(path_value).endswith(".png"):
            continue
        figure_cards.append(
            f"<section class='figure'><h2>{html.escape(name.replace('_', ' ').title())}</h2>"
            f"<img src='{html.escape(rel(path_value))}' alt='{html.escape(name)}'></section>"
        )
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Local Prompt GA Study</title>
  <style>
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f2e9; color: #1f2933; }}
    header {{ padding: 34px 42px; background: linear-gradient(135deg, #263238, #6b4f3a); color: #fff; }}
    header h1 {{ margin: 0 0 8px; font-size: 32px; }}
    main {{ padding: 28px 42px 60px; }}
    table {{ border-collapse: collapse; width: 100%; background: #fff; box-shadow: 0 12px 35px rgba(31,41,51,.10); border-radius: 14px; overflow: hidden; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #e8e1d5; font-size: 13px; text-align: right; }}
    th:first-child, td:first-child, td:last-child {{ text-align: left; }}
    th {{ background: #efe2cf; color: #3d3025; position: sticky; top: 0; }}
    .good {{ color: #126b3a; font-weight: 700; }}
    .bad {{ color: #a9342f; font-weight: 700; }}
    .figure {{ margin-top: 28px; padding: 20px; background: #fff; border-radius: 18px; box-shadow: 0 12px 35px rgba(31,41,51,.10); }}
    .figure img {{ max-width: 100%; display: block; margin: 0 auto; }}
    code {{ white-space: nowrap; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <h1>Local Prompt Genetic Search Study</h1>
    <p>version0_13 prompt assets are split into version0_15 block genes and evolved per local model and category.</p>
    <p>Markdown companion: <code>{html.escape(str(markdown_path))}</code></p>
  </header>
  <main>
    <h2>Best Results</h2>
    <table>
      <thead><tr>
        <th>model</th><th>cat</th><th>rows</th><th>best gen</th><th>gen1 DET</th><th>best valid DET</th><th>delta</th><th>final DET</th><th>final pass</th><th>GT exact</th><th>run dir</th>
      </tr></thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>
    {''.join(figure_cards)}
  </main>
</body>
</html>
"""
    html_path = output_root / "index.html"
    _write_text(html_path, html_text)
    return html_path


def run_study(args: argparse.Namespace) -> dict[str, Any]:
    ensure_workspace()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root = Path(args.output_root).expanduser().resolve() if args.output_root else RESULTS_DIR / f"local_prompt_ga_study_{timestamp}"
    output_root.mkdir(parents=True, exist_ok=True)

    prompt_assets_dir = Path(args.prompt_assets_dir).expanduser().resolve()
    gene_pool, gene_manifest = build_gene_pool(prompt_assets_dir=prompt_assets_dir, output_root=output_root, detail=args.v13_detail)
    rows = load_dataset_rows(args.dataset)
    selected_all = select_rows(rows, start_row=1, end_row=None, limit=args.limit, categories=[])
    selected_all = _limit_rows_per_category(selected_all, limit_per_category=args.limit_per_category)
    categories = _parse_repeated(args.category) or _categories_from_rows(selected_all)
    service_schema = load_service_schema(args.service_schema)
    entries = _model_entries(_parse_repeated(args.model_key))
    preflight_rows = [
        _inspect_model_runtime(entry, args=args, global_llm_extra={})
        for entry in entries
    ]
    if args.preflight_only:
        _print_preflight(preflight_rows, print_worker_info=args.print_worker_info)
        return {"output_root": str(output_root), "preflight": preflight_rows, "preflight_only": True}
    unavailable = [row for row in preflight_rows if row.get("status") != "ready"]
    if unavailable and args.strict_availability:
        _print_preflight(preflight_rows, print_worker_info=args.print_worker_info)
        raise SystemExit(
            "Unavailable models: "
            + ", ".join(f"{row.get('model_key')}={row.get('status')}" for row in unavailable)
        )
    if unavailable and args.skip_unavailable:
        ready_keys = {str(row.get("model_key")) for row in preflight_rows if row.get("status") == "ready"}
        entries = [entry for entry in entries if str(entry.get("key")) in ready_keys]
        if not entries:
            raise SystemExit("No ready models after --skip-unavailable.")

    manifest = {
        "output_root": str(output_root),
        "dataset": str(Path(args.dataset).expanduser().resolve()),
        "service_schema": str(Path(args.service_schema).expanduser().resolve()),
        "prompt_assets_dir": str(prompt_assets_dir),
        "gene_pool_manifest": str(gene_manifest),
        "models": entries,
        "preflight": preflight_rows,
        "categories": categories,
        "args": vars(args),
    }
    dump_json(output_root / "study_manifest.json", manifest)

    if args.dry_run:
        print(json.dumps({"dry_run": True, "output_root": str(output_root), "gene_pool_manifest": str(gene_manifest)}, indent=2))
        return {"output_root": str(output_root), "dry_run": True}

    summary_rows: list[dict[str, Any]] = []
    progress_rows: list[dict[str, Any]] = []
    population_rows: list[dict[str, Any]] = []

    for entry_index, entry in enumerate(entries):
        for category_index, category in enumerate(categories):
            category_rows = [item for item in selected_all if str(item[1].get("category", "")).strip() == str(category)]
            if not category_rows:
                print(f"[skip] {entry['key']} cat{category}: no rows selected", flush=True)
                continue
            run_seed = args.seed + entry_index * 100000 + category_index * 1000
            print(
                f"[start] model={entry['key']} category={category} rows={len(category_rows)} "
                f"population={args.population} gens={args.gens}",
                flush=True,
            )
            result = run_one_model_category(
                args=args,
                entry=entry,
                category=str(category),
                selected_rows=category_rows,
                service_schema=service_schema,
                gene_pool=gene_pool,
                output_root=output_root,
                seed=run_seed,
            )
            summary_rows.append(result["summary"])
            progress_rows.extend(result["progress"])
            population_rows.extend(result["population_records"])
            atomic_write_csv(output_root / "ga_best_by_model_category.csv", list(summary_rows[0].keys()), summary_rows)
            atomic_write_csv(output_root / "ga_progress_all.csv", list(progress_rows[0].keys()), progress_rows)
            atomic_write_csv(output_root / "ga_population_all.csv", list(population_rows[0].keys()), population_rows)

    plot_status = _plot_study(output_root, progress_rows, summary_rows) if progress_rows and summary_rows else {}
    failure_feedback_rows = _failure_feedback_rows(progress_rows)
    if failure_feedback_rows:
        atomic_write_csv(
            output_root / "ga_failure_feedback_summary.csv",
            list(failure_feedback_rows[0].keys()),
            failure_feedback_rows,
        )
    markdown_path = _write_markdown_report(output_root, summary_rows, plot_status)
    html_path = _write_html_report(output_root, summary_rows, plot_status, markdown_path)
    final_summary = {
        "output_root": str(output_root),
        "summary_csv": str(output_root / "ga_best_by_model_category.csv"),
        "progress_csv": str(output_root / "ga_progress_all.csv"),
        "population_csv": str(output_root / "ga_population_all.csv"),
        "failure_feedback_csv": str(output_root / "ga_failure_feedback_summary.csv") if failure_feedback_rows else "",
        "gene_pool_manifest": str(gene_manifest),
        "markdown_report": str(markdown_path),
        "html_report": str(html_path),
        "figures": plot_status,
        "run_count": len(summary_rows),
    }
    dump_json(output_root / "study_summary.json", final_summary)
    print(json.dumps(final_summary, ensure_ascii=False, indent=2), flush=True)
    return final_summary


def main() -> int:
    args = build_parser().parse_args()
    run_study(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
