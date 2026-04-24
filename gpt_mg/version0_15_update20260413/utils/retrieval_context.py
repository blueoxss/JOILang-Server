#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import pickle
import select
import subprocess
import sys
import threading
import atexit
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


VERSION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = VERSION_ROOT.parents[1]
LLM_ROOT = REPO_ROOT.parent
MODEL_MGMT_ROOT = LLM_ROOT / "ModelMagementApp"

DEFAULT_LOCAL_RETRIEVAL_DIR = VERSION_ROOT / "retrieval_assets"
DEFAULT_RETRIEVAL_JSON_CANDIDATES = [
    DEFAULT_LOCAL_RETRIEVAL_DIR / "service_list_ver2.0.1_retrieval_eng.json",
    MODEL_MGMT_ROOT / "datasets" / "service_list_ver2.0.1_retrieval_eng.json",
]
DEFAULT_BUNDLE_DIR_CANDIDATES = [
    DEFAULT_LOCAL_RETRIEVAL_DIR / "embedding_result_v5_ver2.0.1",
    MODEL_MGMT_ROOT / "embedding" / "embedding_result_v5_ver2.0.1",
]
DEFAULT_MODEL_DIR_CANDIDATES = [
    DEFAULT_LOCAL_RETRIEVAL_DIR / "BAAI_bge-m3__service_list_ver2.0.1_retrieval_eng",
    MODEL_MGMT_ROOT / "embedding" / "finetuned_models_eng" / "BAAI_bge-m3__service_list_ver2.0.1_retrieval_eng",
]

TOKEN_RE = __import__("re").compile(r"[A-Za-z0-9가-힣]+")
_LOCK = threading.Lock()
_RETRIEVER_CACHE: dict[tuple[str, str, str, str, str, int], "HybridRetriever"] = {}
_WORKER_PROCESS: subprocess.Popen[str] | None = None
_WORKER_KEY: tuple[str, ...] | None = None


def _env_text(name: str, default: str = "") -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _default_retrieval_python() -> str:
    explicit = _env_text("JOI_V15_RETRIEVAL_PYTHON", "")
    if explicit:
        return explicit
    explicit = _env_text("JOI_V15_WORKER_PYTHON", "")
    if explicit:
        return explicit
    fallback = Path("/home/mgjeong/miniconda3/envs/l/bin/python")
    if fallback.exists():
        return str(fallback)
    return sys.executable or "python3"


DEFAULT_RETRIEVAL_PYTHON = _default_retrieval_python()
DEFAULT_RETRIEVAL_WORKER = str((VERSION_ROOT / "utils" / "persistent_retrieval_worker.py").resolve())


def _first_existing(candidates: list[Path]) -> str:
    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())
    return str(candidates[0].resolve())


@dataclass(frozen=True)
class RetrievalConfig:
    service_context_mode: str = "schema_fallback"
    retrieval_mode: str = "hybrid"
    retrieval_topk: int = 10
    retrieval_device: str = "cpu"
    retrieval_batch_size: int = 16
    retrieval_max_length: int = 512
    retrieval_json_path: str = ""
    retrieval_bundle_dir: str = ""
    retrieval_model_dir: str = ""
    retrieval_python: str = ""
    retrieval_worker_path: str = ""

    @property
    def enabled(self) -> bool:
        return self.service_context_mode in {"auto", "retrieval_fallback"}


def _resolve_candidate_path(explicit: str, candidates: list[Path]) -> str:
    if explicit:
        return str(Path(explicit).expanduser().resolve())
    return _first_existing(candidates)


