#!/bin/bash
set -euo pipefail

ROW_NO="${1:-1}"
TIME="${2:-2026-03-31T12:00:00}"
DATASET_PATH="./datasets/JOICommands-280.csv"
FORBIDDEN_ACTIONS_PATH="./datasets/forbidden_actions.json"
RUN_ID="raw_row${ROW_NO}_$(date +%Y%m%d_%H%M%S)"
GENERATION_DIR="./results/generation/${RUN_ID}"
GENERATION_JSONL="${GENERATION_DIR}/generation.jsonl"
MERGED_VALUE_SERVICES_PATH="${GENERATION_DIR}/merged_value_services.json"
MERGED_FUNCTION_SERVICES_PATH="${GENERATION_DIR}/merged_function_services.json"
DET_OUTPUT_DIR="./results/det_paper"
V14_ROOT="./gpt_mg/version0_14"
V14_CANDIDATE_K="${V14_CANDIDATE_K:-3}"
V14_REPAIR_THRESHOLD="${V14_REPAIR_THRESHOLD:-99}"
V14_REPAIR_ATTEMPTS="${V14_REPAIR_ATTEMPTS:-2}"
V14_ROW_DATASET="${GENERATION_DIR}/version0_14_row.csv"
V14_CANDIDATES_CSV="${GENERATION_DIR}/version0_14_candidates.csv"
V14_RERANK_CSV="${GENERATION_DIR}/version0_14_rerank.csv"

if ! [[ "$ROW_NO" =~ ^[0-9]+$ ]] || [ "$ROW_NO" -lt 1 ]; then
  echo "Usage: ./query_raw.sh <row_no> [current_time]" >&2
  echo "Example: ./query_raw.sh 1" >&2
  exit 1
fi

SENTENCE="$(python3 - "$ROW_NO" <<'PY'
import csv
import sys
from pathlib import Path

target = int(sys.argv[1])
csv_path = Path("./datasets/JOICommands-280.csv")

with csv_path.open(encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for position, row in enumerate(reader, start=1):
        row_index = row.get("index", "").strip()
        if position == target or (row_index.isdigit() and int(row_index) == target):
            print(row.get("command_kor", "").strip())
            break
    else:
        raise SystemExit(f"Row {target} not found in {csv_path}")
PY
)"

if [ -z "$SENTENCE" ]; then
  echo "No command_kor found for row $ROW_NO" >&2
  exit 1
fi

mkdir -p "$GENERATION_DIR" "$DET_OUTPUT_DIR"
: > "$GENERATION_JSONL"

python3 - "$MERGED_VALUE_SERVICES_PATH" \
  "./gpt_mg/version0_13/service_list_ver1.5.4_value.json" \
  "./gpt_mg/version0_12/service_list_ver2.0.1_value.json" <<'PY'
import json
import sys
from pathlib import Path

output_path = Path(sys.argv[1])
items = []
for src in sys.argv[2:]:
    data = json.loads(Path(src).read_text(encoding="utf-8"))
    if isinstance(data, list):
        items.extend(data)
    else:
        items.append(data)
output_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
PY

python3 - "$MERGED_FUNCTION_SERVICES_PATH" \
  "./gpt_mg/version0_13/service_list_ver1.5.4_function.json" \
  "./gpt_mg/version0_12/service_list_ver2.0.1_function.json" <<'PY'
import json
import sys
from pathlib import Path

output_path = Path(sys.argv[1])
items = []
for src in sys.argv[2:]:
    data = json.loads(Path(src).read_text(encoding="utf-8"))
    if isinstance(data, list):
        items.extend(data)
    else:
        items.append(data)
output_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
PY

CONNECTED_DEVICES="$(python3 - <<'PY'
import json
with open("./datasets/things.json", encoding="utf-8") as f:
    print(json.dumps(json.load(f), ensure_ascii=False, separators=(",", ":")))
PY
)"

