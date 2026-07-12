"""WI-07 수용 기준 검사.

- 적합도 5항(α·DETPass + β·S_DET + γ·ReplayFit − λt·Tok̂ − λl·Lat̂) 수치 검산
- 가중치 config 변경이 코드 수정 없이 반영
- 층화 표본기: 범주별 정확히 N건 (논문 9범주×5=45; 실데이터 8범주×5=40)
- llm_backends._usage: total_tokens 미제공/0 시 prompt+completion 파생
- rerank.py 하드코딩 수식 잔재 제거
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

import sys

sys.path.insert(0, str(REPO))

from utils.ga_search.fitness import (  # noqa: E402
    DEFAULT_FITNESS_CONFIG_PATH,
    aggregate_genome_scores,
    compute_fitness,
    load_fitness_config,
)
from utils.ga_search.dataset_runner import select_dataset_rows, stratified_sample_rows  # noqa: E402
from utils.ga_search.llm_backends import _usage  # noqa: E402


def paper_config() -> dict:
    return load_fitness_config(DEFAULT_FITNESS_CONFIG_PATH)


def test_default_config_is_paper_weights():
    cfg = paper_config()
    w = cfg["weights"]
    assert [w["alpha_detpass"], w["beta_sdet"], w["gamma_replayfit"], w["lambda_tokens"], w["lambda_latency"]] == [
        0.50, 0.15, 0.20, 0.10, 0.05,
    ]


def test_fitness_numeric_example():
    cfg = paper_config()
    cfg["normalization"]["tokens_ref"] = 4096
    cfg["normalization"]["latency_ref_sec"] = 5.0
    result = compute_fitness(
        det_pass_rate=0.9,
        avg_det_score=80.0,
        replay_fit=0.9,
        avg_total_tokens=2048.0,
        avg_latency_sec=1.0,
        config=cfg,
    )
    # 0.5*0.9 + 0.15*0.8 + 0.2*0.9 - 0.1*0.5 - 0.05*0.2 = 0.69
    assert result["fitness"] == pytest.approx(0.69)
    assert result["terms"]["tok_hat"] == pytest.approx(0.5)
    assert result["terms"]["lat_hat"] == pytest.approx(0.2)
    assert result["replay_fit_missing"] is False


def test_weights_config_change_without_code_change(tmp_path):
    custom = json.loads((REPO / "configs" / "ga_search_fitness.json").read_text(encoding="utf-8"))
    custom["weights"]["alpha_detpass"] = 1.0
    custom["weights"]["beta_sdet"] = 0.0
    custom["weights"]["gamma_replayfit"] = 0.0
    custom["weights"]["lambda_tokens"] = 0.0
    custom["weights"]["lambda_latency"] = 0.0
    path = tmp_path / "custom.json"
    path.write_text(json.dumps(custom), encoding="utf-8")
    cfg = load_fitness_config(path)
    result = compute_fitness(
        det_pass_rate=0.7, avg_det_score=100.0, replay_fit=1.0,
        avg_total_tokens=999999.0, avg_latency_sec=999.0, config=cfg,
    )
    assert result["fitness"] == pytest.approx(0.7)


def test_replay_fit_missing_contributes_zero():
    cfg = paper_config()
    result = compute_fitness(
        det_pass_rate=1.0, avg_det_score=100.0, replay_fit=None,
        avg_total_tokens=0.0, avg_latency_sec=0.0, config=cfg,
    )
    assert result["replay_fit_missing"] is True
    assert result["fitness"] == pytest.approx(0.5 * 1.0 + 0.15 * 1.0)


def test_cost_terms_clip_to_one():
    cfg = paper_config()
    result = compute_fitness(
        det_pass_rate=0.0, avg_det_score=0.0, replay_fit=0.0,
        avg_total_tokens=10 * cfg["normalization"]["tokens_ref"],
        avg_latency_sec=10 * cfg["normalization"]["latency_ref_sec"],
        config=cfg,
    )
    assert result["terms"]["tok_hat"] == 1.0
    assert result["terms"]["lat_hat"] == 1.0


def _mk_row(genome_id, det_score, det_pass, tokens=100, latency=0.5):
    return {
        "genome_id": genome_id,
        "det_score": det_score,
        "det_pass": det_pass,
        "gt_exact": det_pass,
        "generation_total_tokens_total": tokens,
        "generation_prompt_tokens_total": tokens - 10,
        "latency_sec": latency,
    }


def test_aggregate_ranks_by_configured_fitness():
    rows = [
        _mk_row("g_good", 90.0, True),
        _mk_row("g_good", 80.0, True),
        _mk_row("g_bad", 40.0, False),
        _mk_row("g_bad", 30.0, False),
    ]
    scores = aggregate_genome_scores(rows, replay_fit_by_genome={"g_good": 0.8, "g_bad": 0.9})
    assert scores[0]["genome_id"] == "g_good"
    for record in scores:
        # 하위호환 키 유지
        for key in ("avg_det_score", "det_pass_rate", "gt_exact_rate", "avg_prompt_tokens", "avg_latency_sec", "fitness"):
            assert key in record
        assert "fitness_terms" in record
    # gt_exact는 적합도 항에서 제외 — 검산: g_good = 0.5*1 + 0.15*0.85 + 0.2*0.8 - λ 항
    good = next(r for r in scores if r["genome_id"] == "g_good")
    assert good["fitness_terms"]["gamma_term"] == pytest.approx(0.2 * 0.8)


def test_stratified_sampler_paper_9x5():
    rows = [{"category": str(cat), "gt": "{}"} for cat in range(1, 10) for _ in range(20)]
    sample = stratified_sample_rows(list(enumerate(rows, start=1)), per_category=5, seed=0)
    assert len(sample) == 45
    counts: dict[str, int] = {}
    for _, row in sample:
        counts[row["category"]] = counts.get(row["category"], 0) + 1
    assert set(counts.values()) == {5}
    # 결정성
    again = stratified_sample_rows(list(enumerate(rows, start=1)), per_category=5, seed=0)
    assert [i for i, _ in sample] == [i for i, _ in again]


def test_stratified_sampler_real_dataset_8x5():
    with (REPO / "datasets" / "JOICommands-280.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    selected = select_dataset_rows(rows, stratify_per_category=5, seed=0)
    assert len(selected) == 40  # 8범주 × 5
    counts: dict[str, int] = {}
    for _, row in selected:
        counts[str(row["category"])] = counts.get(str(row["category"]), 0) + 1
    assert set(counts.values()) == {5}


def test_usage_total_derived_from_parts():
    assert _usage(10, 5)["total_tokens"] == 15
    assert _usage(10, 5, 0)["total_tokens"] == 15
    assert _usage(10, 5, 99)["total_tokens"] == 99
    assert _usage(0, 0, 0)["total_tokens"] == 0


def test_rerank_hardcoded_formula_removed():
    src = (REPO / "utils" / "ga_search" / "rerank.py").read_text(encoding="utf-8")
    assert "10.0 * pass_rate" not in src
    assert "5.0 * exact_rate" not in src
