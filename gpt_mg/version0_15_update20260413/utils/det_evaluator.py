#!/usr/bin/env python3
# Assumption: this file lives under gpt_mg/version0_14/utils/ and reads the authoritative schema from datasets/service_list_ver2.0.1.json.
from __future__ import annotations

import json
import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any

from utils.pipeline_common import (
    SERVICE_SCHEMA_DEFAULT,
    canonical_service_name,
    extract_command_numbers,
    lowercase_output_member_name,
    load_service_schema,
    parse_connected_devices,
    split_camel_tokens,
    tokenize_command,
)


LEGACY_WEIGHTS = {
    "schema_ok": 0.15,
    "service_match": 0.20,
    "arg_type": 0.15,
    "precondition": 0.05,
    "semantic": 0.10,
    "extraneous": 0.05,
    "gt_similarity": 0.30,
}

STRICT_WEIGHTS = {
    "schema_ok": 0.05,
    "service_match": 0.10,
    "arg_type": 0.05,
    "precondition": 0.05,
    "semantic": 0.10,
    "extraneous": 0.05,
    "gt_similarity": 0.05,
    "gt_service_coverage": 0.20,
    "gt_receiver_coverage": 0.15,
    "dataflow": 0.10,
    "numeric_grounding": 0.05,
    "enum_grounding": 0.05,
}

DEFAULT_WEIGHTS = LEGACY_WEIGHTS
PROFILE_WEIGHTS = {
    "legacy": LEGACY_WEIGHTS,
    "strict": STRICT_WEIGHTS,
}

MEMBER_ACCESS_RE = re.compile(
    r"(?P<receiver>all\([^\n\r()]+\)|\([^\n\r()]+\))\.(?P<member>[A-Za-z_][A-Za-z0-9_]*)[ \t]*(?:\((?P<args>[^()]*)\))?"
)
TAG_RE = re.compile(r"#([A-Za-z_][A-Za-z0-9_]*)")
NUMERIC_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
INTEGER_RE = re.compile(r"^-?\d+$")
QUOTED_RE = re.compile(r'^"(?:[^"\\]|\\.)*"$')

TOKEN_SYNONYMS = {
    "tv": {"television", "channel"},
    "television": {"television", "channel"},
    "channel": {"channel", "setchannel"},
    "speaker": {"speaker", "speak", "volume"},
    "say": {"speak"},
    "tell": {"speak"},
    "announce": {"speak"},
    "speak": {"speak"},
    "volume": {"volume", "setvolume"},
    "humidity": {"humidity", "weather", "humidityweather"},
    "temperature": {"temperature", "targettemperature", "settargettemperature"},
    "dry": {"dry", "dishwashermode", "setdishwashermode"},
    "dishwasher": {"dishwasher", "dishwashermode", "setdishwashermode"},
    "leak": {"leakage", "leaksensor"},
    "valve": {"valve", "close", "open"},
    "close": {"close", "off", "stop"},
    "open": {"open", "on", "play", "start"},
    "turn": {"on", "off", "toggle"},
    "light": {"light", "brightness", "movetobrightness"},
    "brightness": {"brightness", "movetobrightness"},
    "cook": {"cooking", "setcookingparameters"},
    "cooking": {"cooking", "setcookingparameters"},
    "minute": {"time", "duration"},
    "minutes": {"time", "duration"},
    "second": {"time", "duration"},
    "seconds": {"time", "duration"},
}

HELPER_ACTIONS = {"On", "Off", "Toggle", "Switch_On", "Switch_Off", "Switch_Toggle"}
STRUCTURAL_MARKERS = ("delay(", "wait until", "all(", "prev", "curr", "if (", "else", ":=")


def load_schema(service_list: dict[str, Any] | str | None = None) -> dict[str, dict[str, Any]]:
    if service_list is None:
        return load_service_schema(SERVICE_SCHEMA_DEFAULT)
    if isinstance(service_list, str):
        return load_service_schema(service_list)
    return service_list


def _coerce_candidate_object(candidate_json: Any) -> tuple[bool, dict[str, Any] | None, str]:
    if isinstance(candidate_json, dict):
        return True, candidate_json, json.dumps(candidate_json, ensure_ascii=False)
    if isinstance(candidate_json, list):
        if candidate_json and isinstance(candidate_json[0], dict):
            return True, candidate_json[0], json.dumps(candidate_json[0], ensure_ascii=False)
        return True, None, json.dumps(candidate_json, ensure_ascii=False)
    if not isinstance(candidate_json, str):
        return False, None, ""
    text = candidate_json.strip()
    if not text:
        return False, None, text
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return False, None, text
    if isinstance(parsed, dict):
        return True, parsed, text
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        return True, parsed[0], text
    return True, None, text


