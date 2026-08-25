#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
VERSION_DIR="$ROOT_DIR/gpt_mg/version0_15_update20260413"
RESULTS_DIR="$VERSION_DIR/results"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_ROOT="${1:-$RESULTS_DIR/paper_study_${TIMESTAMP}}"
BENCHMARK_DIR="$OUTPUT_ROOT/benchmarks"
PAPER_DIR="$OUTPUT_ROOT/paper"

mkdir -p "$BENCHMARK_DIR" "$PAPER_DIR"

WORKER_PYTHON="${JOI_V15_WORKER_PYTHON:-/home/mgjeong/miniconda3/envs/l/bin/python}"
GPU_QWEN7="${JOI_V15_GPU_QWEN7:-cuda:0}"
GPU_QWEN14="${JOI_V15_GPU_QWEN14:-cuda:1}"
RETRIEVAL_DEVICE="${JOI_V15_RETRIEVAL_DEVICE:-cpu}"
INCLUDE_CLOUD_REF="${JOI_V15_INCLUDE_CLOUD_REF:-0}"
OPENAI_ENDPOINT="${JOI_V15_OPENAI_ENDPOINT:-}"
OPENAI_MODEL_KEY="${JOI_V15_CLOUD_MODEL_KEY:-gpt41_mini}"

run_condition() {
  local condition="$1"
  local suite="$2"
  local model_key="$3"
  local gpu="$4"
  local extra_flags=("${@:5}")
  local out_dir="$BENCHMARK_DIR/${condition}_${model_key}"
  echo "[run] condition=${condition} suite=${suite} model=${model_key} gpu=${gpu}"
  (
    export JOI_V15_WORKER_PYTHON="$WORKER_PYTHON"
    export JOI_V15_LOCAL_DEVICE="$gpu"
    python "$VERSION_DIR/scripts/run_benchmark.py" \
      --suite "$suite" \
      --model-key "$model_key" \
      --candidate-k 1 \
      --repair-attempts 0 \
      --det-profile strict \
      --paper-fair-mode \
      --measure-latency \
      --measure-vram \
      --export-paper-artifacts \
      --skip-row-report \
      --output-dir "$out_dir" \
      --print-mode summary \
      --strict-availability \
      "${extra_flags[@]}"
  )
}

run_condition baseline paper_local5 qwen25_coder_7b "$GPU_QWEN7" --disable-retrieval-premapping &
PID_BASE_7=$!
run_condition baseline paper_local5 qwen25_coder_14b "$GPU_QWEN14" --disable-retrieval-premapping &
PID_BASE_14=$!

wait "$PID_BASE_7"
wait "$PID_BASE_14"

run_condition retrieval paper_local5 qwen25_coder_7b "$GPU_QWEN7" \
  --enable-retrieval-premapping \
  --retrieval-topk 10 \
  --retrieval-mode hybrid \
  --retrieval-device "$RETRIEVAL_DEVICE" &
PID_RET_7=$!
run_condition retrieval paper_local5 qwen25_coder_14b "$GPU_QWEN14" \
  --enable-retrieval-premapping \
  --retrieval-topk 10 \
  --retrieval-mode hybrid \
  --retrieval-device "$RETRIEVAL_DEVICE" &
PID_RET_14=$!

wait "$PID_RET_7"
wait "$PID_RET_14"

BASELINE_DIR_ARGS=(
  --baseline-dir "$BENCHMARK_DIR/baseline_qwen25_coder_7b"
  --baseline-dir "$BENCHMARK_DIR/baseline_qwen25_coder_14b"
)
RETRIEVAL_DIR_ARGS=(
  --retrieval-dir "$BENCHMARK_DIR/retrieval_qwen25_coder_7b"
  --retrieval-dir "$BENCHMARK_DIR/retrieval_qwen25_coder_14b"
)
BLOCKED_MODEL_ARGS=(
  --blocked-model 'phi35_mini=blocked|CUDA_OOM_with_current_prompt_length'
  --blocked-model 'llama31_8b=blocked|incomplete_cache'
  --blocked-model 'gemma2_9b_it=blocked|incomplete_cache'
)

if [[ "$INCLUDE_CLOUD_REF" == "1" ]]; then
  if [[ -z "$OPENAI_ENDPOINT" ]]; then
    echo "[error] JOI_V15_INCLUDE_CLOUD_REF=1 requires JOI_V15_OPENAI_ENDPOINT to be set." >&2
    exit 1
  fi

  run_condition baseline paper_with_cloud_ref "$OPENAI_MODEL_KEY" cpu \
    --llm-mode openai \
    --llm-endpoint "$OPENAI_ENDPOINT" \
    --disable-retrieval-premapping

  run_condition retrieval paper_with_cloud_ref "$OPENAI_MODEL_KEY" cpu \
    --llm-mode openai \
    --llm-endpoint "$OPENAI_ENDPOINT" \
    --enable-retrieval-premapping \
    --retrieval-topk 10 \
    --retrieval-mode hybrid \
    --retrieval-device "$RETRIEVAL_DEVICE"

  BASELINE_DIR_ARGS+=(--baseline-dir "$BENCHMARK_DIR/baseline_${OPENAI_MODEL_KEY}")
  RETRIEVAL_DIR_ARGS+=(--retrieval-dir "$BENCHMARK_DIR/retrieval_${OPENAI_MODEL_KEY}")
fi

python "$VERSION_DIR/scripts/export_paper_study.py" \
  "${BASELINE_DIR_ARGS[@]}" \
  "${RETRIEVAL_DIR_ARGS[@]}" \
  "${BLOCKED_MODEL_ARGS[@]}" \
  --study-title 'JOILang Full Context Study' \
  --out-dir "$PAPER_DIR"

echo "[done] output_root=$OUTPUT_ROOT"
echo "[done] paper_dir=$PAPER_DIR"
