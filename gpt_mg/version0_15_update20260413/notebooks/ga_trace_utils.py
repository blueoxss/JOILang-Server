import os
import json
import random
import hashlib
from pathlib import Path

def get_block_registry(version_root):
    # Simulated registry if the real one isn't imported
    return {
        "CORE_BLOCKS": ["01", "02"],
        "OPTIONAL_BLOCKS": ["03", "05", "06"],
        "BLOCK_ORDER": ["01", "02", "03", "04", "05", "06"],
        "BLOCK_FILE_MAP": {
            "01": "system_role.txt",
            "02": "service_mapping.txt",
            "03": "output_schema.txt",
            "04": "reranker_asset.txt", # Example of asset not in GA optional space
            "05": "few_shot.txt",
            "06": "temporal_rule.txt"
        },
        "BLOCK_FAMILIES": {
            "01": "Constraint",
            "02": "Adaptive",
            "03": "Constraint",
            "04": "RAG",
            "05": "Conditional",
            "06": "Constraint"
        }
    }

def load_prompt_block(version_root, filename):
    file_path = Path(version_root) / "prompts" / "blocks" / filename
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return f"[{filename} mock content]\n" + ("x " * 50)

def get_token_count(text):
    return max(1, len(text) // 4)

def load_dataset_row(version_root, row_no):
    return {
        "row_no": row_no,
        "category": 1,
        "command_eng": "Turn on the living room light.",
        "command_kor": "거실 불 켜줘.",
        "connected_devices": ["living_room_light"],
        "available_GT_fields": ["service", "target", "action"]
    }

def get_service_context():
    return {
        "mode": "hybrid",
        "uses_connected_devices": True,
        "uses_retrieval_fallback": False,
        "uses_schema_fallback": True,
        "service_list_snippet_source": "connected_devices + default_schema",
        "service_list_snippet_chars": 250
    }

def render_legacy_prompt(row_data, service_context):
    prompt = "Legacy Monolith Prompt Header\n"
    prompt += str(row_data) + "\n" + (str(service_context) * 5)
    return prompt

def render_blocks_prompt(genome, row_data, service_context):
    active = genome.get("core_blocks", []) + genome.get("optional_blocks", [])
    prompt = f"Blocks Rendered Prompt\nActive Blocks: {','.join(active)}\n"
    prompt += f"Micro-rules: {genome.get('micro_rules', [])}\n"
    prompt += str(row_data) + "\n" + (str(service_context) * 2)
    return prompt

def generate_gen1_population():
    return [
        {"genome_id": "gen1_0", "core_blocks": ["01", "02"], "optional_blocks": ["03"], "block_params": {}, "few_shot_count": 0, "max_tokens": 1024, "micro_rules": []},
        {"genome_id": "gen1_1", "core_blocks": ["01", "02"], "optional_blocks": ["03", "05"], "block_params": {}, "few_shot_count": 2, "max_tokens": 1024, "micro_rules": []},
        {"genome_id": "gen1_2", "core_blocks": ["01", "02"], "optional_blocks": ["03", "06"], "block_params": {}, "few_shot_count": 0, "max_tokens": 2048, "micro_rules": []},
        {"genome_id": "gen1_3", "core_blocks": ["01", "02"], "optional_blocks": ["03", "05", "06"], "block_params": {}, "few_shot_count": 4, "max_tokens": 2048, "micro_rules": []}
    ]

def evaluate_genome(genome, use_mock_llm):
    det = random.choice([0.0, 0.5, 1.0])
    is_pass = det == 1.0
    failure_reasons = []
    error_type = "none"
    if not is_pass:
        error_type = random.choice(["invalid_json", "unknown_service", "temporal_error", "owner_device_mismatch", "worker_crash", "empty_output"])
        failure_reasons.append(error_type)
    return {
        "genome_id": genome["genome_id"],
        "DET": det,
        "pass": is_pass,
        "failure_reasons": failure_reasons,
        "generation_error_type": error_type,
        "latency": random.uniform(0.5, 3.0) if use_mock_llm else 2.5
    }

def analyze_deterministic_feedback(eval_results):
    feedback = []
    for res in eval_results:
        for reason in res["failure_reasons"]:
            if reason == "invalid_json":
                feedback.append({"failure_reason": reason, "target_block_id": "03", "affected_block_family": "Constraint", "suggested_mutation_type": "strengthen_json_only_rule", "micro_rule": "Ensure output is ONLY valid JSON."})
            elif reason == "unknown_service":
                feedback.append({"failure_reason": reason, "target_block_id": "02", "affected_block_family": "Adaptive", "suggested_mutation_type": "add_canonical_service_name_rule", "micro_rule": "Map strictly to canonical service names."})
            elif reason == "temporal_error":
                feedback.append({"failure_reason": reason, "target_block_id": "06", "affected_block_family": "Constraint", "suggested_mutation_type": "clarify_temporal_logic", "micro_rule": "Use explicit date-time formats."})
            elif reason in ["worker_crash", "empty_output"]:
                feedback.append({"failure_reason": reason, "target_block_id": "all", "affected_block_family": "System", "suggested_mutation_type": "compress_prompt", "micro_rule": ""})
            else:
                feedback.append({"failure_reason": reason, "target_block_id": "02", "affected_block_family": "Adaptive", "suggested_mutation_type": "add_repair_rule", "micro_rule": "Fix " + reason})
    return feedback

def generate_gen2_children(gen1_population, feedback_summary, simulate_oom=False, use_advisor=False):
    children = []
    # 1. Mutation
    child1 = dict(gen1_population[0])
    child1.update({"genome_id": "gen2_0_mut", "parent_ids": [gen1_population[0]["genome_id"]], "origin": "mutation"})
    child1["block_params"] = {"03": {"mutated_schema": True}}
    children.append(child1)
    
    # 2. Crossover
    child2 = dict(gen1_population[1])
    child2.update({"genome_id": "gen2_1_cross", "parent_ids": [gen1_population[1]["genome_id"], gen1_population[2]["genome_id"]], "origin": "crossover"})
    child2["optional_blocks"] = list(set(gen1_population[1]["optional_blocks"] + gen1_population[2]["optional_blocks"]))
    children.append(child2)

    # 3. Feedback Guided
    child3 = dict(gen1_population[2])
    child3.update({"genome_id": "gen2_2_feedback", "parent_ids": [gen1_population[2]["genome_id"]], "origin": "feedback_guided"})
    if feedback_summary: child3["micro_rules"] = [feedback_summary[0]["micro_rule"]]
    children.append(child3)

    # 4. OOM / Token Compression
    if simulate_oom:
        child4 = dict(gen1_population[3])
        if "05" in child4["optional_blocks"]: child4["optional_blocks"].remove("05")
        child4.update({"genome_id": "gen2_3_compress", "parent_ids": [gen1_population[3]["genome_id"]], "origin": "oom_compression", "few_shot_count": max(0, child4["few_shot_count"]-2)})
        children.append(child4)
        
    return children

def mock_advisor_call():
    return {
        "status": "success",
        "proposals": [
            {"proposal_id": "adv_1", "target_block": "03", "mutation_type": "add_schema_guard", "proposed_micro_rule": "Double check schema brackets.", "accepted": True},
            {"proposal_id": "adv_2", "target_block": "02", "mutation_type": "rewrite_service", "proposed_micro_rule": "Be more verbose.", "accepted": False}
        ]
    }