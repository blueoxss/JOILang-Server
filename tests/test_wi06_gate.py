"""WI-06 수용 기준 검사.

- 채택 게이트 3조건(전체 DETPass / 핵심 부분집합별 DETPass / holdout ReplayFit),
  각 −ε=1.0%p 허용, 하드 게이트(위반 시 거절 + 사유 기록)
- 전 조건 만족 시 채택
- 적합도 코드에 RegPen 심볼 잔재 0
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from utils.ga_search.gate import (  # noqa: E402
    evaluate_adoption_gate,
    load_gate_config,
    subset_detpass_from_eval_rows,
)


def _metrics(overall=0.90, basic=0.95, temporal=0.85, complex_=0.80, replay=0.90):
    return {
        "overall_detpass": overall,
        "subset_detpass": {"basic": basic, "temporal": temporal, "complex": complex_},
        "holdout_replay_fit": replay,
    }


@pytest.fixture(scope="module")
def config():
    return load_gate_config()


def test_all_conditions_pass(config):
    result = evaluate_adoption_gate(_metrics(), _metrics(), config=config)
    assert result["adopted"] is True
    assert result["reject_reasons"] == []
    assert len(result["checks"]) == 5  # overall + 3 subsets + replay


def test_overall_detpass_violation_rejects(config):
    result = evaluate_adoption_gate(_metrics(overall=0.85), _metrics(overall=0.90), config=config)
    assert result["adopted"] is False
    assert any("overall_detpass" in r for r in result["reject_reasons"])


def test_subset_detpass_violation_rejects(config):
    result = evaluate_adoption_gate(_metrics(temporal=0.80), _metrics(temporal=0.85), config=config)
    assert result["adopted"] is False
    assert any("temporal" in r for r in result["reject_reasons"])


def test_holdout_replay_violation_rejects(config):
    result = evaluate_adoption_gate(_metrics(replay=0.70), _metrics(replay=0.90), config=config)
    assert result["adopted"] is False
    assert any("holdout_replay_fit" in r for r in result["reject_reasons"])


def test_epsilon_boundary_one_point_zero_pp_allowed(config):
    # 정확히 −1.0%p 는 허용, 그보다 크면 거절
    result = evaluate_adoption_gate(_metrics(overall=0.89), _metrics(overall=0.90), config=config)
    assert result["adopted"] is True
    result = evaluate_adoption_gate(_metrics(overall=0.889), _metrics(overall=0.90), config=config)
    assert result["adopted"] is False


def test_no_baseline_vacuous_adopt(config):
    result = evaluate_adoption_gate(_metrics(), None, config=config)
    assert result["adopted"] is True
    assert result["baseline_missing"] is True


def test_candidate_replay_missing_with_baseline_rejects(config):
    result = evaluate_adoption_gate(_metrics(replay=None), _metrics(replay=0.90), config=config)
    assert result["adopted"] is False
    assert any("holdout_replay_fit" in r and "missing" in r for r in result["reject_reasons"])


def test_baseline_replay_missing_check_vacuous(config):
    result = evaluate_adoption_gate(_metrics(replay=0.5), _metrics(replay=None), config=config)
    assert result["adopted"] is True
    replay_check = next(c for c in result["checks"] if c["name"] == "holdout_replay_fit")
    assert replay_check["note"]


def test_subset_detpass_from_eval_rows(config):
    rows = [
        {"category": "1", "det_pass": True},
        {"category": "2", "det_pass": False},
        {"category": "3", "det_pass": True},
        {"category": "5", "det_pass": True},
        {"category": "7", "det_pass": False},
    ]
    subsets = subset_detpass_from_eval_rows(rows, config["critical_subsets"])
    assert subsets["basic"] == pytest.approx(0.5)
    assert subsets["temporal"] == pytest.approx(1.0)
    assert subsets["complex"] == pytest.approx(0.0)


def test_no_regpen_symbols_in_canonical_runtime():
    hits = []
    for path in (REPO / "utils" / "ga_search").glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        if "regpen" in text or "reg_pen" in text:
            hits.append(path.name)
    assert hits == []
