#!/usr/bin/env python3
"""WI-04b: 동일 명령에 대한 실패 후보 3건의 S_DET 실값 추출 도구.

gt를 결정적으로 훼손한 3후보(서비스 오명명 / 수치·스케줄 훼손 / JSON 파손)를
strict DET 채점기에 통과시켜, 등급 점수(S_DET=det_score)가 실패 유형별로
어떻게 분포하는지 실값으로 보여준다. 출력: stdout + audit/sdet_examples.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from utils.det_evaluator import strict_det_evaluate_row  # noqa: E402


def _code_key(gt: dict) -> str:
    """gt 는 code 또는 script 키를 쓴다 — 원본 키를 존중한다."""
    return "code" if str(gt.get("code") or "").strip() else "script"


def degrade_wrong_service(gt: dict) -> dict:
    """후보 1: 첫 서비스 호출명을 스키마에 없는 이름으로 교체."""
    candidate = dict(gt)
    key = _code_key(gt)
    candidate[key] = re.sub(
        r"(\([^)]*\)\.)([A-Za-z_][A-Za-z0-9_]*)", r"\1unknownHallucinatedService", str(gt.get(key, "")), count=1
    )
    return candidate


def degrade_schedule_numeric(gt: dict) -> dict:
    """후보 2: cron/period 훼손 + 숫자 리터럴 변조."""
    candidate = dict(gt)
    key = _code_key(gt)
    candidate["cron"] = "0 0 * * *" if not str(gt.get("cron") or "").strip() else ""
    candidate["period"] = 9999
    candidate[key] = re.sub(r"(?<![A-Za-z_])(\d+)", lambda m: str(int(m.group(1)) + 7), str(gt.get(key, "")), count=1)
    return candidate


def degrade_invalid_json(gt: dict) -> str:
    """후보 3: JSON 파손(치명 실패 → S_DET=0 확인용)."""
    return json.dumps(gt, ensure_ascii=False)[:-15] + "..."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(REPO / "datasets" / "JOICommands-280.csv"))
    parser.add_argument("--row-no", type=int, default=1)
    parser.add_argument("--det-threshold", type=float, default=70.0)
    parser.add_argument("--out", default=str(REPO / "audit" / "sdet_examples.json"))
    args = parser.parse_args()

    with open(args.dataset, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    row = rows[args.row_no - 1]
    gt = json.loads(row["gt"]) if not isinstance(row["gt"], dict) else row["gt"]
    if isinstance(gt, list):
        gt = gt[0]

    candidates = {
        "cand_1_unknown_service": degrade_wrong_service(gt),
        "cand_2_schedule_numeric_drift": degrade_schedule_numeric(gt),
        "cand_3_invalid_json": degrade_invalid_json(gt),
    }
    results = []
    for name, candidate in candidates.items():
        scored = strict_det_evaluate_row(
            row=row, candidate=candidate, row_no=args.row_no,
            genome_id="sdet_example", det_threshold=args.det_threshold,
        )
        results.append(
            {
                "candidate": name,
                "det_score(S_DET)": scored["det_score"],
                "det_pass": scored["det_pass"],
                "failure_reasons": scored["failure_reasons"],
                "generated_code": scored["generated_code"][:120],
            }
        )
        print(f"{name}: S_DET={scored['det_score']:.2f} pass={scored['det_pass']} reasons={scored['failure_reasons']}")

    payload = {
        "dataset": args.dataset,
        "row_no": args.row_no,
        "command": row.get("command_eng") or row.get("command_kor"),
        "gt_code": gt.get("code"),
        "det_threshold": args.det_threshold,
        "candidates": results,
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written: {args.out}")


if __name__ == "__main__":
    main()
