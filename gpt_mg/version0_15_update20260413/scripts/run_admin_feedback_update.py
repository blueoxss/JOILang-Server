#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import fmean
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = VERSION_ROOT.parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from scripts.run_category_sweep import run_category_sweep
from scripts.run_feedback_loop import run_feedback_loop
from scripts.run_ga_search import run_ga_search
from scripts.run_generate import _llm_settings, generate_candidates_for_rows
from scripts.run_rerank import rerank_candidates_csv
from utils.pipeline_common import (
    DATASET_DEFAULT,
    LOGS_DIR,
    RESULTS_DIR,
    SERVICE_SCHEMA_DEFAULT,
    atomic_write_csv,
    dump_json,
    ensure_workspace,
    load_dataset_rows,
    load_genome,
    load_service_schema,
    parse_connected_devices,
    read_csv_rows,
    select_rows,
    slugify,
    unique_fieldnames,
)


ADMIN_LOG_ROOT_DEFAULT = REPO_ROOT / "admin_logs"
ADMIN_FEEDBACK_DIR = LOGS_DIR / "admin_feedback"
ACK_ONLY_TEXTS = {
    "",
    "ok",
    "okay",
    "thanks",
    "thank you",
    "got it",
    "감사",
    "감사합니다",
    "확인",
    "확인했습니다",
    "넵",
    "네",
    "ㅇㅋ",
}
FAILURE_HINT_RE = re.compile(
    r"(안돼|안됨|안됩니다|실패|오류|에러|doesn't work|does not work|not working|failed?|broken)",
    re.IGNORECASE,
)
COMMAND_TRIM_RE = re.compile(
    r"^(?P<command>.+?)\s*(?:가|이|은|는)?\s*(?:안돼|안됨|안됩니다|실패|오류|에러|doesn't work|does not work|not working|failed?|broken).*$",
    re.IGNORECASE,
)
KEY_ALIASES = {
    "command": "command",
    "command_eng": "command_eng",
    "command_kor": "command_kor",
    "sentence": "command",
    "text": "text",
    "prompt": "command",
    "connected_devices": "connected_devices",
    "devices": "connected_devices",
    "things": "connected_devices",
    "gt": "gt",
    "ground_truth": "gt",
    "expected_code": "gt",
    "expected_output": "gt",
    "expected_json": "gt",
    "cron": "cron",
    "period": "period",
    "category": "category",
    "row_no": "row_no",
    "benchmark_row_no": "row_no",
    "manual_rule": "manual_rules",
    "manual_rules": "manual_rules",
    "manual_feedback": "manual_rules",
    "feedback_rule": "manual_rules",
    "feedback_rules": "manual_rules",
    "prompt_rule": "manual_rules",
    "prompt_rules": "manual_rules",
    "feedback": "feedback",
    "analysis": "analysis",
    "why_failed": "why_failed",
    "expected_behavior": "expected_behavior",
    "notes": "notes",
    "language": "language",
    "failed": "failed",
    "status": "status",
}
ADMIN_CASE_EXTRA_FIELDS = [
    "case_id",
    "source_path",
    "source_line",
    "seen_count",
    "language",
    "matched_dataset_row_no",
    "source_kind",
    "note_only",
    "raw_text",
    "manual_rules",
]


