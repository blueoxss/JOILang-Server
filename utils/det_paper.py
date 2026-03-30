#!/usr/bin/env python3
"""
Self-contained paper-style DET/SDET evaluator for this repository.

Expected generation JSONL records can contain either:
- a top-level "code" field, or
- a "response" object with the API response shape used by query scripts.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICE_CALL_RE = re.compile(r"\([^)]*\)\.([A-Za-z0-9_]+)\s*(?:\(|==|!=|>=|<=|>|<)")


def _resolve_default_data_file(dataset_path: str, filename: str) -> str:
    dataset_dir_candidate = Path(dataset_path).resolve().parent / filename
    if dataset_dir_candidate.exists():
        return str(dataset_dir_candidate)

    candidates = [
        REPO_ROOT / "data" / filename,
        REPO_ROOT / "datasets" / filename,
        REPO_ROOT / "gpt_mg" / "version0_13" / filename,
        REPO_ROOT / "gpt_mg" / "version0_7" / filename,
        REPO_ROOT / "gpt_mg" / "version0_6" / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())
    return str(candidates[0].resolve())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run repository-local paper-style DET evaluation. "
            "Fatal violation => SDET=0. Otherwise SDET is normalized script similarity."
        )
    )
    parser.add_argument("--generation-jsonl", required=True, help="Path to generation JSONL.")
    parser.add_argument("--dataset", default="datasets/JOICommands-170.csv", help="Path to dataset CSV.")
    parser.add_argument("--output-dir", default="results/det_paper", help="Output directory root.")
    parser.add_argument("--command-column", default="command_eng", help="Command column in the dataset CSV.")
    parser.add_argument(
        "--missing-reference-policy",
        choices=["paper_strict", "legacy_pass", "zero"],
        default="paper_strict",
        help="Behavior when no reference scripts are available.",
    )
    parser.add_argument(
        "--strict-paper",
        action="store_true",
        help="Retained for CLI compatibility. Summary metadata records this flag.",
    )
    parser.add_argument("--run-name", default=None, help="Optional fixed run id.")
    parser.add_argument("--verbose", action="store_true", help="Print per-example rows after execution.")
    parser.add_argument("--services", default=None, help="Optional flat service list JSON fallback.")
    parser.add_argument("--value-services", default=None, help="VALUE service list JSON path.")
    parser.add_argument("--function-services", default=None, help="FUNCTION service list JSON path.")
    parser.add_argument(
        "--forbidden-actions",
        default=None,
        help="Optional JSON/text file listing forbidden action strings.",
    )
    return parser


def _load_json(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def _load_service_names(*paths: str | None) -> set[str]:
    names: set[str] = set()
    for path in paths:
        if not path:
            continue
        candidate = Path(path)
        if not candidate.exists():
            continue
        data = _load_json(candidate)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    service_name = str(item.get("service", "")).strip()
                    if service_name:
                        names.add(service_name)
        elif isinstance(data, dict):
            for key, value in data.items():
                key_name = str(key).strip()
                if key_name:
                    names.add(key_name)
                if isinstance(value, dict):
                    service_name = str(value.get("service", "")).strip()
                    if service_name:
                        names.add(service_name)
    return names


def _load_forbidden_actions(path: str | None) -> list[str]:
    if not path:
        return []

    candidate = Path(path)
    if not candidate.exists():
        return []

    if candidate.suffix.lower() == ".json":
        data = _load_json(candidate)
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
        if isinstance(data, dict):
            if isinstance(data.get("forbidden_actions"), list):
                return [str(item).strip() for item in data["forbidden_actions"] if str(item).strip()]
            return [str(value).strip() for value in data.values() if str(value).strip()]

    with candidate.open(encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def _load_dataset_rows(dataset_path: str, command_column: str) -> tuple[dict[int, dict[str, Any]], dict[str, dict[str, Any]]]:
    rows_by_position: dict[int, dict[str, Any]] = {}
    rows_by_command: dict[str, dict[str, Any]] = {}

    with Path(dataset_path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for position, row in enumerate(reader, start=1):
            row_copy = dict(row)
            row_copy["_position"] = position
            rows_by_position[position] = row_copy

            command_value = str(row.get(command_column, "")).strip()
            if command_value:
                rows_by_command[command_value] = row_copy

    return rows_by_position, rows_by_command


def _parse_embedded_json(text: str) -> dict[str, Any]:
    stripped = str(text or "").strip()
    if not stripped:
        return {}
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return {}


def _coerce_scenario(code_payload: Any) -> dict[str, Any]:
    payload = code_payload
    if isinstance(payload, list):
        if not payload:
            return {}
        payload = payload[0]

    if isinstance(payload, dict):
        return payload

    if isinstance(payload, str):
        parsed = _parse_embedded_json(payload)
        if parsed:
            return parsed
        return {"code": payload}

    return {}


def _extract_service_calls(script: str) -> list[str]:
    return SERVICE_CALL_RE.findall(script or "")


def _normalize_script(script: str) -> str:
    return re.sub(r"\s+", "", script or "")


def _similarity(left: str, right: str) -> float:
    return difflib.SequenceMatcher(None, _normalize_script(left), _normalize_script(right)).ratio()


def _extract_reference(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {}

    for key in ("gt_converted", "gt"):
        value = str(row.get(key, "")).strip()
        parsed = _parse_embedded_json(value)
        if parsed:
            return parsed
    return {}


def _match_row(
    record: dict[str, Any],
    rows_by_position: dict[int, dict[str, Any]],
    rows_by_command: dict[str, dict[str, Any]],
    command_column: str,
) -> dict[str, Any] | None:
    for key in ("row_no", "dataset_index", "position", "index"):
        value = record.get(key)
        try:
            if value is not None:
                matched = rows_by_position.get(int(value))
                if matched:
                    return matched
        except (TypeError, ValueError):
            pass

    sentence = (
        str(record.get("sentence", "")).strip()
        or str(record.get(command_column, "")).strip()
    )
    if sentence:
        return rows_by_command.get(sentence)

    response = record.get("response")
    if isinstance(response, dict):
        response_sentence = str(response.get("sentence", "")).strip()
        if response_sentence:
            return rows_by_command.get(response_sentence)

    return None


def _build_generation_row(
    record: dict[str, Any],
    dataset_row: dict[str, Any] | None,
    allowed_services: set[str],
    forbidden_actions: list[str],
    command_column: str,
    missing_reference_policy: str,
) -> dict[str, Any]:
    response = record.get("response") if isinstance(record.get("response"), dict) else {}
    prediction = _coerce_scenario(record.get("code") or record.get("prediction") or response.get("code"))
    prediction_log = response.get("log") if isinstance(response.get("log"), dict) else {}

    reference = _extract_reference(dataset_row)
    reference_script = str(reference.get("script") or reference.get("code") or "")
    predicted_script = str(prediction.get("code") or prediction.get("script") or "")

    command_text = ""
    if dataset_row:
        command_text = str(dataset_row.get(command_column, "")).strip()
    if not command_text:
        command_text = str(record.get("sentence", "")).strip()

    fatal_reasons: list[str] = []
    if not dataset_row or not reference_script:
        if missing_reference_policy == "paper_strict":
            fatal_reasons.append("missing_reference")
        elif missing_reference_policy == "zero":
            fatal_reasons.append("missing_reference_zero_policy")

    if not predicted_script:
        fatal_reasons.append("missing_prediction_code")

    predicted_services = sorted(set(_extract_service_calls(predicted_script)))
    if allowed_services:
        unknown_services = sorted(service for service in predicted_services if service not in allowed_services)
        if unknown_services:
            fatal_reasons.append("unknown_services:" + ",".join(unknown_services))

    forbidden_hits = [item for item in forbidden_actions if item and item in predicted_script]
    if forbidden_hits:
        fatal_reasons.append("forbidden_actions:" + ",".join(forbidden_hits))

    if prediction_log.get("error"):
        fatal_reasons.append("generation_error:" + str(prediction_log["error"]))

    script_similarity = _similarity(reference_script, predicted_script) if reference_script and predicted_script else 0.0
    det_pass = not fatal_reasons
    if det_pass:
        sdet = script_similarity
    elif missing_reference_policy == "legacy_pass" and "missing_reference" in ",".join(fatal_reasons):
        sdet = 1.0
        det_pass = True
        fatal_reasons = []
    else:
        sdet = 0.0

    return {
        "row_no": record.get("row_no") or (dataset_row or {}).get("_position", ""),
        "dataset_index": (dataset_row or {}).get("index", record.get("dataset_index", "")),
        "model_label": record.get("model_label") or record.get("selected_model") or prediction_log.get("model_name", ""),
        "request_model": record.get("request_model", ""),
        "selected_model": record.get("selected_model", ""),
        "command": command_text,
        "reference_script": reference_script,
        "predicted_script": predicted_script,
        "predicted_services": predicted_services,
        "det_pass": det_pass,
        "sdet": round(float(sdet), 6),
        "script_similarity": round(float(script_similarity), 6),
        "fatal_reasons": fatal_reasons,
    }


def run_det_paper_from_files(
    generation_jsonl: str,
    dataset_path: str,
    output_root: str,
    command_column: str = "command_eng",
    value_services_path: str | None = None,
    function_services_path: str | None = None,
    services_path: str | None = None,
    forbidden_actions_path: str | None = None,
    missing_reference_policy: str = "paper_strict",
    strict_paper: bool = False,
    run_name: str | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    allowed_services = _load_service_names(services_path, value_services_path, function_services_path)
    forbidden_actions = _load_forbidden_actions(forbidden_actions_path)
    rows_by_position, rows_by_command = _load_dataset_rows(dataset_path, command_column)

    generation_path = Path(generation_jsonl)
    if not generation_path.exists():
        raise FileNotFoundError(f"generation_jsonl not found: {generation_jsonl}")

    run_id = run_name or generation_path.parent.name
    output_dir = Path(output_root) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    per_example_jsonl = output_dir / "per_example.jsonl"
    per_example_csv = output_dir / "per_example.csv"
    summary_json = output_dir / "summary.json"

    results: list[dict[str, Any]] = []
    with generation_path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            dataset_row = _match_row(record, rows_by_position, rows_by_command, command_column)
            result = _build_generation_row(
                record=record,
                dataset_row=dataset_row,
                allowed_services=allowed_services,
                forbidden_actions=forbidden_actions,
                command_column=command_column,
                missing_reference_policy=missing_reference_policy,
            )
            result["line_no"] = line_no
            results.append(result)

    with per_example_jsonl.open("w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    csv_columns = [
        "line_no",
        "row_no",
        "dataset_index",
        "model_label",
        "request_model",
        "selected_model",
        "command",
        "det_pass",
        "sdet",
        "script_similarity",
        "fatal_reasons",
        "reference_script",
        "predicted_script",
        "predicted_services",
    ]
    with per_example_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        for row in results:
            writer.writerow(
                {
                    **row,
                    "fatal_reasons": " | ".join(row["fatal_reasons"]),
                    "predicted_services": ", ".join(row["predicted_services"]),
                }
            )

    total = len(results)
    det_pass_count = sum(1 for row in results if row["det_pass"])
    mean_sdet = sum(row["sdet"] for row in results) / total if total else 0.0
    det_pass_rate = det_pass_count / total if total else 0.0
    fatal_failures = total - det_pass_count

    summary = {
        "run_id": run_id,
        "output_dir": str(output_dir.resolve()),
        "per_example_jsonl": str(per_example_jsonl.resolve()),
        "per_example_csv": str(per_example_csv.resolve()),
        "summary_json": str(summary_json.resolve()),
        "mean_sdet": round(float(mean_sdet), 6),
        "det_pass_rate": round(float(det_pass_rate), 6),
        "number_of_fatal_failures": fatal_failures,
        "number_of_examples": total,
        "strict_paper": strict_paper,
        "missing_reference_policy": missing_reference_policy,
    }

    with summary_json.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    if verbose:
        print(json.dumps(results, ensure_ascii=False, indent=2))

    return summary


def main() -> None:
    args = build_parser().parse_args()

    value_services = args.value_services or _resolve_default_data_file(
        args.dataset, "service_list_ver1.5.4_value.json"
    )
    function_services = args.function_services or _resolve_default_data_file(
        args.dataset, "service_list_ver1.5.4_function.json"
    )

    summary = run_det_paper_from_files(
        generation_jsonl=args.generation_jsonl,
        dataset_path=args.dataset,
        output_root=args.output_dir,
        command_column=args.command_column,
        value_services_path=value_services if not args.services else None,
        function_services_path=function_services if not args.services else None,
        services_path=args.services,
        forbidden_actions_path=args.forbidden_actions,
        missing_reference_policy=args.missing_reference_policy,
        strict_paper=bool(args.strict_paper),
        run_name=args.run_name,
        verbose=args.verbose,
    )

    print("Paper DET evaluation completed")
    print(f"- run_id: {summary['run_id']}")
    print(f"- output_dir: {summary['output_dir']}")
    print(f"- per_example_jsonl: {summary['per_example_jsonl']}")
    print(f"- per_example_csv: {summary['per_example_csv']}")
    print(f"- summary_json: {summary['summary_json']}")
    print(f"- mean_sdet: {summary['mean_sdet']:.6f}")
    print(f"- det_pass_rate: {summary['det_pass_rate']:.6f}")
    print(f"- number_of_fatal_failures: {summary['number_of_fatal_failures']}")


if __name__ == "__main__":
    main()
