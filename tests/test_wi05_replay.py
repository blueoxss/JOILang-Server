"""WI-05 수용 기준 검사.

- datasets/replay_split.json 존재, 30건 고유 사례의 결정적 search/holdout 분리
- 적합도 계산부는 holdout을 참조할 수 없음 — 참조 시 ReplayLeakError (§6 WI-05)
- ReplayFit = 리플레이 사례 재해결율 (det_pass 비율)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from utils.ga_search.replay import (  # noqa: E402
    ReplayLeakError,
    ReplaySplit,
    build_replay_split,
    load_replay_split,
    replay_cases_to_rows,
    replay_pass_rate,
)

SPLIT_PATH = REPO / "datasets" / "replay_split.json"


@pytest.fixture(scope="module")
def split() -> ReplaySplit:
    assert SPLIT_PATH.exists(), "datasets/replay_split.json 부재 — tools/build_replay_split.py 실행 필요"
    return load_replay_split(SPLIT_PATH)


def test_split_file_schema_and_counts(split):
    payload = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    assert payload["schema"] == "ga_search.replay_split.v1"
    assert payload["source"]["unique_cases"] == 30
    assert len(payload["search"]) == 15
    assert len(payload["holdout"]) == 15
    ids = {c["replay_id"] for c in payload["search"]} | {c["replay_id"] for c in payload["holdout"]}
    assert len(ids) == 30, "search/holdout 간 사례 중복 금지"


def test_every_case_has_parseable_gt(split):
    for case in split.search_cases() + split.holdout_cases(consumer="report"):
        gt = json.loads(case["gt"])
        assert isinstance(gt, dict)
        assert set(gt) >= {"name", "cron", "period", "code"}
        assert str(gt["code"]).strip()
        assert str(case["command_kor"]).strip()


def test_holdout_blocked_for_fitness(split):
    with pytest.raises(ReplayLeakError):
        split.holdout_cases(consumer="fitness")
    with pytest.raises(ReplayLeakError):
        split.holdout_cases(consumer="search")
    with pytest.raises(TypeError):
        split.holdout_cases("gate")  # positional 금지 — 명시적 keyword 필수
    assert len(split.holdout_cases(consumer="gate")) == 15


def test_split_deterministic(tmp_path):
    a = build_replay_split(REPO / "datasets" / "usr_rag", tmp_path / "a.json", seed=42)
    b = build_replay_split(REPO / "datasets" / "usr_rag", tmp_path / "b.json", seed=42)
    assert [c["replay_id"] for c in a["search"]] == [c["replay_id"] for c in b["search"]]
    c = build_replay_split(REPO / "datasets" / "usr_rag", tmp_path / "c.json", seed=7)
    assert [x["replay_id"] for x in a["search"]] != [x["replay_id"] for x in c["search"]]


def test_replay_cases_to_rows_shape(split):
    rows = replay_cases_to_rows(split.search_cases())
    assert len(rows) == 15
    idx, row = rows[0]
    assert idx >= 1
    assert row["category"] == "replay"
    assert "gt" in row and json.loads(row["gt"])["code"]


def test_replay_pass_rate():
    eval_rows = [
        {"det_pass": True}, {"det_pass": True}, {"det_pass": False}, {"det_pass": "true"},
    ]
    assert replay_pass_rate(eval_rows) == pytest.approx(0.75)
    assert replay_pass_rate([]) is None  # 사례 없음 → 날조 금지, None