def _coerce_gt_object(ground_truth: Any) -> dict[str, Any] | None:
    if not ground_truth:
        return None
    if isinstance(ground_truth, dict):
        return ground_truth
    text = str(ground_truth).strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed
    name = _extract_jsonish_string_field(text, "name")
    cron = _extract_jsonish_string_field(text, "cron")
    script = _extract_jsonish_string_field(text, "script") or _extract_jsonish_string_field(text, "code")
    period = _extract_jsonish_numeric_field(text, "period")
    if any(item is not None for item in (name, cron, script, period)):
        return {
            "name": name or "",
            "cron": cron or "",
            "period": 0 if period is None else period,
            "script": script or "",
        }
    return None


def _extract_jsonish_string_field(text: str, key: str) -> str | None:
    marker = f'"{key}"'
    start = text.find(marker)
    if start == -1:
        return None
    colon = text.find(":", start + len(marker))
    if colon == -1:
        return None
    quote = text.find('"', colon + 1)
    if quote == -1:
        return None
    chars: list[str] = []
    escaped = False
    for idx in range(quote + 1, len(text)):
        ch = text[idx]
        if escaped:
            chars.append(ch)
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            chars.append(ch)
            continue
        if ch == '"':
            return _unescape_jsonish_text("".join(chars))
        chars.append(ch)
    return None


def _extract_jsonish_numeric_field(text: str, key: str) -> int | None:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*(-?\d+)', text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def _unescape_jsonish_text(text: str) -> str:
    value = text.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"')
    value = value.replace("\\r", "\r").replace("\\\\", "\\")
    return value


def _normalize_code(text: str) -> str:
    normalized = (text or "").strip()
    if not normalized:
        return ""
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"\s*([(){}.,=:+\-*/<>!])\s*", r"\1", normalized)
    return normalized.strip()


def _extract_enums(meta: dict[str, Any]) -> set[str]:
    enums = set()
    for raw in meta.get("enums_descriptor", []) or []:
        enums.add(str(raw).split(" - ", 1)[0].strip())
    return {item for item in enums if item}


def _split_args(arg_string: str | None) -> list[str]:
    if arg_string is None:
        return []
    text = arg_string.strip()
    if not text:
        return []
    args: list[str] = []
    current: list[str] = []
    in_string = False
    escaped = False
    depth = 0
    for ch in text:
        if escaped:
            current.append(ch)
            escaped = False
            continue
        if ch == "\\":
            current.append(ch)
            escaped = True
            continue
        if ch == '"':
            current.append(ch)
            in_string = not in_string
            continue
        if not in_string:
            if ch in "([{" :
                depth += 1
            elif ch in ")]}":
                depth = max(0, depth - 1)
            elif ch == "," and depth == 0:
                args.append("".join(current).strip())
                current = []
                continue
        current.append(ch)
    if current:
        args.append("".join(current).strip())
    return args


def _extract_uses(code: str) -> list[dict[str, Any]]:
    uses: list[dict[str, Any]] = []
    for match in MEMBER_ACCESS_RE.finditer(code or ""):
        receiver = match.group("receiver")
        member = match.group("member")
        args = _split_args(match.group("args"))
        uses.append(
            {
                "receiver": receiver,
                "tags": TAG_RE.findall(receiver),
                "member": member,
                "args": args,
                "is_call": match.group("args") is not None,
            }
        )
    return uses


def _connected_context_devices(connected_devices: dict[str, Any], tags: list[str], schema: dict[str, dict[str, Any]]) -> set[str]:
    if not connected_devices or not tags:
        return set()
    matched_devices: set[str] = set()
    tag_set = {tag.lower() for tag in tags}
    for _, meta in connected_devices.items():
        meta_tags = meta.get("tags") or []
        if not isinstance(meta_tags, list):
            meta_tags = [meta_tags]
        meta_tag_set = {str(item).lower() for item in meta_tags if item}
        if tag_set & meta_tag_set:
            category = meta.get("category")
            categories = category if isinstance(category, list) else [category]
            for candidate in categories:
                if candidate in schema:
                    matched_devices.add(candidate)
    return matched_devices


def _infer_devices(receiver_tags: list[str], connected_devices: dict[str, Any], schema: dict[str, dict[str, Any]]) -> set[str]:
    devices = {tag for tag in receiver_tags if tag in schema}
    devices.update(_connected_context_devices(connected_devices, receiver_tags, schema))
    return devices


