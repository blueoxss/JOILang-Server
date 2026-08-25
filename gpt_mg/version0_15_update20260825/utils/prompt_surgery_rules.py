from __future__ import annotations

from copy import deepcopy
from typing import Any


PROMPT_SURGERY_RULES: list[dict[str, Any]] = [
    {
        "id": "json_only_output",
        "source": "version0_13 response/caution prompts",
        "target_block_family": "Output_Schema",
        "target_block_id": "03",
        "suggested_mutation_type": "strengthen_json_only_rule",
        "priority": 1,
        "micro_rule": "Return exactly one JSON object only; never emit markdown, prose, comments, or code fences.",
    },
    {
        "id": "canonical_service_names",
        "source": "version0_13 service prompt",
        "target_block_family": "Service_Mapping",
        "target_block_id": "02",
        "suggested_mutation_type": "add_canonical_service_name_rule",
        "priority": 1,
        "micro_rule": "Use only canonical service/value names from service_list_snippet; never invent helper methods.",
    },
    {
        "id": "enum_type_grounding",
        "source": "version0_13 service prompt",
        "target_block_family": "Enum_Grounding",
        "target_block_id": "02",
        "suggested_mutation_type": "strengthen_enum_type_rule",
        "priority": 1,
        "micro_rule": "For ENUM arguments, copy an allowed enum value exactly; for numeric arguments, use unquoted numeric literals.",
    },
    {
        "id": "descriptor_unit_grounding",
        "source": "version0_13 service prompt",
        "target_block_family": "Service_Mapping",
        "target_block_id": "02",
        "suggested_mutation_type": "add_schema_grounding_rule",
        "priority": 2,
        "micro_rule": "Read descriptor, return_descriptor, argument_type, and argument_bounds before choosing service names or numeric units.",
    },
    {
        "id": "temporal_elapsed_time",
        "source": "version0_13 temporal prompt",
        "target_block_family": "Temporal_Rule",
        "target_block_id": "06",
        "suggested_mutation_type": "strengthen_temporal_rule",
        "priority": 1,
        "micro_rule": "For delayed or duration-based commands, represent elapsed time with explicit state variables and comparisons.",
    },
    {
        "id": "owner_device_binding",
        "source": "version0_13 service prompt",
        "target_block_family": "Owner_Device_Rule",
        "target_block_id": "02",
        "suggested_mutation_type": "strengthen_owner_device_rule",
        "priority": 2,
        "micro_rule": "Preserve command-implied device, owner, location, and group selector tags in the receiver expression.",
    },
    {
        "id": "anti_hallucination_minimality",
        "source": "version0_13 caution prompt",
        "target_block_family": "Minimality",
        "target_block_id": "03",
        "suggested_mutation_type": "strengthen_no_unrelated_action_rule",
        "priority": 2,
        "micro_rule": "Emit only actions required by the command; remove unrelated reads, duplicate actions, and invented wrappers.",
    },
    {
        "id": "sensor_to_action_dataflow",
        "source": "version0_13 response prompt",
        "target_block_family": "Dataflow",
        "target_block_id": "06",
        "suggested_mutation_type": "add_sensor_to_action_flow_rule",
        "priority": 1,
        "micro_rule": "When reading a value for reporting or control, bind it to a variable and use that variable in the downstream action.",
    },
    {
        "id": "service_mapping_disambiguation",
        "source": "version0_13 service prompt",
        "target_block_family": "Service_Mapping",
        "target_block_id": "02",
        "suggested_mutation_type": "add_schema_grounding_rule",
        "priority": 2,
        "micro_rule": "Choose function services for commands that set/change/query with parameters; use value services only for state reads.",
    },
]


