#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from statistics import fmean
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(VERSION_ROOT))

from utils.det_evaluator import evaluate_candidate
from utils.pipeline_common import DATASET_DEFAULT, RESULTS_DIR, atomic_write_csv, dump_json, load_dataset_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze DET legacy vs strict scoring on existing benchmark outputs.")
    parser.add_argument("--results-dir", action="append", default=[], help="Result directory containing row_comparison.csv. Can be repeated.")
    parser.add_argument("--dataset", default=str(DATASET_DEFAULT))
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--high-score-threshold", type=float, default=85.0)
    parser.add_argument("--print-json", action="store_true")
    return parser


def _resolve_out_dir(value: str | None) -> Path:
    if value:
        return Path(value).resolve()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return RESULTS_DIR / f"det_profile_analysis_{stamp}"


def _load_row_comparison(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _model_keys(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return []
    keys: list[str] = []
    for column in rows[0].keys():
        if column.endswith("__output_code"):
            keys.append(column[:-len("__output_code")])
    return sorted(keys)


def _candidate_payload(row: dict[str, str], model_key: str) -> dict[str, Any]:
    return {
        "name": "output",
        "cron": row.get(f"{model_key}__output_cron", "") or "",
        "period": int(float(row.get(f"{model_key}__output_period", "0") or 0)),
        "code": row.get(f"{model_key}__output_code", "") or "",
    }


def _dataset_map(dataset_path: str | Path) -> dict[int, dict[str, str]]:
    return {idx: row for idx, row in enumerate(load_dataset_rows(dataset_path), start=1)}


def _mean(values: list[float]) -> float:
    return round(fmean(values), 4) if values else 0.0


def _synthetic_suite(dataset_rows: dict[int, dict[str, str]]) -> list[dict[str, Any]]:
    suite: list[tuple[int, list[tuple[str, str]]]] = [
        (
            10,
            [
                ("sensor_only", '(#HumiditySensor).HumiditySensor_Humidity'),
                ("speaker_only", '(#Speaker).Speaker_Speak("The current humidity is 55%")'),
                ("malformed_chain", '(#HumiditySensor).humiditysensor_humidity() -> (#Speaker).speaker_speak("The current humidity is ") + str()'),
            ],
        ),
        (
            8,
            [
                ("sensor_only", '(#TemperatureSensor).TemperatureSensor_Temperature'),
                ("speaker_only", '(#Speaker).Speaker_Speak("The temperature is 24 degrees")'),
                ("literal_speak_chain", '(#TemperatureSensor).TemperatureSensor_Temperature\n(#Speaker).Speaker_Speak("The current temperature is ")'),
            ],
        ),
        (
            3,
            [
                ("set_mode_only", '(#RiceCooker).RiceCooker_SetRiceCookerMode("cooking")'),
                ("set_mode_plus_add30", '(#RiceCooker).RiceCooker_SetRiceCookerMode("cooking")\n(#RiceCooker).RiceCooker_AddMoreTime(30)'),
                ("wrong_unit_ms_expr", '(#RiceCooker).RiceCooker_SetCookingParameters("cooking", 30 * 60 * 1000)'),
                ("wrong_service_same_arg", '(#RiceCooker).RiceCooker_SetCookingParameters("warm", 1800)'),
            ],
        ),
        (
            37,
            [
                ("explicit_two", 'all(#Back #DoorLock).DoorLock_Lock()\nall(#Front #DoorLock).DoorLock_Lock()'),
                ("only_back", 'all(#Back #DoorLock).DoorLock_Lock()'),
                ("wrong_service", 'all(#DoorLock).DoorLock_Unlock()'),
            ],
        ),
    ]
    rows: list[dict[str, Any]] = []
    for row_no, variants in suite:
        source = dataset_rows[row_no]
        for variant_name, code in variants:
            candidate = {"name": "synthetic", "cron": "", "period": 0, "code": code}
            legacy = evaluate_candidate(
                source["command_eng"],
                candidate,
                connected_devices=source.get("connected_devices"),
                ground_truth=source.get("gt"),
                profile="legacy",
            )
            strict = evaluate_candidate(
                source["command_eng"],
                candidate,
                connected_devices=source.get("connected_devices"),
                ground_truth=source.get("gt"),
                profile="strict",
            )
            rows.append(
                {
                    "row_no": row_no,
                    "command_eng": source["command_eng"],
                    "variant": variant_name,
                    "code": code,
                    "legacy_score": legacy["det_score"],
                    "strict_score": strict["det_score"],
                    "delta": round(float(strict["det_score"]) - float(legacy["det_score"]), 4),
                    "legacy_failures": json.dumps(legacy["failure_reasons"], ensure_ascii=False),
                    "strict_failures": json.dumps(strict["failure_reasons"], ensure_ascii=False),
                    "legacy_gt_service_coverage": legacy.get("det_gt_service_coverage", 1.0),
                    "strict_gt_service_coverage": strict.get("det_gt_service_coverage", 1.0),
                    "legacy_gt_receiver_coverage": legacy.get("det_gt_receiver_coverage", 1.0),
                    "strict_gt_receiver_coverage": strict.get("det_gt_receiver_coverage", 1.0),
                    "legacy_dataflow_score": legacy.get("det_dataflow_score", 1.0),
                    "strict_dataflow_score": strict.get("det_dataflow_score", 1.0),
                    "legacy_numeric_grounding": legacy.get("det_numeric_grounding", 1.0),
                    "strict_numeric_grounding": strict.get("det_numeric_grounding", 1.0),
                }
            )
    return rows


def analyze_results_dir(
    results_dir: Path,
    dataset_rows: dict[int, dict[str, str]],
    *,
    high_score_threshold: float,
) -> dict[str, Any]:
    row_csv = results_dir / "row_comparison.csv"
    rows = _load_row_comparison(row_csv)
    models = _model_keys(rows)
    recomputed_rows: list[dict[str, Any]] = []
    suspicious_rows: list[dict[str, Any]] = []
    profile_summary_rows: list[dict[str, Any]] = []

    for model_key in models:
        legacy_scores: list[float] = []
        strict_scores: list[float] = []
        exact_count = 0
        suspicious_count = 0
        for row in rows:
            row_no = int(row["row_no"])
            source = dataset_rows[row_no]
            candidate = _candidate_payload(row, model_key)
            legacy = evaluate_candidate(
                source["command_eng"],
                candidate,
                connected_devices=source.get("connected_devices"),
                ground_truth=source.get("gt"),
                profile="legacy",
            )
            strict = evaluate_candidate(
                source["command_eng"],
                candidate,
                connected_devices=source.get("connected_devices"),
                ground_truth=source.get("gt"),
                profile="strict",
            )
            legacy_scores.append(float(legacy["det_score"]))
            strict_scores.append(float(strict["det_score"]))
            if legacy.get("det_gt_exact"):
                exact_count += 1
            delta = round(float(strict["det_score"]) - float(legacy["det_score"]), 4)
            recomputed = {
                "results_dir": str(results_dir),
                "model_key": model_key,
                "row_no": row_no,
                "category": row.get("category", ""),
                "command_eng": source["command_eng"],
                "legacy_score": legacy["det_score"],
                "strict_score": strict["det_score"],
                "delta": delta,
                "legacy_gt_exact": legacy["det_gt_exact"],
                "strict_gt_exact": strict["det_gt_exact"],
                "legacy_failures": json.dumps(legacy["failure_reasons"], ensure_ascii=False),
                "strict_failures": json.dumps(strict["failure_reasons"], ensure_ascii=False),
                "legacy_gt_service_coverage": legacy.get("det_gt_service_coverage", 1.0),
                "strict_gt_service_coverage": strict.get("det_gt_service_coverage", 1.0),
                "legacy_gt_receiver_coverage": legacy.get("det_gt_receiver_coverage", 1.0),
                "strict_gt_receiver_coverage": strict.get("det_gt_receiver_coverage", 1.0),
                "legacy_dataflow_score": legacy.get("det_dataflow_score", 1.0),
                "strict_dataflow_score": strict.get("det_dataflow_score", 1.0),
                "legacy_numeric_grounding": legacy.get("det_numeric_grounding", 1.0),
                "strict_numeric_grounding": strict.get("det_numeric_grounding", 1.0),
                "output_code": candidate["code"],
            }
            recomputed_rows.append(recomputed)
            if (
                float(legacy["det_score"]) >= float(high_score_threshold)
                and not legacy.get("det_gt_exact")
                and float(strict["det_score"]) < 70.0
            ):
                suspicious_count += 1
                suspicious_rows.append(recomputed)
        profile_summary_rows.append(
            {
                "results_dir": str(results_dir),
                "model_key": model_key,
                "row_count": len(rows),
                "legacy_avg_det_score": _mean(legacy_scores),
                "strict_avg_det_score": _mean(strict_scores),
                "avg_delta": round(_mean(strict_scores) - _mean(legacy_scores), 4),
                "exact_count": exact_count,
                "legacy_high_to_strict_fail_count": suspicious_count,
            }
        )

    return {
        "rows": recomputed_rows,
        "summary_rows": profile_summary_rows,
        "suspicious_rows": suspicious_rows,
        "models": models,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.results_dir:
        raise SystemExit("Provide at least one --results-dir")

    dataset_rows = _dataset_map(args.dataset)
    out_dir = _resolve_out_dir(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, Any]] = []
    all_summaries: list[dict[str, Any]] = []
    all_suspicious: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    for raw_dir in args.results_dir:
        results_dir = Path(raw_dir).resolve()
        analysis = analyze_results_dir(results_dir, dataset_rows, high_score_threshold=args.high_score_threshold)
        all_rows.extend(analysis["rows"])
        all_summaries.extend(analysis["summary_rows"])
        all_suspicious.extend(analysis["suspicious_rows"])
        run_summaries.append(
            {
                "results_dir": str(results_dir),
                "models": analysis["models"],
                "row_count": len(analysis["rows"]),
                "suspicious_count": len(analysis["suspicious_rows"]),
            }
        )

    synthetic_rows = _synthetic_suite(dataset_rows)
    summary = {
        "created_at": datetime.now().isoformat(),
        "results_dirs": [str(Path(item).resolve()) for item in args.results_dir],
        "run_summaries": run_summaries,
        "profile_summary": all_summaries,
        "suspicious_high_nonexact_count": len(all_suspicious),
        "synthetic_suite_rows": len(synthetic_rows),
    }

    atomic_write_csv(out_dir / "profile_comparison_rows.csv", list(all_rows[0].keys()) if all_rows else [], all_rows)
    atomic_write_csv(out_dir / "profile_summary.csv", list(all_summaries[0].keys()) if all_summaries else [], all_summaries)
    atomic_write_csv(out_dir / "suspicious_high_legacy_rows.csv", list(all_suspicious[0].keys()) if all_suspicious else [], all_suspicious)
    atomic_write_csv(out_dir / "synthetic_det_suite.csv", list(synthetic_rows[0].keys()) if synthetic_rows else [], synthetic_rows)
    dump_json(out_dir / "analysis_summary.json", summary)

    if args.print_json:
        print(json.dumps({"out_dir": str(out_dir), **summary}, ensure_ascii=False, indent=2))
    else:
        print(f"DET profile analysis written to: {out_dir}")
        print(f"- suspicious_high_nonexact_count: {len(all_suspicious)}")
        print(f"- synthetic_suite_rows: {len(synthetic_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
