#!/usr/bin/env python3
from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Any


def load_dataset_rows(dataset_path: str | Path) -> list[dict[str, Any]]:
    with Path(dataset_path).open(encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def normalize_categories(values: list[str] | tuple[str, ...] | None) -> set[str]:
    out: set[str] = set()
    for raw in values or []:
        for item in str(raw).split(","):
            token = item.strip()
            if token:
                out.add(token)
    return out


def stratified_sample_rows(
    selected: list[tuple[int, dict[str, Any]]],
    *,
    per_category: int,
    seed: int = 0,
) -> list[tuple[int, dict[str, Any]]]:
    """범주 층화 표본: 각 category에서 per_category건을 seed 결정적으로 추출 (논문 C-09)."""
    if per_category < 1:
        raise ValueError(f"per_category must be >= 1: {per_category}")
    groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for idx, row in selected:
        key = str(row.get("category", "")).strip() or "__uncategorized__"
        groups.setdefault(key, []).append((idx, row))
    rng = random.Random(seed)
    sampled: list[tuple[int, dict[str, Any]]] = []
    for key in sorted(groups):
        items = groups[key]
        if len(items) > per_category:
            items = rng.sample(items, per_category)
        sampled.extend(items)
    return sorted(sampled, key=lambda item: item[0])


def select_dataset_rows(
    rows: list[dict[str, Any]],
    *,
    row_no: int | None = None,
    start_row: int = 1,
    end_row: int | None = None,
    categories: list[str] | tuple[str, ...] | None = None,
    limit_per_category: int | None = None,
    sample_size: int | None = None,
    stratify_per_category: int | None = None,
    seed: int = 0,
) -> list[tuple[int, dict[str, Any]]]:
    if row_no is not None:
        if row_no < 1 or row_no > len(rows):
            raise IndexError(f"row_no out of range: {row_no}")
        row = dict(rows[row_no - 1])
        if "gt" not in row or not str(row.get("gt") or "").strip():
            raise ValueError(f"row {row_no} is missing official gt column")
        return [(row_no, row)]

    category_filter = normalize_categories(categories)
    end = end_row if end_row is not None else len(rows)
    selected: list[tuple[int, dict[str, Any]]] = []
    per_category: dict[str, int] = {}
    for idx, row in enumerate(rows, start=1):
        if idx < max(1, start_row) or idx > end:
            continue
        category = str(row.get("category", "")).strip()
        if category_filter and category not in category_filter:
            continue
        if limit_per_category is not None:
            key = category or "__uncategorized__"
            if per_category.get(key, 0) >= limit_per_category:
                continue
            per_category[key] = per_category.get(key, 0) + 1
        if "gt" not in row or not str(row.get("gt") or "").strip():
            raise ValueError(f"row {idx} is missing official gt column")
        selected.append((idx, dict(row)))

    if stratify_per_category is not None:
        if sample_size is not None:
            raise ValueError("stratify_per_category and sample_size are mutually exclusive")
        return stratified_sample_rows(selected, per_category=stratify_per_category, seed=seed)

    if sample_size is not None and sample_size > 0 and len(selected) > sample_size:
        rng = random.Random(seed)
        selected = sorted(rng.sample(selected, sample_size), key=lambda item: item[0])
    return selected


def command_text(row: dict[str, Any]) -> str:
    return str(row.get("command_eng") or row.get("command_kor") or "").strip()
