#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.det_paper import evaluate_generation_records, run_det_paper_from_files


PROFILE_CONFIG = {
    "version0_6": {
        "label": "JOI_gpt4.1-mini_v1.5.4",
        "request_model": "gpt_mg.version0_6",
        "selected_model": "JOI_gpt4.1-mini_v1.5.4",
        "service_dir": REPO_ROOT / "gpt_mg" / "version0_6",
        "value_services_filename": "service_list_ver1.5.4_value.json",
        "function_services_filename": "service_list_ver1.5.4_function.json",
    },
    "version0_7": {
        "label": "JOI5_gpt5-mini_svc-v1.5.4",
        "request_model": "gpt_mg.version0_7",
        "selected_model": "JOI5_gpt5-mini_svc-v1.5.4",
        "service_dir": REPO_ROOT / "gpt_mg" / "version0_7",
        "value_services_filename": "service_list_ver1.5.4_value.json",
        "function_services_filename": "service_list_ver1.5.4_function.json",
    },
    "version0_12": {
        "label": "Local5080_qwen-7b_svc-v2.0.1",
        "request_model": "gpt_mg.version0_12",
        "selected_model": "Local5080_qwen-7b_svc-v2.0.1",
        "service_dir": REPO_ROOT / "gpt_mg" / "version0_12",
        "value_services_filename": "service_list_ver2.0.1_value.json",
        "function_services_filename": "service_list_ver2.0.1_function.json",
    },
    "version0_13": {
        "label": "Local5080_qwen-7b_svc-v1.5.4",
        "request_model": "gpt_mg.version0_13",
        "selected_model": "Local5080_qwen-7b_svc-v1.5.4",
        "service_dir": REPO_ROOT / "gpt_mg" / "version0_13",
        "value_services_filename": "service_list_ver1.5.4_value.json",
        "function_services_filename": "service_list_ver1.5.4_function.json",
    },
    "cap": {
        "label": "CAP-old_gpt4.1-mini_svc-v1.5.4",
        "request_model": "gpt4.1-mini",
        "selected_model": "CAP-old_gpt4.1-mini_svc-v1.5.4",
        "service_dir": REPO_ROOT / "gpt_mg" / "version0_6",
        "value_services_filename": "service_list_ver1.5.4_value.json",
        "function_services_filename": "service_list_ver1.5.4_function.json",
    },
}


ADDED_COLUMNS = [
    "profile",
    "output_joicode",
    "output_name",
    "output_cron",
    "output_period",
    "output_code",
    "output_model_label",
    "output_request_model",
    "output_selected_model",
    "output_translated_sentence",
    "output_generation_error",
    "output_response_time",
    "output_prompt_tokens",
    "output_completion_tokens",
    "output_total_tokens",
    "det_row_no",
    "det_dataset_index",
    "det_command",
    "det_pass",
    "det_sdet",
    "det_script_similarity",
    "det_fatal_reasons",
    "det_predicted_services",
    "det_reference_script",
    "det_predicted_script",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate JOICode for a single profile across JOICommands-280 and "
            "write JOICommands-280_{profile}.csv with generation + DET columns."
        )
    )
    parser.add_argument("--profile", required=True, choices=sorted(PROFILE_CONFIG.keys()))
    parser.add_argument("--dataset", default=str(REPO_ROOT / "datasets" / "JOICommands-280.csv"))
    parser.add_argument("--command-column", default="command_kor")
    parser.add_argument("--server-url", default="http://localhost:8000/generate_joi_code")
    parser.add_argument("--current-time", default="2026-03-31T12:00:00")
    parser.add_argument("--start-row", type=int, default=1)
    parser.add_argument("--end-row", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--category",
        action="append",
        default=[],
        help="Filter by dataset category value. Can be repeated or comma-separated.",
    )
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--output-csv", default=None)
    parser.add_argument("--verbose-every", type=int, default=10)
    return parser


def _safe_profile_name(profile: str) -> str:
    return profile.replace("/", "_").replace(" ", "_")


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _load_dataset_rows(dataset_path: Path) -> list[dict[str, str]]:
    with dataset_path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _load_connected_devices() -> Any:
    return _load_json(REPO_ROOT / "datasets" / "things.json")


