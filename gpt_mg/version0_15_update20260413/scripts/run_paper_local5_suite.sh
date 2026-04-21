#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

python "${VERSION_ROOT}/scripts/prepare_local_models.py" \
  --suite paper_local5 \
  --download-missing

python "${VERSION_ROOT}/scripts/run_model_suite_benchmark.py" \
  --suite paper_local5 \
  --skip-unavailable \
  "$@"
