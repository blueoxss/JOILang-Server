"""paper_v1 DET 평가기·GA 적합도 테스트 (R2 게이트 G1-G10 직접 검증).

회귀 기준값은 2026-08-25에 원본 version0_15_update20260413(무변경)에서
동일 fixture로 실측·동결한 수치다 (docs/iv4_five_round/round_02/changes.md).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

VERSION_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = VERSION_ROOT.parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from utils.det_paper_v1 import (  # noqa: E402
    PAPER_V1_WEIGHTS,
    COMPONENT_KEYS,
    evaluate_row_paper_v1,
    load_det_weights,
    score_from_components,
)
from scripts.fitness_paper_v1 import (  # noqa: E402
    PAPER_V1_FITNESS_WEIGHTS,
    aggregate_paper_v1,
    direct_transfer_refs,
    fitness_paper_v1,
    load_direct_transfer_baseline,
    load_fitness_weights,
)

SCHEMA = str(SERVER_ROOT / "datasets" / "service_list_ver2.0.1.json")
PAPER_E_CONCISE = 0.9264397905759162  # 논문 worked example (main.tex:605-606)


def _fixture_row() -> dict:
    rows = list(csv.DictReader(open(SERVER_ROOT / "datasets" / "JOICommands-280.csv", encoding="utf-8")))
    return next(r for r in rows if "temperatureweather" in r["gt"] and "외부" in r["command_kor"])


def _variants(row: dict) -> dict[str, str]:
    gt = json.loads(row["gt"])
    concise = dict(gt)
    concise["code"] = "\ntemp = (#WeatherProvider).weatherprovider_temperatureweather\n\n(#Speaker).speaker_speak(temp)"
    oneliner = dict(gt)
    oneliner["code"] = "\n(#Speaker).speaker_speak((#WeatherProvider).weatherprovider_temperatureweather)"
    return {
        "exact": row["gt"],
        "concise": json.dumps(concise, ensure_ascii=False),
        "oneliner": json.dumps(oneliner, ensure_ascii=False),
    }


# ---------- G1: configs ----------

def test_config_paper_v1_matches_w0_and_sums_to_1():
    weights, threshold, profile = load_det_weights()
    assert profile == "paper_v1"
    assert weights == PAPER_V1_WEIGHTS
    assert abs(sum(weights.values()) - 1.0) < 1e-12
    assert weights["code_sim"] == 0.30 and weights["schedule"] == 0.15
    assert threshold == 0.70


def test_config_fitness_weights_match_eq7():
    w = load_fitness_weights()
    assert w == {"detpass": 0.70, "sdet": 0.20, "tokens": 0.05, "latency": 0.05}
    assert w == PAPER_V1_FITNESS_WEIGHTS


def test_load_weights_rejects_bad_sum(tmp_path):
    bad = {"profile": "x", "weights": dict(PAPER_V1_WEIGHTS, code_sim=0.5)}
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="sum to 1.0"):
        load_det_weights(p)


def test_load_weights_rejects_unknown_and_missing_keys(tmp_path):
    bad = {"profile": "x", "weights": dict(PAPER_V1_WEIGHTS)}
    bad["weights"].pop("dataflow")
    bad["weights"]["mystery"] = 0.05
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad))
    with pytest.raises(ValueError):
        load_det_weights(p)


# ---------- G2: 논문 worked example ----------

def test_fixture_concise_reproduces_paper_e():
    row = _fixture_row()
    r = evaluate_row_paper_v1(row, _variants(row)["concise"], row_no=8)
    assert abs(r["e"] - PAPER_E_CONCISE) < 1e-8
    assert r["det_pass"] is True and not r["gt_exact"]


def test_fixture_exact_scores_1():
    row = _fixture_row()
    r = evaluate_row_paper_v1(row, row["gt"], row_no=8)
    assert r["e"] == 1.0 and r["det_pass"] is True and r["gt_exact"] is True


def test_fixture_oneliner_scores_root_semantics():
    row = _fixture_row()
    r = evaluate_row_paper_v1(row, _variants(row)["oneliner"], row_no=8)
    assert abs(r["e"] - 0.7846153846153846) < 1e-8  # ROOT 의미론: 69.9 cap 없음
    assert r["det_pass"] is True


# ---------- G3: hard gates + 0-1 스케일 ----------

def test_invalid_json_hard_gate():
    row = _fixture_row()
    r = evaluate_row_paper_v1(row, "this is not json", row_no=8)
    assert r["e"] == 0.0 and r["det_pass"] is False and "invalid_json" in r["hard_gate"]


def test_missing_gt_hard_gate():
    r = evaluate_row_paper_v1({"gt": ""}, '{"name":"x","cron":"","period":0,"code":"(#Light).light_on()"}')
    assert r["e"] == 0.0 and r["det_pass"] is False and "missing_official_gt" in r["hard_gate"]


def test_missing_generated_code_hard_gate():
    row = _fixture_row()
    r = evaluate_row_paper_v1(row, '{"name":"x","cron":"","period":0,"code":""}', row_no=8)
    assert r["e"] == 0.0 and r["det_pass"] is False and "missing_generated_code" in r["hard_gate"]


def test_scale_bounds_all_fixtures():
    row = _fixture_row()
    for cand in list(_variants(row).values()) + ["not json", '{"code":"(#A).b()"}']:
        r = evaluate_row_paper_v1(row, cand, row_no=8)
        assert 0.0 <= r["e"] <= 1.0
        assert all(0.0 <= v <= 1.0 for v in r["components"].values())


# ---------- G9: 다중 참조 max ----------

def test_multi_ref_max_selects_best_reference():
    row = dict(_fixture_row())
    wrong_ref = json.dumps({"name": "x", "cron": "0 0 * * *", "period": 1, "code": "(#Light).light_on()"})
    row["gt_refs"] = [wrong_ref, row["gt"]]
    r = evaluate_row_paper_v1(row, _variants(_fixture_row())["concise"])
    assert r["selected_ref_index"] == 1 and r["n_refs"] == 2
    assert abs(r["e"] - PAPER_E_CONCISE) < 1e-8


def test_single_gt_equals_singleton_gt_refs():
    base = _fixture_row()
    cand = _variants(base)["concise"]
    r_single = evaluate_row_paper_v1(base, cand)
    row_list = dict(base)
    row_list["gt_refs"] = [base["gt"]]
    r_list = evaluate_row_paper_v1(row_list, cand)
    assert abs(r_single["e"] - r_list["e"]) < 1e-12
    assert r_single["det_pass"] == r_list["det_pass"]


# ---------- G10: 성분 벡터 보존 + 재가중 재채점 ----------

def test_component_vector_and_metadata_preserved():
    row = _fixture_row()
    r = evaluate_row_paper_v1(row, _variants(row)["concise"])
    assert set(r["components"]) == set(COMPONENT_KEYS)
    assert r["weights"] == PAPER_V1_WEIGHTS and r["threshold"] == 0.70
    assert r["det_profile"] == "paper_v1"
    assert abs(score_from_components(r["components"]) - r["e"]) < 1e-9


def test_score_from_components_reweighting_no_reextraction():
    row = _fixture_row()
    r = evaluate_row_paper_v1(row, _variants(row)["concise"])
    uniform = {k: 1.0 / 8.0 for k in COMPONENT_KEYS}
    e_uniform = score_from_components(r["components"], uniform)
    assert abs(e_uniform - sum(r["components"].values()) / 8.0) < 1e-12
    assert e_uniform != pytest.approx(r["e"])  # 가중치가 실제로 반영됨


# ---------- G6/G4: v15 dispatch + legacy/strict 회귀 ----------

def test_dispatch_via_v15_evaluate_candidate():
    from utils.det_evaluator import evaluate_candidate

    row = _fixture_row()
    d = evaluate_candidate(row["command_eng"], _variants(row)["concise"], SCHEMA,
                           connected_devices=row["connected_devices"],
                           ground_truth=row["gt"], profile="paper_v1")
    assert d["det_profile"] == "paper_v1"
    assert abs(d["det_score"] - 100.0 * PAPER_E_CONCISE) < 1e-4
    assert abs(d["paper_v1"]["e"] - PAPER_E_CONCISE) < 1e-8


def test_dispatch_multi_ref_via_ground_truth_list():
    from utils.det_evaluator import evaluate_candidate

    row = _fixture_row()
    wrong_ref = json.dumps({"name": "x", "cron": "0 0 * * *", "period": 1, "code": "(#Light).light_on()"})
    d = evaluate_candidate(row["command_eng"], _variants(row)["concise"], SCHEMA,
                           connected_devices=row["connected_devices"],
                           ground_truth=[wrong_ref, row["gt"]], profile="paper_v1")
    assert d["paper_v1"]["n_refs"] == 2 and d["paper_v1"]["selected_ref_index"] == 1


def test_legacy_strict_regression_frozen_baseline():
    """원본 version0_15_update20260413(무변경)에서 2026-08-25 실측·동결한 수치와 동일해야 함."""
    from utils.det_evaluator import evaluate_candidate

    row = _fixture_row()
    variants = _variants(row)
    expected = {  # (variant, profile) -> (det_score, det_gt_exact)
        ("exact", "legacy"): (0.0, False),   # v15는 code 키 없는 raw gt(script)를 후보로 인정하지 않음 (기존 동작)
        ("exact", "strict"): (0.0, False),
        ("concise", "legacy"): (100.0, True),  # v15 semantic exact override
        ("concise", "strict"): (100.0, True),
        ("oneliner", "legacy"): (93.7135, False),
        ("oneliner", "strict"): (69.9, False),  # strict 5조건 min(score, 69.9) cap
    }
    for (variant, profile), (score, exact) in expected.items():
        d = evaluate_candidate(row["command_eng"], variants[variant], SCHEMA,
                               connected_devices=row["connected_devices"],
                               ground_truth=row["gt"], profile=profile)
        assert float(d["det_score"]) == pytest.approx(score, abs=1e-9), (variant, profile)
        assert bool(d.get("det_gt_exact")) is exact, (variant, profile)


# ---------- G5: 적합도 식(7) ----------

def test_fitness_hand_computed_fixture():
    baseline = {"m": {"tokens_ref": 1000.0, "latency_ref_sec": 4.0}}
    out = fitness_paper_v1(detpass=0.9, sdet=0.8, avg_total_tokens=500.0,
                           avg_latency_sec=2.0, model_key="m", baseline=baseline)
    # 0.70*0.9 + 0.20*0.8 - 0.05*0.5 - 0.05*0.5 = 0.74
    assert abs(out["fitness"] - 0.74) < 1e-9
    assert out["tok_hat"] == 0.5 and out["lat_hat"] == 0.5


def test_fitness_fail_fast_on_missing_model():
    with pytest.raises(ValueError, match="DirectTransfer baseline missing"):
        fitness_paper_v1(detpass=1.0, sdet=1.0, avg_total_tokens=1.0,
                         avg_latency_sec=1.0, model_key="no_such_model",
                         baseline={"other": {"tokens_ref": 1.0, "latency_ref_sec": 1.0}})


def test_fitness_refs_reject_nonpositive():
    with pytest.raises(ValueError, match="invalid DirectTransfer refs"):
        direct_transfer_refs("m", {"m": {"tokens_ref": 0.0, "latency_ref_sec": 1.0}})


def test_fitness_weights_loader_validates_keys(tmp_path):
    p = tmp_path / "fw.json"
    p.write_text(json.dumps({"weights": {"detpass": 0.7, "sdet": 0.2, "tokens": 0.05}}))
    with pytest.raises(ValueError, match="latency"):
        load_fitness_weights(p)


def test_aggregate_paper_v1():
    rows = [{"det_pass": True, "e": 1.0}, {"det_pass": True, "e": 0.9},
            {"det_pass": False, "e": 0.5}, {"det_pass": False, "e": 0.0}]
    agg = aggregate_paper_v1(rows)
    assert agg["n"] == 4 and agg["detpass"] == 0.5 and abs(agg["sdet"] - 0.6) < 1e-12


def test_default_baseline_has_provenance_and_loads():
    baseline = load_direct_transfer_baseline()
    assert "qwen25_coder_14b" in baseline and "gpt41_mini" in baseline
    for entry in baseline.values():
        assert entry["tokens_ref"] > 0 and entry["latency_ref_sec"] > 0
        assert entry.get("provenance")
