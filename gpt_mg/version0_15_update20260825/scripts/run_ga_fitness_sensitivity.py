#!/usr/bin/env python3
"""GA 적합도 계수 민감도 (R4, 사전 등록 설계 136dfde4b17e0ac0) — rescore / rerank 수준.

데이터: manual 14B GA 런들의 checkpoints/ga_generation_*.json —
population[i].redesign_metrics 에 (validation_det_pass_rate, validation_avg_det_score,
avg_prompt_tokens, avg_latency_sec)가 보존돼 있어 식(7)을 5개 계수 프로파일로
재계산(rescore)하고, 세대별 순위·우승자 변화(rerank)를 측정한다. LLM 호출 0.

full-GA 수준(계수별 신규 GA 실행)은 GPU 장기 실행 — PAUSED_LONG_RUN 규약으로
run matrix·resume 명령을 문서화하고 실행분만 보고한다 (docs/round_04/changes.md).

출력: generated_tables/ga_fitness_sensitivity.{csv,tex}, artifacts/sensitivity/ga_rescore_rows.csv
"""
from __future__ import annotations

import csv
import itertools
import json
import sys
from pathlib import Path

VERSION_ROOT = Path(__file__).resolve().parent.parent
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from scripts.fitness_paper_v1 import direct_transfer_refs, load_direct_transfer_baseline  # noqa: E402

DATA_RESULTS = Path("/data/mgjeong/JOILang-Server/gpt_mg/version0_15_update20260413/results")
TABLES_DIR = VERSION_ROOT / "generated_tables"
SENS_DIR = VERSION_ROOT / "artifacts" / "sensitivity"
MODEL_KEY = "qwen25_coder_14b"

# 사전 등록 계수 프로파일 (detpass, sdet, tokens, latency)
PROFILES = {
    "base": (0.70, 0.20, 0.05, 0.05),
    "pass_heavy": (0.85, 0.10, 0.025, 0.025),
    "graded_heavy": (0.45, 0.45, 0.05, 0.05),
    "cost_heavy": (0.50, 0.10, 0.20, 0.20),
    "quality_only": (0.78, 0.22, 0.0, 0.0),
}


def find_runs() -> list[Path]:
    runs = sorted(DATA_RESULTS.glob("manual_cloud_only_by_config_*qwen25_coder_14b*/ga_output"))
    return [r for r in runs if (r / "checkpoints").is_dir()]


def load_candidates(run: Path) -> list[dict]:
    """[{run, generation, genome_id, detpass, sdet, tokens, latency}]"""
    out = []
    for ckpt in sorted((run / "checkpoints").glob("ga_generation_*.json")):
        data = json.loads(ckpt.read_text(encoding="utf-8"))
        for item in data.get("population", []):
            m = item.get("redesign_metrics") or {}
            if not m:
                continue
            out.append({
                "run": run.parent.name,
                "generation": int(data.get("generation", 0)),
                "genome_id": str((item.get("genome") or {}).get("id", "")),
                "detpass": float(m.get("validation_det_pass_rate", 0.0)) / 100.0,
                "sdet": float(m.get("validation_avg_det_score", 0.0)) / 100.0,
                "tokens": float(m.get("avg_prompt_tokens", 0.0)),
                "latency": float(m.get("avg_latency_sec", 0.0)),
            })
    return out


def fitness(c: dict, coeffs: tuple, tokens_ref: float, latency_ref: float) -> float:
    a, b, lt, ll = coeffs
    return (a * c["detpass"] + b * c["sdet"]
            - lt * (c["tokens"] / tokens_ref) - ll * (c["latency"] / latency_ref))


def kendall_tau(order_a: list, order_b: list) -> float:
    """두 순위(동일 원소 리스트의 정렬 순서)의 Kendall τ."""
    pos_b = {g: i for i, g in enumerate(order_b)}
    seq = [pos_b[g] for g in order_a]
    n = len(seq)
    if n < 2:
        return 1.0
    concordant = discordant = 0
    for i, j in itertools.combinations(range(n), 2):
        if seq[i] < seq[j]:
            concordant += 1
        else:
            discordant += 1
    return (concordant - discordant) / (concordant + discordant)