def load_retrieval_config(overrides: dict[str, Any] | None = None) -> RetrievalConfig:
    overrides = dict(overrides or {})
    service_context_mode = str(
        overrides.get("service_context_mode")
        or _env_text("JOI_V15_SERVICE_CONTEXT_MODE", "schema_fallback")
    ).strip().lower()
    if service_context_mode not in {"auto", "retrieval_fallback", "schema_fallback"}:
        service_context_mode = "schema_fallback"

    retrieval_mode = str(
        overrides.get("retrieval_mode")
        or _env_text("JOI_V15_RETRIEVAL_MODE", "hybrid")
    ).strip().lower()
    if retrieval_mode not in {"hybrid", "dense", "bm25"}:
        retrieval_mode = "hybrid"

    try:
        retrieval_topk = int(overrides.get("retrieval_topk") or _env_text("JOI_V15_RETRIEVAL_TOPK", "10"))
    except Exception:
        retrieval_topk = 10
    retrieval_topk = max(1, retrieval_topk)

    try:
        retrieval_batch_size = int(overrides.get("retrieval_batch_size") or _env_text("JOI_V15_RETRIEVAL_BATCH_SIZE", "16"))
    except Exception:
        retrieval_batch_size = 16
    retrieval_batch_size = max(1, retrieval_batch_size)

    try:
        retrieval_max_length = int(overrides.get("retrieval_max_length") or _env_text("JOI_V15_RETRIEVAL_MAX_LENGTH", "512"))
    except Exception:
        retrieval_max_length = 512
    retrieval_max_length = max(32, retrieval_max_length)

    retrieval_json_path = _resolve_candidate_path(
        str(overrides.get("retrieval_json_path") or _env_text("JOI_V15_RETRIEVAL_JSON", "")),
        DEFAULT_RETRIEVAL_JSON_CANDIDATES,
    )
    retrieval_bundle_dir = _resolve_candidate_path(
        str(overrides.get("retrieval_bundle_dir") or _env_text("JOI_V15_RETRIEVAL_BUNDLE_DIR", "")),
        DEFAULT_BUNDLE_DIR_CANDIDATES,
    )
    retrieval_model_dir = _resolve_candidate_path(
        str(overrides.get("retrieval_model_dir") or _env_text("JOI_V15_RETRIEVAL_MODEL_DIR", "")),
        DEFAULT_MODEL_DIR_CANDIDATES,
    )
    retrieval_device = str(overrides.get("retrieval_device") or _env_text("JOI_V15_RETRIEVAL_DEVICE", "cpu")).strip().lower() or "cpu"
    retrieval_python = str(overrides.get("retrieval_python") or _env_text("JOI_V15_RETRIEVAL_PYTHON", DEFAULT_RETRIEVAL_PYTHON)).strip()
    retrieval_worker_path = str(
        Path(overrides.get("retrieval_worker_path") or _env_text("JOI_V15_RETRIEVAL_WORKER", DEFAULT_RETRIEVAL_WORKER)).expanduser().resolve()
    )

    return RetrievalConfig(
        service_context_mode=service_context_mode,
        retrieval_mode=retrieval_mode,
        retrieval_topk=retrieval_topk,
        retrieval_device=retrieval_device,
        retrieval_batch_size=retrieval_batch_size,
        retrieval_max_length=retrieval_max_length,
        retrieval_json_path=retrieval_json_path,
        retrieval_bundle_dir=retrieval_bundle_dir,
        retrieval_model_dir=retrieval_model_dir,
        retrieval_python=retrieval_python,
        retrieval_worker_path=retrieval_worker_path,
    )


def _tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in TOKEN_RE.findall(str(text))]


class SimpleBM25:
    def __init__(self, corpus: list[str], k1: float = 1.5, b: float = 0.75):
        self.corpus_size = len(corpus)
        self.avgdl = 0.0
        self.doc_freqs: list[Counter[str]] = []
        self.idf: dict[str, float] = {}
        self.doc_len: list[int] = []
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self._initialize()

    def _initialize(self) -> None:
        total_len = 0
        df: dict[str, int] = {}
        for doc in self.corpus:
            tokens = _tokenize(doc)
            self.doc_len.append(len(tokens))
            total_len += len(tokens)
            freqs = Counter(tokens)
            self.doc_freqs.append(freqs)
            for token in freqs:
                df[token] = df.get(token, 0) + 1

        self.avgdl = (total_len / self.corpus_size) if self.corpus_size else 0.0
        for token, freq in df.items():
            self.idf[token] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query: str) -> np.ndarray:
        scores = np.zeros(self.corpus_size, dtype=np.float32)
        for token in _tokenize(query):
            idf = self.idf.get(token)
            if idf is None:
                continue
            for idx, doc_freqs in enumerate(self.doc_freqs):
                freq = doc_freqs.get(token, 0)
                if freq <= 0:
                    continue
                numerator = idf * freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * self.doc_len[idx] / (self.avgdl + 1e-9))
                scores[idx] += numerator / denominator
        return scores


def _maybe_prefix_e5(model_id: str, texts: list[str], kind: str) -> list[str]:
    if "e5" not in model_id.lower():
        return texts
    prefix = "query: " if kind == "query" else "passage: "
    return [prefix + text for text in texts]


