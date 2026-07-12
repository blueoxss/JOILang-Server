#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def candidate_rank_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        -int(_truthy(row.get("det_pass"))),
        -_float(row.get("det_score")),
        -int(_truthy(row.get("gt_exact"))),
        _float(row.get("generation_prompt_tokens_total"), 0.0),
        _float(row.get("latency_sec"), 0.0),
        str(row.get("genome_id") or ""),
        int(_float(row.get("candidate_index"), 0.0)),
    )


def rerank_rows(eval_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(eval_rows, key=candidate_rank_key)


def best_row(eval_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    ranked = rerank_rows(eval_rows)
    return ranked[0] if ranked else None


def aggregate_genome_scores(
    eval_rows: list[dict[str, Any]],
    *,
    config: dict[str, Any] | None = None,
    replay_fit_by_genome: dict[str, float] | None = None,
    mode: str = "graded",
) -> list[dict[str, Any]]:
    """논문 5항 적합도 기반 genome 집계 (구현: fitness.py, 설정: configs/ga_search_fitness.json)."""
    try:
        from .fitness import aggregate_genome_scores as _aggregate
    except ImportError:
        from fitness import aggregate_genome_scores as _aggregate  # type: ignore
    return _aggregate(eval_rows, config=config, replay_fit_by_genome=replay_fit_by_genome, mode=mode)