def _service_catalog(schema: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    catalog: dict[str, list[str]] = {}
    for device, services in schema.items():
        for service_name in services:
            catalog.setdefault(service_name, []).append(device)
            catalog.setdefault(canonical_service_name(device, service_name), []).append(device)
    return catalog


def _resolve_casefold_device_service(
    schema: dict[str, dict[str, Any]],
    device_token: str,
    service_token: str,
) -> tuple[str, str] | None:
    device_lower = str(device_token or "").lower()
    service_lower = lowercase_output_member_name(service_token)
    for schema_device, services in schema.items():
        if schema_device.lower() != device_lower:
            continue
        for schema_service in services:
            if schema_service.lower() == service_lower:
                return schema_device, schema_service
    return None


def _resolve_casefold_service_for_device(
    schema: dict[str, dict[str, Any]],
    device_name: str,
    member: str,
) -> str | None:
    member_lower = lowercase_output_member_name(member)
    for schema_service in schema.get(device_name, {}):
        if schema_service.lower() == member_lower:
            return schema_service
    return None


def _resolve_service(usage: dict[str, Any], schema: dict[str, dict[str, Any]], connected_devices: dict[str, Any]) -> dict[str, Any] | None:
    member = usage["member"]
    inferred_devices = _infer_devices(usage["tags"], connected_devices, schema)
    if "_" in member:
        device_name, service_name = member.split("_", 1)
        resolved_pair = _resolve_casefold_device_service(schema, device_name, service_name)
        if resolved_pair is not None:
            device_name, service_name = resolved_pair
            meta = dict(schema[device_name][service_name])
            return {
                "device": device_name,
                "service": service_name,
                "canonical_name": canonical_service_name(device_name, service_name),
                "meta": meta,
                "inferred_devices": sorted(inferred_devices),
            }
    candidate_devices = sorted(inferred_devices)
    for device_name in candidate_devices:
        resolved_service = _resolve_casefold_service_for_device(schema, device_name, member)
        if resolved_service is not None:
            meta = dict(schema[device_name][resolved_service])
            return {
                "device": device_name,
                "service": resolved_service,
                "canonical_name": canonical_service_name(device_name, resolved_service),
                "meta": meta,
                "inferred_devices": candidate_devices,
            }
    member_lower = lowercase_output_member_name(member)
    raw_matches = [
        device_name
        for device_name, services in schema.items()
        if any(schema_service.lower() == member_lower for schema_service in services)
    ]
    if len(raw_matches) == 1:
        device_name = raw_matches[0]
        resolved_service = _resolve_casefold_service_for_device(schema, device_name, member)
        if resolved_service is None:
            return None
        meta = dict(schema[device_name][resolved_service])
        return {
            "device": device_name,
            "service": resolved_service,
            "canonical_name": canonical_service_name(device_name, resolved_service),
            "meta": meta,
            "inferred_devices": candidate_devices,
        }
    return None


def _service_overlap_score(
    predicted_usages: list[dict[str, Any]],
    gt_code: str,
    schema: dict[str, dict[str, Any]],
    connected_devices: dict[str, Any],
) -> float:
    gt_usages = _resolved_gt_usages_from_code(gt_code, schema, connected_devices)
    predicted = {usage["canonical_name"] for usage in predicted_usages}
    reference = {usage["canonical_name"] for usage in gt_usages}
    if not reference:
        return 1.0 if not predicted else 0.0
    return len(predicted & reference) / len(reference)


def _resolved_gt_usages_from_code(
    gt_code: str,
    schema: dict[str, dict[str, Any]],
    connected_devices: dict[str, Any],
) -> list[dict[str, Any]]:
    gt_usages: list[dict[str, Any]] = []
    for usage in _extract_uses(gt_code):
        resolved = _resolve_service(usage, schema, connected_devices)
        if resolved is None:
            continue
        gt_usages.append({**usage, **resolved})
    return gt_usages


def _resolved_gt_usages(
    ground_truth: Any,
    schema: dict[str, dict[str, Any]],
    connected_devices: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    gt_obj = _coerce_gt_object(ground_truth)
    if not gt_obj:
        return [], ""
    gt_code = str(gt_obj.get("script") or gt_obj.get("code") or "").strip()
    if not gt_code:
        return [], ""
    return _resolved_gt_usages_from_code(gt_code, schema, connected_devices), gt_code


def _service_set(usages: list[dict[str, Any]]) -> set[str]:
    return {
        str(usage.get("canonical_name", "") or "")
        for usage in usages
        if str(usage.get("canonical_name", "") or "").strip()
    }


def _gt_service_coverage_score(predicted_usages: list[dict[str, Any]], gt_usages: list[dict[str, Any]]) -> float:
    reference = _service_set(gt_usages)
    predicted = _service_set(predicted_usages)
    if not reference:
        return 1.0
    return len(predicted & reference) / len(reference)


def _gt_service_precision_score(predicted_usages: list[dict[str, Any]], gt_usages: list[dict[str, Any]]) -> float:
    reference = _service_set(gt_usages)
    predicted = _service_set(predicted_usages)
    if not predicted:
        return 1.0 if not reference else 0.0
    return len(predicted & reference) / len(predicted)


def _receiver_instance_tokens(
    usage: dict[str, Any],
    connected_devices: dict[str, Any],
) -> set[str]:
    tags = {str(tag).lower() for tag in usage.get("tags", []) if tag}
    device_name = str(usage.get("device", "") or "").lower()
    if connected_devices:
        matched: set[str] = set()
        for device_key, meta in connected_devices.items():
            meta_tags = meta.get("tags") or []
            if not isinstance(meta_tags, list):
                meta_tags = [meta_tags]
            meta_tag_set = {str(item).lower() for item in meta_tags if item}
            category = meta.get("category")
            categories = category if isinstance(category, list) else [category]
            meta_tag_set.update(str(item).lower() for item in categories if item)
            meta_tag_set.add(str(device_key).lower())
            if device_name and device_name not in meta_tag_set:
                continue
            if tags and not tags.issubset(meta_tag_set):
                continue
            matched.add(str(device_key))
        if matched:
            return matched
    fallback = set(tags)
    if device_name:
        fallback.add(device_name)
    return fallback


def _gt_receiver_coverage_score(
    predicted_usages: list[dict[str, Any]],
    gt_usages: list[dict[str, Any]],
    connected_devices: dict[str, Any],
) -> float:
    reference = _service_set(gt_usages)
    if not reference:
        return 1.0
    scores: list[float] = []
    for canonical_name in sorted(reference):
        gt_tokens: set[str] = set()
        pred_tokens: set[str] = set()
        for usage in gt_usages:
            if usage.get("canonical_name") == canonical_name:
                gt_tokens.update(_receiver_instance_tokens(usage, connected_devices))
        for usage in predicted_usages:
            if usage.get("canonical_name") == canonical_name:
                pred_tokens.update(_receiver_instance_tokens(usage, connected_devices))
        if not gt_tokens:
            scores.append(1.0 if pred_tokens else 0.0)
            continue
        scores.append(len(gt_tokens & pred_tokens) / len(gt_tokens))
    return sum(scores) / max(len(scores), 1)


def _requires_dataflow(gt_usages: list[dict[str, Any]]) -> bool:
    has_value = any(str(usage.get("meta", {}).get("type", "")).lower() == "value" for usage in gt_usages)
    has_function = any(str(usage.get("meta", {}).get("type", "")).lower() == "function" for usage in gt_usages)
    return has_value and has_function


def _dataflow_score(code: str, predicted_usages: list[dict[str, Any]], gt_usages: list[dict[str, Any]]) -> float:
    if not _requires_dataflow(gt_usages):
        return 1.0
    predicted_values = [usage for usage in predicted_usages if str(usage.get("meta", {}).get("type", "")).lower() == "value"]
    predicted_functions = [usage for usage in predicted_usages if str(usage.get("meta", {}).get("type", "")).lower() == "function"]
    if not predicted_values or not predicted_functions:
        return 0.0
    assignment_like = ":=" in (code or "") or re.search(r"(^|\n)\s*[A-Za-z_][A-Za-z0-9_]*\s*=", code or "") is not None
    function_args = " ".join(" ".join(usage.get("args", [])) for usage in predicted_functions).lower()
    arg_kinds = [_literal_kind(arg) for usage in predicted_functions for arg in usage.get("args", [])]
    arg_has_expression = any(kind in {"EXPR", "IDENT"} for kind in arg_kinds)
    source_markers: set[str] = set()
    for usage in predicted_values:
        source_markers.add(str(usage.get("member", "")).lower())
        source_markers.add(str(usage.get("canonical_name", "")).lower())
        source_markers.add(str(usage.get("service", "")).lower())
        source_markers.update(str(tag).lower() for tag in usage.get("tags", []) if tag)
    source_mentioned_in_args = any(marker and marker in function_args for marker in source_markers)
    if assignment_like and arg_has_expression:
        return 1.0
    if source_mentioned_in_args and arg_has_expression:
        return 0.85
    if arg_has_expression:
        return 0.5
    return 0.2


def _requires_numeric_grounding(command_eng: str, gt_code: str) -> bool:
    return bool(extract_command_numbers(command_eng) and extract_command_numbers(gt_code))


def _numeric_grounding_score(command_eng: str, code: str, gt_code: str) -> float:
    if not _requires_numeric_grounding(command_eng, gt_code):
        return 1.0
    gt_numbers = extract_command_numbers(gt_code)
    candidate_numbers = extract_command_numbers(code)
    if not gt_numbers:
        return 1.0
    if not candidate_numbers:
        return 0.0
    gt_counter = Counter(gt_numbers)
    candidate_counter = Counter(candidate_numbers)
    matched = 0
    for value, count in gt_counter.items():
        matched += min(count, candidate_counter.get(value, 0))
    precision = matched / max(sum(candidate_counter.values()), 1)
    recall = matched / max(sum(gt_counter.values()), 1)
    return max(0.0, min(1.0, 0.5 * precision + 0.5 * recall))


def _normalize_arg_value(text: str) -> str:
    value = str(text or "").strip()
    if QUOTED_RE.match(value):
        value = value[1:-1]
    return value.strip().lower()


def _requires_enum_grounding(gt_usages: list[dict[str, Any]]) -> bool:
    for usage in gt_usages:
        if "ENUM" in _expected_types(usage.get("meta", {})):
            return True
    return False


def _enum_grounding_score(predicted_usages: list[dict[str, Any]], gt_usages: list[dict[str, Any]]) -> float:
    gt_enum_usages = [usage for usage in gt_usages if "ENUM" in _expected_types(usage.get("meta", {}))]
    if not gt_enum_usages:
        return 1.0
    predicted_by_name: dict[str, list[dict[str, Any]]] = {}
    for usage in predicted_usages:
        predicted_by_name.setdefault(str(usage.get("canonical_name", "") or ""), []).append(usage)
    scores: list[float] = []
    for gt_usage in gt_enum_usages:
        canonical_name = str(gt_usage.get("canonical_name", "") or "")
        predicted_options = predicted_by_name.get(canonical_name) or []
        expected = _expected_types(gt_usage.get("meta", {}))
        enum_positions = [idx for idx, expected_type in enumerate(expected) if expected_type.upper().strip() == "ENUM"]
        if not predicted_options:
            scores.extend([0.0] * max(len(enum_positions), 1))
            continue
        predicted_usage = predicted_options[0]
        for idx in enum_positions:
            gt_args = gt_usage.get("args", []) or []
            predicted_args = predicted_usage.get("args", []) or []
            if idx >= len(gt_args) or idx >= len(predicted_args):
                scores.append(0.0)
                continue
            scores.append(1.0 if _normalize_arg_value(predicted_args[idx]) == _normalize_arg_value(gt_args[idx]) else 0.0)
    return sum(scores) / max(len(scores), 1)


def _requires_group_receiver(gt_usages: list[dict[str, Any]], connected_devices: dict[str, Any]) -> bool:
    for usage in gt_usages:
        receiver = str(usage.get("receiver", "") or "")
        if not receiver.startswith("all("):
            continue
        tokens = _receiver_instance_tokens(usage, connected_devices)
        if len(tokens) > 1:
            return True
    return False


def _structural_feature_score(candidate_code: str, gt_code: str) -> float:
    candidate_lower = (candidate_code or "").lower()
    gt_lower = (gt_code or "").lower()
    required = sorted({marker for marker in STRUCTURAL_MARKERS if marker in gt_lower})
    if not required:
        return 1.0
    matched = sum(1 for marker in required if marker in candidate_lower)
    return matched / len(required)


def _gt_similarity(
    candidate_obj: dict[str, Any],
    code: str,
    predicted_usages: list[dict[str, Any]],
    ground_truth: Any,
    schema: dict[str, dict[str, Any]],
    connected_devices: dict[str, Any],
) -> tuple[bool, float, str]:
    gt_obj = _coerce_gt_object(ground_truth)
    if not gt_obj:
        return False, 0.0, ""
    gt_code = str(gt_obj.get("script") or gt_obj.get("code") or "").strip()
    if not gt_code:
        return False, 0.0, ""
    candidate_norm = _normalize_code(code)
    gt_norm = _normalize_code(gt_code)
    seq_score = SequenceMatcher(None, candidate_norm, gt_norm).ratio() if gt_norm else 0.0
    overlap_score = _service_overlap_score(predicted_usages, gt_code, schema, connected_devices)
    structural_score = _structural_feature_score(candidate_norm, gt_norm)
    gt_cron = str(gt_obj.get("cron", "") or "")
    candidate_cron = str(candidate_obj.get("cron", "") or "")
    try:
        gt_period = int(gt_obj.get("period", -1))
    except Exception:
        gt_period = -1
    try:
        candidate_period = int(candidate_obj.get("period", -1))
    except Exception:
        candidate_period = -1
    schedule_score = 1.0 if gt_cron == candidate_cron and gt_period == candidate_period else 0.0
    exact = candidate_norm == gt_norm and schedule_score == 1.0
    similarity = 1.0 if exact else max(
        0.0,
        min(1.0, 0.45 * seq_score + 0.25 * overlap_score + 0.15 * schedule_score + 0.15 * structural_score),
    )
    return exact, round(similarity, 6), gt_code


def _literal_kind(arg: str) -> str:
    text = arg.strip()
    if not text:
        return "EMPTY"
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return "BOOL"
    if INTEGER_RE.match(text):
        return "INTEGER"
    if NUMERIC_RE.match(text):
        return "DOUBLE"
    if QUOTED_RE.match(text):
        inner = text[1:-1]
        if INTEGER_RE.match(inner):
            return "STRING_NUMERIC_INT"
        if NUMERIC_RE.match(inner):
            return "STRING_NUMERIC_DOUBLE"
        return "STRING"
    if any(op in text for op in ("+", "-", "*", "/", "(", ")")):
        return "EXPR"
    return "IDENT"


def _expected_types(meta: dict[str, Any]) -> list[str]:
    raw = str(meta.get("argument_type") or "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split("|") if item.strip()]


def _score_single_arg(arg: str, expected_type: str, meta: dict[str, Any]) -> float:
    expected = expected_type.upper().strip()
    kind = _literal_kind(arg)
    enums = _extract_enums(meta)
    arg_text = arg.strip().strip('"')
    if expected == "INTEGER":
        if kind == "INTEGER":
            return 1.0
        if kind in {"DOUBLE", "STRING_NUMERIC_INT", "STRING_NUMERIC_DOUBLE"}:
            return 0.5
        if kind in {"IDENT", "EXPR"}:
            return 0.75
        return 0.0
    if expected == "DOUBLE":
        if kind in {"INTEGER", "DOUBLE"}:
            return 1.0
        if kind in {"STRING_NUMERIC_INT", "STRING_NUMERIC_DOUBLE"}:
            return 0.6
        if kind in {"IDENT", "EXPR"}:
            return 0.75
        return 0.0
    if expected == "BOOL":
        if kind == "BOOL":
            return 1.0
        if kind in {"IDENT", "EXPR"}:
            return 0.5
        return 0.0
    if expected == "ENUM":
        if kind in {"STRING", "STRING_NUMERIC_INT", "STRING_NUMERIC_DOUBLE"}:
            if enums and arg_text not in enums:
                return 0.0
            return 1.0
        if kind == "IDENT":
            return 0.5 if not enums or arg_text in enums else 0.0
        return 0.0
    if expected in {"STRING", "BINARY"}:
        if kind in {"STRING", "STRING_NUMERIC_INT", "STRING_NUMERIC_DOUBLE", "IDENT", "EXPR"}:
            return 1.0
        return 0.25
    return 0.5


def _score_args(arg_list: list[str], meta: dict[str, Any]) -> float:
    expected = _expected_types(meta)
    if not expected:
        return 1.0 if not arg_list else 0.0
    if not arg_list:
        return 0.0
    if len(expected) == 1:
        return _score_single_arg(arg_list[0], expected[0], meta) if len(arg_list) == 1 else max(0.0, _score_single_arg(arg_list[0], expected[0], meta) - 0.4)
    scores = []
    for idx, expected_type in enumerate(expected):
        if idx >= len(arg_list):
            scores.append(0.0)
            continue
        scores.append(_score_single_arg(arg_list[idx], expected_type, meta))
    if len(arg_list) > len(expected):
        scores.extend([0.0] * (len(arg_list) - len(expected)))
    return sum(scores) / max(len(scores), 1)


def _normalize_token(token: str) -> set[str]:
    token = token.lower()
    expanded = {token}
    expanded.update(TOKEN_SYNONYMS.get(token, set()))
    return expanded


def _semantic_tokens_from_usage(resolved_usages: list[dict[str, Any]]) -> set[str]:
    tokens: set[str] = set()
    for usage in resolved_usages:
        tokens.update(split_camel_tokens(usage["device"]))
        tokens.update(split_camel_tokens(usage["service"]))
        for arg in usage.get("args", []):
            if QUOTED_RE.match(arg.strip()):
                tokens.update(tokenize_command(arg.strip().strip('"')))
    expanded: set[str] = set()
    for token in tokens:
        expanded.update(_normalize_token(token))
    return expanded


def _semantic_tokens_from_command(command_eng: str) -> set[str]:
    tokens = set(tokenize_command(command_eng))
    expanded: set[str] = set()
    for token in tokens:
        expanded.update(_normalize_token(token))
    return expanded


def _semantic_score(command_eng: str, resolved_usages: list[dict[str, Any]], code: str) -> float:
    if not resolved_usages:
        return 0.0
    command_tokens = _semantic_tokens_from_command(command_eng)
    usage_tokens = _semantic_tokens_from_usage(resolved_usages)
    if not command_tokens:
        return 0.5
    overlap = len(command_tokens & usage_tokens) / len(command_tokens)
    numbers = extract_command_numbers(command_eng)
    number_score = 1.0 if not numbers else sum(1 for value in numbers if value in code) / len(numbers)
    conditional_score = 1.0
    lowered = command_eng.lower()
    if any(word in lowered for word in ("if ", "when ", "whenever ")):
        conditional_score = 1.0 if ("if (" in code or "wait until" in code) else 0.4
    return max(0.0, min(1.0, 0.6 * overlap + 0.2 * number_score + 0.2 * conditional_score))


def _extraneous_score(command_eng: str, resolved_usages: list[dict[str, Any]]) -> float:
    if not resolved_usages:
        return 0.0
    command_tokens = _semantic_tokens_from_command(command_eng)
    matched = 0
    for usage in resolved_usages:
        usage_tokens = set(split_camel_tokens(usage["service"])) | set(split_camel_tokens(usage["device"]))
        expanded: set[str] = set()
        for token in usage_tokens:
            expanded.update(_normalize_token(token))
        if expanded & command_tokens or usage["canonical_name"] in HELPER_ACTIONS or usage["service"] in HELPER_ACTIONS:
            matched += 1
    extraneous_count = max(0, len(resolved_usages) - matched)
    return max(0.0, min(1.0, 1.0 - (extraneous_count / max(len(resolved_usages), 1))))


def _has_power_guard(code: str) -> bool:
    return bool(re.search(r"Switch(?:_[A-Za-z0-9]+)?\s*==|Switch(?:_[A-Za-z0-9]+)?\s*!=|Switch_On\(|SwitchOn\(|\.On\(", code or ""))


def _precondition_score(
    command_eng: str,
    resolved_usages: list[dict[str, Any]],
    connected_devices: dict[str, Any],
    code: str,
) -> bool:
    if not resolved_usages:
        return False
    if _has_power_guard(code):
        return True
    context_tags = {tag for tag in connected_devices}
    category_tags = set()
    for meta in connected_devices.values():
        category = meta.get("category")
        if isinstance(category, list):
            category_tags.update(str(item) for item in category)
        elif category:
            category_tags.add(str(category))
    supports_switch = "Switch" in category_tags or "Switch" in context_tags or "Switch_" in (code or "")
    if not supports_switch:
        return True
    lowered = command_eng.lower()
    if any(token in lowered for token in ("turn on", "switch on", "power on")):
        return True
    non_power_actions = [usage for usage in resolved_usages if usage["service"] not in {"On", "Off", "Toggle"}]
    return not non_power_actions


def evaluate_candidate(
    command_eng: str,
    candidate_json: Any,
    service_list: dict[str, Any] | str | None = None,
    *,
    connected_devices: dict[str, Any] | str | None = None,
    ground_truth: Any = None,
    weights: dict[str, float] | None = None,
    profile: str = "legacy",
) -> dict[str, Any]:
    schema = load_schema(service_list)
    connected = parse_connected_devices(connected_devices)
    profile = str(profile or "legacy").strip().lower() or "legacy"
    weights = dict(PROFILE_WEIGHTS.get(profile, LEGACY_WEIGHTS) if weights is None else weights)

    det_valid_json, candidate_obj, raw_candidate = _coerce_candidate_object(candidate_json)
    result: dict[str, Any] = {
        "det_profile": profile,
        "det_valid_json": det_valid_json,
        "det_schema_ok": False,
        "det_service_match": 0.0,
        "det_arg_type_ok": 0.0,
        "det_precondition_ok": False,
        "det_semantic_ok": 0.0,
        "det_min_extraneous": 0.0,
        "det_gt_service_coverage": 1.0,
        "det_gt_service_precision": 1.0,
        "det_gt_receiver_coverage": 1.0,
        "det_dataflow_score": 1.0,
        "det_numeric_grounding": 1.0,
        "det_enum_grounding": 1.0,
        "det_gt_exact": False,
        "det_gt_similarity": 0.0,
        "det_score": 0.0,
        "failure_reasons": [],
        "resolved_services": [],
        "raw_candidate": raw_candidate,
        "gt_script": "",
    }

    if not det_valid_json:
        result["failure_reasons"].append("invalid_json")
        return result

    required_keys = {"name", "cron", "period", "code"}
    if not isinstance(candidate_obj, dict) or not required_keys.issubset(candidate_obj.keys()):
        result["failure_reasons"].append("schema_missing_keys")
        return result

    result["det_schema_ok"] = True
    code = str(candidate_obj.get("code", "") or "")
    usages = _extract_uses(code)
    resolved_usages: list[dict[str, Any]] = []
    service_match_scores: list[float] = []
    arg_scores: list[float] = []

    for usage in usages:
        resolved = _resolve_service(usage, schema, connected)
        if resolved is None:
            service_match_scores.append(0.0)
            arg_scores.append(0.0 if usage["is_call"] else 1.0)
            result["failure_reasons"].append(f"unknown_service:{usage['member']}")
            continue
        resolved_usage = {
            **usage,
            **resolved,
        }
        resolved_usages.append(resolved_usage)
        service_match_scores.append(1.0)
        if usage["is_call"]:
            arg_scores.append(_score_args(usage["args"], resolved["meta"]))
        else:
            arg_scores.append(1.0)

    if usages:
        result["det_service_match"] = round(sum(service_match_scores) / len(service_match_scores), 6)
        result["det_arg_type_ok"] = round(sum(arg_scores) / len(arg_scores), 6)
    else:
        result["det_service_match"] = 0.0 if code.strip() else 0.0
        result["det_arg_type_ok"] = 0.0 if code.strip() else 0.0
        if code.strip():
            result["failure_reasons"].append("no_parseable_member_access")

    if result["det_service_match"] < 1.0:
        result["failure_reasons"].append("service_match")
    if result["det_arg_type_ok"] < 1.0:
        result["failure_reasons"].append("arg_type")

    result["det_precondition_ok"] = _precondition_score(command_eng, resolved_usages, connected, code)
    if not result["det_precondition_ok"]:
        result["failure_reasons"].append("precondition")

    result["det_semantic_ok"] = round(_semantic_score(command_eng, resolved_usages, code), 6)
    if result["det_semantic_ok"] < 0.6:
        result["failure_reasons"].append("semantic")

    result["det_min_extraneous"] = round(_extraneous_score(command_eng, resolved_usages), 6)
    if result["det_min_extraneous"] < 1.0:
        result["failure_reasons"].append("extraneous")

    gt_usages, gt_code = _resolved_gt_usages(ground_truth, schema, connected)
    result["det_gt_service_coverage"] = round(_gt_service_coverage_score(resolved_usages, gt_usages), 6)
    result["det_gt_service_precision"] = round(_gt_service_precision_score(resolved_usages, gt_usages), 6)
    result["det_gt_receiver_coverage"] = round(_gt_receiver_coverage_score(resolved_usages, gt_usages, connected), 6)
    result["det_dataflow_score"] = round(_dataflow_score(code, resolved_usages, gt_usages), 6)
    result["det_numeric_grounding"] = round(_numeric_grounding_score(command_eng, code, gt_code), 6)
    result["det_enum_grounding"] = round(_enum_grounding_score(resolved_usages, gt_usages), 6)
    if result["det_gt_service_coverage"] < 1.0:
        result["failure_reasons"].append("gt_service_coverage")
    if result["det_gt_receiver_coverage"] < 1.0:
        result["failure_reasons"].append("gt_receiver_coverage")
    if result["det_dataflow_score"] < 0.5:
        result["failure_reasons"].append("dataflow")
    if result["det_numeric_grounding"] < 1.0:
        result["failure_reasons"].append("numeric_grounding")
    if result["det_enum_grounding"] < 1.0:
        result["failure_reasons"].append("enum_grounding")

    gt_exact, gt_similarity, gt_script = _gt_similarity(
        candidate_obj,
        code,
        resolved_usages,
        ground_truth,
        schema,
        connected,
    )
    result["det_gt_exact"] = gt_exact
    result["det_gt_similarity"] = gt_similarity
    result["gt_script"] = gt_script
    if gt_exact:
        result["det_semantic_ok"] = 1.0
        result["det_min_extraneous"] = 1.0
        result["failure_reasons"] = []
    elif gt_script and not gt_exact:
        result["failure_reasons"].append("gt_mismatch")

    schema_component = 1.0 if result["det_schema_ok"] else 0.0
    precondition_component = 1.0 if result["det_precondition_ok"] else 0.0
    score = (
        weights["schema_ok"] * schema_component
        + weights["service_match"] * result["det_service_match"]
        + weights["arg_type"] * result["det_arg_type_ok"]
        + weights["precondition"] * precondition_component
        + weights["semantic"] * result["det_semantic_ok"]
        + weights["extraneous"] * result["det_min_extraneous"]
        + weights.get("gt_similarity", 0.0) * result["det_gt_similarity"]
        + weights.get("gt_service_coverage", 0.0) * result["det_gt_service_coverage"]
        + weights.get("gt_receiver_coverage", 0.0) * result["det_gt_receiver_coverage"]
        + weights.get("dataflow", 0.0) * result["det_dataflow_score"]
        + weights.get("numeric_grounding", 0.0) * result["det_numeric_grounding"]
        + weights.get("enum_grounding", 0.0) * result["det_enum_grounding"]
    ) * 100.0

    if gt_exact:
        score = 100.0
    elif not result["det_valid_json"]:
        score = 0.0
    elif profile == "strict":
        if gt_usages and result["det_gt_service_coverage"] < 0.999999:
            score = min(score, 69.9)
        if _requires_dataflow(gt_usages) and result["det_dataflow_score"] < 0.5:
            score = min(score, 69.9)
        if _requires_group_receiver(gt_usages, connected) and result["det_gt_receiver_coverage"] < 0.999999:
            score = min(score, 69.9)
        if _requires_numeric_grounding(command_eng, gt_code) and result["det_numeric_grounding"] < 0.5:
            score = min(score, 69.9)
        if _requires_enum_grounding(gt_usages) and result["det_enum_grounding"] < 0.5:
            score = min(score, 69.9)
    result["det_score"] = round(max(0.0, min(100.0, score)), 4)
    result["resolved_services"] = [
        {
            "device": usage["device"],
            "service": usage["service"],
            "canonical_name": usage["canonical_name"],
            "args": usage["args"],
            "receiver": usage["receiver"],
        }
        for usage in resolved_usages
    ]
    result["failure_reasons"] = sorted(dict.fromkeys(result["failure_reasons"]))
    return result


def evaluate_candidates(
    command_eng: str,
    candidates: list[Any],
    service_list: dict[str, Any] | str | None = None,
    *,
    connected_devices: dict[str, Any] | str | None = None,
    ground_truth: Any = None,
    weights: dict[str, float] | None = None,
    profile: str = "legacy",
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for idx, candidate in enumerate(candidates):
        det = evaluate_candidate(
            command_eng,
            candidate,
            service_list,
            connected_devices=connected_devices,
            ground_truth=ground_truth,
            weights=weights,
            profile=profile,
        )
        det["candidate_index"] = idx
        det["candidate"] = candidate
        scored.append(det)
    scored.sort(key=lambda item: (-float(item.get("det_score", 0.0)), item.get("candidate_index", 0)))
    return scored


def summarize_failure_patterns(scored_rows: list[dict[str, Any]]) -> dict[str, Any]:
    counter: Counter[str] = Counter()
    for row in scored_rows:
        for reason in row.get("failure_reasons", []):
            counter[reason] += 1
    return {
        "top_failure_types": counter.most_common(),
        "count": sum(counter.values()),
    }