def _lazy_import_transformer_stack():
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except Exception as exc:
        raise RuntimeError(
            "transformers/torch could not be imported for retrieval pre-mapping. "
            f"Original error: {exc}"
        ) from exc
    return torch, AutoTokenizer, AutoModel


def _mean_pool(last_hidden_state, attention_mask, torch_module):
    mask = attention_mask.unsqueeze(-1)
    denom = mask.sum(1).clamp(min=1e-9)
    pooled = (last_hidden_state * mask).sum(1) / denom
    return torch_module.nn.functional.normalize(pooled, p=2, dim=1)


def encode_texts_dense(
    model_id_or_path: str,
    texts: list[str],
    *,
    batch_size: int,
    max_length: int,
    device: str,
) -> np.ndarray:
    torch, AutoTokenizer, AutoModel = _lazy_import_transformer_stack()
    actual_device = "cuda" if device == "cuda" and torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(model_id_or_path, trust_remote_code=True)
    model = AutoModel.from_pretrained(model_id_or_path, trust_remote_code=True).to(actual_device).eval()

    outputs: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, len(texts), batch_size):
            chunk = texts[start:start + batch_size]
            inputs = tokenizer(
                chunk,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            ).to(actual_device)
            out = model(**inputs)
            pooled = _mean_pool(out.last_hidden_state, inputs["attention_mask"], torch)
            outputs.append(pooled.detach().float().cpu().numpy())
    return np.concatenate(outputs, axis=0) if outputs else np.zeros((0, 0), dtype=np.float32)


def _build_candidate_cache(
    dense_sims: np.ndarray,
    bm25_scores: list[np.ndarray],
    A: int,
    B: int,
) -> tuple[list[np.ndarray], list[np.ndarray], list[np.ndarray]]:
    query_count, corpus_size = dense_sims.shape
    A = max(1, min(int(A), corpus_size))
    B = max(1, min(int(B), corpus_size))
    eps = 1e-9

    candidates: list[np.ndarray] = []
    dense_norms: list[np.ndarray] = []
    sparse_norms: list[np.ndarray] = []

    dense_top_a = np.argpartition(-dense_sims, A - 1, axis=1)[:, :A]
    for qi in range(query_count):
        sparse = bm25_scores[qi]
        sparse_top_b = np.argpartition(-sparse, B - 1)[:B]
        cand = np.unique(np.concatenate([dense_top_a[qi], sparse_top_b])).astype(np.int32)
        d = dense_sims[qi, cand]
        s = sparse[cand]
        dn = d / (float(d.max()) + eps) if d.size else d
        sn = s / (float(s.max()) + eps) if s.size and float(s.max()) > 0 else np.zeros_like(s)
        candidates.append(cand)
        dense_norms.append(dn.astype(np.float32))
        sparse_norms.append(sn.astype(np.float32))
    return candidates, dense_norms, sparse_norms


def _rank_candidates(
    candidates: list[np.ndarray],
    dense_norms: list[np.ndarray],
    sparse_norms: list[np.ndarray],
    dense_weight: float,
    topk: int,
) -> list[np.ndarray]:
    ranked: list[np.ndarray] = []
    sparse_weight = 1.0 - dense_weight
    for qi, cand in enumerate(candidates):
        comb = dense_weight * dense_norms[qi] + sparse_weight * sparse_norms[qi]
        k_eff = min(topk, comb.shape[0]) if comb.size else 0
        if k_eff <= 0:
            ranked.append(np.array([], dtype=np.int32))
            continue
        idx = np.argpartition(comb, -k_eff)[-k_eff:]
        idx = idx[np.argsort(-comb[idx])]
        ranked.append(cand[idx])
    return ranked


