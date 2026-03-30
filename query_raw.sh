#!/bin/bash
set -euo pipefail

ROW_NO="${1:-1}"
TIME="${2:-2026-03-31T12:00:00}"
DATASET_PATH="./datasets/JOICommands-280.csv"
VALUE_SERVICES_PATH="./gpt_mg/version0_13/service_list_ver1.5.4_value.json"
FUNCTION_SERVICES_PATH="./gpt_mg/version0_13/service_list_ver1.5.4_function.json"
FORBIDDEN_ACTIONS_PATH="./datasets/forbidden_actions.json"
RUN_ID="raw_row${ROW_NO}_$(date +%Y%m%d_%H%M%S)"
GENERATION_DIR="./results/generation/${RUN_ID}"
GENERATION_JSONL="${GENERATION_DIR}/generation.jsonl"
DET_OUTPUT_DIR="./results/det_paper"

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

echo "=== Row $ROW_NO ==="
echo "SENTENCE: $SENTENCE"
echo "RUN_ID: $RUN_ID"
echo "GENERATION_JSONL: $GENERATION_JSONL"
echo

run_model "[1/3] CAP_gpt4.1_mini_old" "gpt4.1-mini" "CAP_gpt4.1_mini_old"
run_model "[2/3] JOI_gpt4.1_mini (version0_6)" "gpt_mg.version0_6" "JOI_gpt4.1_mini"
run_model "[3/3] local_8b (version0_13)" "gpt_mg.version0_13" "local_8b"

DET_CMD=(
  python3
  ./utils/det_paper.py
  --generation-jsonl "$GENERATION_JSONL"
  --dataset "$DATASET_PATH"
  --command-column command_kor
  --value-services "$VALUE_SERVICES_PATH"
  --function-services "$FUNCTION_SERVICES_PATH"
  --strict-paper
  --output-dir "$DET_OUTPUT_DIR"
  --run-name "$RUN_ID"
)

if [ -f "$FORBIDDEN_ACTIONS_PATH" ]; then
  DET_CMD+=(--forbidden-actions "$FORBIDDEN_ACTIONS_PATH")
fi

echo "=== DET Paper ==="
"${DET_CMD[@]}"
