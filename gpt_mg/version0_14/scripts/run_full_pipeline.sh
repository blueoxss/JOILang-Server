#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="version0_14"
MODE="quick"
GENOME_JSON="$ROOT/genomes/example_genome.json"
LLM_MODE="${JOI_V14_LLM_MODE:-worker}"
LLM_ENDPOINT="${JOI_V14_OPENAI_ENDPOINT:-}"
SEED="14"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --mode)
      MODE="$2"
      shift 2
      ;;
    --genome-json)
      GENOME_JSON="$2"
      shift 2
      ;;
    --llm-mode)
      LLM_MODE="$2"
      shift 2
      ;;
    --llm-endpoint)
      LLM_ENDPOINT="$2"
      shift 2
      ;;
    --seed)
      SEED="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ "$MODE" == "quick" ]]; then
  LIMIT_ARGS=(--limit 5)
  POP=4
  GENS=3
  SAMPLE=5
  VALIDATION=5
  CANDK=2
else
  LIMIT_ARGS=()
  POP=20
  GENS=30
  SAMPLE=20
  VALIDATION=8
  CANDK=3
fi

CANDIDATES_CSV="$ROOT/results/final_candidates_${PROFILE}.csv"
RERANK_CSV="$ROOT/results/final_rerank_${PROFILE}.csv"
BEST_GENOME_JSON="$ROOT/results/best_genome_from_ga.json"
BEST_AFTER_FEEDBACK_JSON="$ROOT/results/best_genome_after_feedback.json"

COMMON_LLM_ARGS=(--llm-mode "$LLM_MODE" --seed "$SEED")
if [[ -n "$LLM_ENDPOINT" ]]; then
  COMMON_LLM_ARGS+=(--llm-endpoint "$LLM_ENDPOINT")
fi

echo "[1/6] quick generate"
python3 "$ROOT/scripts/run_generate.py" \
  --profile "$PROFILE" \
  --genome-json "$GENOME_JSON" \
  --run-id "precheck_${PROFILE}_${SEED}" \
  --output-csv "$ROOT/results/precheck_candidates_${PROFILE}.csv" \
  --candidate-k "$CANDK" \
  "${LIMIT_ARGS[@]}" \
  "${COMMON_LLM_ARGS[@]}"

echo "[2/6] ga search"
python3 "$ROOT/scripts/run_ga_search.py" \
  --profile "$PROFILE" \
  --genome-json "$GENOME_JSON" \
  --population "$POP" \
  --gens "$GENS" \
  --sample-size "$SAMPLE" \
  --validation-size "$VALIDATION" \
  --candidate-k "$CANDK" \
  "${LIMIT_ARGS[@]}" \
  "${COMMON_LLM_ARGS[@]}"

python3 - <<'PY' "$ROOT/results/ga_summary.json" "$BEST_GENOME_JSON"
import json, pathlib, sys
summary = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
best = summary.get('best_genome') or {}
pathlib.Path(sys.argv[2]).write_text(json.dumps(best, ensure_ascii=False, indent=2) + "\n", encoding='utf-8')
PY

echo "[3/6] explicit feedback loop"
python3 "$ROOT/scripts/run_feedback_loop.py" \
  --profile "$PROFILE" \
  --genome-json "$BEST_GENOME_JSON" \
  --validation-size "$VALIDATION" \
  --candidate-k "$CANDK" \
  --attempts 3 \
  "${LIMIT_ARGS[@]}" \
  "${COMMON_LLM_ARGS[@]}"

LATEST_FEEDBACK_SUMMARY="$(find "$ROOT/results/patch_attempts" -name summary.json -type f | sort | tail -n 1)"
python3 - <<'PY' "$LATEST_FEEDBACK_SUMMARY" "$BEST_AFTER_FEEDBACK_JSON"
import json, pathlib, sys
summary_path = pathlib.Path(sys.argv[1])
best_out = pathlib.Path(sys.argv[2])
summary = json.loads(summary_path.read_text(encoding='utf-8'))
best = summary.get('best_genome') or {}
best_out.write_text(json.dumps(best, ensure_ascii=False, indent=2) + "\n", encoding='utf-8')
PY

echo "[4/6] final generate"
python3 "$ROOT/scripts/run_generate.py" \
  --profile "$PROFILE" \
  --genome-json "$BEST_AFTER_FEEDBACK_JSON" \
  --run-id "final_${PROFILE}_${SEED}" \
  --output-csv "$CANDIDATES_CSV" \
  --candidate-k "$CANDK" \
  "${LIMIT_ARGS[@]}" \
  "${COMMON_LLM_ARGS[@]}"

echo "[5/6] rerank + det"
python3 "$ROOT/scripts/run_rerank.py" \
  --profile "$PROFILE" \
  --genome-json "$BEST_AFTER_FEEDBACK_JSON" \
  --candidates-csv "$CANDIDATES_CSV" \
  --output-csv "$RERANK_CSV" \
  "${COMMON_LLM_ARGS[@]}"

echo "[6/6] final summary"
python3 - <<'PY' "$RERANK_CSV"
import csv, pathlib, statistics, sys
path = pathlib.Path(sys.argv[1])
with path.open(encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
scores = [float(r.get('det_score') or 0.0) for r in rows]
passed = sum(1 for s in scores if s >= 70.0)
avg = statistics.fmean(scores) if scores else 0.0
print(f"- rerank_csv: {path}")
print(f"- rows: {len(scores)}")
print(f"- avg_det_score: {avg:.4f}")
print(f"- rows_ge_70: {passed}/{len(scores)}")
PY
