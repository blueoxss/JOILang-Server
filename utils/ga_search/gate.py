#!/usr/bin/env python3
"""채택 게이트 (WI-06, 논문 C-15/C-16).

3조건 하드 게이트 — 기존 채택본(baseline) 대비 epsilon_pp(%p) 초과 회귀 시 채택 거절:
  ① overall_detpass        ② critical_subsets 별 detpass        ③ holdout_replay_fit

원칙:
- 적합도 항이 아니라 채택 여부를 결정하는 하드 게이트다(회귀 페널티를 적합도에 섞는 방식 금지).
- holdout 리플레이는 게이트/보고 전용이다(utils/ga_search/replay.py 의 consumer 규칙).
- baseline 이 없으면(첫 채택) 통과시키되 baseline_missing 을 기록한다.
- 후보의 holdout_replay_fit 이 없는데 baseline 에는 있으면 회귀 검증이 불가능하므로 거절한다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GATE_CONFIG_PATH = REPO_ROOT / "configs" / "ga_search_gate.json"


def load_gate_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_GATE_CONFIG_PATH
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema") != "ga_search.gate.v1":
        raise ValueError(f"unsupported gate config schema: {config.get('schema')!r}")
    config.setdefault("epsilon_pp", 1.0)
    config.setdefault("critical_subsets", {})
    config["_config_path"] = str(config_path)
    return config


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def subset_detpass_from_eval_rows(
    eval_rows: list[dict[str, Any]],
    critical_subsets: dict[str, list[str]],
) -> dict[str, float | None]:
    """행 평가 결과에서 핵심 부분집합별 DETPass 를 계산한다. 해당 행이 없으면 None."""
    out: dict[str, float | None] = {}
    for name, categories in critical_subsets.items():
        members = [row for row in eval_rows if str(row.get("category", "")).strip() in set(categories)]
        out[name] = (sum(1 for row in members if _truthy(row.get("det_pass"))) / len(members)) if members else None
    return out


def _check(name: str, candidate: float | None, baseline: float | None, epsilon: float) -> dict[str, Any]:
    if baseline is None:
        return {
            "name": name,
            "candidate": candidate,
            "baseline": None,
            "allowed_min": None,
            "passed": True,
            "note": "baseline 값 없음 — 회귀 비교 불가, 조건 공허 통과(첫 채택 또는 미평가 부분집합)",
        }
    if candidate is None:
        return {
            "name": name,
            "candidate": None,
            "baseline": baseline,
            "allowed_min": baseline - epsilon,
            "passed": False,
            "note": "candidate 값 missing — 회귀 없음을 검증할 수 없어 거절",
        }
    allowed_min = baseline - epsilon
    # 부동소수 경계(정확히 -epsilon)는 허용
    passed = candidate >= allowed_min - 1e-9
    return {
        "name": name,
        "candidate": candidate,
        "baseline": baseline,
        "allowed_min": allowed_min,
        "passed": passed,
        "note": "",
    }


def evaluate_adoption_gate(
    candidate_metrics: dict[str, Any],
    baseline_metrics: dict[str, Any] | None,
    *,
    config: dict[str, Any],
) -> dict[str, Any]:
    """3조건 채택 게이트. 반환값의 reject_reasons 는 운영 메타데이터로 기록할 것."""
    epsilon = float(config.get("epsilon_pp", 1.0)) / 100.0
    subsets = config.get("critical_subsets", {})
    if baseline_metrics is None:
        return {
            "adopted": True,
            "baseline_missing": True,
            "epsilon_pp": config.get("epsilon_pp", 1.0),
            "checks": [],
            "reject_reasons": [],
            "note": "baseline 부재 — 첫 채택으로 간주하고 게이트 공허 통과",
        }

    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "overall_detpass",
            candidate_metrics.get("overall_detpass"),
            baseline_metrics.get("overall_detpass"),
            epsilon,
        )
    )
    candidate_subsets = candidate_metrics.get("subset_detpass") or {}
    baseline_subsets = baseline_metrics.get("subset_detpass") or {}
    for name in subsets:
        checks.append(
            _check(
                f"subset_detpass:{name}",
                candidate_subsets.get(name),
                baseline_subsets.get(name),
                epsilon,
            )
        )
    checks.append(
        _check(
            "holdout_replay_fit",
            candidate_metrics.get("holdout_replay_fit"),
            baseline_metrics.get("holdout_replay_fit"),
            epsilon,
        )
    )

    reject_reasons = [
        f"{check['name']}: candidate={check['candidate']} < allowed_min={check['allowed_min']}"
        + (f" ({check['note']})" if check["note"] else "")
        for check in checks
        if not check["passed"]
    ]
    return {
        "adopted": not reject_reasons,
        "baseline_missing": False,
        "epsilon_pp": config.get("epsilon_pp", 1.0),
        "checks": checks,
        "reject_reasons": reject_reasons,
    }
