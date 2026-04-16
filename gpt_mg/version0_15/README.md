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

## 주의할 점

- `demo.py`에서는 `connected_devices == {}` 요청이 마지막 요청 재사용으로 동작합니다.
- 반대로 `version0_15/scripts/*`에서는 `connected_devices == {}` 가 곧 schema fallback입니다.
- 즉 API 테스트와 benchmark/GA 스크립트는 빈 `connected_devices`의 의미가 다릅니다.
