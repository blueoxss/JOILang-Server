#!/usr/bin/env python3
"""WI-04c: 이진(DETPass만) vs 등급(+S_DET) 적합도 탐색 비교 러너 (C-22).

동일 seed·예산으로 --fitness-mode graded / binary 를 각각 실행하고
results/search_signal/<ts>/binary_vs_graded.csv 를 생성한다.
(columns: mode, generation, best_det_pass_rate, best_avg_det_score, best_fitness
 + 모드별 요약: 예산 내 최고 DETPass 와 그 도달 세대)
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

MODES = ("graded", "binary")


def run_mode(mode: str, args: argparse.Namespace, out_dir: Path) -> dict:
    cmd = [
        sys.executable, "-m", "utils.ga_search.cli", "search",
        "--model", args.model,
        "--dataset", args.dataset,
        "--service-schema", args.service_schema,
        "--llm-mode", args.llm_mode,
        "--engine-mode", "real",
        "--model-key", args.model_key,
        "--stratify-per-category", str(args.stratify_per_category),
        "--population", str(args.population),
        "--gens", str(args.gens),
        "--seed", str(args.seed),
        "--det-threshold", str(args.det_threshold),
        "--fitness-mode", mode,
        "--timeout-sec", str(args.timeout_sec),
        "--out-dir", str(out_dir),
        "--print-mode", "none",
    ]
    if args.replay_split:
        cmd += ["--replay-split", args.replay_split]
    print(f"[{mode}] RUN:", " ".join(cmd), flush=True)
    completed = subprocess.run(cmd, cwd=args.code_root or REPO)
    if completed.returncode != 0:
        raise SystemExit(f"[{mode}] search failed rc={completed.returncode} (log: {out_dir})")
    return json.loads((out_dir / "ga_summary.json").read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt_mg.version0_13")
    parser.add_argument("--dataset", default="datasets/JOICommands-280.csv")
    parser.add_argument("--service-schema", default="datasets/service_list_ver2.0.1.json")
    parser.add_argument("--llm-mode", default="worker")
    parser.add_argument("--model-key", default="qwen25_coder_7b")
    parser.add_argument("--stratify-per-category", type=int, default=1)
    parser.add_argument("--population", type=int, default=3)
    parser.add_argument("--gens", type=int, default=3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--det-threshold", type=float, default=70.0)
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--replay-split", default="")
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--out-root", default=str(REPO / "results" / "search_signal"))
    parser.add_argument("--code-root", default="", help="실행 코드 스냅샷 위치(worktree). 결과는 out-root에 기록")
    parser.add_argument("--ledger-grade", action="store_true", help="논문 예산 본실험임을 표기 — 이 표기가 있어야 ledger ingest 대상이 됨")
    args = parser.parse_args()

    ts = args.timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = Path(args.out_root) / ts
    root.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    summaries: dict[str, dict] = {}
    for mode in MODES:
        out_dir = root / mode
        summaries[mode] = run_mode(mode, args, out_dir)
        with (out_dir / "ga_generation_progress.csv").open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                rows.append(
                    {
                        "mode": mode,
                        "generation": row["generation"],
                        "best_det_pass_rate": row.get("best_det_pass_rate", ""),
                        "best_avg_det_score": row.get("best_avg_det_score", ""),
                        "best_fitness": row.get("best_fitness", ""),
                    }
                )

    summary_rows = []
    for mode in MODES:
        mode_rows = [row for row in rows if row["mode"] == mode]
        best = max((float(row["best_det_pass_rate"] or 0) for row in mode_rows), default=0.0)
        reach = next(
            (row["generation"] for row in mode_rows if float(row["best_det_pass_rate"] or 0) >= best - 1e-12),
            "",
        )
        summary_rows.append(
            {
                "mode": mode,
                "budget_best_det_pass_rate": best,
                "reach_generation": reach,
                "overall_DETPass_all_rows": summaries[mode].get("best_DETPass"),
                "generation_error_rate": summaries[mode].get("generation_error_rate"),
            }
        )

    out_csv = root / "binary_vs_graded.csv"
    with out_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["mode", "generation", "best_det_pass_rate", "best_avg_det_score", "best_fitness"])
        writer.writeheader()
        writer.writerows(rows)
    with (root / "binary_vs_graded_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["mode", "budget_best_det_pass_rate", "reach_generation", "overall_DETPass_all_rows", "generation_error_rate"])
        writer.writeheader()
        writer.writerows(summary_rows)
    (root / "meta.json").write_text(
        json.dumps({"args": vars(args), "timestamp": ts, "ledger_grade": bool(args.ledger_grade)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"written: {out_csv}")
    for row in summary_rows:
        print(row)


if __name__ == "__main__":
    main()
