#!/usr/bin/env python3
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


try:
    from .retrieval_context import HybridRetriever, RetrievalConfig
except ImportError:
    from retrieval_context import HybridRetriever, RetrievalConfig  # type: ignore


_RETRIEVER: HybridRetriever | None = None
_RETRIEVER_KEY: tuple[str, ...] | None = None


def _write_response(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _config_key(config: RetrievalConfig) -> tuple[str, ...]:
    return (
        config.retrieval_json_path,
        config.retrieval_bundle_dir,
        config.retrieval_model_dir,
        config.retrieval_device,
        str(config.retrieval_batch_size),
        str(config.retrieval_max_length),
    )


def _load_retriever(config: RetrievalConfig) -> HybridRetriever:
    global _RETRIEVER, _RETRIEVER_KEY
    key = _config_key(config)
    if _RETRIEVER is not None and _RETRIEVER_KEY == key:
        return _RETRIEVER
    _RETRIEVER = HybridRetriever(config)
    _RETRIEVER_KEY = key
    return _RETRIEVER


def _parse_request(payload: dict[str, Any]) -> RetrievalConfig:
    return RetrievalConfig(
        service_context_mode="retrieval_fallback",
        retrieval_mode=str(payload.get("mode") or "hybrid"),
        retrieval_topk=max(1, int(payload.get("topk") or 10)),
        retrieval_device=str(payload.get("retrieval_device") or "cpu"),
        retrieval_batch_size=max(1, int(payload.get("retrieval_batch_size") or 16)),
        retrieval_max_length=max(32, int(payload.get("retrieval_max_length") or 512)),
        retrieval_json_path=str(payload.get("retrieval_json_path") or ""),
        retrieval_bundle_dir=str(payload.get("retrieval_bundle_dir") or ""),
        retrieval_model_dir=str(payload.get("retrieval_model_dir") or ""),
        retrieval_python=sys.executable,
        retrieval_worker_path=str(Path(__file__).resolve()),
    )


def main() -> int:
    for line in sys.stdin:
        raw = line.strip()
        if not raw:
            continue
        try:
            request = json.loads(raw)
            if not isinstance(request, dict):
                raise ValueError("request must be a JSON object")
            if request.get("_command") == "shutdown":
                _write_response({"ok": True, "status": "shutdown"})
                return 0

            query = str(request.get("query") or "")
            config = _parse_request(request)
            started = time.perf_counter()
            retriever = _load_retriever(config)
            hits = retriever.search(
                query,
                topk=int(request.get("topk") or config.retrieval_topk),
                mode=str(request.get("mode") or config.retrieval_mode),
            )
            _write_response(
                {
                    "ok": True,
                    "hits": hits,
                    "latency_sec": round(time.perf_counter() - started, 4),
                    "worker_python": sys.executable,
                    "retrieval_device": config.retrieval_device,
                    "retrieval_model_dir": config.retrieval_model_dir,
                }
            )
        except Exception as exc:
            _write_response(
                {
                    "ok": False,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "traceback": traceback.format_exc(limit=12),
                }
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
