#!/usr/bin/env python3
"""논문 5항 적합도 (WI-07).

fitness = alpha*DETPass + beta*S_DET + gamma*ReplayFit_search
          - lambda_t*Tok_hat - lambda_l*Lat_hat

가중치·정규화 기준은 configs/ga_search_fitness.json 에서 로드한다.
ReplayFit 이 제공되지 않으면 gamma 항은 0이 되고 replay_fit_missing 플래그가
기록된다(값 날조 금지 원칙).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FITNESS_CONFIG_PATH = REPO_ROOT / "configs" / "ga_search_fitness.json"

REQUIRED_WEIGHT_KEYS = (
    "alpha_detpass",
    "beta_sdet",
    "gamma_replayfit",
    "lambda_tokens",
    "lambda_latency",
)


def load_fitness_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_FITNESS_CONFIG_PATH
    config = json.loads(config_path.read_text(encoding="utf-8"))
    weights = config.get("weights") or {}
    missing = [key for key in REQUIRED_WEIGHT_KEYS if key not in weights]
    if missing:
        raise ValueError(f"fitness config missing weight keys: {missing} ({config_path})")
    normalization = config.setdefault("normalization", {})
    normalization.setdefault("sdet_scale", 100.0)
    normalization.setdefault("tokens_ref", 4096)
    normalization.setdefault("latency_ref_sec", 5.0)
    config["_config_path"] = str(config_path)
    return config


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _clip01(value: float) -> float:
    return min(1.0, max(0.0, value))


FITNESS_MODES = {"graded", "binary"}


def normalize_fitness_mode(mode: str | None) -> str:
    """CLI 별칭 정규화: strict_det/graded → graded, binary/detpass_only → binary."""
    token = str(mode or "graded").strip().lower()
    if token in {"", "graded", "strict_det", "default"}:
        return "graded"
    if token in {"binary", "detpass_only", "detpass"}:
        return "binary"
    raise ValueError(f"unknown fitness mode: {mode!r} (graded|binary)")


def compute_fitness(
    *,
    det_pass_rate: float,
    avg_det_score: float,
    replay_fit: float | None,
    avg_total_tokens: float,
    avg_latency_sec: float,
    config: dict[str, Any],
    mode: str = "graded",
) -> dict[str, Any]:
    mode = normalize_fitness_mode(mode)
    weights = config["weights"]
    norm = config["normalization"]
    sdet = _clip01(_float(avg_det_score) / _float(norm.get("sdet_scale"), 100.0))
    if mode == "binary":
        sdet = 0.0  # 이진 모드: 등급 신호(β·S_DET) 제거, DETPass 신호만 사용 (C-22 비교용)
    tok_hat = _clip01(_float(avg_total_tokens) / max(1.0, _float(norm.get("tokens_ref"), 4096)))
    lat_hat = _clip01(_float(avg_latency_sec) / max(1e-9, _float(norm.get("latency_ref_sec"), 5.0)))
    replay_fit_missing = replay_fit is None
    gamma_input = 0.0 if replay_fit_missing else _clip01(_float(replay_fit))

    alpha_term = _float(weights["alpha_detpass"]) * _clip01(_float(det_pass_rate))
    beta_term = _float(weights["beta_sdet"]) * sdet
    gamma_term = _float(weights["gamma_replayfit"]) * gamma_input
    tokens_penalty = _float(weights["lambda_tokens"]) * tok_hat
    latency_penalty = _float(weights["lambda_latency"]) * lat_hat
    fitness = alpha_term + beta_term + gamma_term - tokens_penalty - latency_penalty
    return {
        "fitness": fitness,
        "mode": mode,
        "replay_fit_missing": replay_fit_missing,
        "terms": {
            "alpha_term": alpha_term,
            "beta_term": beta_term,
            "gamma_term": gamma_term,
            "tok_hat": tok_hat,
            "lat_hat": lat_hat,
            "tokens_penalty": tokens_penalty,
            "latency_penalty": latency_penalty,
        },
    }


def aggregate_genome_scores(
    eval_rows: list[dict[str, Any]],
    *,
    config: dict[str, Any] | None = None,
    replay_fit_by_genome: dict[str, float] | None = None,
    mode: str = "graded",
) -> list[dict[str, Any]]:
    """genome 단위 지표 집계 + 논문 5항 적합도.

    하위호환 키(avg_det_score, det_pass_rate, gt_exact_rate, avg_prompt_tokens,
    avg_latency_sec, fitness)를 유지한다. gt_exact_rate 는 보고용 지표일 뿐
    적합도 항이 아니다.
    """
    if config is None:
        config = load_fitness_config()
    replay_map = replay_fit_by_genome or {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in eval_rows:
        grouped.setdefault(str(row.get("genome_id") or "base"), []).append(row)
    records = []
    for genome_id, rows in grouped.items():
        count = len(rows) or 1
        avg_det = sum(_float(row.get("det_score")) for row in rows) / count
        pass_rate = sum(1 for row in rows if _truthy(row.get("det_pass"))) / count
        exact_rate = sum(1 for row in rows if _truthy(row.get("gt_exact"))) / count
        prompt_tokens = sum(_float(row.get("generation_prompt_tokens_total")) for row in rows) / count
        total_tokens = sum(_float(row.get("generation_total_tokens_total")) for row in rows) / count
        latency = sum(_float(row.get("latency_sec")) for row in rows) / count
        result = compute_fitness(
            det_pass_rate=pass_rate,
            avg_det_score=avg_det,
            replay_fit=replay_map.get(genome_id),
            avg_total_tokens=total_tokens,
            avg_latency_sec=latency,
            config=config,
            mode=mode,
        )
        records.append(
            {
                "genome_id": genome_id,
                "rows": len(rows),
                "avg_det_score": avg_det,
                "det_pass_rate": pass_rate,
                "gt_exact_rate": exact_rate,
                "avg_prompt_tokens": prompt_tokens,
                "avg_total_tokens": total_tokens,
                "avg_latency_sec": latency,
                "replay_fit": replay_map.get(genome_id),
                "replay_fit_missing": result["replay_fit_missing"],
                "fitness": result["fitness"],
                "fitness_mode": result["mode"],
                "fitness_terms": result["terms"],
            }
        )
    return sorted(records, key=lambda item: (-float(item["fitness"]), item["genome_id"]))