def _rank_topk_from_scores(scores: np.ndarray, topk: int) -> np.ndarray:
    if scores.size == 0:
        return np.array([], dtype=np.int32)
    k_eff = min(topk, scores.shape[0])
    idx = np.argpartition(-scores, k_eff - 1)[:k_eff]
    idx = idx[np.argsort(-scores[idx])]
    return idx.astype(np.int32)


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class HybridRetriever:
    def __init__(self, config: RetrievalConfig) -> None:
        self.config = config
        self.metadata = _load_json(config.retrieval_bundle_dir + "/metadata.json")
        self.hybrid_config = _load_json(config.retrieval_bundle_dir + "/hybrid_config.json")
        self.retrieval_json = _load_json(config.retrieval_json_path)
        self.doc_embs = np.load(Path(config.retrieval_bundle_dir) / "doc_embs_e5.npy")
        self.doc_ids = [str(item) for item in self.metadata.get("keys", [])]
        self.texts = [str(item) for item in self.metadata.get("texts", [])]
        self.model_id_dense = str(
            config.retrieval_model_dir
            or self.metadata.get("model_id_dense")
            or self.metadata.get("model_id")
            or config.retrieval_model_dir
        )
        self.best_A = int(self.hybrid_config.get("best_A", 20))
        self.best_B = int(self.hybrid_config.get("best_B", 20))
        self.best_dense_weight = float((self.hybrid_config.get("best_w") or [0.9])[0])
        self.bm25 = self._load_bm25()

    def _load_bm25(self) -> SimpleBM25:
        bm25_path = Path(self.config.retrieval_bundle_dir) / "bm25.pkl"
        if bm25_path.exists():
            try:
                with bm25_path.open("rb") as handle:
                    return pickle.load(handle)
            except Exception:
                pass
        return SimpleBM25(self.texts)

    def search(self, query: str, *, topk: int | None = None, mode: str | None = None) -> list[dict[str, Any]]:
        topk = max(1, int(topk or self.config.retrieval_topk))
        mode = str(mode or self.config.retrieval_mode).strip().lower()
        query_emb = encode_texts_dense(
            self.model_id_dense,
            _maybe_prefix_e5(self.model_id_dense, [query], "query"),
            batch_size=self.config.retrieval_batch_size,
            max_length=self.config.retrieval_max_length,
            device=self.config.retrieval_device,
        )[0]
        dense_scores = query_emb @ self.doc_embs.T
        bm25_scores = np.asarray(self.bm25.get_scores(query), dtype=np.float32)
        if mode == "dense":
            ranked_idx = _rank_topk_from_scores(dense_scores, topk)
            combined_scores = dense_scores
        elif mode == "bm25":
            ranked_idx = _rank_topk_from_scores(bm25_scores, topk)
            combined_scores = bm25_scores
        else:
            candidates, dense_norms, sparse_norms = _build_candidate_cache(
                dense_scores[None, :],
                [bm25_scores],
                A=self.best_A,
                B=self.best_B,
            )
            ranked_idx = _rank_candidates(candidates, dense_norms, sparse_norms, self.best_dense_weight, topk=topk)[0]
            combined_scores = self.best_dense_weight * dense_scores + (1.0 - self.best_dense_weight) * bm25_scores
        hits: list[dict[str, Any]] = []
        for rank, idx in enumerate(ranked_idx.tolist(), start=1):
            device = self.doc_ids[idx]
            payload = self.retrieval_json.get(device) or {}
            hits.append(
                {
                    "rank": rank,
                    "device": device,
                    "score": float(combined_scores[idx]),
                    "dense_score": float(dense_scores[idx]),
                    "bm25_score": float(bm25_scores[idx]),
                    "info": str(payload.get("info", "") or ""),
                    "services": payload.get("services", []),
                    "examples": list(payload.get("examples", [])[:3]),
                }
            )
        return hits


def _cache_key(config: RetrievalConfig) -> tuple[str, str, str, str, str, int]:
    return (
        config.retrieval_json_path,
        config.retrieval_bundle_dir,
        config.retrieval_model_dir,
        config.retrieval_mode,
        config.retrieval_device,
        config.retrieval_topk,
    )


def _worker_signature(config: RetrievalConfig) -> tuple[str, ...]:
    return (
        str(config.retrieval_python),
        str(config.retrieval_worker_path),
        str(config.retrieval_json_path),
        str(config.retrieval_bundle_dir),
        str(config.retrieval_model_dir),
        str(config.retrieval_device),
        str(config.retrieval_mode),
        str(config.retrieval_topk),
    )


def _close_worker() -> None:
    global _WORKER_PROCESS, _WORKER_KEY
    process = _WORKER_PROCESS
    _WORKER_PROCESS = None
    _WORKER_KEY = None
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


atexit.register(_close_worker)


