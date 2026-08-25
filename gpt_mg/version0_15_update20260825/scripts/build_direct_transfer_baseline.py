#!/usr/bin/env python3
"""configs/direct_transfer_baseline.json 에 모델별 DT 기준값을 실측 아티팩트에서 추가한다.

사용:
  python scripts/build_direct_transfer_baseline.py \
      --model-key qwen25_coder_7b \
      --from-comparison-csv <main_model_comparison.csv> \
      [--provenance "..."] [--baseline PATH]

main_model_comparison.csv 의 avg_total_tokens / warm_latency_mean 열을 읽어
해당 model_key 행의 실측값을 기준값으로 등록한다. 수기 값 입력은 지원하지
않는다 — 기준값은 항상 실측 아티팩트에서 와야 한다(provenance 필수 기록).
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

VERSION_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE_PATH = VERSION_ROOT / "configs" / "direct_transfer_baseline.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model-key", required=True)
    ap.add_argument("--from-comparison-csv", required=True)
    ap.add_argument("--provenance", default="")
    ap.add_argument("--baseline", default="")
    args = ap.parse_args()

    csv_path = Path(args.from_comparison_csv)
    row = next((r for r in csv.DictReader(csv_path.open(encoding="utf-8"))
                if r.get("model_key") == args.model_key), None)
    if row is None:
        raise SystemExit(f"model_key '{args.model_key}' 행이 없음: {csv_path}")
    tokens_ref = float(row["avg_total_tokens"])
    latency_ref = float(row["warm_latency_mean"])
    if tokens_ref <= 0 or latency_ref <= 0:
        raise SystemExit(f"비정상 실측값: tokens={tokens_ref}, latency={latency_ref}")

    baseline_path = Path(args.baseline) if args.baseline else DEFAULT_BASELINE_PATH
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    data["models"][args.model_key] = {
        "tokens_ref": tokens_ref,
        "latency_ref_sec": latency_ref,
        "provenance": args.provenance or str(csv_path),
    }
    baseline_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"registered {args.model_key}: tokens_ref={tokens_ref}, latency_ref_sec={latency_ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
