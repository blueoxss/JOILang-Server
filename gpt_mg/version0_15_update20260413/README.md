# version0_15

`version0_15`는 `connected_devices`를 category/tag/location binding으로 prompt에 넣고, 값이 비어 있으면 `datasets/service_list_ver2.0.1.json` 전체를 schema fallback으로 쓰는 PromptGA 워크스페이스입니다.

## 핵심 동작

- `connected_devices`가 있으면 각 device group별로 `category + 전체 서비스 목록 + 사용자 태그 + location`을 prompt에 넣습니다.
- `connected_devices == {}` 이면 `service_schema_fallback`으로 바뀌고, `service_list_ver2.0.1.json` 전체 category/service 목록이 prompt에 들어갑니다.
- 따라서 benchmark CSV에서 `connected_devices` 칼럼이 비어 있어도 `version0_15`는 전체 서비스 스키마를 기준으로 prompt를 만들 수 있습니다.
- `admin_logs`가 없어도 benchmark + GA search만 단독으로 돌릴 수 있습니다.
- `admin_logs`가 있으면 실패 명령을 replay해서 manual feedback rule로 흡수하고, benchmark non-regression을 확인한 뒤 `version0_15_updateYYYYMMDD*` 폴더로 승격할 수 있습니다.

## 자주 쓰는 환경 변수

`demo.py` 또는 `gpt_mg/run.py gpt_mg.version0_15 ...` 경로:

```env
JOI_VERSION015_PYTHON=/abs/path/to/python
JOI_VERSION015_WORKER=/abs/path/to/gpt_mg/version0_13/qwen_local_worker.py
JOI_VERSION015_GENOME=/abs/path/to/gpt_mg/version0_15/results/best_genome_after_feedback.json
```

`gpt_mg/version0_15/scripts/*` 경로:

```env
JOI_V15_LLM_MODE=worker
JOI_V15_WORKER_PATH=/abs/path/to/gpt_mg/version0_13/qwen_local_worker.py
JOI_V15_PYTHON=/abs/path/to/python
JOI_V15_LOCAL_DEVICE=cuda:0
JOI_V15_OPENAI_ENDPOINT=http://127.0.0.1:8000/v1/chat/completions
```

`version0_15/utils/local_llm_client.py`는 `JOI_V15_*`를 먼저 보고, 없으면 `JOI_V14_*`를 fallback으로 사용합니다.

## 빠른 benchmark + GA

`admin_logs`와 상관없이 benchmark/GA만 확인하려면:

```bash
cd /home/andrew/joi-llm/gpt_mg/version0_15

bash scripts/run_full_pipeline.sh \
  --mode quick \
  --llm-mode worker \
  --seed 31
```

좀 더 직접적으로 보고 싶으면:

```bash
python scripts/run_ga_search.py \
  --profile version0_15 \
  --genome-json genomes/example_genome.json \
  --population 4 \
  --gens 3 \
  --sample-size 5 \
  --validation-size 5 \
  --limit 5 \
  --candidate-k 2 \
  --llm-mode worker \
  --seed 31
```

## `admin_logs`가 없어도 되는 통합 업데이트

아래 스크립트는 `admin_logs`가 없으면 benchmark + GA만 수행합니다.

```bash
cd /home/andrew/joi-llm

python gpt_mg/version0_15/scripts/run_admin_feedback_update.py \
  --admin-log-root /tmp/no-admin-logs \
  --benchmark-limit 20 \
  --llm-mode worker \
  --seed 31
```

빠른 smoke 용도:

```bash
python gpt_mg/version0_15/scripts/run_admin_feedback_update.py \
  --admin-log-root /tmp/no-admin-logs \
  --benchmark-limit 1 \
  --ga-population 2 \
  --ga-gens 1 \
  --ga-sample-size 1 \
  --ga-validation-size 1 \
  --benchmark-candidate-k 1 \
  --skip-category-sweep \
  --llm-mode worker \
  --seed 31
```