append_generation_jsonl() {
  local label="$1"
  local request_model="$2"
  local selected_model="$3"
  local response_json="$4"

  python3 - "$GENERATION_JSONL" "$ROW_NO" "$SENTENCE" "$TIME" "$label" "$request_model" "$selected_model" "$response_json" <<'PY'
import json
import sys
from pathlib import Path

output_path = Path(sys.argv[1])
row_no = int(sys.argv[2])
sentence = sys.argv[3]
current_time = sys.argv[4]
label = sys.argv[5]
request_model = sys.argv[6]
selected_model = sys.argv[7]
response_json = sys.argv[8]

try:
    response = json.loads(response_json)
except json.JSONDecodeError:
    response = {
        "code": "",
        "log": {
            "error": "invalid_json_response",
            "raw_response": response_json,
        },
    }

record = {
    "row_no": row_no,
    "dataset_index": row_no,
    "sentence": sentence,
    "current_time": current_time,
    "model_label": label,
    "request_model": request_model,
    "selected_model": selected_model,
    "response": response,
}

with output_path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False) + "\n")
PY
}

resolve_version0_14_genome() {
  if [ -n "${V14_GENOME_JSON:-}" ] && [ -f "$V14_GENOME_JSON" ]; then
    printf '%s\n' "$V14_GENOME_JSON"
    return 0
  fi

  local candidates=(
    "${V14_ROOT}/results/best_genome_after_feedback.json"
    "${V14_ROOT}/results/best_genome_from_ga.json"
    "${V14_ROOT}/results/best_genome.json"
    "${V14_ROOT}/results/category_sweep_20260331_082722/final_best_genome.json"
    "${V14_ROOT}/genomes/example_genome.json"
  )

  local path
  for path in "${candidates[@]}"; do
    if [ -f "$path" ]; then
      printf '%s\n' "$path"
      return 0
    fi
  done

  return 1
}

write_version0_14_row_dataset() {
  python3 - "$ROW_NO" "$DATASET_PATH" "$V14_ROW_DATASET" "$CONNECTED_DEVICES" <<'PY'
import csv
import json
import sys
from pathlib import Path

target = int(sys.argv[1])
src = Path(sys.argv[2])
dst = Path(sys.argv[3])
connected_devices = json.loads(sys.argv[4])

with src.open(encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames or [])
    if "connected_devices" not in fieldnames:
        fieldnames.append("connected_devices")

    for position, row in enumerate(reader, start=1):
        row_index = str(row.get("index", "")).strip()
        if position == target or (row_index.isdigit() and int(row_index) == target):
            row = dict(row)
            row["connected_devices"] = json.dumps(connected_devices, ensure_ascii=False)
            dst.parent.mkdir(parents=True, exist_ok=True)
            with dst.open("w", encoding="utf-8", newline="") as out:
                writer = csv.DictWriter(out, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow({key: row.get(key, "") for key in fieldnames})
            break
    else:
        raise SystemExit(f"Row {target} not found in {src}")
PY
}

build_version0_14_response() {
  local rerank_csv="$1"
  local genome_json="$2"
  python3 - "$rerank_csv" "$genome_json" <<'PY'
import csv
import json
import sys
from pathlib import Path

rerank_csv = Path(sys.argv[1])
genome_json = sys.argv[2]

with rerank_csv.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

if not rows:
    response = {
        "code": "",
        "log": {
            "error": "version0_14_no_rows",
            "model_name": "gpt_mg.version0_14",
            "genome_json": genome_json,
        },
    }
    print(json.dumps(response, ensure_ascii=False))
    raise SystemExit(0)

row = rows[0]
output_text = str(row.get("output", "")).strip()
if output_text:
    try:
        parsed_output = json.loads(output_text)
    except json.JSONDecodeError:
        parsed_output = {"name": "", "cron": "", "period": -1, "code": output_text}
    code_value = [parsed_output] if isinstance(parsed_output, dict) else parsed_output
else:
    code_value = ""

failure_reasons_raw = str(row.get("det_failure_reasons", "")).strip()
try:
    failure_reasons = json.loads(failure_reasons_raw) if failure_reasons_raw else []
except json.JSONDecodeError:
    failure_reasons = [failure_reasons_raw] if failure_reasons_raw else []

response = {
    "code": code_value,
    "log": {
        "model_name": "gpt_mg.version0_14",
        "request_profile": row.get("profile", "version0_14"),
        "genome_id": row.get("genome_id", ""),
        "genome_json": genome_json,
        "generation_status": row.get("generation_status", ""),
        "selected_candidate_index": row.get("selected_candidate_index", ""),
        "repair_applied": row.get("repair_applied", ""),
        "det_score": row.get("det_score", ""),
        "det_gt_exact": row.get("det_gt_exact", ""),
        "det_failure_reasons": failure_reasons,
        "output_csv": str(rerank_csv),
        "input_mode": "dataset_row_command_eng_with_connected_devices_from_things_json",
    },
}
print(json.dumps(response, ensure_ascii=False))
PY
}

run_model() {
  local label="$1"
  local request_model="$2"
  local selected_model="$3"

  echo "=== ${label} ==="
  local response
  response="$(curl -s -X POST http://localhost:8000/generate_joi_code \
    -H "Content-Type: application/json" \
    -d '{
      "sentence": "'"$SENTENCE"'",
      "model": "'"$request_model"'",
      "connected_devices": '"$CONNECTED_DEVICES"',
      "current_time": "'"$TIME"'",
      "other_params": [{"selected_model": "'"$selected_model"'"}]
    }')"
  echo "$response"
  append_generation_jsonl "$label" "$request_model" "$selected_model" "$response"
  echo -e "\n"
}

