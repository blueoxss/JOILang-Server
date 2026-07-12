#!/usr/bin/env python3
"""WI-03: 절제 사다리 A0~A4 러너 (C-21).

- A0: 탐색 없음 — 기본 프롬프트 eval (베이스라인)
- A1: 일반 GA (블록 교차+6연산, 등급 적합도; advisor·리플레이 없음)
- A2: A1 + 진단 변이 (탐색→advisor 패치→패치 주입 재탐색, feedback-guided)
- A3: A2 + 리플레이 항 (γ·ReplayFit_search + holdout 보고)
- A4: 전체 — A3 + 채택 게이트(baseline=A0 지표) — 전체 파이프라인과 동일 코드 경로

출력: results/ablation/<ts>/ladder.csv
(variant × {DETPass, S_DET, ReplayFit(search/holdout), tokens, critical_regressions})
critical_regressions = A0 대비 핵심 부분집합(basic/temporal/complex) DETPass 가
ε(기본 1.0%p) 초과 하락한 부분집합 수.
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
sys.path.insert(0, str(REPO))

from utils.ga_search.gate import load_gate_config, subset_detpass_from_eval_rows  # noqa: E402


def compute_critical_regressions(
    baseline_subsets: dict[str, float | None],
    variant_subsets: dict[str, float | None],
    *,
    epsilon_pp: float = 1.0,
) -> tuple[int, list[str]]:
    eps = epsilon_pp / 100.0
    regressed = []
    for name, base in baseline_subsets.items():
        current = variant_subsets.get(name)
        if base is None or current is None:
            continue
        if current < base - eps - 1e-9:
            regressed.append(name)
    return len(regressed), regressed


def _read_eval_rows(run_dir: Path) -> list[dict]:
    path = run_dir / "eval" / "row_evaluation.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_failure_report(run_dir: Path) -> Path:
    """정본 row_evaluation.csv → advisor 가 소비하는 local_det_failure_report.json 어댑터."""
    rows = _read_eval_rows(run_dir)
    failures = []
    for row in rows:
        if str(row.get("det_pass", "")).strip().lower() in {"true", "1"}:
            continue
        try:
            reasons = json.loads(row.get("failure_reasons") or "[]")
        except Exception:
            reasons = [item for item in str(row.get("failure_reasons") or "").split(",") if item]
        failures.append(
            {
                "row_no": row.get("row_no", ""),
                "category": row.get("category", ""),
                "gt_code": row.get("gt_code", ""),
                "output_code": row.get("generated_code", ""),
                "failure_reasons": reasons,
            }
        )
    report = {
        "metadata": {"row_count": len(rows), "source": str(run_dir / "eval" / "row_evaluation.csv"), "adapter": "tools/run_ablation_ladder.py:build_failure_report"},
        "rows": failures,
    }
    path = run_dir / "local_det_failure_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _best_rows(run_dir: Path) -> list[dict]:
    """search 산출물에서 최종 best genome 의 행 평가만 추출."""
    best = json.loads((run_dir / "best_genome.json").read_text(encoding="utf-8"))
    rows = _read_eval_rows(run_dir)
    mine = [row for row in rows if str(row.get("genome_id")) == str(best.get("id"))]
    return mine or rows


def _summary(run_dir: Path) -> dict:
    return json.loads((run_dir / "ga_summary.json").read_text(encoding="utf-8"))


def _cli(args: argparse.Namespace, sub: str, out_dir: Path, extra: list[str]) -> None:
    if sub == "advisor":
        # advisor 서브커맨드는 모델·advisor 인자만 받는다
        cmd = [
            sys.executable, "-m", "utils.ga_search.cli", "advisor",
            "--model", args.model,
            "--out-dir", str(out_dir),
        ] + extra
    else:
        cmd = [
            sys.executable, "-m", "utils.ga_search.cli", sub,
            "--model", args.model,
            "--dataset", args.dataset,
            "--service-schema", args.service_schema,
            "--llm-mode", args.llm_mode,
            "--model-key", args.model_key,
            "--stratify-per-category", str(args.stratify_per_category),
            "--seed", str(args.seed),
            "--det-threshold", str(args.det_threshold),
            "--out-dir", str(out_dir),
            "--print-mode", "none",
        ] + extra
    print(f"[{out_dir.name}] RUN:", " ".join(cmd), flush=True)
    completed = subprocess.run(cmd, cwd=args.code_root or REPO)
    if completed.returncode != 0:
        raise SystemExit(f"{out_dir.name} failed rc={completed.returncode}")


def _search_extra(args: argparse.Namespace) -> list[str]:
    return [
        "--engine-mode", "real",
        "--population", str(args.population),
        "--gens", str(args.gens),
    ]


def _metrics_from_search(run_dir: Path, subsets_config: dict) -> dict:
    summary = _summary(run_dir)
    best_rows = _best_rows(run_dir)
    passes = [str(row.get("det_pass", "")).strip().lower() in {"true", "1"} for row in best_rows]
    tokens = [float(row.get("generation_total_tokens_total") or 0) for row in best_rows]
    scores = [float(row.get("det_score") or 0) for row in best_rows]
    replay = summary.get("replay") or {}
    history = replay.get("search_history") or []
    last_fit = ""
    if history:
        fits = history[-1].get("search_replay_fit_by_genome") or {}
        best_id = json.loads((run_dir / "best_genome.json").read_text(encoding="utf-8")).get("id")
        last_fit = fits.get(str(best_id), "")
    return {
        "det_pass_rate": sum(passes) / len(passes) if passes else 0.0,
        "avg_det_score": sum(scores) / len(scores) if scores else 0.0,
        "avg_total_tokens": sum(tokens) / len(tokens) if tokens else 0.0,
        "replay_fit_search": last_fit,
        "holdout_replay_fit": (replay.get("holdout_report") or {}).get("replay_fit", ""),
        "subset_detpass": subset_detpass_from_eval_rows(best_rows, subsets_config),
        "adopted": (summary.get("adoption_gate") or {}).get("adopted", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt_mg.version0_13")
    parser.add_argument("--dataset", default="datasets/JOICommands-280.csv")
    parser.add_argument("--service-schema", default="datasets/service_list_ver2.0.1.json")
    parser.add_argument("--llm-mode", default="worker")
    parser.add_argument("--model-key", default="qwen25_coder_7b")
    parser.add_argument("--stratify-per-category", type=int, default=1)
    parser.add_argument("--population", type=int, default=3)
    parser.add_argument("--gens", type=int, default=2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--det-threshold", type=float, default=70.0)
    parser.add_argument("--replay-split", default="datasets/replay_split.json")
    parser.add_argument("--epsilon-pp", type=float, default=1.0)
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--out-root", default=str(REPO / "results" / "ablation"))
    parser.add_argument("--code-root", default="")
    args = parser.parse_args()

    gate_config = load_gate_config()
    subsets_config = gate_config["critical_subsets"]
    ts = args.timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = Path(args.out_root) / ts
    root.mkdir(parents=True, exist_ok=True)
    rows_out: list[dict] = []

    # ---- A0: 탐색 없음 (기본 프롬프트 eval) --------------------------------
    a0_dir = root / "A0_no_search"
    _cli(args, "eval", a0_dir, ["--candidate-k", "1"])
    a0_rows = _read_eval_rows(a0_dir)
    a0_passes = [str(row.get("det_pass", "")).strip().lower() in {"true", "1"} for row in a0_rows]
    a0_subsets = subset_detpass_from_eval_rows(a0_rows, subsets_config)
    a0_tokens = [float(row.get("generation_total_tokens_total") or 0) for row in a0_rows]
    a0_scores = [float(row.get("det_score") or 0) for row in a0_rows]
    rows_out.append(
        {
            "variant": "A0_no_search",
            "det_pass_rate": sum(a0_passes) / len(a0_passes) if a0_passes else 0.0,
            "avg_det_score": sum(a0_scores) / len(a0_scores) if a0_scores else 0.0,
            "avg_total_tokens": sum(a0_tokens) / len(a0_tokens) if a0_tokens else 0.0,
            "replay_fit_search": "",
            "holdout_replay_fit": "",
            "critical_regressions": 0,
            "regressed_subsets": "",
            "notes": "baseline",
        }
    )

    # A4 게이트 baseline 파일 (A0 지표)
    baseline_path = root / "gate_baseline_from_A0.json"
    baseline_path.write_text(
        json.dumps(
            {
                "overall_detpass": rows_out[0]["det_pass_rate"],
                "subset_detpass": a0_subsets,
                "holdout_replay_fit": None,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # ---- A1~A4 ------------------------------------------------------------
    # (variant, 진단 변이 여부, phase2 추가 플래그, 설명)
    variants: list[tuple[str, bool, list[str], str]] = [
        ("A1_plain_ga", False, [], "일반 GA (advisor·replay 없음)"),
        ("A2_plus_diagnosis", True, [], "A1 + 진단 변이(탐색→advisor 패치→재주입 탐색)"),
        ("A3_plus_replay", True, ["--replay-split", args.replay_split], "A2 + 리플레이 항"),
        (
            "A4_full",
            True,
            ["--replay-split", args.replay_split, "--gate-baseline", str(baseline_path)],
            "전체 파이프라인(게이트 포함) — 동일 코드 경로",
        ),
    ]
    for name, diagnosis, extra, note in variants:
        run_dir = root / name
        _cli(args, "search", run_dir, _search_extra(args) + extra)
        if diagnosis:
            report = build_failure_report(run_dir)
            advisor_dir = root / f"{name}_advisor"
            _cli(
                args, "advisor", advisor_dir,
                ["--advisor-mode", "local", "--dry-run-advisor", "--local-det-report", str(report)],
            )
            patches = advisor_dir / "advisor" / "prompt_patches.json"
            if patches.exists():
                phase2 = root / f"{name}_phase2"
                _cli(
                    args, "search", phase2,
                    _search_extra(args) + extra + ["--prompt-patches", str(patches), "--feedback-guided-mutation"],
                )
                run_dir = phase2
                note += " (patch 재주입 2단계 실행)"
            else:
                note += " (advisor 패치 미생성 — 1단계 결과 사용, 확인 필요)"
        metrics = _metrics_from_search(run_dir, subsets_config)
        count, regressed = compute_critical_regressions(a0_subsets, metrics["subset_detpass"], epsilon_pp=args.epsilon_pp)
        rows_out.append(
            {
                "variant": name,
                "det_pass_rate": metrics["det_pass_rate"],
                "avg_det_score": metrics["avg_det_score"],
                "avg_total_tokens": metrics["avg_total_tokens"],
                "replay_fit_search": metrics["replay_fit_search"],
                "holdout_replay_fit": metrics["holdout_replay_fit"],
                "critical_regressions": count,
                "regressed_subsets": ",".join(regressed),
                "notes": note + (f" | adopted={metrics['adopted']}" if name == "A4_full" else ""),
            }
        )

    out_csv = root / "ladder.csv"
    with out_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["variant", "det_pass_rate", "avg_det_score", "avg_total_tokens", "replay_fit_search", "holdout_replay_fit", "critical_regressions", "regressed_subsets", "notes"],
        )
        writer.writeheader()
        writer.writerows(rows_out)
    (root / "meta.json").write_text(json.dumps({"args": vars(args), "timestamp": ts}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written: {out_csv}")
    for row in rows_out:
        print(row["variant"], row["det_pass_rate"], "regress:", row["critical_regressions"])


if __name__ == "__main__":
    main()
