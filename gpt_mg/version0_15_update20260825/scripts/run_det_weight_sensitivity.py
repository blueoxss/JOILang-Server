#!/usr/bin/env python3
"""DET 가중치 민감도 실험 (R4, 사전 등록 설계 — round_04/criteria.yaml 136dfde4b17e0ac0).

방법: 저장된 실측 출력(gt·output)에서 paper_v1 8성분을 1회 추출·캐시한 뒤,
가중치 변형별로 e=Σw_k·s_k 를 재계산한다(LLM 호출 0, 재생성 0). 치명 오류
행은 가중치와 무관하게 e=0 (hard gate — 식 4).

변형: 프로파일 5(base/uniform/execution_heavy/structure_heavy/no_code_sim)
      + LOO 8 + ±20% 16 = 29 가중치 변형 × 6 데이터셋, τ∈{0.65,0.70,0.75}×6.
데이터셋(실측): GPT-4.1-mini 280행 suite 5종(프롬프트 v07/v12/v13/v14/v15) + Qwen14B 280행.

출력: configs/det_weights/variants/*.json, artifacts/sensitivity/components_*.jsonl,
      generated_tables/{det_weight_sensitivity_by_model,det_weight_sensitivity_summary,tau_sensitivity}.{csv,tex}
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

VERSION_ROOT = Path(__file__).resolve().parent.parent
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from utils.det_paper_v1 import (  # noqa: E402
    COMPONENT_KEYS,
    PAPER_V1_WEIGHTS,
    evaluate_row_paper_v1,
)

DATA_RESULTS = Path("/data/mgjeong/JOILang-Server/gpt_mg/version0_15_update20260413/results")
SERVER_ROOT = VERSION_ROOT.parents[1]
VARIANTS_DIR = VERSION_ROOT / "configs" / "det_weights" / "variants"
SENS_DIR = VERSION_ROOT / "artifacts" / "sensitivity"
TABLES_DIR = VERSION_ROOT / "generated_tables"
TAUS = (0.65, 0.70, 0.75)
BASE_TAU = 0.70

# 실측 데이터셋 (R1 provenance 감사 §D에서 확정한 run id ↔ 프롬프트 버전 대응)
CLOUD_SUITES = {
    "cloud_v07": "model_suite_20260616_204541",
    "cloud_v12": "model_suite_20260616_184016",
    "cloud_v13": "model_suite_20260616_195956",
    "cloud_v14": "model_suite_20260616_205513",
    "cloud_v15": "model_suite_20260616_184935",
}
QWEN_CSV = SERVER_ROOT / "artifacts" / "eval_pipeline_checks_20260623_111811_full" / "strict_det" / "row_comparison.csv"


def _renorm(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()}


def build_variants() -> dict[str, dict[str, float]]:
    """사전 등록 설계 그대로의 29개 가중치 변형."""
    base = dict(PAPER_V1_WEIGHTS)
    variants: dict[str, dict[str, float]] = {
        "base": base,
        "uniform": {key: 1.0 / 8.0 for key in COMPONENT_KEYS},
        "execution_heavy": {"code_sim": 0.10, "schedule": 0.20, "service_coverage": 0.20,
                            "service_precision": 0.15, "receiver_coverage": 0.15,
                            "numeric_grounding": 0.10, "enum_grounding": 0.05, "dataflow": 0.05},
        "structure_heavy": {"code_sim": 0.50, "schedule": 0.10, "service_coverage": 0.10,
                            "service_precision": 0.05, "receiver_coverage": 0.10,
                            "numeric_grounding": 0.05, "enum_grounding": 0.05, "dataflow": 0.05},
        "no_code_sim": _renorm({key: (0.0 if key == "code_sim" else base[key]) for key in COMPONENT_KEYS}),
    }
    for key in COMPONENT_KEYS:
        variants[f"loo_{key}"] = _renorm({k: (0.0 if k == key else base[k]) for k in COMPONENT_KEYS})
    for key in COMPONENT_KEYS:
        for factor, tag in ((0.8, "m20"), (1.2, "p20")):
            w = dict(base)
            w[key] = base[key] * factor
            variants[f"{tag}_{key}"] = _renorm(w)
    return variants


def write_variant_configs(variants: dict[str, dict[str, float]]) -> None:
    VARIANTS_DIR.mkdir(parents=True, exist_ok=True)
    for name, weights in variants.items():
        (VARIANTS_DIR / f"{name}.json").write_text(json.dumps({
            "profile": name, "scale": "0-1", "threshold": BASE_TAU,
            "description": f"R4 민감도 변형 (사전 등록 설계 136dfde4b17e0ac0): {name}",
            "weights": weights}, ensure_ascii=False, indent=1), encoding="utf-8")


def load_dataset_rows(name: str) -> list[dict]:
    """[{row_no, gt, output}] — 실측 아티팩트에서."""
    if name in CLOUD_SUITES:
        summary = json.loads((DATA_RESULTS / CLOUD_SUITES[name] / "gpt41_mini_summary.json").read_text(encoding="utf-8"))
        return [{"row_no": r.get("row_no"), "gt": r["gt"], "output": r["output"]}
                for r in summary["row_metrics"]]
    if name == "qwen14b":
        rows = []
        for r in csv.DictReader(open(QWEN_CSV, encoding="utf-8")):
            rows.append({"row_no": r["row_no"], "gt": r["gt"], "output": r["qwen25_coder_14b__output"]})
        return rows
    raise ValueError(name)


def extract_components(name: str) -> list[dict]:
    """행별 paper_v1 성분 추출 (1회, 캐시). fatal이면 hard_gate 기록."""
    SENS_DIR.mkdir(parents=True, exist_ok=True)
    cache = SENS_DIR / f"components_{name}.jsonl"
    if cache.exists():
        return [json.loads(line) for line in cache.read_text(encoding="utf-8").splitlines()]
    out = []
    for rec in load_dataset_rows(name):
        r = evaluate_row_paper_v1({"gt": rec["gt"]}, rec["output"], row_no=rec["row_no"])
        out.append({"row_no": rec["row_no"], "components": r["components"],
                    "hard_gate": r["hard_gate"], "e_base": r["e"]})
    with open(cache, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return out


def escore(row: dict, weights: dict[str, float]) -> float:
    if row["hard_gate"]:
        return 0.0
    return sum(weights[key] * row["components"][key] for key in COMPONENT_KEYS)


def aggregate(rows: list[dict], weights: dict[str, float], tau: float) -> dict:
    es = [escore(r, weights) for r in rows]
    passes = [(e >= tau and not r["hard_gate"]) for e, r in zip(es, rows)]
    return {"detpass": sum(passes) / len(rows), "sdet": sum(es) / len(es), "passes": passes}


def spearman(rank_a: list[float], rank_b: list[float]) -> float:
    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: -values[i])
        r = [0.0] * len(values)
        for pos, idx in enumerate(order):
            r[idx] = pos + 1.0
        return r
    ra, rb = ranks(rank_a), ranks(rank_b)
    n = len(ra)
    d2 = sum((x - y) ** 2 for x, y in zip(ra, rb))
    return 1.0 - 6.0 * d2 / (n * (n * n - 1))


def main() -> int:
    variants = build_variants()
    write_variant_configs(variants)
    datasets = list(CLOUD_SUITES) + ["qwen14b"]
    comps = {name: extract_components(name) for name in datasets}
    for name in datasets:
        assert len(comps[name]) == 280, (name, len(comps[name]))

    base_agg = {name: aggregate(comps[name], variants["base"], BASE_TAU) for name in datasets}

    by_rows = []
    summary_rows = []
    cloud_names = list(CLOUD_SUITES)
    base_cloud_rank = [base_agg[c]["detpass"] for c in cloud_names]
    for vname, weights in variants.items():
        deltas, flips = [], []
        agg_by_ds = {}
        for name in datasets:
            agg = aggregate(comps[name], weights, BASE_TAU)
            agg_by_ds[name] = agg
            delta_pp = 100.0 * (agg["detpass"] - base_agg[name]["detpass"])
            flip = sum(1 for a, b in zip(agg["passes"], base_agg[name]["passes"]) if a != b) / len(agg["passes"])
            deltas.append(delta_pp)
            flips.append(flip)
            by_rows.append({"variant": vname, "dataset": name, "n": len(comps[name]),
                            "DETPass": round(agg["detpass"], 6), "S_DET": round(agg["sdet"], 6),
                            "delta_detpass_pp": round(delta_pp, 4), "flip_rate": round(flip, 6),
                            "tau": BASE_TAU})
        rho = spearman([agg_by_ds[c]["detpass"] for c in cloud_names], base_cloud_rank)
        max_abs_delta = max(abs(d) for d in deltas)
        max_flip = max(flips)
        if vname == "base":
            grade = "-"
        elif max_abs_delta <= 2.0 and rho >= 0.90 and max_flip <= 0.05:
            grade = "strong"
        elif max_abs_delta <= 5.0 and rho >= 0.80 and max_flip <= 0.10:
            grade = "moderate"
        else:
            grade = "sensitive"
        summary_rows.append({"variant": vname, "max_abs_delta_pp": round(max_abs_delta, 4),
                             "mean_delta_pp": round(sum(deltas) / len(deltas), 4),
                             "spearman_rho_cloud_rank": round(rho, 4),
                             "max_flip_rate": round(max_flip, 6), "robustness": grade})

    tau_rows = []
    for tau in TAUS:
        for name in datasets:
            agg = aggregate(comps[name], variants["base"], tau)
            tau_rows.append({"tau": tau, "dataset": name, "DETPass": round(agg["detpass"], 6),
                             "S_DET": round(agg["sdet"], 6),
                             "delta_detpass_pp_vs_070": round(100.0 * (agg["detpass"] - base_agg[name]["detpass"]), 4)})

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(TABLES_DIR / "det_weight_sensitivity_by_model.csv", by_rows)
    _write_csv(TABLES_DIR / "det_weight_sensitivity_summary.csv", summary_rows)
    _write_csv(TABLES_DIR / "tau_sensitivity.csv", tau_rows)
    _write_tex_tables(summary_rows, tau_rows, by_rows)
    n_cells = len(by_rows)
    print(f"variants={len(variants)} datasets={len(datasets)} cells={n_cells} tau_cells={len(tau_rows)}")
    print("robustness:", {r['variant']: r['robustness'] for r in summary_rows if r['variant'] != 'base'})
    return 0


def _write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


FOOTNOTE = ("% source: GPT-4.1-mini 280-row suites v07/v12/v13/v14/v15 (/data model_suite_20260616_*) "
            "+ Qwen2.5-Coder-14B 280-row (eval_pipeline_checks_20260623_111811_full); "
            "evaluator paper_v1 (w0, tau=0.70); rescoring only, no LLM calls; design frozen 136dfde4b17e0ac0")


def _write_tex_tables(summary_rows: list[dict], tau_rows: list[dict], by_rows: list[dict]) -> None:
    key_variants = ["uniform", "execution_heavy", "structure_heavy", "no_code_sim"]
    lines = [FOOTNOTE, "\\begin{tabular}{lrrrrl}", "\\hline",
             "가중치 변형 & max$|\\Delta$DETPass$|$(pp) & 평균 $\\Delta$(pp) & Spearman $\\rho$ & max flip & 판정 \\\\", "\\hline"]
    names_kr = {"uniform": "균등", "execution_heavy": "실행 강조", "structure_heavy": "구조 강조",
                "no_code_sim": "코드 유사도 제외"}
    for r in summary_rows:
        if r["variant"] in key_variants:
            lines.append(f"{names_kr[r['variant']]} & {r['max_abs_delta_pp']:.2f} & {r['mean_delta_pp']:.2f} & "
                         f"{r['spearman_rho_cloud_rank']:.3f} & {r['max_flip_rate']*100:.1f}\\% & {r['robustness']} \\\\")
    loo = [r for r in summary_rows if r["variant"].startswith("loo_")]
    pm = [r for r in summary_rows if r["variant"].startswith(("m20_", "p20_"))]
    loo_max = max(loo, key=lambda r: r["max_abs_delta_pp"])
    pm_max = max(pm, key=lambda r: r["max_abs_delta_pp"])

    def tex_esc(s: str) -> str:
        return s.replace("_", "\\_")

    lines += ["\\hline",
              f"LOO 8종 최대(={tex_esc(loo_max['variant'][4:])}) & {loo_max['max_abs_delta_pp']:.2f} & {loo_max['mean_delta_pp']:.2f} & "
              f"{loo_max['spearman_rho_cloud_rank']:.3f} & {loo_max['max_flip_rate']*100:.1f}\\% & {loo_max['robustness']} \\\\",
              f"$\\pm$20\\% 16종 최대(={tex_esc(pm_max['variant'])}) & {pm_max['max_abs_delta_pp']:.2f} & {pm_max['mean_delta_pp']:.2f} & "
              f"{pm_max['spearman_rho_cloud_rank']:.3f} & {pm_max['max_flip_rate']*100:.1f}\\% & {pm_max['robustness']} \\\\",
              "\\hline", "\\end{tabular}"]
    (TABLES_DIR / "det_weight_sensitivity_summary.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    datasets = list(dict.fromkeys(r["dataset"] for r in tau_rows))
    lines = [FOOTNOTE, "\\begin{tabular}{l" + "r" * len(datasets) + "}", "\\hline",
             "$\\tau$ & " + " & ".join(d.replace("_", "\\_") for d in datasets) + " \\\\", "\\hline"]
    for tau in TAUS:
        vals = [next(r for r in tau_rows if r["tau"] == tau and r["dataset"] == d) for d in datasets]
        lines.append(f"{tau:.2f} & " + " & ".join(f"{100*v['DETPass']:.1f}" for v in vals) + " \\\\")
    lines += ["\\hline", "\\end{tabular}"]
    (TABLES_DIR / "tau_sensitivity.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
