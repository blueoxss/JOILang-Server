"""WI-03 수용 기준 검사 (판정 로직 단위 검증)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location("run_ablation_ladder", REPO / "tools" / "run_ablation_ladder.py")
ral = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ral)


def test_critical_regressions_counting():
    baseline = {"basic": 0.95, "temporal": 0.90, "complex": 0.80}
    variant = {"basic": 0.95, "temporal": 0.85, "complex": 0.78}
    count, names = ral.compute_critical_regressions(baseline, variant, epsilon_pp=1.0)
    assert count == 2
    assert set(names) == {"temporal", "complex"}


def test_epsilon_boundary_not_regression():
    baseline = {"temporal": 0.90}
    variant = {"temporal": 0.89}  # 정확히 -1.0%p → 허용
    count, _ = ral.compute_critical_regressions(baseline, variant, epsilon_pp=1.0)
    assert count == 0


def test_missing_subset_skipped():
    baseline = {"basic": 0.9, "temporal": None}
    variant = {"basic": None, "temporal": 0.5}
    count, _ = ral.compute_critical_regressions(baseline, variant, epsilon_pp=1.0)
    assert count == 0  # 비교 불가 축은 세지 않음 (날조 금지)
