#!/usr/bin/env python3
# Assumption: this long-lived worker is used only by gpt_mg/version0_14 and keeps a local Qwen model loaded across multiple JSON-line requests.
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_MODULES_CACHE", os.getenv("JOI_V15_HF_MODULES_CACHE", "/tmp/joi_v15_hf_modules"))
Path(os.environ["HF_MODULES_CACHE"]).mkdir(parents=True, exist_ok=True)

import torch
from transformers.cache_utils import DynamicCache
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.utils import logging as hf_logging


try:
    from transformers import BitsAndBytesConfig
except Exception:
    BitsAndBytesConfig = None


hf_logging.set_verbosity_error()


def _write_response(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _parse_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _ensure_dynamic_cache_compat() -> None:
    if hasattr(DynamicCache, "seen_tokens"):
        pass
    else:
        def _seen_tokens(self):
            try:
                return int(self.get_seq_length())
            except Exception:
                return 0

        DynamicCache.seen_tokens = property(_seen_tokens)

    if not hasattr(DynamicCache, "get_max_length"):
        def _get_max_length(self):
            return None

        DynamicCache.get_max_length = _get_max_length

    if not hasattr(DynamicCache, "get_usable_length"):
        def _get_usable_length(self, new_seq_length=0, layer_idx=0):
            try:
                previous_seq_length = int(self.get_seq_length())
            except Exception:
                previous_seq_length = 0
            try:
                max_length = self.get_max_length()
            except Exception:
                max_length = None
            if max_length is not None and previous_seq_length + int(new_seq_length or 0) > int(max_length):
                return max(int(max_length) - int(new_seq_length or 0), 0)
            return previous_seq_length

        DynamicCache.get_usable_length = _get_usable_length


def _resolve_dtype(dtype_name: str):
    normalized = (dtype_name or "bf16").strip().lower()
    if normalized == "bf16":
        return torch.bfloat16
    if normalized == "fp16":
        return torch.float16
    if normalized == "fp32":
        return torch.float32
    raise ValueError(f"Unsupported local_dtype: {dtype_name}")


def _resolve_device_map(local_device: str):
    device_name = (local_device or "cuda").strip().lower()
    if device_name == "cpu":
        return None
    if device_name == "auto":
        return "auto"
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        if device_name.startswith("cuda:"):
            requested_id = int(device_name.split(":", 1)[1])
            if requested_id < gpu_count:
                return {"": requested_id}
            print(f"warning: {device_name} not available, falling back to cuda:0", file=sys.stderr)
            return {"": 0}
        return {"": 0}
    return None


def _classify_exception(exc: Exception) -> str:
    lowered = str(exc or "").strip().lower()
    if "out of memory" in lowered or "cuda out of memory" in lowered or "cuda oom" in lowered:
        return "cuda_oom"
    if "gatedrepoerror" in lowered or "gated repo" in lowered or "access to model" in lowered:
        return "gated_model"
    if "local_files_only" in lowered or "not cached locally" in lowered:
        return "missing_cache"
    if "timed out" in lowered or "timeout" in lowered:
        return "cpu_fallback_timeout"
    if "json" in lowered:
        return "invalid_json"
    if "no module named" in lowered or "unsupported local_dtype" in lowered:
        return "incompatible_runtime"
    return "worker_crash"


def _maybe_sync_cuda() -> None:
    if torch.cuda.is_available():
        try:
            torch.cuda.synchronize()
        except Exception:
            pass


def _reset_cuda_peak_stats() -> None:
    if not torch.cuda.is_available():
        return
    for index in range(torch.cuda.device_count()):
        try:
            torch.cuda.reset_peak_memory_stats(index)
        except Exception:
            try:
                with torch.cuda.device(index):
                    torch.cuda.reset_peak_memory_stats()
            except Exception:
                continue


def _cuda_peak_stats() -> dict[str, Any]:
    if not torch.cuda.is_available():
        return {
            "peak_vram_bytes": 0,
            "peak_vram_gb": 0.0,
            "peak_vram_by_device": {},
        }
    peak_by_device: dict[str, int] = {}
    peak_bytes = 0
    for index in range(torch.cuda.device_count()):
        try:
            device_peak = int(torch.cuda.max_memory_allocated(index))
        except Exception:
            device_peak = 0
        peak_by_device[str(index)] = device_peak
        peak_bytes = max(peak_bytes, device_peak)
    return {
        "peak_vram_bytes": peak_bytes,
        "peak_vram_gb": round(float(peak_bytes) / (1024**3), 4),
        "peak_vram_by_device": peak_by_device,
    }


def _extract_first_json_block(text: str) -> str:
    if not isinstance(text, str):
        return ""
    stripped = text.strip()
    if stripped.startswith("```json"):
        stripped = stripped[len("```json") :].strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
    elif stripped.startswith("```"):
        stripped = stripped[3:].strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
    start = stripped.find("{")
    if start == -1:
        return stripped
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(stripped)):
        ch = stripped[idx]
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
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : idx + 1].strip()
    return stripped[start:].strip()


def _runtime_signature(payload: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(payload.get("local_model_name", "")),
        str(payload.get("local_device", "")),
        str(payload.get("local_dtype", "")),
        str(payload.get("local_files_only", "")),
        str(payload.get("local_trust_remote_code", "")),
        str(payload.get("local_load_in_4bit", "")),
        str(payload.get("local_attn_implementation", "")),
    )


