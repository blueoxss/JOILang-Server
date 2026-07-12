"""WI-04 수용 기준 검사.

- (b) 동일 명령 3후보 S_DET 실값 추출 도구 동작 (후보별 점수 상이, 치명=0)
- (c) 이진(DETPass만) vs 등급(+S_DET) 적합도 모드 전환
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from utils.ga_search.fitness import (  # noqa: E402
    compute_fitness,
    load_fitness_config,
    normalize_fitness_mode,
)


def test_extract_sdet_examples_tool(tmp_path):
    out = tmp_path / "examples.json"
    result = subprocess.run(
        [sys.executable, str(REPO / "tools" / "extract_sdet_examples.py"), "--row-no", "1", "--out", str(out)],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert len(payload["candidates"]) == 3
    scores = [c["det_score(S_DET)"] for c in payload["candidates"]]
    invalid = next(c for c in payload["candidates"] if c["candidate"] == "cand_3_invalid_json")
    assert invalid["det_score(S_DET)"] == 0.0  # 치명 실패 → 0
    assert invalid["det_pass"] is False
    assert len(set(scores)) >= 2, "후보별 등급 점수가 구분되어야 함"
    # 등급 신호 확인: 훼손 후보가 0 < S_DET < 100 대역에 있음
    partial = [s for s in scores if 0.0 < s < 100.0]
    assert partial, "부분 실패 후보의 등급 점수가 존재해야 함"


def test_fitness_mode_normalization():
    assert normalize_fitness_mode("strict_det") == "graded"
    assert normalize_fitness_mode("binary") == "binary"
    assert normalize_fitness_mode(None) == "graded"
    with pytest.raises(ValueError):
        normalize_fitness_mode("nonsense")


def test_binary_mode_drops_sdet_term():
    cfg = load_fitness_config()
    kwargs = dict(
        det_pass_rate=0.5, avg_det_score=90.0, replay_fit=None,
        avg_total_tokens=0.0, avg_latency_sec=0.0, config=cfg,
    )
    graded = compute_fitness(mode="graded", **kwargs)
    binary = compute_fitness(mode="binary", **kwargs)
    assert graded["terms"]["beta_term"] > 0
    assert binary["terms"]["beta_term"] == 0.0
    assert binary["mode"] == "binary"
    assert graded["fitness"] > binary["fitness"]
    # 이진 모드에서 DETPass 신호는 유지
    assert binary["terms"]["alpha_term"] == pytest.approx(0.5 * 0.5)
