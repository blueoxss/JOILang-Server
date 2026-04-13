#!/bin/bash
set -euo pipefail

usage() {
  echo "Usage: ./query_raw.sh <row_no|raw_command> [current_time]" >&2
  echo "Example: ./query_raw.sh 1" >&2
  echo 'Example: ./query_raw.sh "아침 9시마다 사람이 있으면 블라인드를 열어줘."' >&2
}

trim_text() {
  python3 - "$1" <<'PY'
import sys

print(sys.argv[1].strip())
PY
}

if [ "$#" -gt 2 ]; then
  usage
  exit 1
fi

INPUT_ARG="${1:-1}"
TIME="${2:-2026-03-31T12:00:00}"
DATASET_PATH="./datasets/JOICommands-280.csv"
FORBIDDEN_ACTIONS_PATH="./datasets/forbidden_actions.json"
DET_OUTPUT_DIR="./results/det_paper"
V14_ROOT="./gpt_mg/version0_14"
V14_CANDIDATE_K="${V14_CANDIDATE_K:-3}"
V14_REPAIR_THRESHOLD="${V14_REPAIR_THRESHOLD:-99}"
V14_REPAIR_ATTEMPTS="${V14_REPAIR_ATTEMPTS:-2}"
ROW_NO="0"
DATASET_INDEX=""
MATCHED_ROW_NO=""
MATCHED_DATASET_INDEX=""
MATCHED_COLUMN=""
INPUT_MODE=""
SENTENCE=""
DET_COMMAND_COLUMN="command_kor"
HAS_REFERENCE=0

if [[ "$INPUT_ARG" =~ ^[0-9]+$ ]] && [ "$INPUT_ARG" -ge 1 ]; then
  INPUT_MODE="row"
  ROW_NO="$INPUT_ARG"
  IFS=$'\t' read -r SENTENCE DATASET_INDEX <<< "$(python3 - "$ROW_NO" "$DATASET_PATH" <<'PY'
import csv
import sys
from pathlib import Path

target = int(sys.argv[1])
csv_path = Path(sys.argv[2])

with csv_path.open(encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for position, row in enumerate(reader, start=1):
        row_index = row.get("index", "").strip()
        if position == target or (row_index.isdigit() and int(row_index) == target):
            command = row.get("command_kor", "").strip()
            dataset_index = row.get("index", "").strip()
            print(f"{command}\t{dataset_index}")
            break
    else:
        raise SystemExit(f"Row {target} not found in {csv_path}")
PY
)"
  MATCHED_ROW_NO="$ROW_NO"
  MATCHED_DATASET_INDEX="$DATASET_INDEX"
  MATCHED_COLUMN="command_kor"
  HAS_REFERENCE=1
else
  INPUT_MODE="raw_command"
  SENTENCE="$(trim_text "$INPUT_ARG")"
  if [ -z "$SENTENCE" ]; then
    usage
    exit 1
  fi

  IFS=$'\t' read -r MATCHED_ROW_NO MATCHED_DATASET_INDEX MATCHED_COLUMN <<< "$(python3 - "$DATASET_PATH" "$SENTENCE" <<'PY'
import csv
import sys
from pathlib import Path

csv_path = Path(sys.argv[1])
sentence = sys.argv[2].strip()

with csv_path.open(encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for position, row in enumerate(reader, start=1):
        for column in ("command_kor", "command_eng"):
            if sentence == row.get(column, "").strip():
                dataset_index = row.get("index", "").strip()
                print(f"{position}\t{dataset_index}\t{column}")
                raise SystemExit(0)

print("\t\t")
PY
)"

  if [ "$MATCHED_COLUMN" = "command_kor" ] || [ "$MATCHED_COLUMN" = "command_eng" ]; then
    DET_COMMAND_COLUMN="$MATCHED_COLUMN"
    HAS_REFERENCE=1
  fi
fi

if [ -z "$SENTENCE" ]; then
  echo "Input command is empty after trimming whitespace." >&2
  exit 1
fi

if [ "$INPUT_MODE" = "row" ]; then
  RUN_ID="raw_row${ROW_NO}_$(date +%Y%m%d_%H%M%S)"
else
  RUN_ID="raw_text_$(date +%Y%m%d_%H%M%S)"
fi

GENERATION_DIR="./results/generation/${RUN_ID}"
GENERATION_JSONL="${GENERATION_DIR}/generation.jsonl"
MERGED_VALUE_SERVICES_PATH="${GENERATION_DIR}/merged_value_services.json"
MERGED_FUNCTION_SERVICES_PATH="${GENERATION_DIR}/merged_function_services.json"
V14_ROW_DATASET="${GENERATION_DIR}/version0_14_row.csv"
V14_CANDIDATES_CSV="${GENERATION_DIR}/version0_14_candidates.csv"
V14_RERANK_CSV="${GENERATION_DIR}/version0_14_rerank.csv"

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

  python3 - "$GENERATION_JSONL" "$ROW_NO" "$DATASET_INDEX" "$INPUT_MODE" "$SENTENCE" "$TIME" "$label" "$request_model" "$selected_model" "$response_json" <<'PY'
