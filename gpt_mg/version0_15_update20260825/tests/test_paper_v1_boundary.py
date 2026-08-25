"""paper_v1 경계 테스트 (R3 G1) + no-LLM 보장 (G3) + 아티팩트 스키마 (G4).

합성 gt/후보로 각 성분의 경계 동작을 고정한다. 여기서 동결되는 동작은 전부
ROOT utils/det_evaluator.py 의미론과 동일함(이식 검증)이며, 의도적 규칙인지
결함인지의 분류는 round_03/changes.md 에 기록한다.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from utils.det_paper_v1 import (  # noqa: E402
    COMPONENT_KEYS,
    evaluate_row_paper_v1,
    score_from_components,
)


def _row(code: str, *, cron: str = "", period: int = 0) -> dict:
    return {"gt": json.dumps({"name": "t", "cron": cron, "period": period, "code": code}, ensure_ascii=False)}


def _cand(code: str, *, cron: str = "", period: int = 0) -> str:
    return json.dumps({"name": "t", "cron": cron, "period": period, "code": code}, ensure_ascii=False)


GT = "\nvar x = (#Sensor).sensor_read()\n(#Light).light_set(50)"


# ---------- G1: 성분 경계 ----------

def test_schedule_partial_match_is_half():
    r = evaluate_row_paper_v1(_row(GT, cron="0 8 * * *", period=1), _cand(GT, cron="0 8 * * *", period=2))
    assert r["components"]["schedule"] == 0.5


def test_schedule_both_mismatch_is_zero():
    r = evaluate_row_paper_v1(_row(GT, cron="0 8 * * *", period=1), _cand(GT, cron="0 9 * * *", period=2))
    assert r["components"]["schedule"] == 0.0


def test_period_zero_equals_empty_string_by_falsy_coercion():
    # ROOT normalize_text(value)=str(value or "") — period 0은 falsy → ""와 동치(의도된 ROOT 동작, 이식 보존).
    # 즉 '스케줄 없음'을 0/""/None 어느 표기로 써도 일치로 취급된다.
    row = {"gt": json.dumps({"name": "t", "cron": "", "period": 0, "code": GT})}
    cand = json.dumps({"name": "t", "cron": "", "period": "", "code": GT})
    r = evaluate_row_paper_v1(row, cand)
    assert r["components"]["schedule"] == 1.0
    # 반면 0이 아닌 값과는 구분된다
    cand2 = json.dumps({"name": "t", "cron": "", "period": 5, "code": GT})
    assert evaluate_row_paper_v1(row, cand2)["components"]["schedule"] == 0.5


def test_service_multiplicity_uses_counter():
    gt = "(#A).svc_x()\n(#A).svc_x()"
    r = evaluate_row_paper_v1(_row(gt), _cand("(#A).svc_x()"))
    assert r["components"]["service_coverage"] == 0.5  # 2회 요구 중 1회 커버
    assert r["components"]["service_precision"] == 1.0


def test_service_precision_extra_call_penalized():
    r = evaluate_row_paper_v1(_row("(#A).svc_x()"), _cand("(#A).svc_x()\n(#B).svc_y()"))
    assert r["components"]["service_coverage"] == 1.0
    assert r["components"]["service_precision"] == 0.5


def test_precision_empty_generated_with_required_services_is_zero():
    r = evaluate_row_paper_v1(_row("(#A).svc_x()"), _cand("var t = 1"))
    assert r["components"]["service_precision"] == 0.0
    assert r["components"]["service_coverage"] == 0.0


def test_numeric_sign_matters():
    r = evaluate_row_paper_v1(_row("(#A).svc_x(-5)"), _cand("(#A).svc_x(5)"))
    assert r["components"]["numeric_grounding"] == 0.0


def test_numeric_decimal_covered():
    r = evaluate_row_paper_v1(_row("(#A).svc_x(3.5)"), _cand("(#A).svc_x(3.5)"))
    assert r["components"]["numeric_grounding"] == 1.0


def test_empty_reference_code_not_hard_gate():
    # gt의 code가 빈 문자열: missing_gt_code 사유가 남지만 hard gate는 아님(ROOT 동일).
    # 빈 참조 목록의 coverage류는 1.0으로 정의됨 — 결함 아님, ROOT 의미론 보존.
    r = evaluate_row_paper_v1(_row(""), _cand("(#A).svc_x()"))
    assert "missing_gt_code" in r["failure_reasons"]
    assert not r["hard_gate"]
    assert r["components"]["code_sim"] == 0.0
    assert r["components"]["service_coverage"] == 1.0


def test_gt_refs_all_unparseable_is_hard_gate():
    r = evaluate_row_paper_v1({"gt_refs": ["{bad", "also bad"]}, _cand(GT))
    assert r["e"] == 0.0 and r["det_pass"] is False
    assert "missing_official_gt" in r["hard_gate"]
    assert "unparseable_reference" in r["failure_reasons"]


def test_candidate_list_input_uses_first_element():
    r = evaluate_row_paper_v1(_row(GT), [json.loads(_cand(GT))])
    assert r["e"] == 1.0 and r["gt_exact"] is True


def test_enum_grounding_case_insensitive():
    r = evaluate_row_paper_v1(_row('(#S).speak("Hello World")'), _cand('(#S).speak("hello world")'))
    assert r["components"]["enum_grounding"] == 1.0


def test_dataflow_ratio_partial():
    gt = "var a = 1\nvar b = 2\n(#A).svc_x()"
    r = evaluate_row_paper_v1(_row(gt), _cand("var a = 1\n(#A).svc_x()"))
    assert r["components"]["dataflow"] == 0.5


def test_tau_boundary_e_equal_threshold_passes():
    row = _row(GT)
    cand = _cand("var x = (#Sensor).sensor_read()\n(#Light).light_set(50)\n// extra")
    probe = evaluate_row_paper_v1(row, cand)
    assert 0.0 < probe["e"] < 1.0
    at = evaluate_row_paper_v1(row, cand, threshold=probe["e"])
    above = evaluate_row_paper_v1(row, cand, threshold=probe["e"] + 1e-9)
    assert at["det_pass"] is True and above["det_pass"] is False


def test_zero_weight_component_excluded():
    w = {"code_sim": 0.35, "schedule": 0.15, "service_coverage": 0.15, "service_precision": 0.10,
         "receiver_coverage": 0.10, "numeric_grounding": 0.10, "enum_grounding": 0.0, "dataflow": 0.05}
    comps = {k: 1.0 for k in COMPONENT_KEYS}
    comps["enum_grounding"] = 0.0
    assert score_from_components(comps, w) == pytest.approx(1.0)


def test_reweight_single_component_extreme():
    w = {k: 0.0 for k in COMPONENT_KEYS}
    w["code_sim"] = 1.0
    comps = {k: 0.3 for k in COMPONENT_KEYS}
    comps["code_sim"] = 0.77
    assert score_from_components(comps, w) == pytest.approx(0.77)


# ---------- G3: no-LLM 보장 ----------

FORBIDDEN_MODULES = ("openai", "utils.local_llm_client", "anthropic")


def test_static_no_llm_imports_in_paper_v1_stack():
    for rel in ("utils/det_paper_v1.py", "scripts/fitness_paper_v1.py", "scripts/run_paper_v1_eval.py"):
        src = (VERSION_ROOT / rel).read_text(encoding="utf-8")
        for mod in ("local_llm_client", "openai", "anthropic", "requests"):
            assert mod not in src, f"{rel} 이 {mod} 를 참조함"


def test_runtime_no_llm_modules_and_zero_calls(tmp_path):
    inp = tmp_path / "in.jsonl"
    row = _row(GT)
    inp.write_text(json.dumps({"gt": row["gt"], "output": _cand(GT)}) + "\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    code = (
        "import sys, runpy\n"
        f"sys.argv = ['run_paper_v1_eval.py', '--input', {str(inp)!r}, '--out', {str(out_dir)!r}]\n"
        f"sys.path.insert(0, {str(VERSION_ROOT)!r})\n"
        "try:\n"
        f"    runpy.run_path({str(VERSION_ROOT / 'scripts/run_paper_v1_eval.py')!r}, run_name='__main__')\n"
        "except SystemExit as e:\n"
        "    assert e.code in (0, None), e.code\n"
        f"loaded = [m for m in {FORBIDDEN_MODULES!r} if m in sys.modules]\n"
        "assert not loaded, f'LLM 모듈 로드됨: {loaded}'\n"
        "print('NO_LLM_OK')\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-1500:]
    assert "NO_LLM_OK" in proc.stdout
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["llm_calls"] == 0


# ---------- G4: 아티팩트 스키마 ----------

def test_artifact_schema(tmp_path):
    inp = tmp_path / "in.jsonl"
    inp.write_text(json.dumps({"gt": _row(GT)["gt"], "output": _cand(GT)}) + "\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    proc = subprocess.run(
        [sys.executable, str(VERSION_ROOT / "scripts/run_paper_v1_eval.py"),
         "--input", str(inp), "--out", str(out_dir)],
        capture_output=True, text=True, cwd=str(VERSION_ROOT))
    assert proc.returncode == 0, proc.stderr[-1500:]
    rows = [json.loads(l) for l in (out_dir / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows, "rows.jsonl 비어 있음"
    required_row_keys = {"e", "det_score", "det_pass", "components", "weights", "threshold",
                         "hard_gate", "failure_reasons", "det_profile"}
    assert required_row_keys <= set(rows[0])
    assert set(rows[0]["components"]) == set(COMPONENT_KEYS)
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert {"n", "DETPass", "S_DET", "det_threshold", "det_profile", "llm_calls"} <= set(summary)
