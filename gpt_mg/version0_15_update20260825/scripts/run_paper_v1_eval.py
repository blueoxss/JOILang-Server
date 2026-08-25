#!/usr/bin/env python3
"""paper_v1 재채점 단일 진입 CLI — 저장된 생성 결과를 LLM 호출 없이 재평가한다.

논문 IV-4 식 (3)–(7)의 전 플래그를 파싱·소비한다:
  --det-profile {paper_v1,legacy,strict}   행 채점 프로파일
  --det-weights PATH                       DET 가중치 JSON (paper_v1 전용, 합=1 검증)
  --det-threshold FLOAT                    통과 임계값 τ (0-1; 기본 0.70; 임의값 지원 — R4 τ sweep)
  --fitness-mode {none,paper_v1}           집계 후 식(7) 적합도 계산 여부
  --fitness-weights PATH                   적합도 계수 JSON
  --direct-transfer-baseline PATH          DT 정규화 기준값 JSON (모델 부재 시 fail-fast)

입력(택1):
  --suite-summary PATH   v15 model_suite *_summary.json (row_metrics[].gt/.output 사용;
                         tokens·latency도 여기서 집계)
  --input PATH           JSONL — 각 레코드에 gt(또는 gt_refs)와 output(또는 candidate)

보장: 이 스크립트는 어떤 LLM도 호출하지 않는다(재채점 전용, 결정적).
출력: <out>/rows.jsonl, <out>/summary.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VERSION_ROOT = Path(__file__).resolve().parent.parent
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from utils.det_paper_v1 import (  # noqa: E402
    DEFAULT_THRESHOLD,
    evaluate_row_paper_v1,
    load_det_weights,
)


def _load_records(args: argparse.Namespace) -> tuple[list[dict], float, float]:
    """(records, avg_total_tokens, avg_latency_sec). 레코드 키: gt/gt_refs, output, row_no, category(+legacy/strict용 command_eng·connected_devices)."""
    if args.suite_summary:
        data = json.loads(Path(args.suite_summary).read_text(encoding="utf-8"))
        rows = data.get("row_metrics") or []
        if not rows:
            raise SystemExit(f"row_metrics 가 비어 있음: {args.suite_summary}")
        records = [
            {
                "row_no": r.get("row_no", i),
                "category": r.get("row_category", r.get("category", "")),
                "gt": r.get("gt", ""),
                "output": r.get("output", ""),
                "command_eng": r.get("command_eng", ""),
                "connected_devices": r.get("connected_devices", ""),
            }
            for i, r in enumerate(rows)
        ]
        tokens = [float(r.get("total_tokens") or 0.0) for r in rows]
        lats = [float(r.get("llm_latency_sec") or 0.0) for r in rows]
        avg_tokens = sum(tokens) / len(tokens) if tokens else 0.0
        avg_lat = sum(lats) / len(lats) if lats else 0.0
        return records, avg_tokens, avg_lat
    if args.input:
        records = []
        with open(args.input, encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                rec.setdefault("row_no", i)
                rec.setdefault("output", rec.get("candidate", ""))
                records.append(rec)
        if not records:
            raise SystemExit(f"레코드 없음: {args.input}")
        return records, float(args.avg_tokens or 0.0), float(args.avg_latency or 0.0)
    raise SystemExit("--suite-summary 또는 --input 중 하나가 필요합니다.")


def _evaluate(records: list[dict], args: argparse.Namespace) -> list[dict]:
    out = []
    if args.det_profile == "paper_v1":
        weights, cfg_threshold, _ = load_det_weights(args.det_weights or None)
        threshold = float(args.det_threshold) if args.det_threshold is not None else cfg_threshold
        for rec in records:
            row = {"category": rec.get("category", "")}
            if rec.get("gt_refs") is not None:
                row["gt_refs"] = rec["gt_refs"]
            else:
                row["gt"] = rec.get("gt", "")
            r = evaluate_row_paper_v1(row, rec.get("output", ""), weights=weights,
                                      threshold=threshold, row_no=rec.get("row_no", ""))
            out.append(r)
        return out
    # legacy/strict: v15 평가기로 비교 채점 (가중치 override는 paper_v1 전용)
    if args.det_weights:
        raise SystemExit("--det-weights 는 --det-profile paper_v1 에서만 지원합니다.")
    from utils.det_evaluator import evaluate_candidate  # noqa: E402

    threshold_100 = 100.0 * (float(args.det_threshold) if args.det_threshold is not None else DEFAULT_THRESHOLD)
    for rec in records:
        det = evaluate_candidate(
            rec.get("command_eng", ""), rec.get("output", ""),
            connected_devices=rec.get("connected_devices", ""),
            ground_truth=rec.get("gt", ""), profile=args.det_profile)
        score = float(det.get("det_score") or 0.0)
        out.append({
            "row_no": rec.get("row_no", ""), "category": rec.get("category", ""),
            "det_profile": args.det_profile, "e": score / 100.0, "det_score": score,
            "det_pass": bool(det.get("det_gt_exact")) or score >= threshold_100,
            "gt_exact": bool(det.get("det_gt_exact")),
            "failure_reasons": det.get("failure_reasons", []),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite-summary", default="")
    ap.add_argument("--input", default="")
    ap.add_argument("--det-profile", choices=["paper_v1", "legacy", "strict"], default="paper_v1")
    ap.add_argument("--det-weights", default="", help="paper_v1 DET 가중치 JSON 경로")
    ap.add_argument("--det-threshold", type=float, default=None, help="τ (0-1). 기본: 가중치 config의 threshold(0.70)")
    ap.add_argument("--fitness-mode", choices=["none", "paper_v1"], default="none")
    ap.add_argument("--fitness-weights", default="")
    ap.add_argument("--direct-transfer-baseline", default="")
    ap.add_argument("--model-key", default="", help="fitness 계산 시 DT 기준값 조회 키")
    ap.add_argument("--avg-tokens", type=float, default=None, help="--input 모드에서 fitness용 평균 총 토큰")
    ap.add_argument("--avg-latency", type=float, default=None, help="--input 모드에서 fitness용 평균 지연(초)")
    ap.add_argument("--out", required=True, help="출력 디렉터리")
    args = ap.parse_args()

    records, avg_tokens, avg_lat = _load_records(args)
    evals = _evaluate(records, args)

    n = len(evals)
    detpass = sum(1 for r in evals if r["det_pass"]) / n
    sdet = sum(float(r["e"]) for r in evals) / n
    summary = {
        "n": n,
        "det_profile": args.det_profile,
        "det_weights_path": args.det_weights or "(default)",
        "det_threshold": (float(args.det_threshold) if args.det_threshold is not None else DEFAULT_THRESHOLD),
        "DETPass": round(detpass, 6),
        "S_DET": round(sdet, 6),
        "hard_gate_rows": sum(1 for r in evals if r.get("hard_gate")),
        "gt_exact_rows": sum(1 for r in evals if r.get("gt_exact")),
        "source": args.suite_summary or args.input,
        "llm_calls": 0,
    }
    if args.fitness_mode == "paper_v1":
        from scripts.fitness_paper_v1 import (  # noqa: E402
            fitness_paper_v1, load_direct_transfer_baseline, load_fitness_weights)

        if not args.model_key:
            raise SystemExit("--fitness-mode paper_v1 은 --model-key 가 필요합니다.")
        if avg_tokens <= 0 or avg_lat <= 0:
            raise SystemExit("fitness 계산에는 평균 토큰·지연이 필요합니다 (--suite-summary 또는 --avg-tokens/--avg-latency).")
        summary["fitness_paper_v1"] = fitness_paper_v1(
            detpass=detpass, sdet=sdet, avg_total_tokens=avg_tokens, avg_latency_sec=avg_lat,
            model_key=args.model_key,
            weights=load_fitness_weights(args.fitness_weights or None),
            baseline=load_direct_transfer_baseline(args.direct_transfer_baseline or None))

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "rows.jsonl", "w", encoding="utf-8") as f:
        for r in evals:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