def _default_genome_json() -> Path:
    candidates = (
        VERSION_ROOT / "results" / "best_genome_after_feedback.json",
        VERSION_ROOT / "results" / "best_genome_from_ga.json",
        VERSION_ROOT / "results" / "best_genome.json",
        VERSION_ROOT / "genomes" / "example_genome.json",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mine admin_logs feedback, replay failures, run feedback/GA/benchmark, and optionally scaffold a version0_15 update folder."
    )
    parser.add_argument("--profile", default=VERSION_ROOT.name)
    parser.add_argument("--genome-json", default=str(_default_genome_json()))
    parser.add_argument("--dataset", default=str(DATASET_DEFAULT))
    parser.add_argument("--service-schema", default=str(SERVICE_SCHEMA_DEFAULT))
    parser.add_argument("--admin-log-root", default=str(ADMIN_LOG_ROOT_DEFAULT))
    parser.add_argument("--admin-limit", type=int, default=None)
    parser.add_argument("--admin-candidate-k", type=int, default=1)
    parser.add_argument("--admin-validation-size", type=int, default=8)
    parser.add_argument("--admin-feedback-attempts", type=int, default=3)
    parser.add_argument("--admin-improvement-threshold", type=float, default=0.0)
    parser.add_argument("--admin-repair-threshold", type=float, default=60.0)
    parser.add_argument("--admin-repair-attempts", type=int, default=1)
    parser.add_argument("--benchmark-limit", type=int, default=None)
    parser.add_argument("--start-row", type=int, default=1)
    parser.add_argument("--end-row", type=int, default=None)
    parser.add_argument("--category", action="append", default=[], help="Optional benchmark category filter. Can be repeated or comma-separated.")
    parser.add_argument("--skip-benchmark", action="store_true")
    parser.add_argument("--skip-category-sweep", action="store_true")
    parser.add_argument("--benchmark-candidate-k", type=int, default=2)
    parser.add_argument("--ga-population", type=int, default=8)
    parser.add_argument("--ga-gens", type=int, default=6)
    parser.add_argument("--ga-crossover-rate", type=float, default=0.6)
    parser.add_argument("--ga-mutation-rate", type=float, default=0.2)
    parser.add_argument("--ga-elites", type=int, default=2)
    parser.add_argument("--ga-sample-size", type=int, default=16)
    parser.add_argument("--ga-cheap-eval-limit", type=int, default=5)
    parser.add_argument("--ga-validation-size", type=int, default=8)
    parser.add_argument("--ga-alpha", type=float, default=0.5)
    parser.add_argument("--ga-plateau-generations", type=int, default=2)
    parser.add_argument("--ga-feedback-attempts", type=int, default=2)
    parser.add_argument("--ga-feedback-threshold", type=float, default=0.1)
    parser.add_argument("--category-sample-size", type=int, default=3)
    parser.add_argument("--category-attempts", type=int, default=2)
    parser.add_argument("--category-full-failure-sample-size", type=int, default=16)
    parser.add_argument("--category-final-attempts", type=int, default=2)
    parser.add_argument("--repair-threshold", type=float, default=70.0)
    parser.add_argument("--repair-attempts", type=int, default=1)
    parser.add_argument("--llm-mode", default=None)
    parser.add_argument("--llm-endpoint", default=None)
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--seed", type=int, default=15)
    parser.add_argument("--update-name", default=None)
    parser.add_argument("--force-promote", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser


def _normalize_lookup_key(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _contains_hangul(value: str) -> bool:
    return any("\uac00" <= ch <= "\ud7a3" for ch in str(value or ""))


def _language_of_text(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    has_hangul = _contains_hangul(text)
    has_ascii = bool(re.search(r"[A-Za-z]", text))
    if has_hangul and has_ascii:
        return "mixed"
    if has_hangul:
        return "ko"
    if has_ascii:
        return "en"
    return "unknown"


def _dedupe_strings(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token:
            continue
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(token)
    return ordered


def _listify_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = [value]
    values: list[str] = []
    for raw in raw_items:
        if raw is None:
            continue
        if isinstance(raw, str) and "\n" in raw:
            parts = raw.splitlines()
        else:
            parts = [raw]
        for part in parts:
            token = str(part or "").strip()
            if token and not token.startswith("#"):
                values.append(token)
    return _dedupe_strings(values)


def _bool_from_any(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    token = str(value).strip().casefold()
    if token in {"1", "true", "yes", "y", "fail", "failed", "error", "broken"}:
        return True
    if token in {"0", "false", "no", "n", "ok", "pass", "passed"}:
        return False
    return None


def _sanitize_period(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _strip_code_fences(text: str) -> str:
    stripped = str(text or "").strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped


def _extract_json_fragment(text: str) -> str:
    stripped = _strip_code_fences(text)
    candidates = [stripped]
    openings = ("{", "[")
    closings = {"{": "}", "[": "]"}
    for start in range(len(stripped)):
        opener = stripped[start]
        if opener not in openings:
            continue
        closer = closings[opener]
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(stripped)):
            ch = stripped[index]
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    candidates.append(stripped[start : index + 1].strip())
                    break
    for candidate in candidates:
        if not candidate:
            continue
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            continue
    return ""


def _parse_key_value_text(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    current_key = ""
    buffer: list[str] = []

    def flush() -> None:
        nonlocal current_key, buffer
        if not current_key:
            return
        value = "\n".join(buffer).strip()
        if not value:
            current_key = ""
            buffer = []
            return
        existing = parsed.get(current_key)
        if existing is None:
            parsed[current_key] = value
        elif isinstance(existing, list):
            existing.append(value)
        else:
            parsed[current_key] = [existing, value]
        current_key = ""
        buffer = []

    for line in _strip_code_fences(text).splitlines():
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_ -]{0,40})\s*:\s*(.*)$", line)
        if match:
            raw_key = match.group(1).strip().lower().replace(" ", "_").replace("-", "_")
            mapped_key = KEY_ALIASES.get(raw_key)
            if mapped_key:
                flush()
                current_key = mapped_key
                buffer = [match.group(2).rstrip()]
                continue
        if current_key:
            buffer.append(line.rstrip())
    flush()
    return parsed


def _parse_structured_text(text: str) -> dict[str, Any]:
    stripped = _strip_code_fences(text)
    if not stripped:
        return {}
    fragment = _extract_json_fragment(stripped)
    if fragment:
        try:
            parsed = json.loads(fragment)
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            return parsed[0]
    return _parse_key_value_text(stripped)


def _coerce_jsonish_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    for candidate in (_extract_json_fragment(text), text):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return text


def _extract_command_from_free_text(text: str) -> str:
    stripped = str(text or "").strip()
    if not stripped:
        return ""
    quoted = re.findall(r'"([^"\n]{2,})"|\'([^\'\n]{2,})\'|“([^”\n]{2,})”', stripped)
    for match in quoted:
        candidate = next((item for item in match if item), "")
        if candidate:
            return candidate.strip()
    trimmed = COMMAND_TRIM_RE.match(stripped)
    if trimmed:
        return trimmed.group("command").strip()
    first_line = stripped.splitlines()[0].strip()
    return first_line


def _maybe_skip_free_text(text: str) -> bool:
    normalized = _normalize_lookup_key(text)
    return normalized in ACK_ONLY_TEXTS


def _pick_first(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _build_dataset_indexes(rows: list[dict[str, str]]) -> tuple[dict[int, dict[str, str]], dict[str, tuple[int, dict[str, str]]]]:
    by_row_no = {index: row for index, row in enumerate(rows, start=1)}
    by_command: dict[str, tuple[int, dict[str, str]]] = {}
    for index, row in enumerate(rows, start=1):
        for field in ("command_eng", "command_kor"):
            key = _normalize_lookup_key(row.get(field, ""))
            if key and key not in by_command:
                by_command[key] = (index, row)
    return by_row_no, by_command


def _match_dataset_row(
    payload: dict[str, Any],
    raw_text: str,
    by_row_no: dict[int, dict[str, str]],
    by_command: dict[str, tuple[int, dict[str, str]]],
) -> tuple[int | None, dict[str, str] | None]:
    row_no = _pick_first(payload, "row_no")
    if row_no not in (None, ""):
        try:
            index = int(row_no)
        except Exception:
            index = 0
        if index in by_row_no:
            return index, by_row_no[index]

    for candidate in (
        _pick_first(payload, "command_eng"),
        _pick_first(payload, "command_kor"),
        _pick_first(payload, "command"),
        raw_text,
    ):
        key = _normalize_lookup_key(candidate)
        if key and key in by_command:
            return by_command[key]
    return None, None


def _normalize_gt_payload(
    value: Any,
    *,
    command_text: str,
    cron: str,
    period: int,
    matched_row: dict[str, str] | None,
) -> str:
    candidate = value
    if candidate in (None, "", {}, []):
        candidate = matched_row.get("gt") if matched_row else ""
    if candidate in (None, "", {}, []):
        return ""
    parsed = _coerce_jsonish_value(candidate)
    if isinstance(parsed, dict):
        payload = dict(parsed)
        if "script" not in payload and "code" in payload:
            payload["script"] = payload["code"]
        payload.setdefault("name", slugify(command_text)[:48] or "AdminFeedbackCase")
        payload.setdefault("cron", cron)
        payload.setdefault("period", period)
        return json.dumps(payload, ensure_ascii=False)
    if isinstance(parsed, str):
        wrapped = {
            "name": slugify(command_text)[:48] or "AdminFeedbackCase",
            "cron": cron,
            "period": period,
            "script": parsed.strip(),
        }
        return json.dumps(wrapped, ensure_ascii=False)
    return ""


def _merge_case(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    merged["seen_count"] = int(existing.get("seen_count", 1)) + int(incoming.get("seen_count", 1))
    merged["manual_rules"] = json.dumps(
        _dedupe_strings(
            _listify_strings(_coerce_jsonish_value(existing.get("manual_rules", "")))
            + _listify_strings(_coerce_jsonish_value(incoming.get("manual_rules", "")))
        ),
        ensure_ascii=False,
    )
    if not merged.get("gt") and incoming.get("gt"):
        merged["gt"] = incoming["gt"]
    if not merged.get("connected_devices") and incoming.get("connected_devices"):
        merged["connected_devices"] = incoming["connected_devices"]
    if not merged.get("matched_dataset_row_no") and incoming.get("matched_dataset_row_no"):
        merged["matched_dataset_row_no"] = incoming["matched_dataset_row_no"]
    return merged


def _coerce_admin_case(
    *,
    record: dict[str, Any],
    source_path: Path,
    source_line: int,
    by_row_no: dict[int, dict[str, str]],
    by_command: dict[str, tuple[int, dict[str, str]]],
) -> dict[str, Any] | None:
    raw_text = str(record.get("text") or "").strip()
    structured = dict(record)
    structured_text = _parse_structured_text(raw_text)
    if structured_text:
        structured.update(structured_text)
    has_direct_fields = any(
        key in structured
        for key in (
            "command",
            "command_eng",
            "command_kor",
            "connected_devices",
            "gt",
            "manual_rules",
            "feedback",
            "analysis",
            "why_failed",
            "expected_behavior",
            "notes",
            "row_no",
        )
    )

    if not raw_text and not structured_text and not has_direct_fields:
        return None
    if raw_text and _maybe_skip_free_text(raw_text) and not structured_text and not has_direct_fields:
        return None

    matched_row_no, matched_row = _match_dataset_row(structured, raw_text, by_row_no, by_command)
    command_kor = str(_pick_first(structured, "command_kor") or "").strip()
    command_eng = str(_pick_first(structured, "command_eng") or "").strip()
    command = str(_pick_first(structured, "command") or "").strip()
    if not command_kor and matched_row is not None:
        command_kor = str(matched_row.get("command_kor", "") or "").strip()
    if not command_eng and matched_row is not None:
        command_eng = str(matched_row.get("command_eng", "") or "").strip()

    command_text = command_eng or command_kor or command
    if not command_text and raw_text:
        command_text = _extract_command_from_free_text(raw_text)
    if not command_text:
        command_text = raw_text
    if not command_eng:
        command_eng = command_text
    if not command_kor and _contains_hangul(command_text):
        command_kor = command_text

    cron = str(_pick_first(structured, "cron") or (matched_row.get("cron") if matched_row else "") or "")
    period = _sanitize_period(_pick_first(structured, "period"), default=_sanitize_period(matched_row.get("period"), default=0) if matched_row else 0)
    category = str(_pick_first(structured, "category") or (matched_row.get("category") if matched_row else "admin") or "admin")
    connected_devices = parse_connected_devices(
        _pick_first(structured, "connected_devices") or (matched_row.get("connected_devices") if matched_row else "")
    )

    manual_rules = []
    for key in ("manual_rules", "feedback", "analysis", "why_failed", "expected_behavior", "notes"):
        manual_rules.extend(_listify_strings(structured.get(key)))

    raw_failed = _bool_from_any(_pick_first(structured, "failed"))
    if raw_failed is None:
        raw_failed = _bool_from_any(_pick_first(structured, "status"))
    source_kind = "structured_text" if structured_text else "structured_record" if has_direct_fields else "raw_text"
    note_only = not bool(command_text.strip())
    gt = _normalize_gt_payload(
        _pick_first(structured, "gt"),
        command_text=command_text,
        cron=cron,
        period=period,
        matched_row=matched_row,
    )

    if note_only and not manual_rules:
        return None
    if not note_only and not command_text:
        return None

    case_language = str(_pick_first(structured, "language") or _language_of_text(command_text or raw_text))
    case_id = f"{source_path.stem}:{source_line}"
    return {
        "case_id": case_id,
        "source_path": str(source_path),
        "source_line": source_line,
        "source_kind": source_kind,
        "raw_text": raw_text,
        "command_eng": command_eng,
        "command_kor": command_kor,
        "category": category,
        "connected_devices": json.dumps(connected_devices, ensure_ascii=False),
        "gt": gt,
        "cron": cron,
        "period": str(period),
        "language": case_language,
        "matched_dataset_row_no": matched_row_no or "",
        "manual_rules": json.dumps(_dedupe_strings(manual_rules), ensure_ascii=False),
        "note_only": str(note_only).lower(),
        "raw_failed": "" if raw_failed is None else str(bool(raw_failed)).lower(),
        "seen_count": 1,
    }


def _iter_admin_records(admin_log_root: Path) -> list[tuple[Path, int, dict[str, Any]]]:
    records: list[tuple[Path, int, dict[str, Any]]] = []
    if not admin_log_root.exists():
        return records
    for path in sorted(admin_log_root.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        try:
            if suffix == ".jsonl":
                with path.open(encoding="utf-8") as f:
                    for line_no, line in enumerate(f, start=1):
                        text = line.strip()
                        if not text:
                            continue
                        try:
                            payload = json.loads(text)
                        except Exception:
                            payload = {"text": text}
                        if isinstance(payload, dict):
                            records.append((path, line_no, payload))
            elif suffix == ".json":
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    for index, item in enumerate(payload, start=1):
                        if isinstance(item, dict):
                            records.append((path, index, item))
                elif isinstance(payload, dict):
                    records.append((path, 1, payload))
            elif suffix in {".txt", ".md"}:
                text = path.read_text(encoding="utf-8").strip()
                if text:
                    records.append((path, 1, {"text": text}))
        except Exception:
            continue
    return records


def _collect_admin_cases(
    *,
    admin_log_root: Path,
    dataset_rows: list[dict[str, str]],
    admin_limit: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_row_no, by_command = _build_dataset_indexes(dataset_rows)
    extracted: list[dict[str, Any]] = []
    dedupe_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    ignored: list[dict[str, Any]] = []

    for source_path, source_line, record in _iter_admin_records(admin_log_root):
        case = _coerce_admin_case(
            record=record,
            source_path=source_path,
            source_line=source_line,
            by_row_no=by_row_no,
            by_command=by_command,
        )
        if case is None:
            ignored.append(
                {
                    "source_path": str(source_path),
                    "source_line": source_line,
                    "reason": "unparseable_or_ack_only",
                    "preview": str(record.get("text", ""))[:160],
                }
            )
            continue

        dedupe_key = (
            _normalize_lookup_key(case.get("command_eng", "")),
            _normalize_lookup_key(case.get("connected_devices", "")),
            _normalize_lookup_key(case.get("gt", "")),
        )
        existing = dedupe_index.get(dedupe_key)
        if existing is not None:
            merged = _merge_case(existing, case)
            dedupe_index[dedupe_key] = merged
        else:
            dedupe_index[dedupe_key] = case

    extracted = list(dedupe_index.values())
    extracted.sort(key=lambda item: (item.get("matched_dataset_row_no") in ("", None), str(item.get("case_id"))))
    if admin_limit is not None:
        extracted = extracted[: max(0, admin_limit)]
    return extracted, ignored


def _build_manual_feedback_rules(cases: list[dict[str, Any]]) -> list[str]:
    rules: list[str] = []
    languages = {str(case.get("language", "")) for case in cases}
    if {"ko", "mixed"} & languages:
        rules.append("Handle Korean natural-language commands directly; do not require English-only phrasing before resolving JOILang intent.")
    if {"en", "mixed"} & languages:
        rules.append("Handle concise English natural-language commands directly and preserve the requested action ordering, tags, and timing semantics.")
    if any(parse_connected_devices(case.get("connected_devices", "")) for case in cases):
        rules.append("When connected_devices is present, resolve devices only from those connected-device bindings and preserve relevant selector tags and locations.")
    if any(case.get("gt") for case in cases):
        rules.append("If an admin feedback case has a known correct pattern, prefer the smallest schema-valid program that matches that known target behavior exactly.")

    for case in cases:
        direct_rules = _listify_strings(_coerce_jsonish_value(case.get("manual_rules", "")))
        rules.extend(direct_rules)

    return _dedupe_strings(rules)


def _write_admin_feedback_payload(
    *,
    cases: list[dict[str, Any]],
    ignored: list[dict[str, Any]],
    manual_rules: list[str],
    output_dir: Path,
) -> Path:
    ADMIN_FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().isoformat(),
        "case_count": len(cases),
        "ignored_count": len(ignored),
        "manual_feedback": manual_rules,
        "cases": cases,
        "ignored": ignored,
    }
    latest_path = ADMIN_FEEDBACK_DIR / "manual_feedback.json"
    dump_json(latest_path, payload)
    dump_json(output_dir / "admin_feedback_snapshot.json", payload)
    return latest_path


def _write_admin_cases_csv(cases: list[dict[str, Any]], path: Path) -> None:
    if not cases:
        fieldnames = [
            "category",
            "command_kor",
            "command_eng",
            "connected_devices",
            "gt",
            "cron",
            "period",
            *ADMIN_CASE_EXTRA_FIELDS,
        ]
        atomic_write_csv(path, fieldnames, [])
        return
    rows = [
        {
            "category": case.get("category", "admin"),
            "command_kor": case.get("command_kor", ""),
            "command_eng": case.get("command_eng", ""),
            "connected_devices": case.get("connected_devices", ""),
            "gt": case.get("gt", ""),
            "cron": case.get("cron", ""),
            "period": case.get("period", "0"),
            **{field: case.get(field, "") for field in ADMIN_CASE_EXTRA_FIELDS},
        }
        for case in cases
    ]
    fieldnames = unique_fieldnames(rows, [])
    atomic_write_csv(path, fieldnames, rows)


def _rerank_row_threshold(row: dict[str, str], *, default_threshold: float) -> float:
    if row.get("gt"):
        return default_threshold
    text = str(row.get("command_eng", "") or row.get("command_kor", "") or "")
    if _contains_hangul(text):
        return min(default_threshold, 60.0)
    return default_threshold


def _load_failure_reasons(row: dict[str, str]) -> list[str]:
    value = str(row.get("det_failure_reasons", "") or "").strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except Exception:
        return [value]
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item).strip()]
    return [str(parsed)]


def _row_passed(row: dict[str, str], *, default_threshold: float) -> bool:
    exact = str(row.get("det_gt_exact", "")).lower() == "true"
    if exact:
        return True
    threshold = _rerank_row_threshold(row, default_threshold=default_threshold)
    try:
        score = float(row.get("det_score") or 0.0)
    except Exception:
        score = 0.0
    return score >= threshold


def _summarize_rerank_rows(rows: list[dict[str, str]], *, default_threshold: float) -> dict[str, Any]:
    scores = [float(row.get("det_score") or 0.0) for row in rows]
    gt_sims = [float(row.get("det_gt_similarity") or 0.0) for row in rows]
    exact_count = sum(1 for row in rows if str(row.get("det_gt_exact", "")).lower() == "true")
    pass_count = 0
    fail_count = 0
    failure_counter: Counter[str] = Counter()
    failed_row_nos: list[int] = []
    failed_cases: list[dict[str, Any]] = []

    for row in rows:
        passed = _row_passed(row, default_threshold=default_threshold)
        row_no = int(row.get("row_no") or 0)
        if passed:
            pass_count += 1
            continue
        fail_count += 1
        failed_row_nos.append(row_no)
        reasons = _load_failure_reasons(row)
        failure_counter.update(reasons)
        failed_cases.append(
            {
                "row_no": row_no,
                "command_eng": row.get("command_eng", ""),
                "det_score": float(row.get("det_score") or 0.0),
                "threshold": _rerank_row_threshold(row, default_threshold=default_threshold),
                "failure_reasons": reasons,
                "output": row.get("output", ""),
                "gt": row.get("gt", ""),
                "source_path": row.get("source_path", ""),
                "case_id": row.get("case_id", ""),
            }
        )

    return {
        "row_count": len(rows),
        "avg_det_score": round(fmean(scores), 4) if scores else 0.0,
        "avg_gt_similarity": round(fmean(gt_sims), 4) if gt_sims else 0.0,
        "gt_exact_count": exact_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "top_failure_types": failure_counter.most_common(12),
        "failed_row_nos": failed_row_nos,
        "failed_cases": failed_cases,
    }


def _run_generation_rerank_suite(
    *,
    profile: str,
    genome: dict[str, Any],
    dataset_rows: list[tuple[int, dict[str, str]]],
    service_schema: dict[str, dict[str, Any]],
    candidate_k: int,
    repair_threshold: float,
    repair_attempts: int,
    llm_mode: str | None,
    llm_endpoint: str | None,
    timeout_sec: int,
    retries: int,
    seed: int,
    output_dir: Path,
    label: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates_csv = output_dir / f"{label}_candidates.csv"
    rerank_csv = output_dir / f"{label}_rerank.csv"
    temperature, max_tokens, model = _llm_settings(genome, argparse.Namespace(temperature=None, max_tokens=None))
    generation = generate_candidates_for_rows(
        profile=profile,
        genome=genome,
        dataset_rows=dataset_rows,
        service_schema=service_schema,
        candidate_k=candidate_k,
        llm_mode=llm_mode,
        llm_endpoint=llm_endpoint,
        timeout_sec=timeout_sec,
        retries=retries,
        run_id=f"{label}_{slugify(genome.get('id', 'genome'))}_{seed}",
        output_csv=candidates_csv,
        seed=seed,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
    )
    rerank = rerank_candidates_csv(
        profile=profile,
        genome=genome,
        candidates_csv=candidates_csv,
        service_schema=service_schema,
        repair_threshold=repair_threshold,
        repair_attempts=repair_attempts,
        det_profile="legacy",
        output_csv=rerank_csv,
        llm_mode=llm_mode,
        llm_endpoint=llm_endpoint,
        timeout_sec=timeout_sec,
        retries=retries,
        seed=seed,
    )
    rerank_rows = read_csv_rows(rerank_csv)
    metrics = _summarize_rerank_rows(rerank_rows, default_threshold=repair_threshold)
    summary = {
        "label": label,
        "candidates_csv": str(candidates_csv),
        "rerank_csv": str(rerank_csv),
        "generation": generation,
        "rerank": rerank,
        "metrics": metrics,
    }
    dump_json(output_dir / f"{label}_summary.json", summary)
    return summary


def _filter_rows_by_numbers(
    rows: list[tuple[int, dict[str, str]]],
    target_row_nos: list[int],
) -> list[tuple[int, dict[str, str]]]:
    row_no_set = {int(value) for value in target_row_nos}
    return [item for item in rows if item[0] in row_no_set]


def _write_genome(path: Path, genome: dict[str, Any]) -> Path:
    dump_json(path, genome)
    return path


def _metric_guard(before: dict[str, Any] | None, after: dict[str, Any] | None) -> dict[str, Any]:
    if before is None or after is None:
        return {"ok": True, "reason": "not_applicable"}
    avg_ok = float(after.get("avg_det_score", 0.0)) + 1e-9 >= float(before.get("avg_det_score", 0.0))
    gt_ok = float(after.get("avg_gt_similarity", 0.0)) + 1e-9 >= float(before.get("avg_gt_similarity", 0.0))
    exact_ok = int(after.get("gt_exact_count", 0)) >= int(before.get("gt_exact_count", 0))
    fail_ok = int(after.get("fail_count", 0)) <= int(before.get("fail_count", 0))
    return {
        "ok": avg_ok and gt_ok and exact_ok and fail_ok,
        "avg_det_score_non_decreasing": avg_ok,
        "avg_gt_similarity_non_decreasing": gt_ok,
        "gt_exact_count_non_decreasing": exact_ok,
        "fail_count_non_increasing": fail_ok,
        "before": before,
        "after": after,
    }


def _safe_update_name(explicit_name: str | None, *, timestamp: datetime) -> str:
    if explicit_name:
        return slugify(explicit_name)
    base_name = VERSION_ROOT.name
    if base_name.startswith("version0_15_update"):
        base_name = "version0_15"
    elif "_update" in base_name:
        base_name = base_name.split("_update", 1)[0]
    return f"{base_name}_update{timestamp.strftime('%Y%m%d')}"


def _scaffold_update_version(
    *,
    target_name: str,
    promoted_genome_path: Path,
    run_summary: dict[str, Any],
) -> Path:
    target_root = VERSION_ROOT.parent / target_name
    if target_root.exists():
        suffix = datetime.now().strftime("%H%M%S")
        target_root = VERSION_ROOT.parent / f"{target_name}_{suffix}"

    ignore = shutil.ignore_patterns(
        "__pycache__",
        "*.pyc",
        "results",
        "logs",
        "checkpoints",
        "merged_system_prompt_*.md",
    )
    shutil.copytree(VERSION_ROOT, target_root, ignore=ignore)
    for subdir in ("results", "logs", "checkpoints"):
        (target_root / subdir).mkdir(parents=True, exist_ok=True)

    for filename in ("best_genome_after_feedback.json", "best_genome.json", "best_genome_from_ga.json"):
        shutil.copy2(promoted_genome_path, target_root / "results" / filename)

    summary_path = target_root / "results" / "admin_feedback_update_summary.json"
    dump_json(summary_path, run_summary)

    model_config_path = target_root / "model_config.json"
    if model_config_path.exists():
        model_config = json.loads(model_config_path.read_text(encoding="utf-8"))
        model_config["model_version"] = target_root.name
        model_config["model_description"] = (
            f"Admin-feedback-promoted update generated from {VERSION_ROOT.name}. "
            "Includes admin replay feedback and benchmark/GA verification artifacts."
        )
        model_config["model_create"] = datetime.now().strftime("%Y-%m-%d")
        dump_json(model_config_path, model_config)

    promotion_note = "\n".join(
        [
            f"# {target_root.name}",
            "",
            f"- promoted_from: {VERSION_ROOT.name}",
            f"- promoted_at: {datetime.now().isoformat()}",
            f"- promoted_genome: {promoted_genome_path}",
            f"- summary_json: {summary_path}",
            "",
            "This folder was scaffolded automatically by run_admin_feedback_update.py.",
            "",
        ]
    )
    (target_root / "results" / "PROMOTION.md").write_text(promotion_note, encoding="utf-8")
    return target_root


def run_admin_feedback_update(
    *,
    profile: str = VERSION_ROOT.name,
    genome_json: str | Path = _default_genome_json(),
    dataset: str | Path = DATASET_DEFAULT,
    service_schema: str | Path = SERVICE_SCHEMA_DEFAULT,
    admin_log_root: str | Path = ADMIN_LOG_ROOT_DEFAULT,
    admin_limit: int | None = None,
    admin_candidate_k: int = 1,
    admin_validation_size: int = 8,
    admin_feedback_attempts: int = 3,
    admin_improvement_threshold: float = 0.0,
    admin_repair_threshold: float = 60.0,
    admin_repair_attempts: int = 1,
    benchmark_limit: int | None = None,
    start_row: int = 1,
    end_row: int | None = None,
    category: list[str] | tuple[str, ...] | None = None,
    skip_benchmark: bool = False,
    skip_category_sweep: bool = False,
    benchmark_candidate_k: int = 2,
    ga_population: int = 8,
    ga_gens: int = 6,
    ga_crossover_rate: float = 0.6,
    ga_mutation_rate: float = 0.2,
    ga_elites: int = 2,
    ga_sample_size: int = 16,
    ga_cheap_eval_limit: int = 5,
    ga_validation_size: int = 8,
    ga_alpha: float = 0.5,
    ga_plateau_generations: int = 2,
    ga_feedback_attempts: int = 2,
    ga_feedback_threshold: float = 0.1,
    category_sample_size: int = 3,
    category_attempts: int = 2,
    category_full_failure_sample_size: int = 16,
    category_final_attempts: int = 2,
    repair_threshold: float = 70.0,
    repair_attempts: int = 1,
    llm_mode: str | None = None,
    llm_endpoint: str | None = None,
    timeout_sec: int = 1800,
    retries: int = 1,
    seed: int = 15,
    update_name: str | None = None,
    force_promote: bool = False,
) -> dict[str, Any]:
    ensure_workspace()
    timestamp = datetime.now()
    run_dir = RESULTS_DIR / f"admin_feedback_update_{timestamp.strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)

    base_genome = load_genome(genome_json)
    service_schema_dict = load_service_schema(service_schema)
    dataset_rows = load_dataset_rows(dataset)

    admin_cases, ignored_admin_records = _collect_admin_cases(
        admin_log_root=Path(admin_log_root),
        dataset_rows=dataset_rows,
        admin_limit=admin_limit,
    )
    manual_rules = _build_manual_feedback_rules(admin_cases)
    admin_feedback_file = _write_admin_feedback_payload(
        cases=admin_cases,
        ignored=ignored_admin_records,
        manual_rules=manual_rules,
        output_dir=run_dir,
    )
    admin_cases_csv = run_dir / "admin_cases.csv"
    _write_admin_cases_csv(admin_cases, admin_cases_csv)

    admin_rows = [
        (index, row)
        for index, row in enumerate(load_dataset_rows(admin_cases_csv), start=1)
        if str(row.get("note_only", "")).lower() != "true"
    ]

    admin_baseline = None
    admin_feedback = None
    admin_post = None
    admin_final = None
    admin_working_rows: list[int] = []
    admin_failing_rows: list[int] = []
    promoted_source_genome = base_genome
    promoted_source_genome_path = _write_genome(run_dir / "base_genome.json", base_genome)

    if admin_rows:
        admin_baseline = _run_generation_rerank_suite(
            profile=profile,
            genome=base_genome,
            dataset_rows=admin_rows,
            service_schema=service_schema_dict,
            candidate_k=admin_candidate_k,
            repair_threshold=admin_repair_threshold,
            repair_attempts=admin_repair_attempts,
            llm_mode=llm_mode,
            llm_endpoint=llm_endpoint,
            timeout_sec=timeout_sec,
            retries=retries,
            seed=seed,
            output_dir=run_dir,
            label="admin_baseline",
        )
        admin_failing_rows = list(admin_baseline["metrics"]["failed_row_nos"])
        admin_working_rows = [
            row_no
            for row_no, _row in admin_rows
            if row_no not in set(admin_failing_rows)
        ]
        failing_admin_rows = _filter_rows_by_numbers(admin_rows, admin_failing_rows)
        if failing_admin_rows:
            admin_feedback = run_feedback_loop(
                profile=profile,
                genome=base_genome,
                dataset_rows=failing_admin_rows,
                service_schema=service_schema_dict,
                validation_size=min(admin_validation_size, len(failing_admin_rows)),
                candidate_k=admin_candidate_k,
                attempts=admin_feedback_attempts,
                improvement_threshold=admin_improvement_threshold,
                llm_mode=llm_mode,
                llm_endpoint=llm_endpoint,
                timeout_sec=timeout_sec,
                retries=retries,
                seed=seed + 1000,
            )
            promoted_source_genome = admin_feedback["best_genome"] if admin_feedback.get("best_genome") else base_genome
            promoted_source_genome_path = _write_genome(run_dir / "best_after_admin_feedback.json", promoted_source_genome)
            admin_post = _run_generation_rerank_suite(
                profile=profile,
                genome=promoted_source_genome,
                dataset_rows=admin_rows,
                service_schema=service_schema_dict,
                candidate_k=admin_candidate_k,
                repair_threshold=admin_repair_threshold,
                repair_attempts=admin_repair_attempts,
                llm_mode=llm_mode,
                llm_endpoint=llm_endpoint,
                timeout_sec=timeout_sec,
                retries=retries,
                seed=seed + 1001,
                output_dir=run_dir,
                label="admin_after_feedback",
            )

    benchmark_rows: list[tuple[int, dict[str, str]]] = []
    benchmark_baseline = None
    ga_summary = None
    category_summary = None
    benchmark_final = None
    final_genome = promoted_source_genome
    final_genome_path = promoted_source_genome_path

    if not skip_benchmark:
        benchmark_rows = select_rows(
            dataset_rows,
            start_row=start_row,
            end_row=end_row,
            limit=benchmark_limit,
            categories=category,
        )
        if not benchmark_rows:
            raise SystemExit("No benchmark rows selected. Check --start-row/--end-row/--benchmark-limit/--category.")

        benchmark_baseline = _run_generation_rerank_suite(
            profile=profile,
            genome=base_genome,
            dataset_rows=benchmark_rows,
            service_schema=service_schema_dict,
            candidate_k=benchmark_candidate_k,
            repair_threshold=repair_threshold,
            repair_attempts=repair_attempts,
            llm_mode=llm_mode,
            llm_endpoint=llm_endpoint,
            timeout_sec=timeout_sec,
            retries=retries,
            seed=seed + 2000,
            output_dir=run_dir,
            label="benchmark_baseline",
        )

        ga_seed_genome_path = _write_genome(run_dir / "ga_seed_genome.json", promoted_source_genome)
        ga_args = argparse.Namespace(
            profile=profile,
            genome_json=str(ga_seed_genome_path),
            dataset=str(dataset),
            service_schema=str(service_schema),
            limit=benchmark_limit,
            start_row=start_row,
            end_row=end_row,
            category=list(category or []),
            population=ga_population,
            gens=ga_gens,
            crossover_rate=ga_crossover_rate,
            mutation_rate=ga_mutation_rate,
            elites=ga_elites,
            sample_size=ga_sample_size,
            cheap_eval_limit=ga_cheap_eval_limit,
            candidate_k=benchmark_candidate_k,
            validation_size=ga_validation_size,
            alpha=ga_alpha,
            plateau_generations=ga_plateau_generations,
            feedback_attempts=ga_feedback_attempts,
            feedback_threshold=ga_feedback_threshold,
            llm_mode=llm_mode,
            llm_endpoint=llm_endpoint,
            timeout_sec=timeout_sec,
            retries=retries,
            seed=seed + 3000,
        )
        ga_summary = run_ga_search(ga_args)
        ga_best_genome = ga_summary.get("best_genome") or promoted_source_genome
        ga_best_genome_path = _write_genome(run_dir / "best_after_ga.json", ga_best_genome)

        if skip_category_sweep:
            final_genome = ga_best_genome
            final_genome_path = ga_best_genome_path
            benchmark_final = _run_generation_rerank_suite(
                profile=profile,
                genome=final_genome,
                dataset_rows=benchmark_rows,
                service_schema=service_schema_dict,
                candidate_k=benchmark_candidate_k,
                repair_threshold=repair_threshold,
                repair_attempts=repair_attempts,
                llm_mode=llm_mode,
                llm_endpoint=llm_endpoint,
                timeout_sec=timeout_sec,
                retries=retries,
                seed=seed + 4000,
                output_dir=run_dir,
                label="benchmark_final",
            )
        else:
            sweep_args = argparse.Namespace(
                profile=profile,
                genome_json=str(ga_best_genome_path),
                dataset=str(dataset),
                service_schema=str(service_schema),
                limit=benchmark_limit,
                start_row=start_row,
                end_row=end_row,
                category=list(category or []),
                category_sample_size=category_sample_size,
                category_attempts=category_attempts,
                candidate_k=1,
                full_failure_sample_size=category_full_failure_sample_size,
                final_attempts=category_final_attempts,
                repair_threshold=repair_threshold,
                repair_attempts=repair_attempts,
                skip_full_pass=False,
                llm_mode=llm_mode,
                llm_endpoint=llm_endpoint,
                timeout_sec=timeout_sec,
                retries=retries,
                seed=seed + 5000,
            )
            category_summary = run_category_sweep(sweep_args)
            final_genome_path = Path(category_summary["final_best_genome"])
            final_genome = load_genome(final_genome_path)
            benchmark_final = category_summary.get("post_full")

    if admin_rows and final_genome_path != promoted_source_genome_path:
        admin_final = _run_generation_rerank_suite(
            profile=profile,
            genome=final_genome,
            dataset_rows=admin_rows,
            service_schema=service_schema_dict,
            candidate_k=admin_candidate_k,
            repair_threshold=admin_repair_threshold,
            repair_attempts=admin_repair_attempts,
            llm_mode=llm_mode,
            llm_endpoint=llm_endpoint,
            timeout_sec=timeout_sec,
            retries=retries,
            seed=seed + 6000,
            output_dir=run_dir,
            label="admin_final",
        )

    final_admin_metrics = (admin_final or admin_post or admin_baseline or {}).get("metrics")
    final_benchmark_metrics = (benchmark_final or benchmark_baseline or {}).get("metrics")
    benchmark_guard = _metric_guard(
        benchmark_baseline.get("metrics") if benchmark_baseline else None,
        benchmark_final.get("metrics") if benchmark_final else None,
    )
    admin_guard = _metric_guard(
        admin_baseline.get("metrics") if admin_baseline else None,
        final_admin_metrics,
    )

    can_promote = False
    promotion_reason = "benchmark_skipped"
    if force_promote:
        can_promote = True
        promotion_reason = "force_promote"
    elif not skip_benchmark and benchmark_guard.get("ok"):
        if admin_rows:
            can_promote = admin_guard.get("ok", False)
            promotion_reason = "benchmark_and_admin_ok" if can_promote else "admin_guard_failed"
        else:
            can_promote = True
            promotion_reason = "benchmark_ok_no_admin_rows"
    elif not skip_benchmark:
        promotion_reason = "benchmark_guard_failed"

    promoted_version_root = None
    if can_promote:
        promoted_version_root = _scaffold_update_version(
            target_name=_safe_update_name(update_name, timestamp=timestamp),
            promoted_genome_path=final_genome_path,
            run_summary={},
        )

    summary = {
        "run_dir": str(run_dir),
        "profile": profile,
        "admin_log_root": str(admin_log_root),
        "admin_feedback_file": str(admin_feedback_file),
        "base_genome_json": str(genome_json),
        "final_genome_json": str(final_genome_path),
        "admin_case_count": len(admin_cases),
        "admin_replay_case_count": len(admin_rows),
        "admin_working_row_count": len(admin_working_rows),
        "admin_failing_row_count": len(admin_failing_rows),
        "manual_rule_count": len(manual_rules),
        "admin_baseline": admin_baseline,
        "admin_feedback": admin_feedback,
        "admin_post": admin_post,
        "admin_final": admin_final,
        "benchmark_baseline": benchmark_baseline,
        "ga_summary": ga_summary,
        "category_summary": category_summary,
        "benchmark_final": benchmark_final,
        "benchmark_guard": benchmark_guard,
        "admin_guard": admin_guard,
        "promotion": {
            "requested_name": _safe_update_name(update_name, timestamp=timestamp),
            "performed": bool(promoted_version_root),
            "reason": promotion_reason,
            "target_root": str(promoted_version_root) if promoted_version_root else "",
            "runtime_model": f"gpt_mg.{promoted_version_root.name}" if promoted_version_root else "",
            "display_name": f"PromptGA_{promoted_version_root.name}_svc-v2.0.1_cd" if promoted_version_root else "",
        },
    }

    if promoted_version_root is not None:
        dump_json(promoted_version_root / "results" / "admin_feedback_update_summary.json", summary)

    dump_json(run_dir / "summary.json", summary)

    report_lines = [
        f"# {VERSION_ROOT.name} admin feedback update",
        "",
        f"- admin_case_count: {summary['admin_case_count']}",
        f"- admin_replay_case_count: {summary['admin_replay_case_count']}",
        f"- admin_working_row_count: {summary['admin_working_row_count']}",
        f"- admin_failing_row_count: {summary['admin_failing_row_count']}",
        f"- manual_rule_count: {summary['manual_rule_count']}",
        f"- final_genome_json: {summary['final_genome_json']}",
        f"- promotion_performed: {summary['promotion']['performed']}",
        f"- promotion_reason: {summary['promotion']['reason']}",
        "",
        "## Benchmark Guard",
        json.dumps(benchmark_guard, ensure_ascii=False, indent=2),
        "",
        "## Admin Guard",
        json.dumps(admin_guard, ensure_ascii=False, indent=2),
        "",
    ]
    (run_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return summary


def _namespace_to_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "profile": args.profile,
        "genome_json": args.genome_json,
        "dataset": args.dataset,
        "service_schema": args.service_schema,
        "admin_log_root": args.admin_log_root,
        "admin_limit": args.admin_limit,
        "admin_candidate_k": args.admin_candidate_k,
        "admin_validation_size": args.admin_validation_size,
        "admin_feedback_attempts": args.admin_feedback_attempts,
        "admin_improvement_threshold": args.admin_improvement_threshold,
        "admin_repair_threshold": args.admin_repair_threshold,
        "admin_repair_attempts": args.admin_repair_attempts,
        "benchmark_limit": args.benchmark_limit,
        "start_row": args.start_row,
        "end_row": args.end_row,
        "category": args.category,
        "skip_benchmark": args.skip_benchmark,
        "skip_category_sweep": args.skip_category_sweep,
        "benchmark_candidate_k": args.benchmark_candidate_k,
        "ga_population": args.ga_population,
        "ga_gens": args.ga_gens,
        "ga_crossover_rate": args.ga_crossover_rate,
        "ga_mutation_rate": args.ga_mutation_rate,
        "ga_elites": args.ga_elites,
        "ga_sample_size": args.ga_sample_size,
        "ga_cheap_eval_limit": args.ga_cheap_eval_limit,
        "ga_validation_size": args.ga_validation_size,
        "ga_alpha": args.ga_alpha,
        "ga_plateau_generations": args.ga_plateau_generations,
        "ga_feedback_attempts": args.ga_feedback_attempts,
        "ga_feedback_threshold": args.ga_feedback_threshold,
        "category_sample_size": args.category_sample_size,
        "category_attempts": args.category_attempts,
        "category_full_failure_sample_size": args.category_full_failure_sample_size,
        "category_final_attempts": args.category_final_attempts,
        "repair_threshold": args.repair_threshold,
        "repair_attempts": args.repair_attempts,
        "llm_mode": args.llm_mode,
        "llm_endpoint": args.llm_endpoint,
        "timeout_sec": args.timeout_sec,
        "retries": args.retries,
        "seed": args.seed,
        "update_name": args.update_name,
        "force_promote": args.force_promote,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    summary = run_admin_feedback_update(**_namespace_to_kwargs(args))
    if args.print_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("Admin feedback update completed")
        print(f"- run_dir: {summary['run_dir']}")
        print(f"- admin_case_count: {summary['admin_case_count']}")
        print(f"- admin_replay_case_count: {summary['admin_replay_case_count']}")
        print(f"- admin_failing_row_count: {summary['admin_failing_row_count']}")
        if summary.get("benchmark_baseline", {}).get("metrics"):
            print(f"- benchmark_baseline_avg_det_score: {summary['benchmark_baseline']['metrics']['avg_det_score']}")
        if summary.get("benchmark_final", {}).get("metrics"):
            print(f"- benchmark_final_avg_det_score: {summary['benchmark_final']['metrics']['avg_det_score']}")
        print(f"- promotion_performed: {summary['promotion']['performed']}")
        if summary["promotion"]["performed"]:
            print(f"- promoted_runtime_model: {summary['promotion']['runtime_model']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
