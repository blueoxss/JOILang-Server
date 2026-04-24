import copy
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from ..version0_13.qwen_local_backend import ensure_version013_backend_installed
except ImportError:
    try:
        from gpt_mg.version0_13.qwen_local_backend import ensure_version013_backend_installed
    except ImportError:
        from version0_13.qwen_local_backend import ensure_version013_backend_installed

try:
    from .utils.pipeline_common import (
        SERVICE_SCHEMA_DEFAULT,
        build_prompt_values,
        load_genome,
        load_service_schema,
        render_blocks_for_genome,
    )
except ImportError:
    try:
        from gpt_mg.version0_15.utils.pipeline_common import (
            SERVICE_SCHEMA_DEFAULT,
            build_prompt_values,
            load_genome,
            load_service_schema,
            render_blocks_for_genome,
        )
    except ImportError:
        from version0_15.utils.pipeline_common import (
            SERVICE_SCHEMA_DEFAULT,
            build_prompt_values,
            load_genome,
            load_service_schema,
            render_blocks_for_genome,
        )


VERSION_ROOT = Path(__file__).resolve().parent
VERSION_TAG = VERSION_ROOT.name
DEFAULT_GENOME_CANDIDATES = (
    VERSION_ROOT / "results" / "best_genome_after_feedback.json",
    VERSION_ROOT / "results" / "best_genome_from_ga.json",
    VERSION_ROOT / "results" / "best_genome.json",
    VERSION_ROOT / "results" / "category_sweep_20260331_082722" / "final_best_genome.json",
    VERSION_ROOT / "genomes" / "example_genome.json",
)


def _default_local_python() -> str:
    env_python = os.getenv("JOI_VERSION015_PYTHON", "").strip() or os.getenv("JOI_VERSION014_PYTHON", "").strip()
    if env_python:
        return env_python
    return sys.executable or "python"


def _default_local_worker() -> str:
    env_worker = os.getenv("JOI_VERSION015_WORKER", "").strip() or os.getenv("JOI_VERSION014_WORKER", "").strip()
    if env_worker:
        return env_worker
    return str(VERSION_ROOT.parent / "version0_13" / "qwen_local_worker.py")


def _extract_other_param(other_params: Any, key: str, default: Any = None) -> Any:
    if isinstance(other_params, dict):
        return other_params.get(key, default)
    if isinstance(other_params, list):
        for item in other_params:
            if isinstance(item, dict) and key in item:
                return item[key]
    return default


def _resolve_genome_path(other_params: Any) -> Path:
    explicit = _extract_other_param(other_params, "genome_json")
    if explicit:
        candidate = Path(str(explicit))
        if not candidate.is_absolute():
            candidate = (VERSION_ROOT / str(explicit)).resolve()
        if candidate.exists():
            return candidate

    env_candidate = os.getenv("JOI_VERSION015_GENOME", "").strip() or os.getenv("JOI_VERSION014_GENOME", "").strip()
    if env_candidate:
        candidate = Path(env_candidate)
        if not candidate.is_absolute():
            candidate = (VERSION_ROOT / env_candidate).resolve()
        if candidate.exists():
            return candidate

    for candidate in DEFAULT_GENOME_CANDIDATES:
        if candidate.exists():
            return candidate

    return DEFAULT_GENOME_CANDIDATES[-1]


def _candidate_strategy(genome: dict[str, Any], other_params: Any) -> str:
    explicit = _extract_other_param(other_params, "candidate_strategy")
    if explicit:
        return str(explicit)
    strategies = genome.get("params", {}).get("candidate_strategies") or ["direct"]
    return str(strategies[0])


def _temperature(genome: dict[str, Any], model_input: dict[str, Any], other_params: Any) -> float:
    explicit = _extract_other_param(other_params, "temperature")
    if explicit is not None:
        try:
            return float(explicit)
        except Exception:
            pass
    block_02 = genome.get("block_params", {}).get("02", {})
    if "temperature" in block_02:
        return float(block_02["temperature"])
    if "temperature" in genome.get("params", {}):
        return float(genome["params"]["temperature"])
    return float(model_input.get("temperature", 0.0))


def _max_tokens(genome: dict[str, Any], model_input: dict[str, Any], other_params: Any) -> int:
    explicit = _extract_other_param(other_params, "max_tokens")
    if explicit is not None:
        try:
            return int(explicit)
        except Exception:
            pass
    block_02 = genome.get("block_params", {}).get("02", {})
    if "max_tokens" in block_02:
        return int(block_02["max_tokens"])
    if "max_tokens" in genome.get("params", {}):
        return int(genome["params"]["max_tokens"])
    return int(model_input.get("local_max_new_tokens", 512))


