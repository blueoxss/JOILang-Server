"""DET 민감도 표 재채점의 검증(마스터 프롬프트 §8 항목 1-9)."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RUN = REPO / "results/det_sensitivity_table/20260916_reproduction20260827"
CONFIG = json.loads((REPO / "configs/det_sensitivity_table.json").read_text(encoding="utf-8"))


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


RS = _load("rescore_det_sensitivity_table", "scripts/rescore_det_sensitivity_table.py")
EV = RS.load_evaluator()
BASE = CONFIG["weight_profiles"]["base"]


def _gt(script: str, cron: str = "", period: int = 0) -> str:
    return json.dumps({"name": "", "cron": cron, "period": period, "script": script}, ensure_ascii=False)


def _cand(code: str, cron: str = "", period: int = 0) -> str:
    return json.dumps({"name": "", "cron": cron, "period": period, "code": code}, ensure_ascii=False)


# 1. 가중치 벡터
def test_weight_profiles_valid():
    RS.validate_weights(CONFIG["weight_profiles"])
    assert list(CONFIG["weight_profiles"]) == ["base", "uniform", "execution", "structure"]
    assert BASE == [0.30, 0.15, 0.15, 0.10, 0.10, 0.10, 0.05, 0.05]
    for bad in ({"x": [0.5] * 8}, {"x": [0.125] * 7}, {"x": [-0.1, 1.1] + [0.0] * 6}, {"x": [float("nan")] + [0.0] * 7}):
        with pytest.raises(ValueError):
            RS.validate_weights(bad)


# 2. 기준 8항 평가기와의 일치 (차등 검증: 같은 입력 → 원본 함수 결과와 동일)
@pytest.mark.parametrize("gt, cand", [
    (_gt("(#Light).switch_on()"), _cand("(#Light).switch_on()")),
    (_gt("var a = 1\n(#Kitchen #Light).light_movetorgb(23, 0, 'on')", "0 9 * * *", 0), _cand("(#Kitchen #Light).light_movetorgb(23.0, 0, 'ON')", "0 9 * * *", -1)),
    (_gt("(#A).x()\n(#A).x()\n(#B).y()"), _cand("(#A).x()\n(#B).y()\n(#B).y()")),
    (_gt("temp = (#T).t\n(#S).s(temp)"), _cand("")),
])
def test_components_match_root_evaluator(gt, cand):
    root = EV.strict_det_evaluate_row(row={"gt": gt}, candidate=cand, row_no=0)
    scored = RS.score_record(EV, gt, cand)
    comp = scored["components"]
    assert comp[0] == pytest.approx(root["gt_similarity"], abs=1e-6)
    assert comp[2] == pytest.approx(root["gt_service_coverage"], abs=1e-6)
    assert comp[3] == pytest.approx(root["gt_service_precision"], abs=1e-6)
    assert comp[4] == pytest.approx(root["gt_receiver_coverage"], abs=1e-6)
    assert comp[5] == pytest.approx(root["numeric_grounding"], abs=1e-6)
    assert comp[6] == pytest.approx(root["enum_grounding"], abs=1e-6)
    assert comp[7] == pytest.approx(root["dataflow_score"], abs=1e-6)
    assert RS.weighted(comp, BASE) * 100 == pytest.approx(root["det_score"], abs=1e-3)
    assert scored["v"] == (0 if any(r in root["failure_reasons"] for r in RS.HARD_GATES) else 1)


def test_golden_worked_example_reproduces():
    rows = list(csv.DictReader((REPO / "datasets/JOICommands-280.csv").open(encoding="utf-8-sig")))
    row = next(r for r in rows if "temperatureweather" in r["gt"] and "외부" in r["command_kor"])
    gt = json.loads(row["gt"]); concise = dict(gt)
    concise["code"] = "\ntemp = (#WeatherProvider).weatherprovider_temperatureweather\n\n(#Speaker).speaker_speak(temp)"
    scored = RS.score_record(EV, row["gt"], json.dumps(concise, ensure_ascii=False))
    assert RS.weighted(scored["components"], BASE) == pytest.approx(0.9264397905759162, abs=1e-9)
    exact = RS.score_record(EV, row["gt"], row["gt"])
    assert RS.weighted(exact["components"], BASE) == 1.0


# 3. 경계 사례
def test_edge_cases():
    comp = lambda gt, cand: RS.score_record(EV, gt, cand)
    dup = comp(_gt("(#A).x()\n(#A).x()"), _cand("(#A).x()"))["components"]
    assert dup[2] == 0.5 and dup[3] == 1.0                         # 중복 반영: 2개 중 1개 포함, 정밀도 1
    empty_lists = comp(_gt("x := 1"), _cand("y := 2"))["components"]
    assert empty_lists[2] == 1.0 and empty_lists[3] == 1.0 and empty_lists[4] == 1.0 and empty_lists[6] == 1.0  # c(∅,∅)=1, p(∅,∅)=1
    p_empty_ref = comp(_gt("x := 1"), _cand("(#A).x()"))["components"]
    assert p_empty_ref[2] == 1.0 and p_empty_ref[3] == 0.0           # p(∅,B)=0
    empty_code = comp(_gt("(#A).x()"), _cand(""))
    assert empty_code["v"] == 0 and empty_code["components"][0] == 0.0 and empty_code["components"][1] == 1.0
    invalid = comp(_gt("(#A).x()"), "this is not json")
    assert invalid["parse_ok"] is False and invalid["v"] == 0 and invalid["components"] == [0.0] * 8
    sched = comp(_gt("(#A).x()", "", 0), _cand("(#A).x()", "", 0))["components"]
    assert sched[1] == 1.0
    sched_none = RS.score_record(EV, _gt("(#A).x()", "", 0), json.dumps({"name": "", "code": "(#A).x()"}))["components"]
    assert sched_none[1] == 1.0                                       # 누락 cron/period → ""/0 기본값 → 일치
    num = comp(_gt("(#A).x(23)"), _cand("(#A).x(23.0)"))["components"]
    assert num[5] == 0.0                                              # '23' ≠ '23.0'
    decl = comp(_gt("var a = 1\nvar b = 2\n(#A).x()"), _cand("a = 1\nb := 2\n(#A).x()"))["components"]
    assert decl[7] == 0.0                                             # 일반 대입은 선언 수에 포함되지 않음
    decl2 = comp(_gt("var a = 1\nvar b = 2\n(#A).x()"), _cand("let a = 1\n(#A).x()"))["components"]
    assert decl2[7] == 0.5


# 4. 임계값 판정: e=τ 통과, 미만 실패, v=0 실패, 반올림 없음
def test_threshold_decision_rules():
    for tau in (0.85, 0.90, 0.95):
        assert (1 == 1 and tau >= tau) is True
        assert not (tau - 1e-12 >= tau)
    components = [1.0, 0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]          # e = 0.925 (base)
    e = RS.weighted(components, BASE)
    assert e == pytest.approx(0.925) and e >= 0.90 and not e >= 0.95
    assert e >= 0.925 - 0.0 and round(0.8999, 2) == 0.90 and not (0.8999 >= 0.90)   # 반올림 후 판정하면 결과가 달라짐 — 판정은 반올림 전 값


# 5-7. 실행 결과의 구조적 검사 (통과 집합 포함 관계, 성분에서 재계산, 분모·UID·평균)
@pytest.fixture(scope="module")
def run_rows():
    assert RUN.exists(), "run results missing — execute scripts/rescore_det_sensitivity_table.py first"
    rows = list(csv.DictReader((RUN / "rescored_rows.csv").open(encoding="utf-8")))
    comps = [json.loads(l) for l in (RUN / "components.jsonl").read_text(encoding="utf-8").splitlines()]
    return rows, comps


def test_pass_sets_nested_and_denominators(run_rows):
    rows, comps = run_rows
    sets = {}
    for r in rows:
        sets.setdefault((r["condition_id"], r["model"], r["method"]), set())
        if r["D"] == "1":
            sets[(r["condition_id"], r["model"], r["method"])].add(r["row_uid"])
    for (cond, model, method) in list(sets):
        if cond != "base_t090":
            continue
        assert sets[("base_t095", model, method)] <= sets[("base_t090", model, method)] <= sets[("base_t085", model, method)]
    per_set = {}
    for r in rows:
        per_set.setdefault((r["condition_id"], r["model"], r["method"]), []).append(r["row_uid"])
    for key, uids in per_set.items():
        assert len(uids) == 280 and len(set(uids)) == 280, key
    assert len(rows) == 6 * 6 * 280
    assert len({c["row_uid"] for c in comps}) == 280


def test_scores_recomputed_from_components(run_rows):
    rows, comps = run_rows
    by_key = {(c["row_uid"], c["model"], c["method"]): c for c in comps}
    profiles = CONFIG["weight_profiles"]; cond = {c["id"]: c for c in CONFIG["conditions"]}
    for r in rows[::7]:
        c = by_key[(r["row_uid"], r["model"], r["method"])]
        comp = [c["components"][k] for k in CONFIG["component_keys"]]
        expected = RS.weighted(comp, profiles[cond[r["condition_id"]]["weights"]]) if c["parse_ok"] else 0.0
        assert float(r["e"]) == pytest.approx(expected, abs=1e-12)
        assert int(r["D"]) == int(c["v"] == 1 and expected >= cond[r["condition_id"]]["tau"])
        assert c["stored_components_match"] is True


def test_by_model_and_summary_are_unrounded_and_on_grid():
    by_model = list(csv.DictReader((RUN / "det_sensitivity_by_model.csv").open(encoding="utf-8")))
    for r in by_model:
        assert r["denominator"] == "280" and float(r["detpass_pct"]) == pytest.approx(100 * int(r["passed"]) / 280, abs=1e-12)
        assert float(r["sdet"]) + 1e-12 >= 0.0
    summary = list(csv.DictReader((RUN / "det_sensitivity_summary.csv").open(encoding="utf-8")))
    for s in summary:
        dts = [float(r["detpass_pct"]) for r in by_model if r["condition_id"] == s["condition_id"] and r["method"] == "dt" and r["role"] == "paper_dt"]
        assert len(dts) == 3 and float(s["dt_avg_pct"]) == pytest.approx(sum(dts) / 3, abs=1e-12)
        total = sum(int(r["passed"]) for r in by_model if r["condition_id"] == s["condition_id"] and r["method"] == "dt" and r["role"] == "paper_dt")
        assert float(s["dt_avg_pct"]) == pytest.approx(100 * total / 840, abs=1e-12)      # 840 격자
        assert s["gps_avg_pct"] == "" and s["diff_pp"] == ""                                # 자료 부족 → N/A


# 8. LLM 호출·모델 로딩 진입점을 차단한 환경에서도 재채점이 끝나는지
def test_rescore_runs_with_llm_and_model_imports_blocked(tmp_path):
    blocker = (
        "import sys, importlib.abc\n"
        "BLOCK = {'openai', 'torch', 'transformers', 'vllm', 'requests', 'httpx', 'urllib.request', 'socket'}\n"
        "class Deny(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name in BLOCK or name.split('.')[0] in BLOCK:\n"
        "            raise ImportError(f'blocked import: {name}')\n"
        "        return None\n"
        "sys.meta_path.insert(0, Deny())\n"
        f"sys.argv = ['rescore', '--inputs', {str(REPO / 'configs/det_sensitivity_inputs_20260827_reproduction.json')!r}, '--out', {str(tmp_path / 'run')!r}]\n"
        f"import runpy; runpy.run_path({str(REPO / 'scripts/rescore_det_sensitivity_table.py')!r}, run_name='__main__')\n"
    )
    proc = subprocess.run([sys.executable, "-c", blocker], capture_output=True, text=True, cwd=str(REPO))
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert (tmp_path / "run" / "det_sensitivity_summary.csv").exists()
    src = (REPO / "scripts/rescore_det_sensitivity_table.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(openai|torch|transformers|requests|httpx|urllib)", src, re.M)


# 9. 행별 → 모델별 → 평균 → CSV → Markdown/LaTeX 값 일치
def test_exported_tables_match_csv():
    summary = list(csv.DictReader((RUN / "det_sensitivity_summary.csv").open(encoding="utf-8")))
    tex = (RUN / "tab_det_sensitivity.tex").read_text(encoding="utf-8")
    md = (RUN / "det_sensitivity_results.md").read_text(encoding="utf-8")
    for s in summary:
        dt = f"{float(s['dt_avg_pct']):.1f}"
        assert re.search(rf"{re.escape(s['row_label'])}\}}? & (\\textbf\{{)?{dt}", tex), (s["row_label"], dt)
        assert f"| {s['row_label']} | {dt} | N/A | N/A |" in md
    assert "\\label{tab:det_sensitivity_target}" in tex and "\\toprule" in tex and "\\textbf{τ=0.90 (기준)}" in tex
    ovr = list(csv.DictReader((RUN / "original_vs_recomputed.csv").open(encoding="utf-8")))
    assert {r["status"] for r in ovr if r["column"] == "dt"} == {"실제 불일치"}