def _load_runtime(payload: dict[str, Any]):
    load_started = time.perf_counter()
    hf_modules_cache = str(payload.get("local_hf_modules_cache") or os.environ.get("HF_MODULES_CACHE") or "/tmp/joi_v15_hf_modules")
    os.environ["HF_MODULES_CACHE"] = hf_modules_cache
    Path(hf_modules_cache).mkdir(parents=True, exist_ok=True)
    _ensure_dynamic_cache_compat()
    local_model_name = payload["local_model_name"]
    local_device = payload.get("local_device", "cuda")
    local_dtype = payload.get("local_dtype", "bf16")
    local_files_only = _parse_bool(payload.get("local_files_only"), False)
    local_trust_remote_code = _parse_bool(payload.get("local_trust_remote_code"), False)
    local_load_in_4bit = _parse_bool(payload.get("local_load_in_4bit"), False)
    local_attn_implementation = str(payload.get("local_attn_implementation", "") or "").strip()

    tokenizer = AutoTokenizer.from_pretrained(
        local_model_name,
        trust_remote_code=local_trust_remote_code,
        local_files_only=local_files_only,
    )
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs: dict[str, Any] = {
        "trust_remote_code": local_trust_remote_code,
        "local_files_only": local_files_only,
    }
    if local_attn_implementation:
        model_kwargs["attn_implementation"] = local_attn_implementation
    if local_load_in_4bit:
        if BitsAndBytesConfig is None:
            raise RuntimeError("bitsandbytes is not installed, but local_load_in_4bit=true was requested.")
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=_resolve_dtype(local_dtype),
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        model_kwargs["device_map"] = _resolve_device_map(local_device)
    else:
        model_kwargs["torch_dtype"] = _resolve_dtype(local_dtype)
        if local_device != "cpu":
            model_kwargs["device_map"] = _resolve_device_map(local_device)

    _reset_cuda_peak_stats()
    model = AutoModelForCausalLM.from_pretrained(local_model_name, **model_kwargs)
    model.eval()
    _maybe_sync_cuda()
    load_metrics = {
        "load_sec": round(time.perf_counter() - load_started, 4),
    }
    load_metrics.update(
        {
            "load_peak_vram_bytes": _cuda_peak_stats().get("peak_vram_bytes", 0),
            "load_peak_vram_gb": _cuda_peak_stats().get("peak_vram_gb", 0.0),
        }
    )
    _reset_cuda_peak_stats()
    return tokenizer, model, load_metrics


def _generate(tokenizer, model, payload: dict[str, Any], *, load_metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    request_started = time.perf_counter()
    messages = payload.get("messages", [])
    local_max_new_tokens = int(payload.get("local_max_new_tokens", 256))
    _reset_cuda_peak_stats()
    prompt_started = time.perf_counter()
    prompt_tokens = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_tensors="pt",
    )
    device = next(model.parameters()).device
    prompt_tokens = prompt_tokens.to(device)
    _maybe_sync_cuda()
    prompt_prep_sec = round(time.perf_counter() - prompt_started, 4)
    generation_started = time.perf_counter()
    with torch.no_grad():
        generated = model.generate(
            prompt_tokens,
            max_new_tokens=local_max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    _maybe_sync_cuda()
    generate_sec = round(time.perf_counter() - generation_started, 4)
    decode_started = time.perf_counter()
    completion_tokens = max(0, generated.shape[-1] - prompt_tokens.shape[-1])
    content = tokenizer.decode(generated[0][prompt_tokens.shape[-1] :], skip_special_tokens=True).strip()
    _maybe_sync_cuda()
    decode_sec = round(time.perf_counter() - decode_started, 4)
    content = _extract_first_json_block(content)
    vram_stats = _cuda_peak_stats()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    response = {
        "ok": True,
        "content": content,
        "prompt_tokens": int(prompt_tokens.shape[-1]),
        "completion_tokens": int(completion_tokens),
        "prompt_prep_sec": prompt_prep_sec,
        "generate_sec": generate_sec,
        "decode_sec": decode_sec,
        "total_worker_sec": round(time.perf_counter() - request_started, 4),
        "worker_pid": int(os.getpid()),
    }
    response.update(vram_stats)
    if load_metrics:
        response.update(load_metrics)
    return response


def main() -> None:
    tokenizer = None
    model = None
    signature: tuple[str, ...] | None = None
    load_metrics: dict[str, Any] | None = None
    for raw_line in sys.stdin:
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
        except Exception as exc:
            _write_response({"ok": False, "error": f"invalid request json: {exc}", "error_type": "invalid_json"})
            continue
        if payload.get("_command") == "shutdown":
            break
        try:
            next_signature = _runtime_signature(payload)
            if model is None or tokenizer is None or signature != next_signature:
                tokenizer, model, load_metrics = _load_runtime(payload)
                signature = next_signature
            _write_response(_generate(tokenizer, model, payload, load_metrics=load_metrics))
            load_metrics = None
        except Exception as exc:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            _write_response(
                {
                    "ok": False,
                    "error": str(exc),
                    "error_type": _classify_exception(exc),
                    "oom_flag": _classify_exception(exc) == "cuda_oom",
                    "traceback": traceback.format_exc(limit=8),
                }
            )


if __name__ == "__main__":
    main()
