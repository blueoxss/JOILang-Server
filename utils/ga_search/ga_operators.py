#!/usr/bin/env python3
"""논문 정합 GA 연산자 (WI-16, C-10/C-11).

- 교차: 블록 단위 균등 재조합(block_uniform) — 문자열 절단 없음.
- 변이 6종: 유전형 g=(B,O,V,R,E,Θ) 6축에 1:1 대응.
    toggle_block(B) / reorder_blocks(O) / swap_block_version(V)
    / edit_micro_rule(R) / adjust_few_shot(E) / adjust_decoding(Θ)
- 선택: elitism + tournament, 비엘리트 자식은 교차로 생성 후 확률 p_m 로 변이.
- 예산(pop/gen/elite/tournament/p_m)은 configs/ga_search_budget.json 로 외부화.

주의: O(순서)·V(버전)·E(예제 수) 유전자의 렌더러 반영은 WI-09 범위다.
여기서는 유전형 조작·기록을 논문 연산 단위로 정확히 수행하고,
렌더 미반영 축은 mutation_events 에 그대로 남겨 추적 가능하게 한다.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUDGET_CONFIG_PATH = REPO_ROOT / "configs" / "ga_search_budget.json"

MANDATORY_BLOCKS = {"01", "02"}
OPTIONAL_BLOCKS = ["03", "05", "06"]
BLOCK_UNIVERSE = ["01", "02", "03", "05", "06"]

MICRO_RULES = [
    "Prefer canonical service names exactly as given by the service schema.",
    "Before final JSON, verify every receiver tag mentioned by the user is still present.",
    "Derive cron and period before writing code; do not invent repeated loops for one-shot commands.",
    "Use unquoted numeric literals for numeric service arguments.",
    "Return one JSON object only with name, cron, period, and code.",
]

BLOCK_VERSION_TAGS = ["v1", "v2"]


def load_budget_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_BUDGET_CONFIG_PATH
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != "ga_search.budget.v1":
        raise ValueError(f"unsupported budget config schema: {config.get('schema')!r}")
    for key in ("population", "generations", "elite", "tournament", "p_mutation"):
        if key not in config:
            raise ValueError(f"budget config missing key: {key} ({config_path})")
    config["_config_path"] = str(config_path)
    return config


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _norm_blocks(blocks: Any) -> list[str]:
    seen: list[str] = []
    for block in blocks or []:
        token = str(block).zfill(2)
        if token not in seen:
            seen.append(token)
    for token in MANDATORY_BLOCKS:
        if token not in seen:
            seen.append(token)
    return seen


# ---------------------------------------------------------------------------
# 변이 6종 — 유전형 축별
# ---------------------------------------------------------------------------

def _mut_toggle_block(child: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    blocks = _norm_blocks(child.get("blocks"))
    target = rng.choice(OPTIONAL_BLOCKS)
    if target in blocks:
        blocks = [b for b in blocks if b != target or b in MANDATORY_BLOCKS]
    else:
        blocks.append(target)
    child["blocks"] = blocks
    return {"block_id": target, "active_blocks": blocks}


def _mut_reorder_blocks(child: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    blocks = _norm_blocks(child.get("blocks"))
    if len(blocks) >= 2:
        i, j = rng.sample(range(len(blocks)), 2)
        blocks[i], blocks[j] = blocks[j], blocks[i]
    child["blocks"] = blocks
    return {"order": blocks, "renderer_note": "블록 순서 유전자 — 렌더 반영은 WI-09"}


def _mut_swap_block_version(child: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    blocks = _norm_blocks(child.get("blocks"))
    target = rng.choice(blocks)
    params = child.setdefault("block_params", {}).setdefault(target, {})
    current = params.get("version", BLOCK_VERSION_TAGS[0])
    candidates = [tag for tag in BLOCK_VERSION_TAGS if tag != current]
    params["version"] = rng.choice(candidates) if candidates else current
    return {"block_id": target, "version": params["version"], "renderer_note": "버전 유전자 — 렌더 반영은 WI-09"}


def _mut_edit_micro_rule(child: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    blocks = _norm_blocks(child.get("blocks"))
    target = rng.choice(blocks)
    rules = child.setdefault("block_params", {}).setdefault(target, {}).setdefault("micro_rules", [])
    missing = [rule for rule in MICRO_RULES if rule not in rules]
    if missing:
        rule = rng.choice(missing)
        rules.append(rule)
        return {"block_id": target, "added_rule": rule}
    removed = rules.pop(rng.randrange(len(rules)))
    return {"block_id": target, "removed_rule": removed}


def _mut_adjust_few_shot(child: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    params = child.setdefault("params", {})
    current = int(params.get("few_shot_count", 2) or 0)
    delta = rng.choice([-1, 1])
    params["few_shot_count"] = max(0, min(8, current + delta))
    return {"few_shot_count": params["few_shot_count"], "renderer_note": "예제 유전자 — 렌더 반영은 WI-09"}


def _mut_adjust_decoding(child: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    params = child.setdefault("params", {})
    if rng.random() < 0.5:
        current = int(params.get("max_tokens", 512) or 512)
        params["max_tokens"] = max(128, min(2048, current + rng.choice([-128, 128])))
        return {"max_tokens": params["max_tokens"]}
    current_t = float(params.get("temperature", 0.0) or 0.0)
    params["temperature"] = round(max(0.0, min(1.0, current_t + rng.choice([-0.1, 0.1]))), 2)
    return {"temperature": params["temperature"]}


MUTATION_OPERATORS: dict[str, Callable[[dict[str, Any], random.Random], dict[str, Any]]] = {
    "toggle_block": _mut_toggle_block,
    "reorder_blocks": _mut_reorder_blocks,
    "swap_block_version": _mut_swap_block_version,
    "edit_micro_rule": _mut_edit_micro_rule,
    "adjust_few_shot": _mut_adjust_few_shot,
    "adjust_decoding": _mut_adjust_decoding,
}


def mutate_genome(
    parent: dict[str, Any],
    rng: random.Random,
    *,
    generation: int,
    index: int,
    operator: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    child = _copy(parent)
    child["id"] = f"{parent.get('id', 'genome')}_g{generation:03d}_m{index:03d}"
    child.setdefault("params", {})
    child.setdefault("block_params", {})
    name = operator or rng.choice(sorted(MUTATION_OPERATORS))
    if name not in MUTATION_OPERATORS:
        raise ValueError(f"unknown mutation operator: {name}")
    details = MUTATION_OPERATORS[name](child, rng)
    event = {
        "generation": generation,
        "parent_id": parent.get("id", ""),
        "child_id": child["id"],
        "mutation_type": name,
        "details": details,
    }
    return child, event


def block_uniform_crossover(
    parent_a: dict[str, Any],
    parent_b: dict[str, Any],
    rng: random.Random,
    *,
    generation: int,
    index: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """블록 단위 균등 교차 — 블록 활성/파라미터를 키 단위로 부모 중 하나에서 선택."""
    child: dict[str, Any] = {
        "id": f"x_{parent_a.get('id', 'a')}_{parent_b.get('id', 'b')}_g{generation:03d}_c{index:03d}",
        "blocks": [],
        "params": {},
        "block_params": {},
    }
    blocks_a = set(_norm_blocks(parent_a.get("blocks")))
    blocks_b = set(_norm_blocks(parent_b.get("blocks")))
    chosen: list[str] = []
    for block in BLOCK_UNIVERSE:
        in_a = block in blocks_a
        in_b = block in blocks_b
        take = in_a if rng.random() < 0.5 else in_b
        if take or block in MANDATORY_BLOCKS:
            chosen.append(block)
    child["blocks"] = chosen

    params_a = parent_a.get("params") or {}
    params_b = parent_b.get("params") or {}
    for key in sorted(set(params_a) | set(params_b)):
        source = params_a if (key in params_a and (key not in params_b or rng.random() < 0.5)) else params_b
        child["params"][key] = _copy(source.get(key))

    bp_a = parent_a.get("block_params") or {}
    bp_b = parent_b.get("block_params") or {}
    for block in sorted(set(bp_a) | set(bp_b)):
        source = bp_a if (block in bp_a and (block not in bp_b or rng.random() < 0.5)) else bp_b
        child["block_params"][block] = _copy(source.get(block))

    event = {
        "generation": generation,
        "parent_ids": [parent_a.get("id", ""), parent_b.get("id", "")],
        "child_id": child["id"],
        "crossover_type": "block_uniform",
        "details": {"blocks": chosen},
    }
    return child, event


def tournament_select(
    genome_ids: list[str],
    fitness_by_id: dict[str, float],
    rng: random.Random,
    *,
    k: int = 3,
) -> str:
    contenders = rng.sample(genome_ids, min(k, len(genome_ids)))
    return max(contenders, key=lambda gid: (fitness_by_id.get(gid, float("-inf")), gid))


def next_generation(
    population: list[dict[str, Any]],
    fitness_by_id: dict[str, float],
    rng: random.Random,
    *,
    generation: int,
    elite: int = 2,
    tournament: int = 3,
    p_mutation: float = 0.35,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """논문 절차: elitism → tournament 부모 2 → 블록 교차 → 확률 p_m 변이."""
    by_id = {str(genome.get("id")): genome for genome in population}
    ranked = sorted(by_id, key=lambda gid: (-fitness_by_id.get(gid, float("-inf")), gid))
    children: list[dict[str, Any]] = [_copy(by_id[gid]) for gid in ranked[: max(0, elite)]]
    events: list[dict[str, Any]] = []
    index = 0
    while len(children) < len(population):
        parent_a = by_id[tournament_select(ranked, fitness_by_id, rng, k=tournament)]
        parent_b = by_id[tournament_select(ranked, fitness_by_id, rng, k=tournament)]
        child, xover_event = block_uniform_crossover(
            parent_a, parent_b, rng, generation=generation, index=index
        )
        events.append(xover_event)
        if rng.random() < p_mutation:
            child, mut_event = mutate_genome(child, rng, generation=generation, index=index)
            events.append(mut_event)
        children.append(child)
        index += 1
    return children, events
