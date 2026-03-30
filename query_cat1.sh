#!/bin/bash
set -euo pipefail

SENTENCE="불을 켜줘"
TIME="2026-03-31T12:00:00"
CONNECTED_DEVICES="$(python - <<'PY'
import json
with open("./datasets/things.json", encoding="utf-8") as f:
    print(json.dumps(json.load(f), ensure_ascii=False, separators=(",", ":")))
PY
)"

echo "=== [1/4] CAP-old_gpt4.1-mini_svc-v1.5.4 ==="
curl -s -X POST http://localhost:8000/generate_joi_code \
  -H "Content-Type: application/json" \
  -d '{
    "sentence": "'"$SENTENCE"'",
    "model": "gpt4.1-mini",
    "connected_devices": '"$CONNECTED_DEVICES"',
    "current_time": "'"$TIME"'",
    "other_params": [{"selected_model": "CAP-old_gpt4.1-mini_svc-v1.5.4"}]
  }'
echo -e "\n"

echo "=== [2/4] JOI_gpt4.1-mini_v1.5.4 ==="
curl -s -X POST http://localhost:8000/generate_joi_code \
  -H "Content-Type: application/json" \
  -d '{
    "sentence": "'"$SENTENCE"'",
    "model": "gpt_mg.version0_6",
    "connected_devices": '"$CONNECTED_DEVICES"',
    "current_time": "'"$TIME"'",
    "other_params": [{"selected_model": "JOI_gpt4.1-mini_v1.5.4"}]
  }'
echo -e "\n"

echo "=== [3/4] Local5080_qwen-7b_svc-v1.5.4 ==="
curl -s -X POST http://localhost:8000/generate_joi_code \
  -H "Content-Type: application/json" \
  -d '{
    "sentence": "'"$SENTENCE"'",
    "model": "gpt_mg.version0_13",
    "connected_devices": '"$CONNECTED_DEVICES"',
    "current_time": "'"$TIME"'",
    "other_params": [{"selected_model": "Local5080_qwen-7b_svc-v1.5.4"}]
  }'
echo -e "\n"

echo "=== [4/4] Local5080_qwen-7b_svc-v2.0.1 ==="
curl -s -X POST http://localhost:8000/generate_joi_code \
  -H "Content-Type: application/json" \
  -d '{
    "sentence": "'"$SENTENCE"'",
    "model": "gpt_mg.version0_12",
    "connected_devices": '"$CONNECTED_DEVICES"',
    "current_time": "'"$TIME"'",
    "other_params": [{"selected_model": "Local5080_qwen-7b_svc-v2.0.1"}]
  }'
echo -e "\n"