def _ensure_worker(config: RetrievalConfig) -> subprocess.Popen[str]:
    global _WORKER_PROCESS, _WORKER_KEY
    signature = _worker_signature(config)
    if (
        _WORKER_PROCESS is not None
        and _WORKER_PROCESS.poll() is None
        and _WORKER_KEY == signature
    ):
        return _WORKER_PROCESS

    _close_worker()
    env = os.environ.copy()
    env.setdefault("TOKENIZERS_PARALLELISM", "false")
    process = subprocess.Popen(
        [config.retrieval_python, config.retrieval_worker_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )
    _WORKER_PROCESS = process
    _WORKER_KEY = signature
    return process


def _read_worker_response(process: subprocess.Popen[str], timeout_sec: float = 120.0) -> dict[str, Any]:
    if process.stdout is None:
        raise RuntimeError("retrieval worker stdout is unavailable")
    ready, _, _ = select.select([process.stdout], [], [], timeout_sec)
    if not ready:
        raise RuntimeError(f"retrieval worker timed out after {timeout_sec:.1f}s")
    line = process.stdout.readline()
    if not line:
        stderr_text = ""
        if process.stderr is not None:
            try:
                stderr_text = process.stderr.read().strip()
            except Exception:
                stderr_text = ""
        raise RuntimeError(f"retrieval worker exited unexpectedly. stderr={stderr_text[:500]}")
    payload = json.loads(line)
    if not isinstance(payload, dict):
        raise RuntimeError(f"retrieval worker returned unexpected payload: {type(payload).__name__}")
    if not payload.get("ok", False):
        raise RuntimeError(str(payload.get("error", "retrieval worker error")))
    return payload


def search_with_worker(config: RetrievalConfig, query: str, *, topk: int | None = None, mode: str | None = None) -> list[dict[str, Any]]:
    process = _ensure_worker(config)
    if process.stdin is None:
        raise RuntimeError("retrieval worker stdin is unavailable")
    request = {
        "query": str(query or ""),
        "topk": int(topk or config.retrieval_topk),
        "mode": str(mode or config.retrieval_mode),
        "retrieval_json_path": config.retrieval_json_path,
        "retrieval_bundle_dir": config.retrieval_bundle_dir,
        "retrieval_model_dir": config.retrieval_model_dir,
        "retrieval_device": config.retrieval_device,
        "retrieval_batch_size": config.retrieval_batch_size,
        "retrieval_max_length": config.retrieval_max_length,
    }
    process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
    process.stdin.flush()
    response = _read_worker_response(process)
    hits = response.get("hits", [])
    return hits if isinstance(hits, list) else []


def get_retriever(config: RetrievalConfig) -> HybridRetriever:
    key = _cache_key(config)
    with _LOCK:
        retriever = _RETRIEVER_CACHE.get(key)
        if retriever is None:
            retriever = HybridRetriever(config)
            _RETRIEVER_CACHE[key] = retriever
    return retriever


def probe_retrieval_assets(config: RetrievalConfig) -> dict[str, Any]:
    retrieval_json = Path(config.retrieval_json_path)
    bundle_dir = Path(config.retrieval_bundle_dir)
    model_dir = Path(config.retrieval_model_dir)
    retrieval_python = Path(config.retrieval_python).expanduser()
    retrieval_worker_path = Path(config.retrieval_worker_path)
    status = "ready"
    message = ""
    required = [
        retrieval_json.exists(),
        bundle_dir.exists(),
        (bundle_dir / "metadata.json").exists(),
        (bundle_dir / "hybrid_config.json").exists(),
        (bundle_dir / "doc_embs_e5.npy").exists(),
        model_dir.exists(),
        retrieval_python.exists(),
        retrieval_worker_path.exists(),
    ]
    if not all(required):
        status = "missing_assets"
        message = "Retrieval assets are incomplete; schema fallback will be used."
    return {
        "status": status,
        "message": message,
        "retrieval_json_path": str(retrieval_json),
        "retrieval_bundle_dir": str(bundle_dir),
        "retrieval_model_dir": str(model_dir),
        "retrieval_python": str(retrieval_python),
        "retrieval_worker_path": str(retrieval_worker_path),
        "retrieval_mode": config.retrieval_mode,
        "retrieval_topk": config.retrieval_topk,
        "retrieval_device": config.retrieval_device,
    }


def retrieval_ready(config: RetrievalConfig) -> tuple[bool, dict[str, Any]]:
    info = probe_retrieval_assets(config)
    return info.get("status") == "ready", info
