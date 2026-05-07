#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
PYTHON_BIN="${JOI_V15_WORKER_PYTHON:-${PYTHON:-python}}"

cd "${SERVER_ROOT}"
exec "${PYTHON_BIN}" gpt_mg/version0_15_update20260413/scripts/run_local_prompt_ga_study.py "$@"