import json
import sys
from pathlib import Path

output_path = Path(sys.argv[1])
row_no_text = sys.argv[2].strip()
dataset_index = sys.argv[3].strip()
input_mode = sys.argv[4]
sentence = sys.argv[5]
current_time = sys.argv[6]
label = sys.argv[7]
request_model = sys.argv[8]
selected_model = sys.argv[9]
response_json = sys.argv[10]

try:
    row_no = int(row_no_text)
except ValueError:
    row_no = 0

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
    "dataset_index": dataset_index,
    "input_mode": input_mode,
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
  python3 - "$INPUT_MODE" "$ROW_NO" "$MATCHED_ROW_NO" "$SENTENCE" "$DATASET_PATH" "$V14_ROW_DATASET" "$CONNECTED_DEVICES" <<'PY'
import csv
import json
import sys
from pathlib import Path

input_mode = sys.argv[1]
row_no_text = sys.argv[2].strip()
matched_row_no_text = sys.argv[3].strip()
sentence = sys.argv[4]
src = Path(sys.argv[5])
dst = Path(sys.argv[6])
connected_devices = json.loads(sys.argv[7])

target = None
if input_mode == "row" and row_no_text.isdigit():
    target = int(row_no_text)
elif matched_row_no_text.isdigit():
    target = int(matched_row_no_text)

with src.open(encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames or [])
    if "connected_devices" not in fieldnames:
        fieldnames.append("connected_devices")

    selected_row = None
    if target is not None:
        for position, row in enumerate(reader, start=1):
            row_index = str(row.get("index", "")).strip()
            if position == target or (row_index.isdigit() and int(row_index) == target):
                selected_row = dict(row)
                break

    if selected_row is None and input_mode == "row":
        raise SystemExit(f"Row {target} not found in {src}")

    if selected_row is None:
        selected_row = {key: "" for key in fieldnames}
        selected_row["index"] = "0"
        selected_row["category"] = "raw"
        selected_row["command_kor"] = sentence
        selected_row["command_eng"] = sentence
        selected_row["gt_raw"] = ""
        selected_row["gt"] = ""

    selected_row["connected_devices"] = json.dumps(connected_devices, ensure_ascii=False)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({key: selected_row.get(key, "") for key in fieldnames})
PY
}

build_version0_14_response() {
  local rerank_csv="$1"
  local genome_json="$2"
  python3 - "$rerank_csv" "$genome_json" "$INPUT_MODE" "$MATCHED_ROW_NO" <<'PY'
import csv
import json
import sys
from pathlib import Path

rerank_csv = Path(sys.argv[1])
genome_json = sys.argv[2]
input_mode = sys.argv[3]
matched_row_no = sys.argv[4].strip()

if input_mode == "row":
    resolved_input_mode = "dataset_row_command_eng_with_connected_devices_from_things_json"
elif matched_row_no:
    resolved_input_mode = "raw_command_matched_dataset_row_with_connected_devices_from_things_json"
else:
    resolved_input_mode = "raw_command_synthetic_single_row_with_connected_devices_from_things_json"

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
        "input_mode": resolved_input_mode,
    },
}
print(json.dumps(response, ensure_ascii=False))
PY
}

run_model() {
  local label="$1"
  local request_model="$2"
  local selected_model="$3"
  local payload

  echo "=== ${label} ==="
  payload="$(python3 - "$SENTENCE" "$request_model" "$CONNECTED_DEVICES" "$TIME" "$selected_model" <<'PY'
import json
import sys

sentence = sys.argv[1]
request_model = sys.argv[2]
connected_devices = json.loads(sys.argv[3])
current_time = sys.argv[4]
selected_model = sys.argv[5]

print(json.dumps({
    "sentence": sentence,
    "model": request_model,
    "connected_devices": connected_devices,
    "current_time": current_time,
    "other_params": [{"selected_model": selected_model}],
}, ensure_ascii=False))
PY
)"
  local response
  response="$(curl -s -X POST http://localhost:8000/generate_joi_code \
    -H "Content-Type: application/json" \
    -d "$payload")"
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

if [ "$INPUT_MODE" = "row" ]; then
  echo "=== Row $ROW_NO ==="
else
  echo "=== Raw Command ==="
fi
echo "INPUT_MODE: $INPUT_MODE"
if [ -n "$MATCHED_ROW_NO" ]; then
  echo "MATCHED_DATASET_ROW: ${MATCHED_ROW_NO} (${MATCHED_COLUMN})"
else
  echo "MATCHED_DATASET_ROW: none"
fi
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
  --command-column "$DET_COMMAND_COLUMN"
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
if [ "$HAS_REFERENCE" -eq 1 ]; then
  "${DET_CMD[@]}"
else
  echo "Skipped: raw command does not exactly match a dataset command, so there is no reference script for DET scoring."
fi
