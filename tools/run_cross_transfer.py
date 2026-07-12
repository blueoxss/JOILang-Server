#!/usr/bin/env python3
"""WI-02: 교차 전이 3×3 러너 (C-20).

프롬프트 아티팩트(모델별 최종 유전형/프롬프트) × 대상 모델의 전이 행렬을 평가한다.
- 9셀: {P_Q7, P_L8, P_Q14} × {Q7, L8, Q14}
- DT 3셀: 클라우드 저작 기본 프롬프트(모델 패키지 원본)를 각 대상 모델에 직접 적용
출력: results/cross_transfer/<ts>/matrix.csv, verdicts.json
검증: (a) 각 열 argmax가 대각인지, (b) 대각 셀이 §3 앵커 ±1.0%p 내인지 —
프롬프트 provenance 가 paper_grade 가 아니면 앵커 검증은 SKIPPED 로 기록(수치 조작 금지).
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

# §3 수치 앵커 (절대 수정 금지) — GPS 대각 / DT 셀 기대값
ANCHORS = {
    "GPS": {
        "Q7": {"detpass": 92.6, "sdet": 0.87, "replayacc": 91.2},
        "L8": {"detpass": 88.7, "sdet": 0.82, "replayacc": 89.4},
        "Q14": {"detpass": 94.0, "sdet": 0.89, "replayacc": 92.2},
    },
    "DT": {
        "Q7": {"detpass": 87.8, "sdet": 0.73, "replayacc": 80.8},
        "L8": {"detpass": 81.7, "sdet": 0.68, "replayacc": 72.4},
        "Q14": {"detpass": 90.1, "sdet": 0.77, "replayacc": 84.3},
    },
}
ANCHOR_TOLERANCE_PP = 1.0


def run_eval_cell(
    *,
    model_package: str,
    target_model_key: str,
    genome_json: str | None,
    args: argparse.Namespace,
    out_dir: Path,
) -> dict:
    cmd = [
        sys.executable, "-m", "utils.ga_search.cli", "eval",
        "--model", model_package,
        "--dataset", args.dataset,
        "--service-schema", args.service_schema,
        "--llm-mode", args.llm_mode,
        "--model-key", target_model_key,
        "--det-profile", "strict",
        "--det-threshold", str(args.det_threshold),
        "--candidate-k", str(args.candidate_k),
        "--out-dir", str(out_dir),
        "--print-mode", "none",
    ]
    if args.stratify_per_category:
        cmd += ["--stratify-per-category", str(args.stratify_per_category)]
        cmd += ["--seed", str(args.seed)]
    if genome_json:
        cmd += ["--genome-json", genome_json]
    completed = subprocess.run(cmd, cwd=args.code_root or REPO)
    if completed.returncode != 0:
        return {"error": f"eval failed rc={completed.returncode}"}
    summary = json.loads((out_dir / "eval" / "summary.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((out_dir / "eval" / "row_evaluation.csv").open(encoding="utf-8-sig")))
    tokens = [float(row.get("generation_total_tokens_total") or 0) for row in rows]
    latency = [float(row.get("latency_sec") or 0) for row in rows if str(row.get("latency_sec") or "").strip()]
    return {
        "det_pass_rate": summary.get("det_pass_rate"),
        "avg_det_score": summary.get("avg_det_score"),
        "generation_error_rate": summary.get("generation_error_rate"),
        "rows": summary.get("rows"),
        "avg_total_tokens": sum(tokens) / len(tokens) if tokens else 0.0,
        "avg_latency_sec": sum(latency) / len(latency) if latency else 0.0,
    }


def build_verdicts(cells: list[dict], prompts: list[dict], targets: list[dict]) -> dict:
    verdicts: dict = {"argmax_by_target": {}, "anchor_checks": [], "notes": []}
    prompt_ids = [p["id"] for p in prompts]
    for target in targets:
        label = target["label"]
        column = {
            c["prompt_id"]: float(c["det_pass_rate"] or 0)
            for c in cells
            if c["target"] == label and c["prompt_id"] in prompt_ids and not c.get("error")
        }
        if not column:
            continue
        best = max(column, key=column.get)
        expected = next((p["id"] for p in prompts if p.get("source_target_label") == label), None)
        verdicts["argmax_by_target"][label] = {
            "argmax_prompt": best,
            "diagonal_prompt": expected,
            "diagonal_is_argmax": best == expected,
            "column": column,
        }
    for c in cells:
        anchor_group = "DT" if c["prompt_id"] == "DT" else "GPS"
        diagonal = c["prompt_id"] == "DT" or c.get("is_diagonal")
        if not diagonal or c.get("error"):
            continue
        anchor = ANCHORS[anchor_group].get(c["target"])
        if anchor is None:
            continue
        if c.get("provenance") != "paper_grade":
            verdicts["anchor_checks"].append(
                {
                    "cell": f"{c['prompt_id']}×{c['target']}",
                    "status": "SKIPPED",
                    "diagnosis": f"provenance={c.get('provenance')} — 논문 예산 GA 산출물이 아니므로 앵커 비교는 무의미(수치 조작 금지 원칙)",
                }
            )
            continue
        measured_pp = float(c["det_pass_rate"] or 0) * 100.0
        delta = measured_pp - anchor["detpass"]
        status = "WITHIN" if abs(delta) <= ANCHOR_TOLERANCE_PP else "OUT_OF_BAND"
        entry = {
            "cell": f"{c['prompt_id']}×{c['target']}",
            "anchor_detpass": anchor["detpass"],
            "measured_detpass": measured_pp,
            "delta_pp": round(delta, 2),
            "status": status,
        }
        if status == "OUT_OF_BAND":
            entry["diagnosis"] = "실험 환경/예산 차이 진단 필요 — 앵커에 맞춘 수치 조작 금지"
        verdicts["anchor_checks"].append(entry)
    return verdicts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="프롬프트×타깃 구성 JSON")
    parser.add_argument("--dataset", default="datasets/JOICommands-280.csv")
    parser.add_argument("--service-schema", default="datasets/service_list_ver2.0.1.json")
    parser.add_argument("--llm-mode", default="worker")
    parser.add_argument("--stratify-per-category", type=int, default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--det-threshold", type=float, default=70.0)
    parser.add_argument("--candidate-k", type=int, default=1)
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--out-root", default=str(REPO / "results" / "cross_transfer"))
    parser.add_argument("--code-root", default="")
    parser.add_argument("--ledger-grade", action="store_true", help="논문 예산 본실험 표기 — ledger ingest 자격")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    prompts: list[dict] = config["prompts"]
    targets: list[dict] = config["targets"]
    ts = args.timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = Path(args.out_root) / ts
    root.mkdir(parents=True, exist_ok=True)

    cells: list[dict] = []
    for prompt in prompts + [{"id": "DT", "model_package": config.get("dt_model_package", "gpt_mg.version0_13"), "genome_json": None, "provenance": config.get("dt_provenance", "cloud_authored_base_prompt")}]:
        for target in targets:
            cell_dir = root / f"{prompt['id']}__{target['label']}"
            result = run_eval_cell(
                model_package=prompt.get("model_package", config.get("dt_model_package", "gpt_mg.version0_13")),
                target_model_key=target["key"],
                genome_json=prompt.get("genome_json"),
                args=args,
                out_dir=cell_dir,
            )
            cells.append(
                {
                    "prompt_id": prompt["id"],
                    "target": target["label"],
                    "is_diagonal": prompt.get("source_target_label") == target["label"],
                    "provenance": prompt.get("provenance", "unspecified"),
                    **result,
                }
            )
            print(f"[{prompt['id']}×{target['label']}] {result}", flush=True)

    with (root / "matrix.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["prompt_id", "target", "is_diagonal", "provenance", "det_pass_rate", "avg_det_score", "avg_total_tokens", "avg_latency_sec", "generation_error_rate", "rows", "error"],
        )
        writer.writeheader()
        for cell in cells:
            writer.writerow({key: cell.get(key, "") for key in writer.fieldnames})

    verdicts = build_verdicts(cells, prompts, targets)
    (root / "verdicts.json").write_text(json.dumps(verdicts, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "meta.json").write_text(
        json.dumps({"args": vars(args), "config": config, "timestamp": ts, "ledger_grade": bool(args.ledger_grade)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"written: {root / 'matrix.csv'}")
    print(json.dumps(verdicts["argmax_by_target"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
