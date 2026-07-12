"""WI-16 수용 기준 검사.

- 블록 단위 교차(문자열 절단 아님) + 유전형 6축(B,O,V,R,E,Θ) 대응 변이 연산 6종
- elitism 2 + tournament 3 + p_m 0.35 (config 외부화, 논문 C-10/C-11)
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from utils.ga_search.ga_operators import (  # noqa: E402
    MUTATION_OPERATORS,
    block_uniform_crossover,
    load_budget_config,
    mutate_genome,
    next_generation,
    tournament_select,
)


def _genome(gid: str, blocks=None, max_tokens=512) -> dict:
    return {
        "id": gid,
        "blocks": blocks or ["01", "02", "03", "06"],
        "params": {"candidate_strategies": ["direct"], "max_tokens": max_tokens, "few_shot_count": 2},
        "block_params": {"02": {"micro_rules": ["Use canonical service names."]}},
    }


def test_budget_config_paper_values():
    cfg = load_budget_config()
    assert (cfg["population"], cfg["generations"], cfg["elite"], cfg["tournament"], cfg["p_mutation"]) == (
        10, 12, 2, 3, 0.35,
    )


def test_six_mutation_operators_cover_genotype_axes():
    assert set(MUTATION_OPERATORS) == {
        "toggle_block",        # B: 블록 활성/비활성
        "reorder_blocks",      # O: 블록 순서
        "swap_block_version",  # V: 블록 버전/워딩
        "edit_micro_rule",     # R: 세부 규칙
        "adjust_few_shot",     # E: 예제 설정
        "adjust_decoding",     # Θ: 디코딩 파라미터
    }


def test_each_operator_records_type_and_returns_valid_genome():
    rng = random.Random(0)
    parent = _genome("p0")
    for name in MUTATION_OPERATORS:
        child, event = mutate_genome(parent, rng, generation=1, index=0, operator=name)
        assert event["mutation_type"] == name
        assert child["id"] != parent["id"]
        assert isinstance(child["blocks"], list)
        # 문자열 절단 없음 — 블록 id 는 항상 2자리 토큰
        assert all(isinstance(b, str) and len(b) == 2 for b in child["blocks"])


def test_block_uniform_crossover_is_block_level():
    rng = random.Random(1)
    a = _genome("a", blocks=["01", "02", "03"], max_tokens=256)
    b = _genome("b", blocks=["01", "02", "05", "06"], max_tokens=1024)
    child, event = block_uniform_crossover(a, b, rng, generation=1, index=0)
    union = set(a["blocks"]) | set(b["blocks"])
    assert set(child["blocks"]) <= union
    assert set(child["blocks"]) >= {"01", "02"}  # 필수 블록 유지
    assert child["params"]["max_tokens"] in (256, 1024)  # 파라미터도 키 단위 선택
    assert event["crossover_type"] == "block_uniform"
    assert event["parent_ids"] == ["a", "b"]


def test_tournament_select_picks_best_of_k():
    rng = random.Random(42)
    ranked_ids = ["g0", "g1", "g2", "g3", "g4"]  # 앞이 우수
    fitness = {gid: -i for i, gid in enumerate(ranked_ids)}
    wins = {gid: 0 for gid in ranked_ids}
    for _ in range(300):
        winner = tournament_select(ranked_ids, fitness, rng, k=3)
        wins[winner] += 1
    assert wins["g0"] > wins["g4"]
    assert wins["g4"] < 30  # 최하위는 k=3 토너먼트에서 거의 못 이김


def test_next_generation_elitism_and_pm():
    rng = random.Random(7)
    population = [_genome(f"g{i}") for i in range(6)]
    fitness = {f"g{i}": -i for i in range(6)}  # g0 최고
    children, events = next_generation(
        population, fitness, rng, generation=1, elite=2, tournament=3, p_mutation=0.35,
    )
    assert len(children) == 6
    assert children[0]["id"] == "g0" and children[1]["id"] == "g1"  # elite 2 무변형 유지
    assert all(e["generation"] == 1 for e in events)
    # 비엘리트 자식은 crossover 이벤트를 가짐, 변이는 p_m 확률
    crossover_events = [e for e in events if e.get("crossover_type")]
    assert len(crossover_events) == 4


def test_pm_statistics():
    rng = random.Random(11)
    population = [_genome(f"g{i}") for i in range(4)]
    fitness = {f"g{i}": -i for i in range(4)}
    mutated = 0
    trials = 300
    for _ in range(trials):
        _, events = next_generation(
            population, fitness, rng, generation=1, elite=2, tournament=3, p_mutation=0.35,
        )
        mutated += sum(1 for e in events if e.get("mutation_type"))
    rate = mutated / (trials * 2)  # 비엘리트 자식 2명/세대
    assert 0.30 < rate < 0.40, f"p_m 0.35 기대, 실측 {rate:.3f}"