run_version0_14() {
  local label="$1"
  local selected_model="$2"
  local genome_json

  echo "=== ${label} ==="

  if ! genome_json="$(resolve_version0_14_genome)"; then
    local missing_response
    missing_response='{"code":"","log":{"error":"version0_14_genome_not_found","model_name":"gpt_mg.version0_14"}}'
    echo "$missing_response"
    append_generation_jsonl "$label" "gpt_mg.version0_14" "$selected_model" "$missing_response"
    echo -e "\n"
    return 0
  fi

  write_version0_14_row_dataset

  python3 "${V14_ROOT}/scripts/run_generate.py" \
    --profile version0_14 \
    --genome-json "$genome_json" \
    --dataset "$V14_ROW_DATASET" \
    --start-row 1 \
    --end-row 1 \
    --candidate-k "$V14_CANDIDATE_K" \
    --run-id "${RUN_ID}_version0_14" \
    --output-csv "$V14_CANDIDATES_CSV" >/dev/null

  python3 "${V14_ROOT}/scripts/run_rerank.py" \
    --profile version0_14 \
    --genome-json "$genome_json" \
    --candidates-csv "$V14_CANDIDATES_CSV" \
    --repair-threshold "$V14_REPAIR_THRESHOLD" \
    --repair-attempts "$V14_REPAIR_ATTEMPTS" \
    --output-csv "$V14_RERANK_CSV" >/dev/null

  local response
  response="$(build_version0_14_response "$V14_RERANK_CSV" "$genome_json")"
  echo "$response"
  append_generation_jsonl "$label" "gpt_mg.version0_14" "$selected_model" "$response"
  echo -e "\n"
}

echo "=== Row $ROW_NO ==="
echo "SENTENCE: $SENTENCE"
echo "RUN_ID: $RUN_ID"
echo "GENERATION_JSONL: $GENERATION_JSONL"
echo

run_model "[1/5] CAP-old_gpt4.1-mini_svc-v1.5.4" "gpt4.1-mini" "CAP-old_gpt4.1-mini_svc-v1.5.4"
run_model "[2/5] JOI_gpt4.1-mini_v1.5.4" "gpt_mg.version0_6" "JOI_gpt4.1-mini_v1.5.4"
run_model "[3/5] Local5080_qwen-7b_svc-v1.5.4" "gpt_mg.version0_13" "Local5080_qwen-7b_svc-v1.5.4"
run_model "[4/5] Local5080_qwen-7b_svc-v2.0.1" "gpt_mg.version0_12" "Local5080_qwen-7b_svc-v2.0.1"
run_version0_14 "[5/5] PromptGA_v0.14_svc-v2.0.1" "PromptGA_v0.14_svc-v2.0.1"

DET_CMD=(
  python3
  ./utils/det_paper.py
  --generation-jsonl "$GENERATION_JSONL"
  --dataset "$DATASET_PATH"
  --command-column command_kor
  --value-services "$MERGED_VALUE_SERVICES_PATH"
  --function-services "$MERGED_FUNCTION_SERVICES_PATH"
  --strict-paper
  --output-dir "$DET_OUTPUT_DIR"
  --run-name "$RUN_ID"
)

if [ -f "$FORBIDDEN_ACTIONS_PATH" ]; then
  DET_CMD+=(--forbidden-actions "$FORBIDDEN_ACTIONS_PATH")
fi

echo "=== DET Paper ==="
"${DET_CMD[@]}"
