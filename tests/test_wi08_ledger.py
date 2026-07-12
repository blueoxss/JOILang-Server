"""WI-08 수용 기준 검사.

- sync 실행 시 MEASURED/ANCHOR 행만 값 그대로, PROJECTED 는 † 유지
- PROJECTED 잔존 행 수 stdout 보고 + dry-run 모드
- ingest: mock 실행 결과는 절대 반영 금지, 실측(worker 등)만 PROJECTED→MEASURED
- ANCHOR 행은 ingest 로도 수정 불가 (§3 절대 수정 금지)
"""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location("sync_ledger", REPO / "tools" / "sync_ledger_to_tex.py")
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)


def test_ledger_anchor_values_match_master_prompt():
    rows = sl.load_ledger(REPO / "projected_results_ledger.csv")
    by_id = {row["metric_id"]: row for row in rows}
    assert by_id["main.cloudref.detpass"]["value"] == "94.5"
    assert by_id["main.q7.gps.detpass"]["value"] == "92.6"
    assert by_id["main.l8.gps.detpass"]["value"] == "88.7"
    assert by_id["main.q14.gps.detpass"]["value"] == "94.0"
    assert all(by_id[k]["status"] == "ANCHOR" for k in by_id if k.startswith("main."))


def test_macro_name_no_digits():
    name = sl.macro_name("cross_transfer.P_Q7.Q7.detpass")
    assert name[0:3] == "res"
    assert not any(ch.isdigit() for ch in name)


def test_sync_dagger_and_projected_count(tmp_path):
    rows = [
        {"metric_id": "a.b", "description": "", "status": "PROJECTED", "value": "TBD", "unit": "", "source": "", "updated_by": ""},
        {"metric_id": "c.d", "description": "", "status": "MEASURED", "value": "91.2", "unit": "", "source": "", "updated_by": ""},
        {"metric_id": "e.f", "description": "", "status": "ANCHOR", "value": "94.5", "unit": "", "source": "", "updated_by": ""},
    ]
    tex = tmp_path / "vals.tex"
    report = sl.sync_tex(rows, tex, dry_run=False)
    assert report["projected_remaining"] == 1
    text = tex.read_text(encoding="utf-8")
    assert "\\dagger" in text and "TBD$^\\dagger$" in text
    assert "{91.2}" in text and "{94.5}" in text
    # dry-run 은 쓰지 않음
    tex2 = tmp_path / "vals2.tex"
    report2 = sl.sync_tex(rows, tex2, dry_run=True)
    assert report2["written"] is False and not tex2.exists()


def _mk_search_signal(root: Path, llm_mode: str):
    run = root / "search_signal" / "20990101T000000Z"
    run.mkdir(parents=True)
    (run / "meta.json").write_text(json.dumps({"args": {"llm_mode": llm_mode}}), encoding="utf-8")
    with (run / "binary_vs_graded_summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["mode", "budget_best_det_pass_rate", "reach_generation", "overall_DETPass_all_rows", "generation_error_rate"])
        writer.writeheader()
        writer.writerow({"mode": "graded", "budget_best_det_pass_rate": "0.912", "reach_generation": "7", "overall_DETPass_all_rows": "0.9", "generation_error_rate": "0"})
        writer.writerow({"mode": "binary", "budget_best_det_pass_rate": "0.887", "reach_generation": "10", "overall_DETPass_all_rows": "0.87", "generation_error_rate": "0"})


def _base_rows():
    return [
        {"metric_id": "search_signal.graded.budget_best_detpass", "description": "", "status": "PROJECTED", "value": "TBD", "unit": "pp", "source": "", "updated_by": ""},
        {"metric_id": "search_signal.graded.reach_generation", "description": "", "status": "PROJECTED", "value": "TBD", "unit": "gen", "source": "", "updated_by": ""},
        {"metric_id": "search_signal.binary.budget_best_detpass", "description": "", "status": "PROJECTED", "value": "TBD", "unit": "pp", "source": "", "updated_by": ""},
        {"metric_id": "search_signal.binary.reach_generation", "description": "", "status": "PROJECTED", "value": "TBD", "unit": "gen", "source": "", "updated_by": ""},
    ]


def test_ingest_real_run_flips_to_measured(tmp_path):
    _mk_search_signal(tmp_path, "worker")
    rows = _base_rows()
    updated = sl.ingest(rows, tmp_path)
    assert len(updated) == 4
    graded = next(r for r in rows if r["metric_id"] == "search_signal.graded.budget_best_detpass")
    assert graded["status"] == "MEASURED"
    assert graded["value"] == 91.2
    assert "search_signal" in graded["source"]


def test_ingest_refuses_mock_runs(tmp_path):
    _mk_search_signal(tmp_path, "mock")
    rows = _base_rows()
    updated = sl.ingest(rows, tmp_path)
    assert updated == []
    assert all(row["status"] == "PROJECTED" for row in rows)
