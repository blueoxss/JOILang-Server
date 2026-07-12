#!/usr/bin/env python3
"""리플레이 사례 분리(search/holdout)와 ReplayFit (WI-05).

- 원천: datasets/usr_rag/sentence_best_code_log_*.csv (demo.py 확정 결과, sentence→best_code)
  admin_logs/slack/*.jsonl 은 gt(확정 코드)가 없어 제외한다.
- 분리 원칙(논문 C-14): 적합도는 search 사례만, 보고·채택 게이트는 holdout 사례만 본다.
  holdout 접근은 consumer 화이트리스트("gate", "report")로 강제하며,
  그 외 소비자는 ReplayLeakError 를 발생시킨다 — 데이터 누수 방지가 목적이므로
  이 예외를 우회하는 호출을 추가하지 말 것.
- ReplayFit = 재해결율 = strict DET pass 비율. 사례가 없으면 None(날조 금지).
"""
from __future__ import annotations

import ast
import csv
import json
import random
from pathlib import Path
from typing import Any, Callable

REPLAY_SPLIT_SCHEMA = "ga_search.replay_split.v1"
DEFAULT_REPLAY_SPLIT_PATH = Path(__file__).resolve().parents[2] / "datasets" / "replay_split.json"

HOLDOUT_CONSUMERS = {"gate", "report"}


class ReplayLeakError(RuntimeError):
    """holdout 리플레이 사례가 적합도/탐색 경로로 새는 것을 차단한다."""


def _normalize_best_code(raw: str) -> dict[str, Any]:
    """usr_rag 의 best_code(Python 리터럴 문자열)를 gt 객체로 정규화."""
    text = str(raw or "").strip()
    if not text:
        raise ValueError("empty best_code")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = ast.literal_eval(text)
    if isinstance(parsed, list):
        if not parsed:
            raise ValueError("empty best_code list")
        parsed = parsed[0]
    if not isinstance(parsed, dict):
        raise ValueError(f"best_code must be an object, got {type(parsed).__name__}")
    return {
        "name": str(parsed.get("name", "")),
        "cron": str(parsed.get("cron", "")),
        "period": parsed.get("period", 0),
        "code": str(parsed.get("code") or parsed.get("script") or ""),
    }


def build_replay_split(
    usr_rag_dir: str | Path,
    out_path: str | Path,
    *,
    seed: int = 0,
    search_count: int | None = None,
) -> dict[str, Any]:
    """usr_rag 사례를 중복 제거해 결정적 search/holdout 분할 파일을 생성한다."""
    source_dir = Path(usr_rag_dir)
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    total_rows = 0
    files = sorted(source_dir.glob("*.csv"))
    skipped: list[dict[str, str]] = []
    for path in files:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                total_rows += 1
                sentence = str(row.get("sentence") or "").strip()
                raw_code = str(row.get("best_code") or "").strip()
                key = (sentence, raw_code)
                if not sentence or not raw_code or key in unique:
                    continue
                try:
                    gt = _normalize_best_code(raw_code)
                except Exception as exc:
                    skipped.append({"file": path.name, "sentence": sentence[:50], "reason": str(exc)})
                    continue
                unique[key] = {
                    "command_kor": sentence,
                    "gt": json.dumps(gt, ensure_ascii=False),
                    "source_file": path.name,
                }
    cases = [dict(case, replay_id=f"replay_{index:03d}") for index, case in enumerate(sorted(unique.values(), key=lambda c: (c["command_kor"], c["gt"])), start=1)]
    count = search_count if search_count is not None else len(cases) // 2
    rng = random.Random(seed)
    search_ids = set(rng.sample([c["replay_id"] for c in cases], count))
    payload = {
        "schema": REPLAY_SPLIT_SCHEMA,
        "seed": seed,
        "source": {
            "dir": str(source_dir),
            "files": len(files),
            "total_rows": total_rows,
            "unique_cases": len(cases),
            "skipped": skipped,
            "excluded_sources": ["admin_logs/slack/*.jsonl — gt(확정 코드) 부재로 제외"],
            "paper_note": "논문은 리플레이 60건(30/30)을 서술하나 실측 고유 사례는 이 수치임 — audit/assumptions_diff.md AS-02 참조",
        },
        "search": [c for c in cases if c["replay_id"] in search_ids],
        "holdout": [c for c in cases if c["replay_id"] not in search_ids],
    }
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


class ReplaySplit:
    def __init__(self, payload: dict[str, Any], *, path: str | Path | None = None) -> None:
        if payload.get("schema") != REPLAY_SPLIT_SCHEMA:
            raise ValueError(f"unsupported replay split schema: {payload.get('schema')!r}")
        self._search = list(payload.get("search") or [])
        self._holdout = list(payload.get("holdout") or [])
        self.source = dict(payload.get("source") or {})
        self.seed = payload.get("seed")
        self.path = str(path) if path else None

    def search_cases(self) -> list[dict[str, Any]]:
        return [dict(case) for case in self._search]

    def holdout_cases(self, *, consumer: str) -> list[dict[str, Any]]:
        if consumer not in HOLDOUT_CONSUMERS:
            raise ReplayLeakError(
                f"holdout replay cases are restricted to consumers {sorted(HOLDOUT_CONSUMERS)}; "
                f"got consumer={consumer!r}. 적합도/탐색 경로에서 holdout 접근은 데이터 누수다."
            )
        return [dict(case) for case in self._holdout]

    @property
    def counts(self) -> dict[str, int]:
        return {"search": len(self._search), "holdout": len(self._holdout)}


def load_replay_split(path: str | Path | None = None) -> ReplaySplit:
    split_path = Path(path) if path else DEFAULT_REPLAY_SPLIT_PATH
    payload = json.loads(split_path.read_text(encoding="utf-8"))
    return ReplaySplit(payload, path=split_path)


def replay_cases_to_rows(cases: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    """리플레이 사례를 데이터셋 행 형식으로 변환(평가 파이프라인 재사용)."""
    rows: list[tuple[int, dict[str, Any]]] = []
    for index, case in enumerate(cases, start=1):
        rows.append(
            (
                index,
                {
                    "category": "replay",
                    "replay_id": case.get("replay_id", f"replay_{index:03d}"),
                    "command_kor": case.get("command_kor", ""),
                    "command_eng": "",
                    "gt": case.get("gt", ""),
                },
            )
        )
    return rows


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def replay_pass_rate(eval_rows: list[dict[str, Any]]) -> float | None:
    """ReplayFit = det_pass 비율. 평가된 사례가 없으면 None(값 날조 금지)."""
    if not eval_rows:
        return None
    return sum(1 for row in eval_rows if _truthy(row.get("det_pass"))) / len(eval_rows)


def evaluate_replay_fit(
    cases: list[dict[str, Any]],
    *,
    evaluate_rows: Callable[[list[tuple[int, dict[str, Any]]]], list[dict[str, Any]]],
) -> dict[str, Any]:
    """사례 목록을 평가 콜백에 통과시켜 ReplayFit 을 계산한다.

    evaluate_rows 는 (idx, row) 목록을 받아 det_pass 필드를 가진 평가 행을 반환해야 한다.
    """
    rows = replay_cases_to_rows(cases)
    eval_rows = evaluate_rows(rows)
    return {
        "replay_fit": replay_pass_rate(eval_rows),
        "cases": len(cases),
        "evaluated_rows": len(eval_rows),
        "case_ids": [case.get("replay_id") for case in cases],
        "eval_rows": eval_rows,
    }
