"""WI-02 수용 기준 검사 (판정 로직 단위 검증 — LLM 불필요).

- 각 열 argmax 대각 판정
- 앵커 ±1.0%p 검증: paper_grade 만 비교, 그 외 SKIPPED(+사유), 이탈 시 OUT_OF_BAND(+진단)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location("run_cross_transfer", REPO / "tools" / "run_cross_transfer.py")
rct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rct)

PROMPTS = [
    {"id": "P_Q7", "source_target_label": "Q7"},
    {"id": "P_L8", "source_target_label": "L8"},
    {"id": "P_Q14", "source_target_label": "Q14"},
]
TARGETS = [{"key": "q7", "label": "Q7"}, {"key": "l8", "label": "L8"}, {"key": "q14", "label": "Q14"}]


def _cell(pid, target, rate, provenance="paper_grade"):
    return {
        "prompt_id": pid,
        "target": target,
        "det_pass_rate": rate,
        "is_diagonal": next(p["source_target_label"] for p in PROMPTS if p["id"] == pid) == target if pid != "DT" else False,
        "provenance": provenance,
    }


def test_argmax_diagonal_detection():
    cells = [
        _cell("P_Q7", "Q7", 0.926), _cell("P_L8", "Q7", 0.90), _cell("P_Q14", "Q7", 0.91),
        _cell("P_Q7", "L8", 0.85), _cell("P_L8", "L8", 0.887), _cell("P_Q14", "L8", 0.86),
        _cell("P_Q7", "Q14", 0.95), _cell("P_L8", "Q14", 0.91), _cell("P_Q14", "Q14", 0.94),
    ]
    verdicts = rct.build_verdicts(cells, PROMPTS, TARGETS)
    assert verdicts["argmax_by_target"]["Q7"]["diagonal_is_argmax"] is True
    assert verdicts["argmax_by_target"]["L8"]["diagonal_is_argmax"] is True
    assert verdicts["argmax_by_target"]["Q14"]["diagonal_is_argmax"] is False  # P_Q7 이 더 높게 조작된 케이스


def test_anchor_within_and_out_of_band():
    cells = [
        _cell("P_Q7", "Q7", 0.921),   # 92.1 vs 92.6 → |Δ|=0.5 → WITHIN
        _cell("P_L8", "L8", 0.86),    # 86.0 vs 88.7 → OUT_OF_BAND + 진단
    ]
    verdicts = rct.build_verdicts(cells, PROMPTS, TARGETS)
    checks = {c["cell"]: c for c in verdicts["anchor_checks"]}
    assert checks["P_Q7×Q7"]["status"] == "WITHIN"
    assert checks["P_L8×L8"]["status"] == "OUT_OF_BAND"
    assert "diagnosis" in checks["P_L8×L8"]


def test_anchor_skipped_for_placeholder_provenance():
    cells = [_cell("P_Q7", "Q7", 1.0, provenance="PLACEHOLDER_base_prompt")]
    verdicts = rct.build_verdicts(cells, PROMPTS, TARGETS)
    check = verdicts["anchor_checks"][0]
    assert check["status"] == "SKIPPED"
    assert "diagnosis" in check


def test_config_template_valid():
    config = json.loads((REPO / "configs" / "cross_transfer_q7_l8_q14.json").read_text(encoding="utf-8"))
    assert len(config["prompts"]) == 3
    assert len(config["targets"]) == 3
    assert {p["source_target_label"] for p in config["prompts"]} == {t["label"] for t in config["targets"]}
    assert all(p["genome_json"] is None for p in config["prompts"]), "승격 산출물 확보 전에는 placeholder 여야 함"
