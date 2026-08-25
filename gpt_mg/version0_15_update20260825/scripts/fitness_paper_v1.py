#!/usr/bin/env python3
"""paper_v1 GA 적합도 — 논문 IV-4 식 (7)의 구현.

f(C,M) = 0.70·DETPass + 0.20·S_DET − 0.05·Tok̂ − 0.05·Lat̂

- DETPass, S_DET ∈ [0,1]: paper_v1 행 채점(utils/det_paper_v1.py) 집계 (식 5·6)
- Tok̂ = avg_total_tokens / tokens_ref(M), Lat̂ = avg_latency_sec / latency_ref_sec(M)
  — 동일 모델 DirectTransfer 실측 기준값(configs/direct_transfer_baseline.json)으로 정규화.
  기준값이 없는 모델은 **fail-fast** (침묵 기본값 금지, 마스터 §9).
- 식(7)의 0.70은 식(4)의 통과 임계값 τ=0.70과 역할이 다른 별도 설계값.
- 정규화 항은 클리핑하지 않는다(논문에 클리핑 없음): Tok̂>1은 DT보다 긴 프롬프트를 뜻함.

기존 적합도 4종(root fitness.py 5항, v15 legacy AvgDET−αVar, v15 score_main,
run_local_prompt_ga_study)과 **공존**하며 어느 것도 변경하지 않는다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

VERSION_DIR = Path(__file__).resolve().parent.parent
DEFAULT_FITNESS_WEIGHTS_PATH = VERSION_DIR / "configs" / "fitness_weights" / "paper_v1.json"
DEFAULT_BASELINE_PATH = VERSION_DIR / "configs" / "direct_transfer_baseline.json"

# 식(7) 설계값 — config 부재 시에도 동일값 (이중 기록)
PAPER_V1_FITNESS_WEIGHTS = {"detpass": 0.70, "sdet": 0.20, "tokens": 0.05, "latency": 0.05}
FITNESS_KEYS = tuple(PAPER_V1_FITNESS_WEIGHTS)


def load_fitness_weights(path: str | Path | None = None) -> dict[str, float]:
    weights_path = Path(path) if path else DEFAULT_FITNESS_WEIGHTS_PATH
    data = json.loads(weights_path.read_text(encoding="utf-8"))
    weights = {key: float(value) for key, value in dict(data["weights"]).items()}
    missing = set(FITNESS_KEYS) - set(weights)
    unknown = set(weights) - set(FITNESS_KEYS)
    if missing or unknown:
        raise ValueError(
            f"fitness weights keys must be exactly {list(FITNESS_KEYS)} (missing={sorted(missing)}, unknown={sorted(unknown)})")
    return weights


def load_direct_transfer_baseline(path: str | Path | None = None) -> dict[str, dict[str, float]]:
    baseline_path = Path(path) if path else DEFAULT_BASELINE_PATH
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    return dict(data["models"])


def direct_transfer_refs(model_key: str, baseline: dict[str, dict[str, Any]]) -> tuple[float, float]:
    """모델의 (tokens_ref, latency_ref_sec). 부재 시 fail-fast."""
    entry = baseline.get(model_key)
    if entry is None:
        raise ValueError(
            f"DirectTransfer baseline missing for model '{model_key}' "
            f"(available: {sorted(baseline)}). 침묵 기본값은 금지 — "
            f"scripts/build_direct_transfer_baseline.py 로 실측 추가 후 재실행하세요.")
    tokens_ref = float(entry["tokens_ref"])
    latency_ref = float(entry["latency_ref_sec"])
    if tokens_ref <= 0 or latency_ref <= 0:
        raise ValueError(f"invalid DirectTransfer refs for '{model_key}': {entry}")
    return tokens_ref, latency_ref


def aggregate_paper_v1(row_evals: Iterable[dict[str, Any]]) -> dict[str, float]:
    """행 채점 결과 → DETPass(식 5)·S_DET(식 6)."""
    evals = list(row_evals)
    if not evals:
        raise ValueError("row_evals is empty")
    n = len(evals)
    detpass = sum(1.0 for r in evals if r["det_pass"]) / n
    sdet = sum(float(r["e"]) for r in evals) / n
    return {"n": n, "detpass": detpass, "sdet": sdet}


def fitness_paper_v1(
    *,
    detpass: float,
    sdet: float,
    avg_total_tokens: float,
    avg_latency_sec: float,
    model_key: str,
    weights: dict[str, float] | None = None,
    baseline: dict[str, dict[str, Any]] | None = None,
) -> dict[str, float]:
    """식(7) 계산. 반환값에 분해 항 전부 보존 (R4 계수 민감도 재채점용)."""
    w = dict(weights) if weights else dict(PAPER_V1_FITNESS_WEIGHTS)
    refs = baseline if baseline is not None else load_direct_transfer_baseline()
    tokens_ref, latency_ref = direct_transfer_refs(model_key, refs)
    tok_hat = float(avg_total_tokens) / tokens_ref
    lat_hat = float(avg_latency_sec) / latency_ref
    fitness = (w["detpass"] * float(detpass) + w["sdet"] * float(sdet)
               - w["tokens"] * tok_hat - w["latency"] * lat_hat)
    return {
        "fitness": fitness,
        "detpass": float(detpass),
        "sdet": float(sdet),
        "tok_hat": tok_hat,
        "lat_hat": lat_hat,
        "tokens_ref": tokens_ref,
        "latency_ref_sec": latency_ref,
        "weights": w,
        "model_key": model_key,
        "fitness_mode": "paper_v1",
    }


def fitness_from_rows(
    row_evals: Iterable[dict[str, Any]],
    *,
    avg_total_tokens: float,
    avg_latency_sec: float,
    model_key: str,
    weights: dict[str, float] | None = None,
    baseline: dict[str, dict[str, Any]] | None = None,
) -> dict[str, float]:
    agg = aggregate_paper_v1(row_evals)
    out = fitness_paper_v1(
        detpass=agg["detpass"], sdet=agg["sdet"],
        avg_total_tokens=avg_total_tokens, avg_latency_sec=avg_latency_sec,
        model_key=model_key, weights=weights, baseline=baseline)
    out["n"] = agg["n"]
    return out
