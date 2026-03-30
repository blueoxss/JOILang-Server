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

from utils.det_paper import run_det_paper_from_files


PROFILE_CONFIG = {
    "version0_6": {
        "label": "JOI_gpt4.1_mini (version0_6)",
        "request_model": "gpt_mg.version0_6",
        "selected_model": "JOI_gpt4.1_mini",
        "service_dir": REPO_ROOT / "gpt_mg" / "version0_6",
    },
    "version0_7": {
        "label": "JOI_gpt5_mini (version0_7)",
        "request_model": "gpt_mg.version0_7",
        "selected_model": "JOI_gpt5_mini",
        "service_dir": REPO_ROOT / "gpt_mg" / "version0_7",
    },
    "version0_13": {
        "label": "local_8b (version0_13)",
        "request_model": "gpt_mg.version0_13",
        "selected_model": "local_8b",
        "service_dir": REPO_ROOT / "gpt_mg" / "version0_13",
    },
    "cap": {
        "label": "CAP_gpt4.1_mini_old",
        "request_model": "gpt4.1-mini",
        "selected_model": "CAP_gpt4.1_mini_old",
        "service_dir": REPO_ROOT / "gpt_mg" / "version0_6",
    },
}


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


def main() -> None:
    args = build_parser().parse_args()
    profile_cfg = PROFILE_CONFIG[args.profile]
    dataset_path = Path(args.dataset)
    rows = _load_dataset_rows(dataset_path)

    start_row = max(args.start_row, 1)
    end_row = args.end_row if args.end_row is not None else len(rows)
    if args.limit is not None:
        end_row = min(end_row, start_row + args.limit - 1)
    end_row = min(end_row, len(rows))

    if start_row > end_row:
        raise SystemExit("No rows selected. Check --start-row/--end-row/--limit.")

    connected_devices = _load_connected_devices()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"batch_{_safe_profile_name(args.profile)}_{timestamp}"
    generation_jsonl = REPO_ROOT / "results" / "generation" / run_id / "generation.jsonl"
    det_output_dir = REPO_ROOT / "results" / "det_paper"

    generation_records: list[dict[str, Any]] = []
    processed_rows: dict[int, dict[str, Any]] = {}

    for row_no in range(start_row, end_row + 1):
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

        if args.verbose_every > 0 and ((row_no - start_row + 1) % args.verbose_every == 0 or row_no == end_row):
            print(f"[{args.profile}] processed row {row_no}/{end_row}")

        if args.sleep_seconds > 0 and row_no < end_row:
            time.sleep(args.sleep_seconds)

    _write_generation_jsonl(generation_jsonl, generation_records)

    forbidden_actions_path = REPO_ROOT / "datasets" / "forbidden_actions.json"
    summary = run_det_paper_from_files(
        generation_jsonl=str(generation_jsonl),
        dataset_path=str(dataset_path),
        output_root=str(det_output_dir),
        command_column=args.command_column,
        value_services_path=str(profile_cfg["service_dir"] / "service_list_ver1.5.4_value.json"),
        function_services_path=str(profile_cfg["service_dir"] / "service_list_ver1.5.4_function.json"),
        forbidden_actions_path=str(forbidden_actions_path) if forbidden_actions_path.exists() else None,
        strict_paper=True,
        run_name=run_id,
        verbose=False,
    )

    det_rows = _load_det_rows(Path(summary["per_example_jsonl"]))
    output_csv = (
        Path(args.output_csv)
        if args.output_csv
        else dataset_path.with_name(f"{dataset_path.stem}_{_safe_profile_name(args.profile)}{dataset_path.suffix}")
    )

    added_columns = [
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

    fieldnames = list(rows[0].keys()) + [col for col in added_columns if col not in rows[0]]
    output_rows = []
    for row_no, source_row in enumerate(rows, start=1):
        output_rows.append(
            _build_output_row(
                source_row=source_row,
                row_no=row_no,
                generation_record=processed_rows.get(row_no),
                det_row=det_rows.get(row_no),
                profile=args.profile,
            )
        )

    with output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print("Profile CSV generation completed")
    print(f"- profile: {args.profile}")
    print(f"- run_id: {run_id}")
    print(f"- generation_jsonl: {generation_jsonl}")
    print(f"- det_summary_json: {summary['summary_json']}")
    print(f"- output_csv: {output_csv}")
    print(f"- mean_sdet: {summary['mean_sdet']:.6f}")
    print(f"- det_pass_rate: {summary['det_pass_rate']:.6f}")
    print(f"- number_of_fatal_failures: {summary['number_of_fatal_failures']}")


if __name__ == "__main__":
    main()