def _service_context_kwargs(other_params: Any) -> dict[str, Any]:
    def _truthy(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}

    service_context_mode = _extract_other_param(other_params, "service_context_mode")
    if service_context_mode is None:
        if _truthy(_extract_other_param(other_params, "enable_retrieval_premapping")):
            service_context_mode = "retrieval_fallback"
        elif _truthy(_extract_other_param(other_params, "disable_retrieval_premapping")):
            service_context_mode = "schema_fallback"
    return {
        "service_context_mode": service_context_mode,
        "retrieval_topk": _extract_other_param(other_params, "retrieval_topk"),
        "retrieval_mode": _extract_other_param(other_params, "retrieval_mode"),
        "retrieval_json_path": _extract_other_param(other_params, "retrieval_json"),
        "retrieval_bundle_dir": _extract_other_param(other_params, "retrieval_bundle_dir"),
        "retrieval_model_dir": _extract_other_param(other_params, "retrieval_model_dir"),
        "retrieval_device": _extract_other_param(other_params, "retrieval_device"),
    }


def _system_prompt() -> str:
    return (
        "You are a deterministic JOILang generation engine. "
        "The natural-language command may be written in English or Korean. "
        "If it is Korean, translate it internally to the closest intent-preserving English meaning before reasoning. "
        "Follow the user instructions exactly and return only the requested JSON object."
    )


def load_version_config(user_input, connected_devices: dict = None, other_params: dict = None, base_path: str = "."):
    connected_devices = connected_devices or {}
    print(f"[{VERSION_TAG}] connected_devices:\n" + json.dumps(connected_devices, ensure_ascii=False, indent=2, sort_keys=True))
    ensure_version013_backend_installed()

    base_dir = VERSION_ROOT
    with open(base_dir / "model_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    model_input = copy.deepcopy(config["model_input"])
    model_input["local_python"] = _default_local_python()
    model_input["local_worker"] = _default_local_worker()

    genome_path = _resolve_genome_path(other_params)
    genome = load_genome(genome_path)

    service_schema_path = _extract_other_param(other_params, "service_schema")
    if service_schema_path:
        service_schema = load_service_schema(service_schema_path)
    else:
        service_schema = load_service_schema(SERVICE_SCHEMA_DEFAULT)

    row = {
        "command_eng": str(user_input or ""),
        "connected_devices": json.dumps(connected_devices, ensure_ascii=False),
        "cron": str(_extract_other_param(other_params, "cron", "") or ""),
        "period": str(_extract_other_param(other_params, "period", 0) or 0),
    }
    values = build_prompt_values(
        0,
        row,
        service_schema,
        candidate_strategy=_candidate_strategy(genome, other_params),
        **_service_context_kwargs(other_params),
    )
    rendered_prompt, manifest = render_blocks_for_genome(genome, values=values)
    language_bridge = (
        "Language handling rule:\n"
        "- The command may be English or Korean.\n"
        "- If it is Korean, translate it internally to the closest English command intent first.\n"
        "- Do not output the translation. Output only the final JOI JSON object.\n"
    )
    user_prompt = language_bridge + "\n" + rendered_prompt.rstrip() + "\n\nReturn the final JSON object now."

    model_input["temperature"] = _temperature(genome, model_input, other_params)
    model_input["local_max_new_tokens"] = _max_tokens(genome, model_input, other_params)
    model_input["messages"] = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": user_prompt},
    ]

    config["resolved_genome_json"] = str(genome_path)
    config["resolved_block_manifest"] = manifest

    today_str = datetime.now().strftime("%y%m%d")
    debug_path = base_dir / f"merged_system_prompt_{today_str}.md"
    debug_lines = [
        f"# {VERSION_TAG} external prompt",
        f"- genome_json: {genome_path}",
        f"- temperature: {model_input['temperature']}",
        f"- local_max_new_tokens: {model_input['local_max_new_tokens']}",
        f"- service_list_snippet_source: {values.get('service_list_snippet_source', '')}",
        f"- service_list_device_count: {values.get('service_list_device_count', '')}",
        f"- service_list_retrieval_status: {values.get('service_list_retrieval_status', '')}",
        f"- service_list_retrieval_categories: {values.get('service_list_retrieval_categories', '')}",
        "",
        "## System",
        _system_prompt(),
        "",
        "## User",
        user_prompt,
    ]
    debug_path.write_text("\n".join(debug_lines) + "\n", encoding="utf-8")

    return config, model_input
