#!/usr/bin/env python3
from __future__ import annotations

import json
import random
import csv
from pathlib import Path
from typing import Any

try:
    from .candidate_generation import generate_candidates_for_rows, write_candidate_csv
    from .evaluation import evaluate_candidate_records, write_evaluation_outputs
    from .fitness import load_fitness_config
    from .ga_operators import load_budget_config, next_generation
    from .gate import evaluate_adoption_gate, load_gate_config, subset_detpass_from_eval_rows
    from .prompt_patch_apply import rendered_prompt_with_genome
    from .replay import load_replay_split, replay_cases_to_rows, replay_pass_rate
    from .rerank import aggregate_genome_scores
except ImportError:
    from candidate_generation import generate_candidates_for_rows, write_candidate_csv  # type: ignore
    from evaluation import evaluate_candidate_records, write_evaluation_outputs  # type: ignore
    from fitness import load_fitness_config  # type: ignore
    from ga_operators import load_budget_config, next_generation  # type: ignore
    from gate import evaluate_adoption_gate, load_gate_config, subset_detpass_from_eval_rows  # type: ignore
    from prompt_patch_apply import rendered_prompt_with_genome  # type: ignore
    from replay import load_replay_split, replay_cases_to_rows, replay_pass_rate  # type: ignore
    from rerank import aggregate_genome_scores  # type: ignore


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fallback_genome(genome_id: str = "base") -> dict[str, Any]:
    return {
        "id": genome_id,
        "blocks": ["01", "02", "03", "06"],
        "params": {"candidate_strategies": ["mock_gt_copy"]},
        "block_params": {},
        "seed": 0,
    }


def _copy_json(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _csv_cell(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _write_rows_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: _csv_cell(row.get(col, "")) for col in columns})


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _render_for_genome(rendered_package: dict[str, Any], genome: dict[str, Any]) -> dict[str, Any]:
    patched = _copy_json(rendered_package)
    prompt = rendered_prompt_with_genome(rendered_package, genome)
    patched["prompt_text"] = prompt
    patched["system_prompt"] = prompt if not patched.get("user_prompt") else patched.get("system_prompt", "")
    patched["genome"] = genome
    messages = patched.get("messages")
    if isinstance(messages, list) and messages:
        new_messages = _copy_json(messages)
        for message in new_messages:
            if isinstance(message, dict) and message.get("role") == "system":
                message["content"] = prompt if not patched.get("user_prompt") else str(message.get("content") or "") + "\n\n" + prompt.split("[GA Prompt Patch Overlay]", 1)[-1]
                break
        else:
            new_messages.insert(0, {"role": "system", "content": prompt})
        patched["messages"] = new_messages
    return patched


