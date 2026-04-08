#!/usr/bin/env python3
# Assumption: this GA search runs entirely inside gpt_mg/version0_14 and records all checkpoints/results there.
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from scripts.run_feedback_loop import evaluate_genome_on_rows, run_feedback_loop
from utils.pipeline_common import (
    CHECKPOINTS_DIR,
    DATASET_DEFAULT,
    RESULTS_DIR,
    SERVICE_SCHEMA_DEFAULT,
    dump_json,
    ensure_workspace,
    load_dataset_rows,
    load_genome,
    load_service_schema,
    sample_rows,
    seeded_uuid,
    select_rows,
)


MUTATION_RULES = [
    "Prefer canonical_name exactly when available.",
    "Use value entries in conditions and function entries in actions.",
    "For INTEGER and DOUBLE arguments, avoid quoted numeric literals.",
    "Return exactly one JSON object only with keys name, cron, period, code.",
    "Keep the code minimal and remove unrelated actions.",
]

OPTIONAL_BLOCKS = ["03", "06"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run genetic search over version0_14 prompt-block genomes.")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--genome-json", default=str(VERSION_ROOT / "genomes" / "example_genome.json"))
    parser.add_argument("--dataset", default=str(DATASET_DEFAULT))
    parser.add_argument("--service-schema", default=str(SERVICE_SCHEMA_DEFAULT))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--start-row", type=int, default=1)
    parser.add_argument("--end-row", type=int, default=None)
    parser.add_argument("--category", action="append", default=[], help="Filter by dataset category. Can be repeated or comma-separated.")
    parser.add_argument("--population", type=int, default=20)
    parser.add_argument("--gens", type=int, default=30)
    parser.add_argument("--crossover-rate", type=float, default=0.6)
    parser.add_argument("--mutation-rate", type=float, default=0.2)
    parser.add_argument("--elites", type=int, default=2)
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--cheap-eval-limit", type=int, default=5)
    parser.add_argument("--candidate-k", type=int, default=2)
    parser.add_argument("--validation-size", type=int, default=8)
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument("--plateau-generations", type=int, default=3)
    parser.add_argument("--feedback-attempts", type=int, default=3)
    parser.add_argument("--feedback-threshold", type=float, default=0.25)
    parser.add_argument("--llm-mode", default=None)
    parser.add_argument("--llm-endpoint", default=None)
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--seed", type=int, default=14)
    return parser


def _copy_genome(genome: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(genome))


def _normalize_blocks(blocks: list[str]) -> list[str]:
    ordered = []
    for block_id in ["01", "02", "03", "06"]:
        if block_id in blocks and block_id not in ordered:
            ordered.append(block_id)
    if "01" not in ordered:
        ordered.insert(0, "01")
    if "02" not in ordered:
        ordered.insert(1 if ordered and ordered[0] == "01" else 0, "02")
    return ordered