## `admin_logs`를 반영한 업데이트

Slack JSONL이나 직접 만든 JSON/JSONL/TXT/MD를 `admin_logs` 아래에 두고 실행하면 됩니다.

```bash
python gpt_mg/version0_15/scripts/run_admin_feedback_update.py \
  --admin-log-root admin_logs \
  --benchmark-limit 20 \
  --llm-mode worker \
  --seed 31
```

지원하는 입력 형태:

- `admin_logs/slack/*.jsonl` 같은 Slack DM 로그
- `command_eng`, `command_kor`, `gt`, `connected_devices`, `manual_rules`가 들어 있는 `.json`
- 자유 텍스트 `.txt` 또는 `.md`

구조화된 케이스일수록 replay와 prompt patch 품질이 좋아집니다.

## `demo.py`에서 실행

서버를 켠 뒤:

```bash
curl -s -X POST http://localhost:8000/run_admin_feedback_update \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt_mg.version0_15",
    "admin_log_root": "/tmp/no-admin-logs",
    "benchmark_limit": 20,
    "llm_mode": "worker",
    "seed": 31
  }'
```

promotion이 성공하면 `demo.py`는 `gpt_mg/version0_15_update*` 폴더를 자동으로 `/get_model_list` 결과에 추가합니다.

## 결과 파일

- `results/admin_feedback_update_<timestamp>/summary.json`
- `results/admin_feedback_update_<timestamp>/report.md`
- `results/admin_feedback_update_<timestamp>/admin_cases.csv`
- `results/best_genome_from_ga.json`
- `results/best_genome_after_feedback.json`
- `logs/admin_feedback/manual_feedback.json`
- promotion 성공 시 `gpt_mg/version0_15_updateYYYYMMDD*/results/admin_feedback_update_summary.json`

## 같은 prompt로 논문 모델군 비교하기

현재 `results/best_genome.json` 또는 지정한 genome을 그대로 유지한 채, 모델만 바꿔서 같은 prompt를 비교하려면 `scripts/run_model_suite_benchmark.py`를 사용하면 됩니다.

기본 suite:

- `paper_local5`: `Phi-3.5-mini-instruct`, `Qwen2.5-Coder-7B-Instruct`, `Llama-3.1-8B-Instruct`, `Gemma-2-9B-it`, `Qwen2.5-Coder-14B-Instruct`
- `paper_with_cloud_ref`: 위 5개 + `GPT-4.1-mini`

현재 readiness snapshot은 아래 문서를 기준으로 보는 것이 가장 정확합니다.

- `MODEL_SETUP.md`
- `EXPERIMENT_SETUP.md`

현재 이 워크스페이스에서 바로 same-prompt compare까지 확인된 모델:

- `qwen25_coder_7b`
- `qwen25_coder_14b`

현재 막혀 있는 모델:

- `phi35_mini`
  - cache는 있음
  - row 1 schema-fallback prompt에서 GPU OOM으로 smoke 실패
- `llama31_8b`
  - Hugging Face gated repo
- `gemma2_9b_it`
  - Hugging Face gated repo

먼저 worker runtime과 cache 상태부터 확인:

```bash
cd /home/mgjeong/Desktop/llm/JOILang-Server

export JOI_V15_WORKER_PYTHON=/home/mgjeong/miniconda3/envs/l/bin/python
export JOI_V15_LOCAL_DEVICE=cuda:0

python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --preflight-only \
  --print-worker-info
```

모델 준비와 one-row smoke까지 한 번에 다시 돌리려면:

```bash
python gpt_mg/version0_15_update20260413/scripts/prepare_local_models.py \
  --suite paper_local5 \
  --download-missing
```

지금 바로 되는 단일 모델 compare 예시:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --print-mode compare \
  --strict-availability
```

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_14b \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --print-mode compare \
  --strict-availability
```

지금 바로 되는 same-prompt 다중 모델 compare 예시:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --model-key qwen25_coder_14b \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --print-mode compare \
  --strict-availability