def _coerce_scenario(code_payload: Any) -> dict[str, Any]:
    payload = code_payload
    if isinstance(payload, list):
        if not payload:
            return {}
        payload = payload[0]
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        stripped = payload.strip()
        if not stripped:
            return {}
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return {"code": stripped}
        if isinstance(parsed, list):
            return parsed[0] if parsed else {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def _post_generation(server_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        server_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return {
            "code": "",
            "log": {
                "error": f"http_error:{exc.code}",
                "raw_response": exc.read().decode("utf-8", errors="replace"),
            },
        }
    except urllib.error.URLError as exc:
        return {
            "code": "",
            "log": {
                "error": f"url_error:{exc.reason}",
            },
        }

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {
            "code": "",
            "log": {
                "error": "invalid_json_response",
                "raw_response": body,
            },
        }


def _write_generation_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _append_generation_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_det_rows(path: Path) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            row_no = int(row["row_no"])
            rows[row_no] = row
    return rows


def _build_output_row(
    source_row: dict[str, str],
    row_no: int,
    generation_record: dict[str, Any] | None,
    det_row: dict[str, Any] | None,
    profile: str,
) -> dict[str, Any]:
    result = dict(source_row)
    response = generation_record.get("response", {}) if generation_record else {}
    response_log = response.get("log", {}) if isinstance(response.get("log"), dict) else {}
    scenario = _coerce_scenario(response.get("code")) if isinstance(response, dict) else {}

    result.update(
        {
            "profile": profile,
            "output_joicode": json.dumps(scenario, ensure_ascii=False) if scenario else "",
            "output_name": scenario.get("name", "") if scenario else "",
            "output_cron": scenario.get("cron", "") if scenario else "",
            "output_period": scenario.get("period", "") if scenario else "",
            "output_code": scenario.get("code", "") if scenario else "",
            "output_model_label": generation_record.get("model_label", "") if generation_record else "",
            "output_request_model": generation_record.get("request_model", "") if generation_record else "",
            "output_selected_model": generation_record.get("selected_model", "") if generation_record else "",
            "output_translated_sentence": response_log.get("translated_sentence", ""),
            "output_generation_error": response_log.get("error", ""),
            "output_response_time": response_log.get("response_time", ""),
            "output_prompt_tokens": response_log.get("prompt_tokens", ""),
            "output_completion_tokens": response_log.get("completion_tokens", ""),
            "output_total_tokens": response_log.get("total_tokens", ""),
            "det_row_no": det_row.get("row_no", "") if det_row else "",
            "det_dataset_index": det_row.get("dataset_index", "") if det_row else "",
            "det_command": det_row.get("command", "") if det_row else "",
            "det_pass": det_row.get("det_pass", "") if det_row else "",
            "det_sdet": det_row.get("sdet", "") if det_row else "",
            "det_script_similarity": det_row.get("script_similarity", "") if det_row else "",
            "det_fatal_reasons": " | ".join(det_row.get("fatal_reasons", [])) if det_row else "",
            "det_predicted_services": ", ".join(det_row.get("predicted_services", [])) if det_row else "",
            "det_reference_script": det_row.get("reference_script", "") if det_row else "",
            "det_predicted_script": det_row.get("predicted_script", "") if det_row else "",
        }
    )
    return result


def _parse_category_filter(raw_values: list[str]) -> set[str]:
    categories: set[str] = set()
    for raw in raw_values:
        for item in str(raw).split(","):
            normalized = item.strip()
            if normalized:
                categories.add(normalized)
    return categories


def _select_row_numbers(
    rows: list[dict[str, str]],
    start_row: int,
    end_row: int | None,
    limit: int | None,
    categories: set[str],
) -> list[int]:
    row_start = max(start_row, 1)
    row_end = min(end_row if end_row is not None else len(rows), len(rows))
    selected: list[int] = []

    for row_no in range(row_start, row_end + 1):
        row = rows[row_no - 1]
        row_category = str(row.get("category", "")).strip()
        if categories and row_category not in categories:
            continue
        selected.append(row_no)
        if limit is not None and len(selected) >= limit:
            break

    return selected


def _build_output_fieldnames(source_rows: list[dict[str, str]]) -> list[str]:
    base_fields = list(source_rows[0].keys()) if source_rows else []
    return base_fields + [col for col in ADDED_COLUMNS if col not in base_fields]


def _seed_output_row(source_row: dict[str, str], fieldnames: list[str], profile: str) -> dict[str, Any]:
    row = {field: "" for field in fieldnames}
    row.update(source_row)
    row["profile"] = profile
    return row


def _load_existing_output_rows(
    source_rows: list[dict[str, str]],
    output_csv: Path,
    fieldnames: list[str],
    profile: str,
) -> list[dict[str, Any]]:
    existing_rows: list[dict[str, str]] = []
    if output_csv.exists():
        with output_csv.open(encoding="utf-8-sig", newline="") as f:
            existing_rows = list(csv.DictReader(f))
        if len(existing_rows) != len(source_rows):
            print(
                f"Existing output row count mismatch for {output_csv.name} "
                f"({len(existing_rows)} != {len(source_rows)}). Rebuilding from source dataset."
            )
            existing_rows = []

    merged_rows: list[dict[str, Any]] = []
    for idx, source_row in enumerate(source_rows):
        merged = _seed_output_row(source_row, fieldnames, profile)
        if idx < len(existing_rows):
            existing = existing_rows[idx]
            for field in fieldnames:
                if field in source_row:
                    merged[field] = source_row.get(field, "")
                else:
                    merged[field] = existing.get(field, merged.get(field, ""))
            if not merged.get("profile"):
                merged["profile"] = profile
        merged_rows.append(merged)
    return merged_rows


def _write_output_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temp_path.replace(path)


def _service_paths_for_profile(profile_cfg: dict[str, Any]) -> tuple[str, str]:
    value_path = profile_cfg["service_dir"] / profile_cfg["value_services_filename"]
    function_path = profile_cfg["service_dir"] / profile_cfg["function_services_filename"]
    return str(value_path), str(function_path)


def main() -> None:
    args = build_parser().parse_args()
    profile_cfg = PROFILE_CONFIG[args.profile]
    dataset_path = Path(args.dataset)
    rows = _load_dataset_rows(dataset_path)

    selected_categories = _parse_category_filter(args.category)
    selected_row_numbers = _select_row_numbers(
        rows=rows,
        start_row=args.start_row,
        end_row=args.end_row,
        limit=args.limit,
        categories=selected_categories,
    )
    if not selected_row_numbers:
        raise SystemExit("No rows selected. Check --start-row/--end-row/--limit/--category.")

    connected_devices = _load_connected_devices()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"batch_{_safe_profile_name(args.profile)}_{timestamp}"
    generation_jsonl = REPO_ROOT / "results" / "generation" / run_id / "generation.jsonl"
    det_output_dir = REPO_ROOT / "results" / "det_paper"
    output_csv = (
        Path(args.output_csv)
        if args.output_csv
        else dataset_path.with_name(f"{dataset_path.stem}_{_safe_profile_name(args.profile)}{dataset_path.suffix}")
    )
    fieldnames = _build_output_fieldnames(rows)
    output_rows = _load_existing_output_rows(rows, output_csv, fieldnames, args.profile)
    _write_output_csv(output_csv, fieldnames, output_rows)
    value_services_path, function_services_path = _service_paths_for_profile(profile_cfg)

    generation_records: list[dict[str, Any]] = []
    processed_rows: dict[int, dict[str, Any]] = {}
    forbidden_actions_path = REPO_ROOT / "datasets" / "forbidden_actions.json"

    total_selected = len(selected_row_numbers)
    for processed_count, row_no in enumerate(selected_row_numbers, start=1):
        source_row = rows[row_no - 1]
        sentence = str(source_row.get(args.command_column, "")).strip()
        payload = {
            "sentence": sentence,
            "model": profile_cfg["request_model"],
            "connected_devices": connected_devices,
            "current_time": args.current_time,
            "other_params": [{"selected_model": profile_cfg["selected_model"]}],
        }
        response = _post_generation(args.server_url, payload)
        record = {
            "row_no": row_no,
            "dataset_index": row_no,
            "sentence": sentence,
            "current_time": args.current_time,
            "model_label": profile_cfg["label"],
            "request_model": profile_cfg["request_model"],
            "selected_model": profile_cfg["selected_model"],
            "response": response,
        }
        generation_records.append(record)
        processed_rows[row_no] = record
        _append_generation_jsonl(generation_jsonl, record)

        det_result_rows = evaluate_generation_records(
            records=[record],
            dataset_path=str(dataset_path),
            command_column=args.command_column,
            value_services_path=value_services_path,
            function_services_path=function_services_path,
            forbidden_actions_path=str(forbidden_actions_path) if forbidden_actions_path.exists() else None,
            missing_reference_policy="paper_strict",
        )
        det_row = det_result_rows[0] if det_result_rows else None
        output_rows[row_no - 1] = _build_output_row(
            source_row=source_row,
            row_no=row_no,
            generation_record=record,
            det_row=det_row,
            profile=args.profile,
        )
        _write_output_csv(output_csv, fieldnames, output_rows)

        if args.verbose_every > 0 and (processed_count % args.verbose_every == 0 or processed_count == total_selected):
            print(f"[{args.profile}] saved row {row_no} ({processed_count}/{total_selected}) -> {output_csv.name}")

        if args.sleep_seconds > 0 and processed_count < total_selected:
            time.sleep(args.sleep_seconds)

    summary = run_det_paper_from_files(
        generation_jsonl=str(generation_jsonl),
        dataset_path=str(dataset_path),
        output_root=str(det_output_dir),
        command_column=args.command_column,
        value_services_path=value_services_path,
        function_services_path=function_services_path,
        forbidden_actions_path=str(forbidden_actions_path) if forbidden_actions_path.exists() else None,
        strict_paper=True,
        run_name=run_id,
        verbose=False,
    )

    det_rows = _load_det_rows(Path(summary["per_example_jsonl"]))
    for row_no in selected_row_numbers:
        source_row = rows[row_no - 1]
        output_rows[row_no - 1] = _build_output_row(
            source_row=source_row,
            row_no=row_no,
            generation_record=processed_rows.get(row_no),
            det_row=det_rows.get(row_no),
            profile=args.profile,
        )
    _write_output_csv(output_csv, fieldnames, output_rows)

    print("Profile CSV generation completed")
    print(f"- profile: {args.profile}")
    print(f"- run_id: {run_id}")
    print(f"- generation_jsonl: {generation_jsonl}")
    print(f"- det_summary_json: {summary['summary_json']}")
    print(f"- output_csv: {output_csv}")
    print(f"- selected_rows: {len(selected_row_numbers)}")
    print(f"- mean_sdet: {summary['mean_sdet']:.6f}")
    print(f"- det_pass_rate: {summary['det_pass_rate']:.6f}")
    print(f"- number_of_fatal_failures: {summary['number_of_fatal_failures']}")


if __name__ == "__main__":
    main()
