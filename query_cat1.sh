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

echo "=== [1/3] CAP_gpt4.1_mini_old ==="
curl -s -X POST http://localhost:8000/generate_joi_code \
  -H "Content-Type: application/json" \
  -d '{
    "sentence": "'"$SENTENCE"'",
    "model": "gpt4.1-mini",
    "connected_devices": '"$CONNECTED_DEVICES"',
    "current_time": "'"$TIME"'",
    "other_params": [{"selected_model": "CAP_gpt4.1_mini_old"}]
  }'
echo -e "\n"

echo "=== [2/3] JOI_gpt4.1_mini (version0_6) ==="
curl -s -X POST http://localhost:8000/generate_joi_code \
  -H "Content-Type: application/json" \
  -d '{
    "sentence": "'"$SENTENCE"'",
    "model": "gpt_mg.version0_6",
    "connected_devices": '"$CONNECTED_DEVICES"',
    "current_time": "'"$TIME"'",
    "other_params": [{"selected_model": "JOI_gpt4.1_mini"}]
  }'
echo -e "\n"

echo "=== [3/3] local_8b (version0_13) ==="
curl -s -X POST http://localhost:8000/generate_joi_code \
  -H "Content-Type: application/json" \
  -d '{
    "sentence": "'"$SENTENCE"'",
    "model": "gpt_mg.version0_13",
    "connected_devices": '"$CONNECTED_DEVICES"',
    "current_time": "'"$TIME"'",
    "other_params": [{"selected_model": "local_8b"}]
  }'
echo -e "\n"
