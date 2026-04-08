#!/usr/bin/env python3
# Assumption: by default this client reuses the existing local worker environment from gpt_mg/version0_13 without modifying it.
from __future__ import annotations

import atexit
import json
import os
import select
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from utils.pipeline_common import REPO_ROOT, dump_json


DEFAULT_MODEL = os.getenv("JOI_V14_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct")
DEFAULT_MODE = os.getenv("JOI_V14_LLM_MODE", "worker")
DEFAULT_ENDPOINT = os.getenv("JOI_V14_OPENAI_ENDPOINT", "http://127.0.0.1:8000/v1/chat/completions")
DEFAULT_WORKER = str((REPO_ROOT / "gpt_mg" / "version0_13" / "qwen_local_worker.py").resolve())
DEFAULT_PERSISTENT_WORKER = str((Path(__file__).resolve().parent / "persistent_qwen_worker.py").resolve())
DEFAULT_PYTHON = os.getenv("JOI_V14_PYTHON", sys.executable or "python3")


class LocalLLMError(RuntimeError):
    pass


def _python_has_torch(python_path: str) -> bool:
    if not python_path or not Path(python_path).exists():
        return False
    completed = subprocess.run(
        [python_path, "-c", "import torch; print(torch.__version__)"],
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    return completed.returncode == 0


def _discover_worker_python() -> str:
    explicit = os.getenv("JOI_V14_WORKER_PYTHON", "").strip()
    if explicit:
        return explicit
    candidates = [
        DEFAULT_PYTHON,
        "/home/andrew/llm/v/bin/python",
        "/usr/bin/python3",
    ]
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if _python_has_torch(candidate):
            return candidate
    return DEFAULT_PYTHON


DEFAULT_WORKER_PYTHON = _discover_worker_python()
_PERSISTENT_WORKER_PROCESS: subprocess.Popen[str] | None = None
_PERSISTENT_WORKER_KEY: tuple[str, ...] | None = None


def _local_max_new_tokens(max_tokens: int) -> int:
    configured = os.getenv("JOI_V14_LOCAL_MAX_NEW_TOKENS", "256").strip()
    try:
        configured_value = int(configured)
    except Exception:
        configured_value = 256
    if configured_value <= 0:
        configured_value = int(max_tokens)
    return max(32, min(int(max_tokens), configured_value))


def _use_persistent_worker() -> bool:
    value = os.getenv("JOI_V14_PERSISTENT_WORKER", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _build_worker_payload(
    system: str,
    user: str,
    *,
    model: str,
    max_tokens: int,
    extra_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "local_model_name": os.getenv("JOI_V14_LOCAL_MODEL_NAME", model),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "local_device": os.getenv("JOI_V14_LOCAL_DEVICE", "cuda:1"),
        "local_dtype": os.getenv("JOI_V14_LOCAL_DTYPE", "bf16"),
        "local_max_new_tokens": _local_max_new_tokens(max_tokens),
        "local_files_only": os.getenv("JOI_V14_LOCAL_FILES_ONLY", "true").strip().lower() in {"1", "true", "yes", "on"},
        "local_trust_remote_code": os.getenv("JOI_V14_LOCAL_TRUST_REMOTE_CODE", "false").strip().lower() in {"1", "true", "yes", "on"},
        "local_load_in_4bit": os.getenv("JOI_V14_LOCAL_LOAD_IN_4BIT", "false").strip().lower() in {"1", "true", "yes", "on"},
    }
    if extra_payload:
        payload.update(extra_payload)
    return payload


def _persistent_worker_key(worker_python: str, worker_path: str, payload: dict[str, Any]) -> tuple[str, ...]:
    return (
        worker_python,
        worker_path,
        str(payload.get("local_model_name", "")),
        str(payload.get("local_device", "")),
        str(payload.get("local_dtype", "")),
        str(payload.get("local_files_only", "")),
        str(payload.get("local_trust_remote_code", "")),
        str(payload.get("local_load_in_4bit", "")),
    )


def _close_persistent_worker() -> None:
    global _PERSISTENT_WORKER_PROCESS, _PERSISTENT_WORKER_KEY
    process = _PERSISTENT_WORKER_PROCESS
    _PERSISTENT_WORKER_PROCESS = None
    _PERSISTENT_WORKER_KEY = None
    if process is None:
        return
    try:
        if process.stdin and process.poll() is None:
            process.stdin.write(json.dumps({"_command": "shutdown"}) + "\n")
            process.stdin.flush()
    except Exception:
        pass
    try:
        process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


atexit.register(_close_persistent_worker)


def _ensure_persistent_worker(worker_python: str, worker_path: str, payload: dict[str, Any]) -> subprocess.Popen[str]:
    global _PERSISTENT_WORKER_PROCESS, _PERSISTENT_WORKER_KEY
    key = _persistent_worker_key(worker_python, worker_path, payload)
    process = _PERSISTENT_WORKER_PROCESS
    if process is not None and process.poll() is None and _PERSISTENT_WORKER_KEY == key:
        return process
    _close_persistent_worker()
    process = subprocess.Popen(
        [worker_python, worker_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    if process.stdin is None or process.stdout is None:
        raise LocalLLMError("persistent worker did not expose stdin/stdout pipes")
    _PERSISTENT_WORKER_PROCESS = process
    _PERSISTENT_WORKER_KEY = key
    return process


def _read_persistent_worker_response(process: subprocess.Popen[str], timeout_sec: int) -> dict[str, Any]:
    if process.stdout is None:
        raise LocalLLMError("persistent worker stdout is unavailable")
    ready, _, _ = select.select([process.stdout], [], [], timeout_sec)
    if not ready:
        raise LocalLLMError(f"persistent worker timed out after {timeout_sec} seconds")
    line = process.stdout.readline()
    if not line:
        raise LocalLLMError("persistent worker closed stdout unexpectedly")
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise LocalLLMError(f"persistent worker returned non-JSON output: {line[:500]}") from exc
    if not payload.get("ok", False):
        raise LocalLLMError(str(payload.get("error", "persistent worker failed")))
    return payload


def _request_json(url: str, payload: dict[str, Any], timeout_sec: int) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8"))


def _call_openai_compatible(
    system: str,
    user: str,
    *,
    endpoint: str,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout_sec: int,
    extra_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if extra_payload:
        payload.update(extra_payload)
    response = _request_json(endpoint, payload, timeout_sec)
    try:
        content = response["choices"][0]["message"]["content"]
    except Exception as exc:
        raise LocalLLMError(f"OpenAI-compatible endpoint returned unexpected payload: {response}") from exc
    usage = response.get("usage") or {}
    return {
        "content": content,
        "prompt_tokens": int(usage.get("prompt_tokens", 0)),
        "completion_tokens": int(usage.get("completion_tokens", 0)),
        "total_tokens": int(usage.get("total_tokens", 0)),
        "raw": response,
    }


def _call_worker(
    system: str,
    user: str,
    *,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout_sec: int,
    extra_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = _build_worker_payload(
        system,
        user,
        model=model,
        max_tokens=max_tokens,
        extra_payload=extra_payload,
    )
    worker_python = DEFAULT_WORKER_PYTHON
    worker_path = os.getenv("JOI_V14_WORKER_PATH", DEFAULT_WORKER)
    completed = subprocess.run(
        [worker_python, worker_path],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=timeout_sec,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise LocalLLMError(f"local worker failed with exit code {completed.returncode}: {detail}")
    try:
        worker_result = json.loads((completed.stdout or "").strip())
    except json.JSONDecodeError as exc:
        raise LocalLLMError(f"local worker returned non-JSON output: {(completed.stdout or '')[:500]}") from exc
    return {
        "content": worker_result.get("content", ""),
        "prompt_tokens": int(worker_result.get("prompt_tokens", 0)),
        "completion_tokens": int(worker_result.get("completion_tokens", 0)),
        "total_tokens": int(worker_result.get("prompt_tokens", 0)) + int(worker_result.get("completion_tokens", 0)),
        "raw": worker_result,
    }


def _call_worker_persistent(
    system: str,
    user: str,
    *,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout_sec: int,
    extra_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    del temperature
    payload = _build_worker_payload(
        system,
        user,
        model=model,
        max_tokens=max_tokens,
        extra_payload=extra_payload,
    )
    worker_python = DEFAULT_WORKER_PYTHON
    worker_path = os.getenv("JOI_V14_PERSISTENT_WORKER_PATH", DEFAULT_PERSISTENT_WORKER)
    process = _ensure_persistent_worker(worker_python, worker_path, payload)
    if process.stdin is None:
        raise LocalLLMError("persistent worker stdin is unavailable")
    try:
        process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        process.stdin.flush()
    except BrokenPipeError as exc:
        _close_persistent_worker()
        raise LocalLLMError("persistent worker stdin pipe broke") from exc
    worker_result = _read_persistent_worker_response(process, timeout_sec)
    return {
        "content": worker_result.get("content", ""),
        "prompt_tokens": int(worker_result.get("prompt_tokens", 0)),
        "completion_tokens": int(worker_result.get("completion_tokens", 0)),
        "total_tokens": int(worker_result.get("prompt_tokens", 0)) + int(worker_result.get("completion_tokens", 0)),
        "raw": worker_result,
    }


def call(
    system: str,
    user: str,
    *,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    mode: str | None = None,
    model: str | None = None,
    endpoint: str | None = None,
    timeout_sec: int = 1800,
    retries: int = 2,
    backoff_sec: float = 2.0,
    seed: int | None = None,
    log_path: str | Path | None = None,
    extra_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    effective_mode = (mode or DEFAULT_MODE).strip().lower()
    effective_model = model or DEFAULT_MODEL
    effective_endpoint = endpoint or DEFAULT_ENDPOINT
    if seed is not None:
        effective_model = os.getenv("JOI_V14_MODEL", effective_model)
    last_error: Exception | None = None
    request_record = {
        "mode": effective_mode,
        "model": effective_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "seed": seed,
        "system": system,
        "user": user,
        "endpoint": effective_endpoint if effective_mode != "worker" else None,
        "worker_path": (
            os.getenv("JOI_V14_PERSISTENT_WORKER_PATH", DEFAULT_PERSISTENT_WORKER)
            if effective_mode == "worker" and _use_persistent_worker()
            else os.getenv("JOI_V14_WORKER_PATH", DEFAULT_WORKER) if effective_mode == "worker" else None
        ),
        "worker_python": DEFAULT_WORKER_PYTHON if effective_mode == "worker" else None,
        "persistent_worker": _use_persistent_worker() if effective_mode == "worker" else False,
    }
    for attempt in range(retries + 1):
        started_at = time.time()
        try:
            if effective_mode == "worker":
                if _use_persistent_worker():
                    response = _call_worker_persistent(
                        system,
                        user,
                        model=effective_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout_sec=timeout_sec,
                        extra_payload=extra_payload,
                    )
                else:
                    response = _call_worker(
                        system,
                        user,
                        model=effective_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout_sec=timeout_sec,
                        extra_payload=extra_payload,
                    )
            elif effective_mode in {"openai", "openai_compatible", "http"}:
                response = _call_openai_compatible(
                    system,
                    user,
                    endpoint=effective_endpoint,
                    model=effective_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout_sec=timeout_sec,
                    extra_payload=extra_payload,
                )
            elif effective_mode == "mock":
                response = {
                    "content": os.getenv(
                        "JOI_V14_MOCK_RESPONSE",
                        '{"name":"MockCandidate","cron":"","period":-1,"code":""}',
                    ),
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "raw": {"mock": True},
                }
            else:
                raise LocalLLMError(f"Unsupported JOI_V14_LLM_MODE: {effective_mode}")
            response["latency_sec"] = round(time.time() - started_at, 4)
            response["attempt"] = attempt + 1
            if log_path is not None:
                dump_json(log_path, {"request": request_record, "response": response})
            return response
        except (LocalLLMError, urllib.error.URLError, urllib.error.HTTPError, subprocess.SubprocessError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(backoff_sec * (attempt + 1))
    if log_path is not None:
        dump_json(log_path, {"request": request_record, "error": str(last_error)})
    raise LocalLLMError(str(last_error) if last_error else "local llm call failed")
