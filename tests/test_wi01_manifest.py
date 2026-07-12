"""WI-01 수용 기준 검사.

audit/manifest.json 에 벤치마크/리플레이/스트레스/GA예산/가중치/max_model_len의
'실측값'이 존재하고, 논문 가정(AS-01~08) diff 표가 생성되어 있어야 한다.
모든 수치는 저장소 실측과 재대조한다(P-1: 유추 금지).
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "audit" / "manifest.json"
DIFF_MD = REPO / "audit" / "assumptions_diff.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST.exists(), "audit/manifest.json 부재 — tools/build_settings_manifest.py 실행 필요"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_benchmark_measured_matches_dataset(manifest):
    bench = manifest["datasets"]["benchmark"]
    with (REPO / bench["path"]).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert bench["rows"] == len(rows) == 280
    dist: dict[str, int] = {}
    for r in rows:
        dist[str(r["category"])] = dist.get(str(r["category"]), 0) + 1
    assert bench["category_distribution"] == dist
    assert bench["n_categories"] == len(dist) == 8


def test_replay_and_stress_measured(manifest):
    replay = manifest["datasets"]["replay_sources"]
    total = 0
    for p in sorted((REPO / "datasets" / "usr_rag").glob("*.csv")):
        with p.open(encoding="utf-8-sig", newline="") as f:
            total += len(list(csv.DictReader(f)))
    assert replay["usr_rag_rows"] == total
    assert manifest["datasets"]["stress"]["status"] == "NOT_FOUND"


def test_ga_budget_extracted_from_source(manifest):
    budget = manifest["ga_budget"]["canonical_cli_defaults"]
    cli_src = (REPO / "utils" / "ga_search" / "cli.py").read_text(encoding="utf-8")
    pop = re.search(r'--population",\s*type=int,\s*default=(\d+)', cli_src)
    gens = re.search(r'--gens",\s*type=int,\s*default=(\d+)', cli_src)
    assert pop and budget["population"] == int(pop.group(1))
    assert gens and budget["generations"] == int(gens.group(1))
    # 논문 예산 대비 항목이 diff에 존재해야 함
    assert "elite" in manifest["ga_budget"]["canonical_engine_behavior"]
    assert "tournament" in manifest["ga_budget"]["canonical_engine_behavior"]


def test_fitness_weights_recorded(manifest):
    fitness = manifest["fitness"]["canonical"]
    rerank_src = (REPO / "utils" / "ga_search" / "rerank.py").read_text(encoding="utf-8")
    assert "avg_det + 10.0 * pass_rate" in rerank_src, "rerank.py 수식이 변경되면 manifest 재생성 필요"
    assert fitness["hardcoded"] is True
    assert fitness["source"].startswith("utils/ga_search/rerank.py:")
    paper = manifest["fitness"]["paper_assumption"]
    assert paper["weights"] == [0.50, 0.15, 0.20, 0.10, 0.05]


def test_det_threshold_and_sdet_components(manifest):
    det = manifest["det"]
    assert det["threshold"] == 70.0
    assert det["paper_threshold_claim"] == 0.8
    comps = det["sdet_component_weights"]
    assert abs(sum(comps.values()) - 1.0) < 1e-9
    assert comps["code_sim"] == 0.30


def test_serving_and_max_model_len(manifest):
    serving = manifest["serving"]
    assert serving["vllm_present"] is False
    assert serving["max_model_len"] == "NOT_FOUND"
    assert "local_max_new_tokens" in serving


def test_assumptions_diff_complete(manifest):
    diff = manifest["assumptions_diff"]
    ids = {d["id"] for d in diff}
    assert ids == {f"AS-{i:02d}" for i in range(1, 9)}
    for d in diff:
        assert d["status"] in {"MATCH", "MISMATCH", "ABSENT", "PARTIAL"}
        assert d["measured"], f"{d['id']}: 실측값 비어 있음"
    assert DIFF_MD.exists(), "audit/assumptions_diff.md 부재"
    md = DIFF_MD.read_text(encoding="utf-8")
    for i in range(1, 9):
        assert f"AS-{i:02d}" in md
