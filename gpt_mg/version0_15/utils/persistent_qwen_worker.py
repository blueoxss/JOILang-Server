#!/usr/bin/env python3
# Assumption: this long-lived worker is used only by gpt_mg/version0_14 and keeps a local Qwen model loaded across multiple JSON-line requests.
from __future__ import annotations

import json
import os
import sys
import traceback
from typing import Any

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

import torch
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
    )


def _load_runtime(payload: dict[str, Any]):
    local_model_name = payload["local_model_name"]
    local_device = payload.get("local_device", "cuda")
    local_dtype = payload.get("local_dtype", "bf16")
    local_files_only = _parse_bool(payload.get("local_files_only"), False)
    local_trust_remote_code = _parse_bool(payload.get("local_trust_remote_code"), False)
    local_load_in_4bit = _parse_bool(payload.get("local_load_in_4bit"), False)

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

    model = AutoModelForCausalLM.from_pretrained(local_model_name, **model_kwargs)
    model.eval()
    return tokenizer, model


def _generate(tokenizer, model, payload: dict[str, Any]) -> dict[str, Any]:
    messages = payload.get("messages", [])
    local_max_new_tokens = int(payload.get("local_max_new_tokens", 256))
    prompt_tokens = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_tensors="pt",
    )
    device = next(model.parameters()).device
    prompt_tokens = prompt_tokens.to(device)
    with torch.no_grad():
        generated = model.generate(
            prompt_tokens,
            max_new_tokens=local_max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    completion_tokens = max(0, generated.shape[-1] - prompt_tokens.shape[-1])
    content = tokenizer.decode(generated[0][prompt_tokens.shape[-1] :], skip_special_tokens=True).strip()
    content = _extract_first_json_block(content)
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return {
        "ok": True,
        "content": content,
        "prompt_tokens": int(prompt_tokens.shape[-1]),
        "completion_tokens": int(completion_tokens),
    }


def main() -> None:
    tokenizer = None
    model = None
    signature: tuple[str, ...] | None = None
    for raw_line in sys.stdin:
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
        except Exception as exc:
            _write_response({"ok": False, "error": f"invalid request json: {exc}"})
            continue
        if payload.get("_command") == "shutdown":
            break
        try:
            next_signature = _runtime_signature(payload)
            if model is None or tokenizer is None or signature != next_signature:
                tokenizer, model = _load_runtime(payload)
                signature = next_signature
            _write_response(_generate(tokenizer, model, payload))
        except Exception as exc:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            _write_response(
                {
                    "ok": False,
                    "error": str(exc),
                    "traceback": traceback.format_exc(limit=8),
                }
            )


if __name__ == "__main__":
    main()
