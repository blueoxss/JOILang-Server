#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
VERSION_DIR="$ROOT_DIR/gpt_mg/version0_15_update20260413"
RESULTS_DIR="$VERSION_DIR/results"

MODEL_KEY="${JOI_V15_CLOUD_MODEL_KEY:-gpt41_mini}"
ENDPOINT_DEFAULT="https://api.openai.com/v1/chat/completions"
OPENAI_ENDPOINT="${JOI_V15_OPENAI_ENDPOINT:-$ENDPOINT_DEFAULT}"
RETRIEVAL_DEVICE="${JOI_V15_RETRIEVAL_DEVICE:-cpu}"
PROMPT_RENDER_MODE="${JOI_V15_PROMPT_RENDER_MODE:-legacy_v13_monolith}"
PROMPT_ASSETS_DIR="${JOI_V15_PROMPT_ASSETS_DIR:-$ROOT_DIR/gpt_mg/version0_13}"
CONDITION="retrieval"
OUTPUT_ROOT=""

usage() {
  cat <<'EOF'
Usage:
  run_gpt41_mini_by_category.sh [options]

Options:
  --condition baseline|retrieval   Which context condition to run. Default: retrieval
  --output-root PATH               Root directory for all category result dirs
  --category N                     Category to run. Repeatable. Default: 1 2 3 4 5 6 7 8
  --prompt-render-mode MODE        Prompt render mode. Default: legacy_v13_monolith
  --prompt-assets-dir PATH         Prompt assets directory for monolith mode
  --retrieval-device DEVICE        Retrieval device. Default: cpu
  --model-key KEY                  Cloud model key. Default: gpt41_mini
  --help                           Show this help

Environment:
  JOI_V15_OPENAI_API_KEY           Must be set
  JOI_V15_OPENAI_ENDPOINT          Optional. Defaults to official OpenAI chat completions endpoint
EOF
}

declare -a CATEGORIES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --condition)
      CONDITION="${2:?missing value for --condition}"
      shift 2
      ;;
    --output-root)
      OUTPUT_ROOT="${2:?missing value for --output-root}"
      shift 2
      ;;
    --category)
      CATEGORIES+=("${2:?missing value for --category}")
      shift 2
      ;;
    --prompt-render-mode)
      PROMPT_RENDER_MODE="${2:?missing value for --prompt-render-mode}"
      shift 2
      ;;
    --prompt-assets-dir)
      PROMPT_ASSETS_DIR="${2:?missing value for --prompt-assets-dir}"
      shift 2
      ;;
    --retrieval-device)
      RETRIEVAL_DEVICE="${2:?missing value for --retrieval-device}"
      shift 2
      ;;
    --model-key)
      MODEL_KEY="${2:?missing value for --model-key}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "[error] Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${JOI_V15_OPENAI_API_KEY:-}" ]]; then
  echo "[error] JOI_V15_OPENAI_API_KEY is not set in the current shell." >&2
  exit 1
fi

if [[ "${#CATEGORIES[@]}" -eq 0 ]]; then
  CATEGORIES=(1 2 3 4 5 6 7 8)
fi

if [[ -z "$OUTPUT_ROOT" ]]; then
  TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
  OUTPUT_ROOT="$RESULTS_DIR/gpt41_mini_${CONDITION}_by_category_${TIMESTAMP}"
fi

mkdir -p "$OUTPUT_ROOT"
OUTPUT_ROOT="$(cd "$OUTPUT_ROOT" && pwd)"

echo "[info] output_root=$OUTPUT_ROOT"
echo "[info] model_key=$MODEL_KEY"
echo "[info] condition=$CONDITION"
echo "[info] prompt_render_mode=$PROMPT_RENDER_MODE"
echo "[info] prompt_assets_dir=$PROMPT_ASSETS_DIR"
echo "[info] openai_endpoint=$OPENAI_ENDPOINT"
echo "[info] categories=${CATEGORIES[*]}"

for category in "${CATEGORIES[@]}"; do
  RUN_DIR="$OUTPUT_ROOT/${CONDITION}_${MODEL_KEY}_cat${category}"
  echo
  echo "[run] category=$category -> $RUN_DIR"

  EXTRA_FLAGS=()
  if [[ "$CONDITION" == "retrieval" ]]; then
    EXTRA_FLAGS+=(
      --enable-retrieval-premapping
      --retrieval-topk 10
      --retrieval-mode hybrid
      --retrieval-device "$RETRIEVAL_DEVICE"
    )
  else
    EXTRA_FLAGS+=(--disable-retrieval-premapping)
  fi

  python "$VERSION_DIR/scripts/run_benchmark.py" \
    --suite paper_with_cloud_ref \
    --model-key "$MODEL_KEY" \
    --llm-mode openai \
    --llm-endpoint "$OPENAI_ENDPOINT" \
    --category "$category" \
    --candidate-k 1 \
    --repair-attempts 0 \
    --det-profile strict \
    --prompt-render-mode "$PROMPT_RENDER_MODE" \
    --prompt-assets-dir "$PROMPT_ASSETS_DIR" \
    --output-dir "$RUN_DIR" \
    --print-mode summary \
    --strict-availability \
    "${EXTRA_FLAGS[@]}"

  FAIL_COUNT="$(python - <<PY
import csv, pathlib, sys
path = pathlib.Path(r"$RUN_DIR") / "row_comparison.csv"
if not path.exists():
    raise SystemExit("row_comparison.csv not found")
with path.open() as f:
    rows = list(csv.DictReader(f))
fails = 0
for row in rows:
    value = str(row.get("${MODEL_KEY}__det_pass", "")).strip().lower()
    if value not in {"1", "true", "yes"}:
        fails += 1
print(fails)
PY
)"
  echo "[post] category=$category failures=$FAIL_COUNT"
  if [[ "${FAIL_COUNT:-0}" -gt 0 ]]; then
    python "$VERSION_DIR/scripts/export_row_report.py" \
      --results-dir "$RUN_DIR" \
      --model-key "$MODEL_KEY" \
      --failures-only \
      --output-dir "$RUN_DIR/side_by_side_report_${MODEL_KEY}_failures_only" \
      --print-json || true
  fi
done

python "$VERSION_DIR/scripts/analyze_gpt41_mini_category_failures.py" \
  --root-dir "$OUTPUT_ROOT" \
  --model-key "$MODEL_KEY" \
  --condition "$CONDITION" \
  --print-json

echo "[done] category study complete: $OUTPUT_ROOT"