def main() -> int:
    baseline = load_direct_transfer_baseline()
    tokens_ref, latency_ref = direct_transfer_refs(MODEL_KEY, baseline)
    runs = find_runs()
    if not runs:
        raise SystemExit("checkpoints를 가진 manual GA 런이 없음")

    SENS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    raw_rows, summary = [], []
    per_gen_groups = []  # (run, generation, candidates)
    all_candidates = []
    for run in runs:
        cands = load_candidates(run)
        all_candidates.extend(cands)
        for gen in sorted({c["generation"] for c in cands}):
            group = [c for c in cands if c["generation"] == gen]
            if len(group) >= 2:
                per_gen_groups.append((run.parent.name, gen, group))

    for pname, coeffs in PROFILES.items():
        for c in all_candidates:
            f = fitness(c, coeffs, tokens_ref, latency_ref)
            raw_rows.append({"profile": pname, "run": c["run"], "generation": c["generation"],
                             "genome_id": c["genome_id"], "fitness": round(f, 6),
                             "detpass": c["detpass"], "sdet": round(c["sdet"], 6),
                             "tok_hat": round(c["tokens"] / tokens_ref, 6),
                             "lat_hat": round(c["latency"] / latency_ref, 6)})
        winner_changes, taus = 0, []
        for run_name, gen, group in per_gen_groups:
            def order(cf):
                return [c["genome_id"] for c in sorted(
                    group, key=lambda c: (-fitness(c, cf, tokens_ref, latency_ref), c["genome_id"]))]
            base_order, var_order = order(PROFILES["base"]), order(coeffs)
            if base_order[0] != var_order[0]:
                winner_changes += 1
            taus.append(kendall_tau(base_order, var_order))
        n_groups = len(per_gen_groups)
        f_vals = [r["fitness"] for r in raw_rows if r["profile"] == pname]
        summary.append({
            "profile": pname,
            "coeffs": "/".join(f"{x:g}" for x in coeffs),
            "n_candidates": len(all_candidates),
            "n_generation_groups": n_groups,
            "fitness_mean": round(sum(f_vals) / len(f_vals), 6),
            "fitness_min": round(min(f_vals), 6),
            "fitness_max": round(max(f_vals), 6),
            "winner_change_rate": round(winner_changes / n_groups, 6) if n_groups else 0.0,
            "mean_kendall_tau_vs_base": round(sum(taus) / len(taus), 6) if taus else 1.0,
        })

    with open(SENS_DIR / "ga_rescore_rows.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(raw_rows[0]))
        w.writeheader()
        w.writerows(raw_rows)
    with open(TABLES_DIR / "ga_fitness_sensitivity.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)

    foot = (f"% source: {len(runs)} manual 14B GA runs (/data .../results/manual_cloud_only_by_config_*), "
            f"{len(all_candidates)} candidate evaluations, {len(per_gen_groups)} generation groups; "
            f"DT normalization {MODEL_KEY} tokens_ref={tokens_ref:.1f} latency_ref={latency_ref:.2f}s; "
            "rescore/rerank only (no new GA runs); design frozen 136dfde4b17e0ac0")
    names_kr = {"base": "기본 (식 7)", "pass_heavy": "통과율 강조", "graded_heavy": "점수 강조",
                "cost_heavy": "비용 강조", "quality_only": "품질 전용"}
    lines = [foot, "\\begin{tabular}{llrrr}", "\\hline",
             "계수 프로파일 & $(\\alpha,\\beta,\\lambda_t,\\lambda_l)$ & 우승자 변경률 & 평균 Kendall $\\tau$ & 평균 적합도 \\\\", "\\hline"]
    for r in summary:
        lines.append(f"{names_kr[r['profile']]} & ({r['coeffs'].replace('/', ', ')}) & "
                     f"{r['winner_change_rate']*100:.1f}\\% & {r['mean_kendall_tau_vs_base']:.3f} & {r['fitness_mean']:.3f} \\\\")
    lines += ["\\hline", "\\end{tabular}"]
    (TABLES_DIR / "ga_fitness_sensitivity.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"runs={len(runs)} candidates={len(all_candidates)} generation_groups={len(per_gen_groups)}")
    for r in summary:
        print(f"  {r['profile']:13s} winner_change={r['winner_change_rate']:.2%} tau={r['mean_kendall_tau_vs_base']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
