from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Any

from .prompt_surgery_rules import det_feedback_rules, get_prompt_surgery_rule


CORE_BLOCKS = ("01", "02")
OPTIONAL_BLOCKS = ("03", "05", "06")
BLOCK_ORDER = ("01", "02", "03", "05", "06")

BLOCK_FAMILIES = {
    "01": "Core_System",
    "02": "Service_Mapping",
    "03": "Output_Schema",
    "05": "Repair_Clause",
    "06": "DET_Helper",
}

FEEDBACK_RULES = {
    "invalid_json": {
        "failure_type": "invalid_json",
        "affected_block_family": "Output_Schema",
        "prompt_block_id": "03",
        "suggested_mutation_type": "strengthen_json_only_rule",
        "rule": "Return exactly one JSON object only; never emit markdown, prose, or code fences.",
    },
    "schema_missing_keys": {
        "failure_type": "schema_violation",
        "affected_block_family": "Output_Schema",
        "prompt_block_id": "03",
        "suggested_mutation_type": "add_schema_grounding_rule",
        "rule": "Always include exactly the required keys: name, cron, period, and code.",
    },
    "schema_violation": {
        "failure_type": "schema_violation",
        "affected_block_family": "Service_Mapping",
        "prompt_block_id": "02",
        "suggested_mutation_type": "add_schema_grounding_rule",
        "rule": "Ground every receiver, value, function, argument count, and return type in service_list_snippet before emitting code.",
    },
    "unknown_service": {
        "failure_type": "unknown_service",
        "affected_block_family": "Service_Mapping",
        "prompt_block_id": "02",
        "suggested_mutation_type": "add_canonical_service_name_rule",
        "rule": "Use the provided canonical_name exactly, then lowercase only the final emitted member token after the receiver dot.",
    },
    "service_match": {
        "failure_type": "schema_violation",
        "affected_block_family": "Service_Mapping",
        "prompt_block_id": "02",
        "suggested_mutation_type": "add_schema_grounding_rule",
        "rule": "Do not invent service/value names; choose only functions and values present in service_list_snippet.",
    },
    "arg_type": {
        "failure_type": "enum_type_mismatch",
        "affected_block_family": "Enum_Grounding",
        "prompt_block_id": "02",
        "suggested_mutation_type": "strengthen_enum_type_rule",
        "rule": "Match argument_type positionally; enum strings must come from enums_descriptor and numbers must remain unquoted.",
    },
    "enum_grounding": {
        "failure_type": "enum_type_mismatch",
        "affected_block_family": "Enum_Grounding",
        "prompt_block_id": "02",
        "suggested_mutation_type": "strengthen_enum_type_rule",
        "rule": "For ENUM arguments, copy one allowed enum value exactly from the selected service descriptor.",
    },
    "numeric_grounding": {
        "failure_type": "temporal_error",
        "affected_block_family": "Temporal_Rule",
        "prompt_block_id": "06",
        "suggested_mutation_type": "activate_or_strengthen_temporal_rule",
        "rule": "Convert elapsed time and units exactly according to the service descriptor before writing numeric literals.",
    },
    "gt_receiver_coverage": {
        "failure_type": "owner_device_mismatch",
        "affected_block_family": "Owner_Device_Rule",
        "prompt_block_id": "02",
        "suggested_mutation_type": "strengthen_owner_device_rule",
        "rule": "Preserve every command-implied owner, location, and device tag; do not drop non-service selector tags.",
    },
    "dataflow": {
        "failure_type": "dataflow_error",
        "affected_block_family": "Dataflow",
        "prompt_block_id": "06",
        "suggested_mutation_type": "add_sensor_to_action_flow_rule",
        "rule": "When a sensor/value is read for reporting or control, bind it to a variable and use that variable in the downstream action.",
    },
    "gt_service_coverage": {
        "failure_type": "schema_violation",
        "affected_block_family": "Service_Mapping",
        "prompt_block_id": "02",
        "suggested_mutation_type": "add_schema_grounding_rule",
        "rule": "Include every service family implied by the command, including both sensor reads and actuator actions.",
    },
    "semantic": {
        "failure_type": "semantic_error",
        "affected_block_family": "Skeleton",
        "prompt_block_id": "06",
        "suggested_mutation_type": "strengthen_skeleton_rule",
        "rule": "Choose the smallest JOILang skeleton that matches the command verb, timing, target receiver, and side effect.",
    },
    "extraneous": {
        "failure_type": "schema_violation",
        "affected_block_family": "Output_Schema",
        "prompt_block_id": "03",
        "suggested_mutation_type": "strengthen_minimality_rule",
        "rule": "Remove unrelated actions, duplicate calls, and helper statements not required by the command.",
    },
    "gt_mismatch": {
        "failure_type": "semantic_error",
        "affected_block_family": "DET_Helper",
        "prompt_block_id": "06",
        "suggested_mutation_type": "add_targeted_repair_hint",
        "rule": "If the code is schema-valid but not target-equivalent, repair toward receiver coverage, service coverage, dataflow, numeric, and enum grounding.",
    },
}