```

dataset 일부를 두 모델로 비교할 때:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --model-key qwen25_coder_14b \
  --start-row 1 \
  --end-row 20 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --print-mode summary
```

full suite를 정의 그대로 호출하고 싶으면:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --skip-unavailable \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --print-mode summary
```

단, `--skip-unavailable`는 preflight에서 `ready`가 아닌 모델만 건너뜁니다. 현재 `phi35_mini`는 cache 기준으로는 ready이지만 smoke에서 OOM이므로, "지금 바로 성공해야 하는" 실험이면 `--model-key qwen25_coder_7b --model-key qwen25_coder_14b`처럼 명시하는 것이 안전합니다.

`local_model_name`을 직접 줄 때는 placeholder가 아니라 실제 snapshot 절대경로를 써야 합니다.

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --print-mode compare \
  --llm-extra-json '{"local_model_name":"/home/mgjeong/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242"}'
```

산출물:

- `results/model_suite_<timestamp>/suite_manifest.json`
- `results/model_suite_<timestamp>/suite_summary.json`
- `results/model_suite_<timestamp>/suite_summary.csv`
- `results/model_suite_<timestamp>/row_comparison.csv`
- `results/model_suite_<timestamp>/failure_reason_summary.csv`
- `results/model_suite_<timestamp>/category_summary.csv`
- 모델별 `*_candidates.csv`, `*_rerank.csv`, `*_summary.json`

참고:

- `--repair-attempts 0`이면 raw same-prompt transfer 비교에 가깝습니다.
- `--preflight`는 실행 전에 모델 cache/endpoint 상태를 먼저 출력하고, `--preflight-only`는 점검만 하고 종료합니다.
- `--strict-availability`를 함께 주면 선택한 모델 중 현재 runtime에서 쓸 수 없는 모델이 있을 때 benchmark를 시작하지 않습니다.
- 현재 기본 `worker` 경로는 `ollama`가 아니라 Hugging Face cache를 사용합니다. 따라서 `ready` 여부는 `ollama list`가 아니라 HF cache 또는 명시한 `local_model_name` 경로 기준으로 판단합니다.
- `--print-mode paths`는 결과 경로만 출력하고, `--print-mode summary`는 모델별 평균 점수를, `--print-mode compare`는 row별 `GT code`, `Generated code`, `det_score`, `failure_reasons`, `diff summary`까지 출력합니다.
- `--print-limit 5`처럼 주면 `compare` 모드에서 앞의 몇 개 row만 콘솔에 출력하고 전체 결과는 CSV에 남길 수 있습니다.
- `--max-workers`는 safe bounded parallel 옵션이지만, worker-backed local model은 GPU 메모리 사용량 때문에 보수적으로 쓰는 편이 좋습니다.
- `--debug-runtime`과 `--print-worker-info`를 주면 worker python, torch, cuda, resolved model path를 더 자세히 볼 수 있습니다.
- `--llm-mode mock`을 주면 실제 모델 로딩 없이 결과 파일 구조만 smoke test할 수 있습니다.
- `paper_with_cloud_ref`에서 `GPT-4.1-mini`를 쓰려면 `--llm-mode openai`와 `--llm-endpoint`를 같이 지정하거나, `JOI_V15_OPENAI_ENDPOINT` 및 bearer token 환경 변수를 설정해야 합니다.
- worker별 추가 옵션은 `--llm-extra-json '{"local_device":"cuda:0","local_load_in_4bit":true}'`처럼 줄 수 있습니다.

## 주의할 점

- `demo.py`에서는 `connected_devices == {}` 요청이 마지막 요청 재사용으로 동작합니다.
- 반대로 `version0_15/scripts/*`에서는 `connected_devices == {}` 가 곧 schema fallback입니다.
- 즉 API 테스트와 benchmark/GA 스크립트는 빈 `connected_devices`의 의미가 다릅니다.