DET_FEEDBACK_RULES: dict[str, dict[str, Any]] = {
    "invalid_json": {
        "failure_type": "invalid_json",
        "affected_block_family": "Output_Schema",
        "prompt_block_id": "03",
        "suggested_mutation_type": "strengthen_json_only_rule",
        "rule": PROMPT_SURGERY_RULES[0]["micro_rule"],
        "priority": 1,
    },
    "schema_missing_keys": {
        "failure_type": "schema_violation",
        "affected_block_family": "Output_Schema",
        "prompt_block_id": "03",
        "suggested_mutation_type": "add_schema_grounding_rule",
        "rule": "Always include exactly the required keys: name, cron, period, and code.",
        "priority": 1,
    },
    "schema_violation": {
        "failure_type": "schema_violation",
        "affected_block_family": "Service_Mapping",
        "prompt_block_id": "02",
        "suggested_mutation_type": "add_schema_grounding_rule",
        "rule": PROMPT_SURGERY_RULES[3]["micro_rule"],
        "priority": 1,
    },
    "unknown_service": {
        "failure_type": "unknown_service",
        "affected_block_family": "Service_Mapping",
        "prompt_block_id": "02",
        "suggested_mutation_type": "add_canonical_service_name_rule",
        "rule": PROMPT_SURGERY_RULES[1]["micro_rule"],
        "priority": 1,
    },
    "service_match": {
        "failure_type": "schema_violation",
        "affected_block_family": "Service_Mapping",
        "prompt_block_id": "02",
        "suggested_mutation_type": "add_schema_grounding_rule",
        "rule": "Do not invent service/value names; choose only functions and values present in service_list_snippet.",
        "priority": 1,
    },
    "gt_service_coverage": {
        "failure_type": "schema_violation",
        "affected_block_family": "Service_Mapping",
        "prompt_block_id": "02",
        "suggested_mutation_type": "add_schema_grounding_rule",
        "rule": "Include every service family implied by the command, including both sensor reads and actuator actions.",
        "priority": 2,
    },
    "arg_type": {
        "failure_type": "enum_type_mismatch",
        "affected_block_family": "Enum_Grounding",
        "prompt_block_id": "02",
        "suggested_mutation_type": "strengthen_enum_type_rule",
        "rule": PROMPT_SURGERY_RULES[2]["micro_rule"],
        "priority": 1,
    },
    "enum_grounding": {
        "failure_type": "enum_type_mismatch",
        "affected_block_family": "Enum_Grounding",
        "prompt_block_id": "02",
        "suggested_mutation_type": "strengthen_enum_type_rule",
        "rule": "For ENUM arguments, copy one allowed enum value exactly from the selected service descriptor.",
        "priority": 1,
    },
    "enum_type_mismatch": {
        "failure_type": "enum_type_mismatch",
        "affected_block_family": "Enum_Grounding",
        "prompt_block_id": "02",
        "suggested_mutation_type": "strengthen_enum_type_rule",
        "rule": PROMPT_SURGERY_RULES[2]["micro_rule"],
        "priority": 1,
    },
    "numeric_grounding": {
        "failure_type": "temporal_error",
        "affected_block_family": "Temporal_Rule",
        "prompt_block_id": "06",
        "suggested_mutation_type": "strengthen_temporal_rule",
        "rule": "Convert elapsed time and units exactly according to the service descriptor before writing numeric literals.",
        "priority": 2,
    },
    "temporal_error": {
        "failure_type": "temporal_error",
        "affected_block_family": "Temporal_Rule",
        "prompt_block_id": "06",
        "suggested_mutation_type": "strengthen_temporal_rule",
        "rule": PROMPT_SURGERY_RULES[4]["micro_rule"],
        "priority": 1,
    },
    "gt_receiver_coverage": {
        "failure_type": "owner_device_mismatch",
        "affected_block_family": "Owner_Device_Rule",
        "prompt_block_id": "02",
        "suggested_mutation_type": "strengthen_owner_device_rule",
        "rule": PROMPT_SURGERY_RULES[5]["micro_rule"],
        "priority": 2,
    },
    "owner_device_mismatch": {
        "failure_type": "owner_device_mismatch",
        "affected_block_family": "Owner_Device_Rule",
        "prompt_block_id": "02",
        "suggested_mutation_type": "strengthen_owner_device_rule",
        "rule": PROMPT_SURGERY_RULES[5]["micro_rule"],
        "priority": 2,
    },
    "dataflow": {
        "failure_type": "dataflow_error",
        "affected_block_family": "Dataflow",
        "prompt_block_id": "06",
        "suggested_mutation_type": "add_sensor_to_action_flow_rule",
        "rule": PROMPT_SURGERY_RULES[7]["micro_rule"],
        "priority": 1,
    },
    "dataflow_error": {
        "failure_type": "dataflow_error",
        "affected_block_family": "Dataflow",
        "prompt_block_id": "06",
        "suggested_mutation_type": "add_sensor_to_action_flow_rule",
        "rule": PROMPT_SURGERY_RULES[7]["micro_rule"],
        "priority": 1,
    },
    "extraneous": {
        "failure_type": "extraneous_action",
        "affected_block_family": "Minimality",
        "prompt_block_id": "03",
        "suggested_mutation_type": "strengthen_no_unrelated_action_rule",
        "rule": PROMPT_SURGERY_RULES[6]["micro_rule"],
        "priority": 2,
    },
    "extraneous_action": {
        "failure_type": "extraneous_action",
        "affected_block_family": "Minimality",
        "prompt_block_id": "03",
        "suggested_mutation_type": "strengthen_no_unrelated_action_rule",
        "rule": PROMPT_SURGERY_RULES[6]["micro_rule"],
        "priority": 2,
    },
    "semantic": {
        "failure_type": "semantic_error",
        "affected_block_family": "Skeleton",
        "prompt_block_id": "06",
        "suggested_mutation_type": "strengthen_skeleton_rule",
        "rule": "Choose the smallest JOILang skeleton that matches the command verb, timing, target receiver, and side effect.",
        "priority": 3,
    },
    "gt_mismatch": {
        "failure_type": "semantic_error",
        "affected_block_family": "DET_Helper",
        "prompt_block_id": "06",
        "suggested_mutation_type": "add_targeted_repair_hint",
        "rule": "If code is schema-valid but not target-equivalent, repair receiver coverage, service coverage, dataflow, numeric, and enum grounding.",
        "priority": 3,
    },
}


def base_failure_reason(reason: str) -> str:
    token = str(reason or "").strip()
    if ":" in token:
        token = token.split(":", 1)[0]
    return token or "unknown"


def det_feedback_rules() -> dict[str, dict[str, Any]]:
    return deepcopy(DET_FEEDBACK_RULES)


def prompt_surgery_registry() -> list[dict[str, Any]]:
    return deepcopy(PROMPT_SURGERY_RULES)


def get_prompt_surgery_rule(failure_reason: str) -> dict[str, Any]:
    base = base_failure_reason(failure_reason)
    rule = DET_FEEDBACK_RULES.get(base)
    if rule is None:
        rule = {
            "failure_type": base,
            "affected_block_family": "DET_Helper",
            "prompt_block_id": "06",
            "suggested_mutation_type": "add_targeted_repair_hint",
            "rule": "Use deterministic validation feedback to repair the exact failed DET axis without changing retrieval context.",
            "priority": 5,
        }
    return {"original_failure_reason": str(failure_reason), **deepcopy(rule)}