def _random_genome(base_genome: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    genome = _copy_genome(base_genome)
    genome["id"] = f"gen-{seeded_uuid(rng)}"
    genome["seed"] = rng.randint(1, 10**9)
    genome.setdefault("params", {})
    genome.setdefault("block_params", {})
    blocks = ["01", "02"]
    for block in OPTIONAL_BLOCKS:
        if rng.random() < 0.75:
            blocks.append(block)
    genome["blocks"] = _normalize_blocks(blocks)
    genome["params"]["temperature"] = rng.choice([0.0, 0.0, 0.05, 0.1])
    genome["params"]["max_tokens"] = rng.choice([512, 768, 1024])
    genome["params"]["candidate_strategies"] = rng.sample(
        ["direct", "minimal", "canonical_names_first", "explicit_preconditions", "compact_json"],
        k=rng.randint(2, 5),
    )
    block02 = genome.setdefault("block_params", {}).setdefault("02", {})
    block02["few_shot_count"] = rng.choice([1, 2, 3])
    block02["micro_rules"] = rng.sample(MUTATION_RULES, k=rng.randint(0, min(3, len(MUTATION_RULES))))
    return genome


def _mutate_genome(genome: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    child = _copy_genome(genome)
    child["id"] = f"gen-{seeded_uuid(rng)}"
    child["seed"] = rng.randint(1, 10**9)
    child.setdefault("params", {})
    child.setdefault("block_params", {})
    block02 = child["block_params"].setdefault("02", {})
    mutation_choice = rng.choice(["toggle_block", "few_shot", "max_tokens", "temperature", "micro_rules", "strategies"])
    if mutation_choice == "toggle_block":
        target = rng.choice(OPTIONAL_BLOCKS)
        blocks = list(child.get("blocks", ["01", "02", "03", "06"]))
        if target in blocks:
            blocks.remove(target)
        else:
            blocks.append(target)
        child["blocks"] = _normalize_blocks(blocks)
    elif mutation_choice == "few_shot":
        block02["few_shot_count"] = rng.choice([1, 2, 3])
    elif mutation_choice == "max_tokens":
        child["params"]["max_tokens"] = rng.choice([512, 768, 1024])
    elif mutation_choice == "temperature":
        child["params"]["temperature"] = rng.choice([0.0, 0.0, 0.05, 0.1])
    elif mutation_choice == "micro_rules":
        block02["micro_rules"] = rng.sample(MUTATION_RULES, k=rng.randint(0, min(3, len(MUTATION_RULES))))
    elif mutation_choice == "strategies":
        child["params"]["candidate_strategies"] = rng.sample(
            ["direct", "minimal", "canonical_names_first", "explicit_preconditions", "compact_json"],
            k=rng.randint(2, 5),
        )
    return child


def _crossover(parent_a: dict[str, Any], parent_b: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    child = _copy_genome(parent_a if rng.random() < 0.5 else parent_b)
    child["id"] = f"gen-{seeded_uuid(rng)}"
    child["seed"] = rng.randint(1, 10**9)
    child.setdefault("params", {})
    child.setdefault("block_params", {})

    blocks = []
    for block_id in ["01", "02", "03", "06"]:
        owner = parent_a if rng.random() < 0.5 else parent_b
        if block_id in owner.get("blocks", []):
            blocks.append(block_id)
    child["blocks"] = _normalize_blocks(blocks)
    for key in {*(parent_a.get("params", {}).keys()), *(parent_b.get("params", {}).keys())}:
        owner = parent_a if rng.random() < 0.5 else parent_b
        if key in owner.get("params", {}):
            child["params"][key] = owner["params"][key]
    for block_id in {*(parent_a.get("block_params", {}).keys()), *(parent_b.get("block_params", {}).keys())}:
        owner = parent_a if rng.random() < 0.5 else parent_b
        if block_id in owner.get("block_params", {}):
            child["block_params"][block_id] = _copy_genome(owner["block_params"][block_id])
    return child


def _tournament_select(population: list[dict[str, Any]], rng: random.Random, size: int = 3) -> dict[str, Any]:
    contenders = rng.sample(population, k=min(size, len(population)))
    contenders.sort(key=lambda item: (-float(item["fitness"]), float(item["variance"]), item["genome"]["id"]))
    return contenders[0]["genome"]


def _evaluate_one(
    *,
    profile: str,
    genome: dict[str, Any],
    train_rows: list[tuple[int, dict[str, str]]],
    validation_rows: list[tuple[int, dict[str, str]]],
    service_schema: dict[str, dict[str, Any]],
    candidate_k: int,
    cheap_eval_limit: int,
    llm_mode: str | None,
    llm_endpoint: str | None,
    timeout_sec: int,
    retries: int,
    alpha: float,
    seed: int,
) -> dict[str, Any]:
    cheap_rows = train_rows[: min(len(train_rows), cheap_eval_limit)]
    quick_metrics = evaluate_genome_on_rows(
        profile=profile,
        genome=genome,
        row_subset=cheap_rows,
        service_schema=service_schema,
        candidate_k=max(1, min(candidate_k, 2)),
        llm_mode=llm_mode,
        llm_endpoint=llm_endpoint,
        timeout_sec=timeout_sec,
        retries=retries,
        seed=seed,
        run_label="ga_quick",
    )
    metrics = quick_metrics
    if len(train_rows) > len(cheap_rows) and float(quick_metrics["avg_det_score"]) > 0.0:
        metrics = evaluate_genome_on_rows(
            profile=profile,
            genome=genome,
            row_subset=train_rows,
            service_schema=service_schema,
            candidate_k=candidate_k,
            llm_mode=llm_mode,
            llm_endpoint=llm_endpoint,
            timeout_sec=timeout_sec,
            retries=retries,
            seed=seed,
            run_label="ga_full",
        )
    validation_metrics = evaluate_genome_on_rows(
        profile=profile,
        genome=genome,
        row_subset=validation_rows,
        service_schema=service_schema,
        candidate_k=max(1, min(candidate_k, 2)),
        llm_mode=llm_mode,
        llm_endpoint=llm_endpoint,
        timeout_sec=timeout_sec,
        retries=retries,
        seed=seed + 500000,
        run_label="ga_validation",
    )
    fitness = float(metrics["avg_det_score"]) - alpha * float(metrics["variance"])
    evaluation = {
        "genome": genome,
        "fitness": round(fitness, 6),
        "avg_det_score": metrics["avg_det_score"],
        "variance": metrics["variance"],
        "validation_avg_det_score": validation_metrics["avg_det_score"],
        "train_metrics": metrics,
        "validation_metrics": validation_metrics,
    }
    dump_json(RESULTS_DIR / f"genome_{genome['id']}.json", evaluation)
    return evaluation


def run_ga_search(args: argparse.Namespace) -> dict[str, Any]:
    ensure_workspace()
    rng = random.Random(args.seed)
    base_genome = load_genome(args.genome_json)
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

    validation_rows = sample_rows(selected_rows, sample_size=args.validation_size, seed=args.seed + 9000)
    validation_row_nos = {row_no for row_no, _ in validation_rows}

    population = [_random_genome(base_genome, rng) for _ in range(args.population)]
    best_history: list[dict[str, Any]] = []
    global_best: dict[str, Any] | None = None
    no_improvement_generations = 0

    for generation in range(1, args.gens + 1):
        train_rows = sample_rows(
            selected_rows,
            sample_size=args.sample_size,
            seed=args.seed + generation,
            exclude_row_nos=validation_row_nos,
        )
        if not train_rows:
            train_rows = [item for item in selected_rows if item[0] not in validation_row_nos] or selected_rows

        evaluated_population: list[dict[str, Any]] = []
        for genome in population:
            evaluation = _evaluate_one(
                profile=args.profile,
                genome=genome,
                train_rows=train_rows,
                validation_rows=validation_rows,
                service_schema=service_schema,
                candidate_k=args.candidate_k,
                cheap_eval_limit=args.cheap_eval_limit,
                llm_mode=args.llm_mode,
                llm_endpoint=args.llm_endpoint,
                timeout_sec=args.timeout_sec,
                retries=args.retries,
                alpha=args.alpha,
                seed=args.seed + generation + int(genome.get("seed", 0)) % 10000,
            )
            evaluated_population.append(evaluation)

        evaluated_population.sort(
            key=lambda item: (-float(item["fitness"]), -float(item["validation_avg_det_score"]), item["genome"]["id"])
        )
        generation_best = evaluated_population[0]
        best_history.append(
            {
                "generation": generation,
                "genome_id": generation_best["genome"]["id"],
                "fitness": generation_best["fitness"],
                "avg_det_score": generation_best["avg_det_score"],
                "validation_avg_det_score": generation_best["validation_avg_det_score"],
                "genome": generation_best["genome"],
            }
        )
        dump_json(CHECKPOINTS_DIR / f"ga_generation_{generation:03d}.json", {"generation": generation, "population": evaluated_population})

        if global_best is None or float(generation_best["validation_avg_det_score"]) > float(global_best["validation_avg_det_score"]):
            global_best = generation_best
            no_improvement_generations = 0
        else:
            no_improvement_generations += 1

        if no_improvement_generations >= args.plateau_generations:
            feedback = run_feedback_loop(
                profile=args.profile,
                genome=generation_best["genome"],
                dataset_rows=selected_rows,
                service_schema=service_schema,
                validation_size=args.validation_size,
                candidate_k=max(1, min(args.candidate_k, 2)),
                attempts=args.feedback_attempts,
                improvement_threshold=args.feedback_threshold,
                llm_mode=args.llm_mode,
                llm_endpoint=args.llm_endpoint,
                timeout_sec=args.timeout_sec,
                retries=args.retries,
                seed=args.seed + generation,
            )
            if feedback.get("improved"):
                injected = feedback["best_genome"]
                injected_eval = _evaluate_one(
                    profile=args.profile,
                    genome=injected,
                    train_rows=train_rows,
                    validation_rows=validation_rows,
                    service_schema=service_schema,
                    candidate_k=args.candidate_k,
                    cheap_eval_limit=args.cheap_eval_limit,
                    llm_mode=args.llm_mode,
                    llm_endpoint=args.llm_endpoint,
                    timeout_sec=args.timeout_sec,
                    retries=args.retries,
                    alpha=args.alpha,
                    seed=args.seed + generation + 12345,
                )
                evaluated_population.append(injected_eval)
                evaluated_population.sort(
                    key=lambda item: (-float(item["fitness"]), -float(item["validation_avg_det_score"]), item["genome"]["id"])
                )
                generation_best = evaluated_population[0]
                if global_best is None or float(generation_best["validation_avg_det_score"]) > float(global_best["validation_avg_det_score"]):
                    global_best = generation_best
                no_improvement_generations = 0

        elites = [item["genome"] for item in evaluated_population[: max(1, args.elites)]]
        next_population: list[dict[str, Any]] = [_copy_genome(genome) for genome in elites]
        while len(next_population) < args.population:
            parent_a = _tournament_select(evaluated_population, rng)
            if rng.random() < args.crossover_rate and len(evaluated_population) > 1:
                parent_b = _tournament_select(evaluated_population, rng)
                child = _crossover(parent_a, parent_b, rng)
            else:
                child = _copy_genome(parent_a)
                child["id"] = f"gen-{seeded_uuid(rng)}"
                child["seed"] = rng.randint(1, 10**9)
            if rng.random() < args.mutation_rate:
                child = _mutate_genome(child, rng)
            next_population.append(child)
        population = next_population[: args.population]

        dump_json(RESULTS_DIR / "best_genomes.json", best_history)

    final_best = global_best if global_best is not None else {}
    summary = {
        "best_history": best_history,
        "best_genome": final_best.get("genome") if final_best else None,
        "best_fitness": final_best.get("fitness") if final_best else None,
        "best_validation_avg_det_score": final_best.get("validation_avg_det_score") if final_best else None,
    }
    dump_json(RESULTS_DIR / "ga_summary.json", summary)
    if summary["best_genome"] is not None:
        dump_json(RESULTS_DIR / "best_genome.json", summary["best_genome"])
    return summary


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    summary = run_ga_search(args)
    print("GA search completed")
    print(f"- best_fitness: {summary.get('best_fitness')}")
    print(f"- best_validation_avg_det_score: {summary.get('best_validation_avg_det_score')}")
    best_genome = summary.get("best_genome") or {}
    print(f"- best_genome_id: {best_genome.get('id', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