# Keep the historical constant name for callers, but source the active mapping
# from the v13-derived prompt-surgery registry.
FEEDBACK_RULES = det_feedback_rules()


def get_core_blocks() -> list[str]:
    return list(CORE_BLOCKS)


def get_optional_blocks() -> list[str]:
    return list(OPTIONAL_BLOCKS)


def normalize_active_blocks(blocks: list[str] | tuple[str, ...] | None) -> list[str]:
    requested = [str(block) for block in (blocks or [])]
    active = list(CORE_BLOCKS)
    for block_id in BLOCK_ORDER:
        if block_id in CORE_BLOCKS:
            continue
        if block_id in requested and block_id not in active:
            active.append(block_id)
    return active


def validate_genome_blocks(genome: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(genome, ensure_ascii=False))
    normalized["blocks"] = normalize_active_blocks(list(normalized.get("blocks") or []))
    normalized.setdefault("block_params", {})
    normalized.setdefault("params", {})
    return normalized


def active_block_summary(genome: dict[str, Any]) -> dict[str, list[str]]:
    active = normalize_active_blocks(list(genome.get("blocks") or []))
    return {
        "core": [block for block in active if block in CORE_BLOCKS],
        "optional": [block for block in active if block in OPTIONAL_BLOCKS],
    }


def split_core_optional_blocks(genome: dict[str, Any]) -> dict[str, list[str]]:
    return active_block_summary(genome)


def format_block_summary(genome: dict[str, Any]) -> str:
    summary = active_block_summary(genome)
    return f"core=[{','.join(summary['core'])}] optional=[{','.join(summary['optional'])}]"


def _base_reason(reason: str) -> str:
    token = str(reason or "").strip()
    if ":" in token:
        token = token.split(":", 1)[0]
    return token or "unknown"


def map_failure_to_block_family(failure_reason: str) -> dict[str, str]:
    return get_prompt_surgery_rule(failure_reason)


def feedback_records_from_rows(
    rows: list[dict[str, Any]],
    *,
    model_key: str,
    genome_id: str,
    generation: int,
    det_profile: str,
) -> list[dict[str, Any]]:
    now = datetime.now().isoformat(timespec="seconds")
    records: list[dict[str, Any]] = []
    for row in rows:
        reasons = row.get("failure_reasons") or []
        if isinstance(reasons, str):
            reasons = [reasons]
        counts = Counter(str(reason) for reason in reasons if str(reason).strip())
        for reason, count in counts.items():
            mapped = map_failure_to_block_family(reason)
            records.append(
                {
                    "row_id": row.get("row_no", ""),
                    "model_key": model_key,
                    "genome_id": genome_id,
                    "generation": generation,
                    "det_profile": det_profile,
                    "failure_type": mapped["failure_type"],
                    "failure_count": count,
                    "affected_block_family": mapped["affected_block_family"],
                    "suggested_mutation_type": mapped["suggested_mutation_type"],
                    "original_failure_reasons": reason,
                    "prompt_block_id": mapped["prompt_block_id"],
                    "timestamp": now,
                }
            )
    return records


def summarize_deterministic_feedback(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter: Counter[tuple[str, str, str, str]] = Counter()
    originals: dict[tuple[str, str, str, str], set[str]] = {}
    for record in records:
        key = (
            str(record.get("failure_type", "")),
            str(record.get("affected_block_family", "")),
            str(record.get("suggested_mutation_type", "")),
            str(record.get("prompt_block_id", "")),
        )
        counter[key] += int(record.get("failure_count") or 1)
        originals.setdefault(key, set()).add(str(record.get("original_failure_reasons", "")))
    rows: list[dict[str, Any]] = []
    for key, count in counter.most_common():
        mapped_rule = next(
            (
                item
                for item in FEEDBACK_RULES.values()
                if item.get("suggested_mutation_type") == key[2]
                and item.get("affected_block_family") == key[1]
                and item.get("prompt_block_id") == key[3]
            ),
            {},
        )
        rows.append(
            {
                "failure_type": key[0],
                "affected_block_family": key[1],
                "suggested_mutation_type": key[2],
                "prompt_block_id": key[3],
                "failure_count": count,
                "original_failure_reasons": "|".join(sorted(originals.get(key, set()))),
                "rule": mapped_rule.get("rule", ""),
                "priority": mapped_rule.get("priority", ""),
            }
        )
    return rows


def suggest_mutation_from_feedback(summary_rows: list[dict[str, Any]]) -> dict[str, str] | None:
    if not summary_rows:
        return None
    top = summary_rows[0]
    mutation_type = str(top.get("suggested_mutation_type", ""))
    for item in FEEDBACK_RULES.values():
        if item["suggested_mutation_type"] == mutation_type:
            return dict(item)
    return {
        "failure_type": str(top.get("failure_type", "")),
        "affected_block_family": str(top.get("affected_block_family", "")),
        "prompt_block_id": str(top.get("prompt_block_id", "06") or "06"),
        "suggested_mutation_type": mutation_type or "add_targeted_repair_hint",
        "rule": "Use the deterministic validator failure summary as a targeted repair hint.",
    }