def _initial_population(population: int, initial_genomes: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if initial_genomes:
        out = []
        for index, genome in enumerate(initial_genomes[: max(1, population)]):
            item = _copy_json(genome)
            item["id"] = str(item.get("id") or f"genome_{index:03d}")
            out.append(item)
        while len(out) < max(1, population):
            out.append(fallback_genome(f"genome_{len(out):03d}"))
        return out
    return [fallback_genome(f"genome_{idx:03d}") for idx in range(max(1, population))]


# 변이·교차 연산은 ga_operators.py 로 이동했다 (WI-16, 논문 6연산 + 블록 교차).


def _candidate_strategy(genome: dict[str, Any]) -> str:
    strategies = (genome.get("params") or {}).get("candidate_strategies")
    if isinstance(strategies, list) and strategies:
        return str(strategies[0])
    if isinstance(strategies, str) and strategies.strip():
        return strategies.strip()
    return "direct"


def run_mock_search(
    *,
    rows: list[tuple[int, dict[str, Any]]],
    rendered_package: dict[str, Any],
    out_dir: str | Path,
    population: int = 2,
    gens: int = 1,
    candidate_k: int = 1,
    llm_mode: str = "mock",
    det_threshold: float = 70.0,
    search_mode: str = "monolith",
    service_schema: str | Path | None = None,
    service_context_mode: str = "schema_fallback",
) -> dict[str, Any]:
    root = Path(out_dir)
    genomes_dir = root / "genomes"
    candidates_dir = root / "candidates"
    genomes_dir.mkdir(parents=True, exist_ok=True)
    candidates_dir.mkdir(parents=True, exist_ok=True)

    initial_population = [fallback_genome(f"genome_{idx:03d}") for idx in range(max(1, population))]
    _write_json(genomes_dir / "initial_population.json", initial_population)
    all_eval_rows: list[dict[str, Any]] = []
    progress_rows: list[dict[str, Any]] = []
    best_history: list[dict[str, Any]] = []

    total_gens = max(1, gens)
    for generation in range(total_gens):
        _write_json(genomes_dir / f"generation_{generation:03d}.json", initial_population)
        generation_records = []
        for genome in initial_population:
            records = generate_candidates_for_rows(
                rows=rows,
                rendered_package=rendered_package,
                out_dir=root,
                llm_mode=llm_mode,
                candidate_k=candidate_k,
                generation=generation,
                genome_id=str(genome["id"]),
                candidate_strategy="mock_gt_copy" if llm_mode == "mock" else "unsupported",
                service_schema=service_schema,
                service_context_mode=service_context_mode,
            )
            generation_records.extend(records)
        write_candidate_csv(candidates_dir / f"generation_{generation:03d}.csv", generation_records)
        eval_rows = evaluate_candidate_records(generation_records, det_threshold=det_threshold)
        all_eval_rows.extend(eval_rows)
        avg_det = sum(float(row.get("det_score") or 0) for row in eval_rows) / len(eval_rows) if eval_rows else 0.0
        pass_rate = sum(1 for row in eval_rows if row.get("det_pass")) / len(eval_rows) if eval_rows else 0.0
        progress = {
            "generation": generation,
            "candidate_rows": len(eval_rows),
            "avg_det_score": avg_det,
            "train_det_pass_rate": pass_rate,
            "best_genome_id": initial_population[0]["id"],
        }
        progress_rows.append(progress)
        best_history.append(progress)

    eval_summary = write_evaluation_outputs(root, all_eval_rows)
    best_genome = initial_population[0]
    _write_json(root / "best_genome.json", best_genome)
    (root / "ga_generation_progress.csv").write_text(
        "generation,candidate_rows,avg_det_score,train_det_pass_rate,best_genome_id\n"
        + "\n".join(
            f"{row['generation']},{row['candidate_rows']},{row['avg_det_score']},{row['train_det_pass_rate']},{row['best_genome_id']}"
            for row in progress_rows
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "ga_block_diffs.jsonl").write_text("", encoding="utf-8")
    summary = {
        "run_id": root.name,
        "model_id": rendered_package.get("model_id") or rendered_package.get("model_package_id"),
        "model_package_path": rendered_package.get("source_model_package") or rendered_package.get("model_package"),
        "model_key": "",
        "search_mode": search_mode,
        "ga_engine_mode": "mock_foundation",
        "llm_mode": llm_mode,
        "official_metric": "strict_det",
        "ground_truth_column": "gt",
        "rows": len(rows),
        "best_DETPass": eval_summary.get("det_pass_rate", 0.0),
        "best_avg_DET": eval_summary.get("avg_det_score", 0.0),
        "best_avg_prompt_tokens": 0,
        "generation_error_rate": eval_summary.get("generation_error_rate", 0.0),
        "stop_reason": "completed_requested_generations",
        "best_history": best_history,
        "cloud_is_auxiliary": True,
        "known_limitations": ["mock mode copies official gt as a deterministic pipeline fixture; do not use it for model quality claims"],
    }
    _write_json(root / "ga_summary.json", summary)
    _write_json(root / "promotion_decisions.json", {"promoted": False, "reason": "smoke foundation run"})
    (root / "promotion_decisions.csv").write_text("promoted,reason\nfalse,smoke foundation run\n", encoding="utf-8")
    (root / "mutation_events.csv").write_text("generation,mutation_type,details\n", encoding="utf-8")
    (root / "mutation_events.jsonl").write_text("", encoding="utf-8")
    return summary


def run_search(
    *,
    rows: list[tuple[int, dict[str, Any]]],
    rendered_package: dict[str, Any],
    out_dir: str | Path,
    population: int = 2,
    gens: int = 1,
    candidate_k: int = 1,
    llm_mode: str = "mock",
    det_threshold: float = 70.0,
    search_mode: str = "monolith",
    engine_mode: str = "auto",
    model_key: str = "",
    service_schema: str | Path | None = None,
    service_context_mode: str = "schema_fallback",
    timeout_sec: int = 1800,
    retries: int = 0,
    llm_endpoint: str = "",
    llm_extra: dict[str, Any] | None = None,
    repair_attempts: int = 0,
    initial_genomes: list[dict[str, Any]] | None = None,
    seed: int = 0,
    feedback_guided_mutation: bool = False,
    compression_mutation: bool = False,
    fitness_config: str | Path | None = None,
    replay_split: str | Path | None = None,
    gate_config: str | Path | None = None,
    gate_baseline: str | Path | None = None,
    elite: int | None = None,
    tournament: int | None = None,
    p_mutation: float | None = None,
    budget_config: str | Path | None = None,
    fitness_mode: str = "graded",
) -> dict[str, Any]:
    requested_engine_mode = str(engine_mode or "auto").lower()
    if requested_engine_mode == "mock" or (requested_engine_mode == "auto" and llm_mode == "mock"):
        return run_mock_search(
            rows=rows,
            rendered_package=rendered_package,
            out_dir=out_dir,
            population=population,
            gens=gens,
            candidate_k=candidate_k,
            llm_mode=llm_mode,
            det_threshold=det_threshold,
            search_mode=search_mode,
            service_schema=service_schema,
            service_context_mode=service_context_mode,
        )

    root = Path(out_dir)
    genomes_dir = root / "genomes"
    candidates_dir = root / "candidates"
    genomes_dir.mkdir(parents=True, exist_ok=True)
    candidates_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    fitness_config_loaded = load_fitness_config(fitness_config)
    budget = load_budget_config(budget_config)
    # 명시 인자 > budget config (population/gens 는 기존 시그니처 유지 — 호출부가 결정)
    elite_n = elite if elite is not None else int(budget["elite"])
    tournament_n = tournament if tournament is not None else int(budget["tournament"])
    p_m = p_mutation if p_mutation is not None else float(budget["p_mutation"])
    replay_split_loaded = load_replay_split(replay_split) if replay_split else None
    replay_history: list[dict[str, Any]] = []
    current_population = _initial_population(population, initial_genomes=initial_genomes)
    _write_json(genomes_dir / "initial_population.json", current_population)

    all_eval_rows: list[dict[str, Any]] = []
    progress_rows: list[dict[str, Any]] = []
    best_history: list[dict[str, Any]] = []
    mutation_events: list[dict[str, Any]] = []
    promotion_rows: list[dict[str, Any]] = []
    best_genome = current_population[0]
    best_score = -1.0
    best_eval_rows: list[dict[str, Any]] = []
    known_limitations = [
        "real engine evaluates genomes with strict DET and records selection/crossover/mutation artifacts",
        "O(블록 순서)·V(블록 버전)·E(예제 수) 유전자는 연산·기록만 되고 렌더러 반영은 WI-09 범위",
        "pareto archive and compression mutation policies are hooks, not full legacy parity",
    ]
    if feedback_guided_mutation:
        known_limitations.append("feedback_guided_mutation flag recorded; advisor-generated genomes must be passed through prompt patches/advisor artifacts")
    if compression_mutation:
        known_limitations.append("compression mutation hook recorded; no prompt decompiler compression policy is executed yet")

    for generation in range(max(1, gens)):
        _write_json(genomes_dir / f"generation_{generation:03d}.json", current_population)
        generation_records: list[dict[str, Any]] = []
        for genome in current_population:
            rendered_for_genome = _render_for_genome(rendered_package, genome)
            records = generate_candidates_for_rows(
                rows=rows,
                rendered_package=rendered_for_genome,
                out_dir=root,
                llm_mode=llm_mode,
                model_key=model_key,
                candidate_k=candidate_k,
                generation=generation,
                genome_id=str(genome.get("id") or "genome"),
                candidate_strategy=_candidate_strategy(genome),
                service_schema=service_schema,
                service_context_mode=service_context_mode,
                timeout_sec=timeout_sec,
                retries=retries,
                llm_endpoint=llm_endpoint,
                llm_extra=llm_extra,
                repair_attempts=repair_attempts,
            )
            generation_records.extend(records)
        write_candidate_csv(candidates_dir / f"generation_{generation:03d}.csv", generation_records)
        eval_rows = evaluate_candidate_records(generation_records, det_threshold=det_threshold)
        all_eval_rows.extend(eval_rows)
        replay_fit_by_genome: dict[str, float] = {}
        if replay_split_loaded:
            # 적합도에는 search 사례만 사용한다(C-14). holdout 은 최종 보고/게이트 전용.
            search_cases = replay_split_loaded.search_cases()
            for genome in current_population:
                rendered_for_genome = _render_for_genome(rendered_package, genome)
                replay_records = generate_candidates_for_rows(
                    rows=replay_cases_to_rows(search_cases),
                    rendered_package=rendered_for_genome,
                    out_dir=root / "replay",
                    llm_mode=llm_mode,
                    model_key=model_key,
                    candidate_k=1,
                    generation=generation,
                    genome_id=str(genome.get("id") or "genome"),
                    candidate_strategy=_candidate_strategy(genome),
                    service_schema=service_schema,
                    service_context_mode=service_context_mode,
                    timeout_sec=timeout_sec,
                    retries=retries,
                    llm_endpoint=llm_endpoint,
                    llm_extra=llm_extra,
                    repair_attempts=repair_attempts,
                )
                replay_eval = evaluate_candidate_records(replay_records, det_threshold=det_threshold)
                _write_jsonl(
                    root / "replay" / f"search_eval_gen{generation:03d}_{genome.get('id')}.jsonl",
                    replay_eval,
                )
                fit = replay_pass_rate(replay_eval)
                if fit is not None:
                    replay_fit_by_genome[str(genome.get("id") or "genome")] = fit
            replay_history.append({"generation": generation, "search_replay_fit_by_genome": dict(replay_fit_by_genome)})
        genome_scores = aggregate_genome_scores(
            eval_rows,
            config=fitness_config_loaded,
            replay_fit_by_genome=replay_fit_by_genome or None,
            mode=fitness_mode,
        )
        generation_best = genome_scores[0] if genome_scores else {"genome_id": "", "avg_det_score": 0.0, "det_pass_rate": 0.0, "fitness": 0.0}
        if float(generation_best.get("fitness") or 0.0) > best_score:
            best_score = float(generation_best.get("fitness") or 0.0)
            best_id = str(generation_best.get("genome_id") or "")
            best_genome = next((genome for genome in current_population if str(genome.get("id")) == best_id), current_population[0])
            best_eval_rows = [row for row in eval_rows if str(row.get("genome_id")) == best_id]
        progress = {
            "generation": generation,
            "candidate_rows": len(eval_rows),
            "avg_det_score": sum(float(row.get("det_score") or 0) for row in eval_rows) / len(eval_rows) if eval_rows else 0.0,
            "train_det_pass_rate": sum(1 for row in eval_rows if row.get("det_pass")) / len(eval_rows) if eval_rows else 0.0,
            "best_genome_id": generation_best.get("genome_id", ""),
            "best_avg_det_score": generation_best.get("avg_det_score", 0.0),
            "best_det_pass_rate": generation_best.get("det_pass_rate", 0.0),
            "best_fitness": generation_best.get("fitness", 0.0),
        }
        progress_rows.append(progress)
        best_history.append(progress)
        promotion_rows.append(
            {
                "generation": generation,
                "promoted_genome_id": generation_best.get("genome_id", ""),
                "reason": "highest_strict_det_fitness",
                "avg_det_score": generation_best.get("avg_det_score", 0.0),
            }
        )
        if generation < max(1, gens) - 1:
            fitness_by_id = {str(item["genome_id"]): float(item.get("fitness") or 0.0) for item in genome_scores}
            current_population, succession_events = next_generation(
                current_population,
                fitness_by_id,
                rng,
                generation=generation + 1,
                elite=elite_n,
                tournament=tournament_n,
                p_mutation=p_m,
            )
            mutation_events.extend(succession_events)

    eval_summary = write_evaluation_outputs(root, all_eval_rows)
    holdout_replay: dict[str, Any] | None = None
    if replay_split_loaded:
        # 보고 전용 holdout 평가 — 최종 best genome 1개에 대해서만 수행한다.
        holdout_cases = replay_split_loaded.holdout_cases(consumer="report")
        rendered_best = _render_for_genome(rendered_package, best_genome)
        holdout_records = generate_candidates_for_rows(
            rows=replay_cases_to_rows(holdout_cases),
            rendered_package=rendered_best,
            out_dir=root / "replay_holdout",
            llm_mode=llm_mode,
            model_key=model_key,
            candidate_k=1,
            generation=0,
            genome_id=str(best_genome.get("id") or "best"),
            candidate_strategy=_candidate_strategy(best_genome),
            service_schema=service_schema,
            service_context_mode=service_context_mode,
            timeout_sec=timeout_sec,
            retries=retries,
            llm_endpoint=llm_endpoint,
            llm_extra=llm_extra,
            repair_attempts=repair_attempts,
        )
        holdout_eval = evaluate_candidate_records(holdout_records, det_threshold=det_threshold)
        _write_jsonl(root / "replay_holdout" / "holdout_eval.jsonl", holdout_eval)
        holdout_replay = {
            "replay_fit": replay_pass_rate(holdout_eval),
            "cases": len(holdout_cases),
            "best_genome_id": best_genome.get("id"),
        }
    # 채택 게이트(C-15): 하드 게이트 — 적합도가 아니라 최종 채택 여부를 결정한다.
    gate_config_loaded = load_gate_config(gate_config)
    baseline_metrics = None
    if gate_baseline:
        baseline_metrics = json.loads(Path(gate_baseline).read_text(encoding="utf-8"))
    candidate_metrics = {
        "overall_detpass": (
            sum(1 for row in best_eval_rows if bool(row.get("det_pass"))) / len(best_eval_rows)
            if best_eval_rows
            else None
        ),
        "subset_detpass": subset_detpass_from_eval_rows(best_eval_rows, gate_config_loaded.get("critical_subsets", {})),
        "holdout_replay_fit": (holdout_replay or {}).get("replay_fit"),
    }
    adoption_gate = evaluate_adoption_gate(candidate_metrics, baseline_metrics, config=gate_config_loaded)
    adoption_gate["candidate_metrics"] = candidate_metrics
    adoption_gate["baseline_source"] = str(gate_baseline) if gate_baseline else None
    adoption_gate["best_genome_id"] = best_genome.get("id")
    _write_json(root / "adoption_gate.json", adoption_gate)

    _write_json(root / "best_genome.json", best_genome)
    _write_json(root / "best_genomes.json", best_history)
    _write_rows_csv(
        root / "ga_generation_progress.csv",
        progress_rows,
        ["generation", "candidate_rows", "avg_det_score", "train_det_pass_rate", "best_genome_id", "best_avg_det_score", "best_det_pass_rate", "best_fitness"],
    )
    _write_rows_csv(root / "promotion_decisions.csv", promotion_rows, ["generation", "promoted_genome_id", "reason", "avg_det_score"])
    _write_json(
        root / "promotion_decisions.json",
        {
            "decisions": promotion_rows,
            "final_best_genome_id": best_genome.get("id"),
            "adoption_gate": {
                "adopted": adoption_gate["adopted"],
                "reject_reasons": adoption_gate["reject_reasons"],
                "epsilon_pp": adoption_gate["epsilon_pp"],
            },
        },
    )
    _write_rows_csv(
        root / "mutation_events.csv",
        mutation_events,
        ["generation", "parent_id", "parent_ids", "child_id", "mutation_type", "crossover_type", "details"],
    )
    _write_jsonl(root / "mutation_events.jsonl", mutation_events)
    _write_jsonl(root / "ga_block_diffs.jsonl", [])
    generation_error_rate = eval_summary.get("generation_error_rate", 0.0)
    summary = {
        "run_id": root.name,
        "model_id": rendered_package.get("model_id") or rendered_package.get("model_package_id"),
        "model_package_path": rendered_package.get("source_model_package") or rendered_package.get("model_package"),
        "model_key": model_key,
        "search_mode": search_mode,
        "ga_engine_mode": "real_generation_skeleton",
        "requested_engine_mode": requested_engine_mode,
        "llm_mode": llm_mode,
        "official_metric": "strict_det",
        "ground_truth_column": "gt",
        "rows": len(rows),
        "best_DETPass": eval_summary.get("det_pass_rate", 0.0),
        "best_avg_DET": eval_summary.get("avg_det_score", 0.0),
        "best_avg_prompt_tokens": sum(float(row.get("generation_prompt_tokens_total") or 0) for row in all_eval_rows) / len(all_eval_rows) if all_eval_rows else 0.0,
        "fitness_config": {
            "path": fitness_config_loaded.get("_config_path"),
            "weights": fitness_config_loaded.get("weights"),
            "normalization": fitness_config_loaded.get("normalization"),
            "mode": fitness_mode,
        },
        "ga_budget": {
            "population": population,
            "gens": gens,
            "elite": elite_n,
            "tournament": tournament_n,
            "p_mutation": p_m,
            "budget_config_path": budget.get("_config_path"),
        },
        "replay": {
            "split_path": replay_split_loaded.path,
            "counts": replay_split_loaded.counts,
            "search_history": replay_history,
            "holdout_report": holdout_replay,
        }
        if replay_split_loaded
        else None,
        "adoption_gate": adoption_gate,
        "generation_error_rate": generation_error_rate,
        "stop_reason": "completed_requested_generations",
        "best_history": best_history,
        "cloud_is_auxiliary": True,
        "known_limitations": known_limitations,
    }
    _write_json(root / "ga_summary.json", summary)
    return summary
