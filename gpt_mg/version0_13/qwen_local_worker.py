import json
import sys
from typing import Any, Dict

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


try:
    from transformers import BitsAndBytesConfig
except Exception:
    BitsAndBytesConfig = None


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
        
    # Hugging Face의 자동 할당 기능 (VRAM 부족 시 여러 GPU에 쪼개서 올림)
    if device_name == "auto":
        return "auto"

    # GPU 개수를 파악해서 알아서 할당하는 로직
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        
        if device_name.startswith("cuda:"):
            requested_id = int(device_name.split(":", 1)[1])
            # 요청한 GPU 번호가 실제 존재하는 경우 (예: GPU 2개인데 cuda:1 요청)
            if requested_id < gpu_count:
                return {"": requested_id}
            else:
                # 요청한 GPU가 없는 경우 (예: GPU 1개뿐인데 cuda:1 요청) -> 안전하게 0번으로 폴백!
                print(f"경고: {device_name}이 존재하지 않아 cuda:0으로 자동 전환합니다.", file=sys.stderr)
                return {"": 0}
        
        # 그냥 "cuda"라고만 들어오면 무조건 첫 번째(0번) 사용
        return {"": 0}
        
    # GPU가 아예 없으면 CPU로 자동 전환
    return None


def _extract_first_json_block(text: str) -> str:
    if not isinstance(text, str):
        return ""

    stripped = text.strip()
    if stripped.startswith("```json"):
        stripped = stripped[len("```json"):].strip()
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
                return stripped[start:idx + 1].strip()

    return stripped[start:].strip()


def _read_payload() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise RuntimeError("No payload was provided to qwen_local_worker.py")
    return json.loads(raw)


def main():
    payload = _read_payload()
    local_model_name = payload["local_model_name"]
    local_device = payload.get("local_device", "cuda") # 번호를 빼서 알아서 찾게 만듦
    local_dtype = payload.get("local_dtype", "bf16")
    local_files_only = False #_parse_bool(payload.get("local_files_only"), False)
    local_trust_remote_code = _parse_bool(payload.get("local_trust_remote_code"), False)
    local_load_in_4bit = _parse_bool(payload.get("local_load_in_4bit"), False)
    local_max_new_tokens = int(payload.get("local_max_new_tokens", 256))
    messages = payload.get("messages", [])

    tokenizer = AutoTokenizer.from_pretrained(
        local_model_name,
        trust_remote_code=local_trust_remote_code,
        local_files_only=local_files_only,
    )
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs: Dict[str, Any] = {
        "trust_remote_code": local_trust_remote_code,
        "local_files_only": local_files_only,
    }

    if local_load_in_4bit:
        if BitsAndBytesConfig is None:
            raise RuntimeError(
                "bitsandbytes is not installed, but local_load_in_4bit=true was requested."
            )
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

    prompt_tokens = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_tensors="pt",
    )
    prompt_tokens = prompt_tokens.to(next(model.parameters()).device)

    with torch.no_grad():
        generated = model.generate(
            prompt_tokens,
            max_new_tokens=local_max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    completion_tokens = max(0, generated.shape[-1] - prompt_tokens.shape[-1])
    content = tokenizer.decode(
        generated[0][prompt_tokens.shape[-1]:],
        skip_special_tokens=True,
    ).strip()
    content = _extract_first_json_block(content)

    sys.stdout.write(
        json.dumps(
            {
                "content": content,
                "prompt_tokens": int(prompt_tokens.shape[-1]),
                "completion_tokens": int(completion_tokens),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
