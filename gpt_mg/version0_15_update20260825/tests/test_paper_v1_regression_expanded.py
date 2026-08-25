"""확장 회귀 테스트 (R3 G2): 원본 20260413에서 동결한 12행×2후보 fixture와
canonical의 legacy/strict 수치가 완전히 일치해야 한다.

fixture 생성: 2026-08-25, 원본 디렉터리 별도 subprocess (tests/fixtures/regression_expanded.json).
paper_v1 자체 수치도 최초 실행 시 baseline으로 동결해(paper_v1_expanded_baseline.json)
이후 라운드(R4·R5)의 로직 불변을 감시한다.
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

from utils.det_evaluator import evaluate_candidate  # noqa: E402
from utils.det_paper_v1 import evaluate_row_paper_v1  # noqa: E402

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "regression_expanded.json").read_text(encoding="utf-8"))
PAPER_BASELINE_PATH = Path(__file__).parent / "fixtures" / "paper_v1_expanded_baseline.json"
SCHEMA = str(SERVER_ROOT / "datasets" / "service_list_ver2.0.1.json")


def _dataset_rows() -> list[dict]:
    return list(csv.DictReader(open(SERVER_ROOT / "datasets" / "JOICommands-280.csv", encoding="utf-8")))


@pytest.fixture(scope="module")
def rows():
    return _dataset_rows()


def test_fixture_shape():
    assert len(FIXTURE["rows"]) == 12
    assert FIXTURE["source_version"].startswith("version0_15_update20260413")


@pytest.mark.parametrize("entry", FIXTURE["rows"], ids=lambda e: f"row{e['row_index']}")
def test_legacy_strict_match_frozen_original(entry, rows):
    row = rows[entry["row_index"]]
    for label, case in entry["candidates"].items():
        for prof, expected in case["scores"].items():
            d = evaluate_candidate(row["command_eng"], case["candidate_json"], SCHEMA,
                                   connected_devices=row["connected_devices"],
                                   ground_truth=row["gt"], profile=prof)
            assert float(d["det_score"]) == pytest.approx(expected["det_score"], abs=1e-9), (
                entry["row_index"], label, prof)
            assert bool(d.get("det_gt_exact")) is expected["det_gt_exact"], (entry["row_index"], label, prof)


def test_paper_v1_baseline_frozen(rows):
    """paper_v1 수치를 R3 시점에 동결하고 이후 로직 불변을 감시한다 (최초 실행 시 생성)."""
    current = {}
    for entry in FIXTURE["rows"]:
        row = rows[entry["row_index"]]
        for label, case in entry["candidates"].items():
            r = evaluate_row_paper_v1({"gt": row["gt"], "category": row["category"]},
                                      case["candidate_json"], row_no=entry["row_index"])
            current[f"{entry['row_index']}:{label}"] = {"e": round(r["e"], 12), "det_pass": r["det_pass"]}
    if not PAPER_BASELINE_PATH.exists():
        PAPER_BASELINE_PATH.write_text(json.dumps(
            {"generated": "2026-08-25", "note": "R3 시점 paper_v1 동결 baseline", "cases": current},
            ensure_ascii=False, indent=1), encoding="utf-8")
        pytest.skip("baseline 최초 생성 — 다음 실행부터 비교")
    frozen = json.loads(PAPER_BASELINE_PATH.read_text(encoding="utf-8"))["cases"]
    assert set(current) == set(frozen)
    for key, cur in current.items():
        assert cur["e"] == pytest.approx(frozen[key]["e"], abs=1e-9), key
        assert cur["det_pass"] == frozen[key]["det_pass"], key
