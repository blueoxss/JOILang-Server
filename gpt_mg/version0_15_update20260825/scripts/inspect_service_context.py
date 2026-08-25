#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

DEFAULT_GENOME_CANDIDATES = [
    VERSION_ROOT / "results" / "best_genome.json",
    VERSION_ROOT / "results" / "best_genome_after_feedback.json",
    VERSION_ROOT / "results" / "best_genome_from_ga.json",
]

from utils.pipeline_common import (
    DATASET_DEFAULT,
    SERVICE_SCHEMA_DEFAULT,
    RESULTS_DIR,
    atomic_write_csv,
    build_prompt_values,
    dump_json,
    load_dataset_rows,
    load_genome,
    load_service_schema,
    render_blocks_for_genome,
    select_rows,
)


DEFAULT_MODES = ["schema_fallback", "retrieval_fallback"]


def _default_genome_json() -> str:
    for candidate in DEFAULT_GENOME_CANDIDATES:
        if candidate.exists():
            return str(candidate.resolve())
    return ""


def _pretty_json_list(value: str) -> list[Any]:
    text = str(value or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return [text]
    return parsed if isinstance(parsed, list) else [parsed]


def _render_prompt_chars(values: dict[str, Any], genome: dict[str, Any] | None) -> int:
    if not genome:
        return 0
    rendered, _manifest = render_blocks_for_genome(genome, values=values)
    return len(rendered)


def _inspect_row(
    row_no: int,
    row: dict[str, str],
    service_schema: dict[str, dict[str, Any]],
    *,
    genome: dict[str, Any] | None,
    candidate_strategy: str,
    mode: str,
    retrieval_topk: int | None,
    retrieval_mode: str | None,
    retrieval_json: str | None,
    retrieval_bundle_dir: str | None,
    retrieval_model_dir: str | None,
    retrieval_device: str | None,
) -> dict[str, Any]:
    values = build_prompt_values(
        row_no,
        row,
        service_schema,
        candidate_strategy=candidate_strategy,
        service_context_mode=mode,
        retrieval_topk=retrieval_topk,
        retrieval_mode=retrieval_mode,
        retrieval_json_path=retrieval_json,
        retrieval_bundle_dir=retrieval_bundle_dir,
        retrieval_model_dir=retrieval_model_dir,
        retrieval_device=retrieval_device,
    )
    snippet = str(values.get("service_list_snippet", "") or "")
    return {
        "row_no": row_no,
        "category": str(row.get("category", "") or ""),
        "command_eng": str(row.get("command_eng", "") or ""),
        "command_kor": str(row.get("command_kor", "") or ""),
        "mode": mode,
        "service_list_snippet_source": str(values.get("service_list_snippet_source", "") or ""),
        "service_list_device_count": int(values.get("service_list_device_count") or 0),
        "service_list_retrieval_status": str(values.get("service_list_retrieval_status", "") or ""),
        "service_list_retrieval_mode": str(values.get("service_list_retrieval_mode", "") or ""),
        "service_list_retrieval_topk": int(values.get("service_list_retrieval_topk") or 0),
        "service_list_retrieval_device": str(values.get("service_list_retrieval_device", "") or ""),
        "service_list_retrieval_categories": _pretty_json_list(str(values.get("service_list_retrieval_categories", "") or "")),
        "service_list_retrieval_scores": _pretty_json_list(str(values.get("service_list_retrieval_scores", "") or "")),
        "service_list_retrieval_fallback_reason": str(values.get("service_list_retrieval_fallback_reason", "") or ""),
        "service_list_snippet_chars": len(snippet),
        "rendered_prompt_chars": _render_prompt_chars(values, genome),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect service-list prompt context for schema vs retrieval fallback.")
    parser.add_argument("--dataset", default=str(DATASET_DEFAULT))
    parser.add_argument("--service-schema", default=str(SERVICE_SCHEMA_DEFAULT))
    parser.add_argument("--genome-json", default=_default_genome_json())
    parser.add_argument("--row-no", type=int, default=None)
    parser.add_argument("--start-row", type=int, default=1)
    parser.add_argument("--end-row", type=int, default=None)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--candidate-strategy", default="direct")
    parser.add_argument("--mode", action="append", dest="modes", default=[])
    parser.add_argument("--enable-retrieval-premapping", action="store_true", help="If no --mode is provided, compare only retrieval_fallback.")
    parser.add_argument("--disable-retrieval-premapping", action="store_true", help="If no --mode is provided, compare only schema_fallback.")
    parser.add_argument("--retrieval-topk", type=int, default=10)
    parser.add_argument("--retrieval-mode", default="hybrid")
    parser.add_argument("--retrieval-json", default="")
    parser.add_argument("--retrieval-bundle-dir", default="")
    parser.add_argument("--retrieval-model-dir", default="")
    parser.add_argument("--retrieval-device", default="cpu")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    dataset_rows = load_dataset_rows(args.dataset)
    service_schema = load_service_schema(args.service_schema)
    genome = load_genome(args.genome_json) if args.genome_json else None
    if args.modes:
        modes = args.modes
    elif args.enable_retrieval_premapping:
        modes = ["retrieval_fallback"]
    elif args.disable_retrieval_premapping:
        modes = ["schema_fallback"]
    else:
        modes = list(DEFAULT_MODES)
    if args.row_no is not None:
        selected = [(args.row_no, dataset_rows[args.row_no - 1])]
    else:
        selected = select_rows(
            dataset_rows,
            start_row=args.start_row,
            end_row=args.end_row,
            limit=args.limit,
            categories=args.category,
        )

    records: list[dict[str, Any]] = []
    for row_no, row in selected:
        for mode in modes:
            records.append(
                _inspect_row(
                    row_no,
                    row,
                    service_schema,
                    genome=genome,
                    candidate_strategy=args.candidate_strategy,
                    mode=mode,
                    retrieval_topk=args.retrieval_topk,
                    retrieval_mode=args.retrieval_mode,
                    retrieval_json=args.retrieval_json or None,
                    retrieval_bundle_dir=args.retrieval_bundle_dir or None,
                    retrieval_model_dir=args.retrieval_model_dir or None,
                    retrieval_device=args.retrieval_device or None,
                )
            )

    output_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR / "service_context_inspection"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_rows: list[dict[str, Any]] = []
    for record in records:
        flat = dict(record)
        flat["service_list_retrieval_categories"] = json.dumps(flat.get("service_list_retrieval_categories", []), ensure_ascii=False)
        flat["service_list_retrieval_scores"] = json.dumps(flat.get("service_list_retrieval_scores", []), ensure_ascii=False)
        csv_rows.append(flat)
    summary = {
        "dataset": str(Path(args.dataset).resolve()),
        "service_schema": str(Path(args.service_schema).resolve()),
        "genome_json": str(Path(args.genome_json).resolve()) if args.genome_json else "",
        "modes": modes,
        "row_count": len(selected),
        "records": records,
    }
    dump_json(output_dir / "service_context_summary.json", summary)
    if csv_rows:
        atomic_write_csv(output_dir / "service_context_rows.csv", list(csv_rows[0].keys()), csv_rows)

    if args.print_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        for record in records:
            cats = ", ".join(record.get("service_list_retrieval_categories", []))
            print(
                f"[row {record['row_no']}] mode={record['mode']} "
                f"source={record['service_list_snippet_source']} "
                f"groups={record['service_list_device_count']} "
                f"snippet_chars={record['service_list_snippet_chars']} "
                f"prompt_chars={record['rendered_prompt_chars']} "
                f"retrieval_status={record['service_list_retrieval_status']} "
                f"categories={cats}"
            )
        print(f"Summary JSON: {output_dir / 'service_context_summary.json'}")
        if csv_rows:
            print(f"Rows CSV: {output_dir / 'service_context_rows.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
