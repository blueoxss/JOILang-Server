#!/usr/bin/env python3
# Assumption: compare row-level outputs across generation result CSVs under gpt_mg/version0_14/results/.
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = VERSION_ROOT / "results"
DEFAULT_RESULTS = [
    RESULTS_DIR / "full_280_rerank.csv",
    RESULTS_DIR / "full_280_rerank_v2.csv",
    RESULTS_DIR / "full_280_rerank_v3.csv",
    RESULTS_DIR / "full_280_rerank_v4.csv",
    RESULTS_DIR / "full_280_rerank_best_of_v2_v3_v4.csv",
]
GENERATION_LABELS = {
    "full_280_rerank.csv": "v1",
    "full_280_rerank_v2.csv": "v2",
    "full_280_rerank_v3.csv": "v3",
    "full_280_rerank_v4.csv": "v4",
    "full_280_rerank_best_of_v2_v3_v4.csv": "best_of_v2_v3_v4",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect one dataset row across multiple generation CSVs.")
    parser.add_argument("query", nargs="?", default=None, help="Search text when not using --row-no.")
    parser.add_argument("--row-no", type=int, default=None, help="Inspect a specific dataset row number.")
    parser.add_argument("--category", default=None, help="Restrict the match to a category.")
    parser.add_argument(
        "--only-best",
        action="store_true",
        help="Show only the best row among the selected generations. Prefer best_of csv when present.",
    )
    parser.add_argument(
        "--results",
        nargs="*",
        default=None,
        help="Explicit result CSV paths. Defaults to known full-run CSVs under results/.",
    )
    parser.add_argument(
        "--match",
        choices=["auto", "row_no", "index", "contains", "exact"],
        default="auto",
        help="How to interpret query. Default: auto",
    )
    return parser


def generation_name(path: Path) -> str:
    return GENERATION_LABELS.get(path.name, path.stem)


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def detect_results(paths: list[str] | None) -> list[Path]:
    if paths:
        candidates = [Path(item).resolve() if not Path(item).is_absolute() else Path(item) for item in paths]
    else:
        candidates = DEFAULT_RESULTS
    return [path for path in candidates if path.exists()]


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def as_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def find_match(rows: list[dict[str, str]], query: str, match_mode: str) -> dict[str, str] | None:
    lowered = query.strip().lower()
    if match_mode in {"auto", "row_no"} and lowered.isdigit():
        for row in rows:
            if row.get("row_no", "") == lowered:
                return row
    if match_mode == "row_no":
        return None
    if match_mode in {"auto", "index"} and lowered.isdigit():
        for row in rows:
            if row.get("index", "") == lowered:
                return row
    if match_mode == "index":
        return None
    if match_mode in {"auto", "exact"}:
        for row in rows:
            if row.get("command_eng", "").strip().lower() == lowered:
                return row
        if match_mode == "exact":
            return None
    for row in rows:
        if lowered in row.get("command_eng", "").lower() or lowered in row.get("command_kor", "").lower():
            return row
    return None


def filter_rows_by_category(rows: list[dict[str, str]], category: str | None) -> list[dict[str, str]]:
    if not category:
        return rows
    return [row for row in rows if str(row.get("category", "")).strip() == str(category).strip()]


def select_best_row(matched_rows: list[tuple[str, dict[str, str]]]) -> list[tuple[str, dict[str, str]]]:
    if not matched_rows:
        return matched_rows
    for name, row in matched_rows:
        if name == "best_of_v2_v3_v4":
            return [(name, row)]
    ranked = sorted(
        matched_rows,
        key=lambda item: (
            1 if as_bool(item[1].get("det_gt_exact")) else 0,
            as_float(item[1].get("det_score")),
        ),
        reverse=True,
    )
    return [ranked[0]]


def render_summary_table(rows: list[tuple[str, dict[str, str]]]) -> str:
    headers = ["generation", "det_score", "gt_exact", "selected_from"]
    body = []
    for name, row in rows:
        body.append(
            [
                name,
                f"{as_float(row.get('det_score')):.4f}",
                "Y" if as_bool(row.get("det_gt_exact")) else "N",
                row.get("selected_from", "-") or "-",
            ]
        )
    widths = [len(header) for header in headers]
    for row in body:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    lines = []
    header_line = "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    divider = "  ".join("-" * width for width in widths)
    lines.append(header_line)
    lines.append(divider)
    for row in body:
        lines.append("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))
    return "\n".join(lines)


def compact_json_string(raw: str) -> str:
    if not raw:
        return ""
    try:
        parsed = json.loads(raw)
    except Exception:
        return raw
    return json.dumps(parsed, ensure_ascii=False, indent=2)


def main() -> int:
    args = build_parser().parse_args()
    if args.row_no is None and not args.query:
        print("Provide either QUERY text or --row-no.", file=sys.stderr)
        return 1
    result_paths = detect_results(args.results)
    if not result_paths:
        print("No generation result CSVs found.", file=sys.stderr)
        return 1

    matched_rows: list[tuple[str, dict[str, str]]] = []
    reference_row: dict[str, str] | None = None
    query_value = str(args.row_no) if args.row_no is not None else str(args.query or "")
    query_mode = "row_no" if args.row_no is not None else args.match
    for path in result_paths:
        rows = filter_rows_by_category(load_rows(path), args.category)
        row = find_match(rows, query_value, query_mode)
        if row is None:
            continue
        if reference_row is None:
            reference_row = row
        matched_rows.append((generation_name(path), row))

    if not matched_rows or reference_row is None:
        target = f"row_no={args.row_no}" if args.row_no is not None else f"query={args.query}"
        if args.category:
            target += f", category={args.category}"
        print(f"No row found for {target}", file=sys.stderr)
        return 1

    if args.only_best:
        matched_rows = select_best_row(matched_rows)

    print(f"row_no: {reference_row.get('row_no', '-')}")
    print(f"index: {reference_row.get('index', '-')}")
    print(f"category: {reference_row.get('category', '-')}")
    print(f"command_eng: {reference_row.get('command_eng', '')}")
    print(f"command_kor: {reference_row.get('command_kor', '')}")
    print("\n[SUMMARY]")
    print(render_summary_table(matched_rows))
    if reference_row.get("gt"):
        print("\n[GT]")
        print(compact_json_string(reference_row.get("gt", "")))

    for name, row in matched_rows:
        print(f"\n[{name}]")
        print(f"det_score: {as_float(row.get('det_score')):.4f}")
        print(f"det_gt_exact: {as_bool(row.get('det_gt_exact'))}")
        print(f"det_failure_reasons: {row.get('det_failure_reasons', '[]')}")
        if row.get("selected_from"):
            print(f"selected_from: {row.get('selected_from')}")
        print("output:")
        print(compact_json_string(row.get("output", "")))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
