# version0_15

`version0_15_update20260413`는 `connected_devices`를 category/tag/location binding으로 prompt에 넣고, 필요할 때 retrieval pre-mapping으로 top-k category만 추려 `service_list_snippet`에 넣을 수 있는 PromptGA 워크스페이스입니다. 기본값은 연구 비교를 위해 기존과 같은 full schema fallback입니다.

## 핵심 동작

- `connected_devices`가 있으면 각 device group별로 `category + 전체 서비스 목록 + 사용자 태그 + location`을 prompt에 넣습니다.
- `connected_devices == {}` 이면 기본값은 `service_schema_fallback`이고, `service_list_ver2.0.1.json` 전체 category/service 목록이 prompt에 들어갑니다.
- retrieval pre-mapping을 명시적으로 켜면 학습된 retrieval bundle이 뽑은 top-k category만 `service_retrieval_fallback`으로 prompt에 들어갑니다.
- retrieval asset이 없거나 retrieval worker가 실패하면 자동으로 `service_schema_fallback`으로 내려갑니다.
- 따라서 같은 row subset에 대해 baseline full schema와 retrieval top-k prompt를 연구용으로 직접 비교할 수 있습니다.
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

## Retrieval Pre-mapping

`service_list_snippet`은 이제 prompt block 안에서 직접 진화시키는 텍스트가 아니라, runtime에서 강제로 채워 넣는 capability scope입니다.

- GA가 바꿀 수 있는 것은 block 본문뿐이고, retrieval shortlist 생성은 `utils/pipeline_common.py`의 runtime path에서 고정됩니다.
- 즉 prompt search를 돌려도 retrieval pre-mapping 자체를 제거하거나 다른 구조로 바꾸지 못합니다.
- 기본 service context mode는 `schema_fallback`입니다.
  - `connected_devices` 있음: 항상 `connected_devices_only`
  - `connected_devices` 비어 있음 + 명시적으로 retrieval 사용: `service_retrieval_fallback`
  - 그 외: `service_schema_fallback`

기본 retrieval asset 탐색 순서:

- `gpt_mg/version0_15_update20260413/retrieval_assets/...`
- 없으면 sibling repo인 `../ModelMagementApp/...`

즉 학습된 retrieval model/bundle을 굳이 `JOILang-Server` 안으로 복사하지 않아도 됩니다. 그대로 sibling `ModelMagementApp` 경로를 참조합니다. 원하면 `JOI_V15_RETRIEVAL_JSON`, `JOI_V15_RETRIEVAL_BUNDLE_DIR`, `JOI_V15_RETRIEVAL_MODEL_DIR`로 override할 수 있습니다.

추가 환경 변수:

```env
JOI_V15_SERVICE_CONTEXT_MODE=schema_fallback
JOI_V15_RETRIEVAL_TOPK=10
JOI_V15_RETRIEVAL_MODE=hybrid
JOI_V15_RETRIEVAL_DEVICE=cpu
JOI_V15_RETRIEVAL_PYTHON=/home/mgjeong/miniconda3/envs/l/bin/python
JOI_V15_RETRIEVAL_JSON=/abs/path/to/service_list_ver2.0.1_retrieval_eng.json
JOI_V15_RETRIEVAL_BUNDLE_DIR=/abs/path/to/embedding_result_v5_ver2.0.1
JOI_V15_RETRIEVAL_MODEL_DIR=/abs/path/to/BAAI_bge-m3__service_list_ver2.0.1_retrieval_eng
```

빠르게 snippet source와 prompt 길이를 비교하려면:

```bash
python gpt_mg/version0_15_update20260413/scripts/inspect_service_context.py \
  --row-no 1 \
  --mode schema_fallback \
  --mode retrieval_fallback \
  --retrieval-topk 10 \
  --retrieval-device cpu
```

이 스크립트는 다음을 기록합니다.

- `service_list_snippet_source`
- `service_list_device_count`
- `service_list_retrieval_status`
- `service_list_retrieval_categories`
- `service_list_snippet_chars`
- `rendered_prompt_chars`

출력 파일:

- `results/service_context_inspection/service_context_summary.json`
- `results/service_context_inspection/service_context_rows.csv`

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

기본 실행 환경:

```bash
cd /home/mgjeong/Desktop/llm/JOILang-Server

export JOI_V15_WORKER_PYTHON=/home/mgjeong/miniconda3/envs/l/bin/python
export JOI_V15_LOCAL_DEVICE=cuda:0
```

먼저 worker runtime과 cache 상태부터 확인:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --preflight-only \
  --print-worker-info
```

모델 준비와 one-row smoke를 다시 돌리려면:

```bash
python gpt_mg/version0_15_update20260413/scripts/prepare_local_models.py \
  --suite paper_local5 \
  --download-missing
```

## 공정한 비교 원칙

- 정확도만 보지 말고 `DET`, `warm latency`, `cold load time`, `prompt tokens`, `peak VRAM`, `OOM/failure rate`를 함께 봅니다.
- 여러 모델을 동시에 VRAM에 상주시킨 상태의 latency 비교는 권장하지 않습니다.
- 공정한 latency 비교는 `--paper-fair-mode` 또는 `--latency-isolation-mode fresh_worker`로 모델별 fresh worker를 띄운 뒤 warmup 후 측정합니다.
- `cold_load_sec`는 fresh worker에서 warmup 첫 요청에 걸린 시간을 사용합니다.
- `warm_latency_*`는 warmup 이후 evaluation row들만 기준으로 계산합니다.
- `prompt_tokens`는 모델별 tokenizer 기준으로 측정되므로 같은 문자열 prompt여도 모델마다 달라질 수 있습니다.

## 가장 많이 쓰는 명령

single row compare:

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

single row compare with stricter DET profile:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --row-no 10 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --det-profile strict \
  --disable-retrieval-premapping \
  --print-mode compare \
  --strict-availability
```

single row compare with retrieval pre-mapping:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --enable-retrieval-premapping \
  --retrieval-topk 10 \
  --retrieval-device cpu \
  --print-mode compare \
  --strict-availability
```

force old full-schema behavior for ablation:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --disable-retrieval-premapping \
  --print-mode compare \
  --strict-availability
```

row range compare:

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

single category:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --category 1 \
  --limit 5 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --print-mode summary
```

multiple categories:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --category 1 \
  --category 2 \
  --limit-per-category 10 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --print-mode summary
```

category file:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --category-file /tmp/joi_categories.txt \
  --limit-per-category 10 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --print-mode summary
```

available categories:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --list-categories
```

full dataset:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --model-key qwen25_coder_14b \
  --candidate-k 1 \
  --repair-attempts 0 \
  --print-mode summary
```

paper-fair mode:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --model-key qwen25_coder_14b \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --paper-fair-mode \
  --export-paper-artifacts \
  --print-mode summary \
  --strict-availability
```

explicit warmup row:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --start-row 1 \
  --end-row 20 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --measure-latency \
  --latency-isolation-mode fresh_worker \
  --warmup-row-no 1 \
  --print-mode summary
```

wall-clock oriented parallel mode:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --model-key qwen25_coder_14b \
  --start-row 1 \
  --end-row 20 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --max-workers 2 \
  --print-mode summary
```

이 parallel 모드는 전체 실험 시간을 줄이기 위한 것이고, latency 공정 비교용 숫자로 해석하면 안 됩니다.

paper figure export only:

```bash
python gpt_mg/version0_15_update20260413/scripts/export_paper_figures.py \
  --results-dir /home/mgjeong/Desktop/llm/JOILang-Server/gpt_mg/version0_15_update20260413/results/model_suite_20260421_121042
```

GT code와 생성된 JOICode를 좌우 비교하는 HTML/PDF 리포트:

```bash
python gpt_mg/version0_15_update20260413/scripts/export_joi_code_side_by_side_report.py \
  --results-dir /home/mgjeong/Desktop/llm/JOILang-Server/gpt_mg/version0_15_update20260413/results/model_suite_20260423_222827 \
  --model-key qwen25_coder_14b \
  --category 1 \
  --category 2
```

이 리포트는 아래를 함께 보여줍니다.

- row별 `GT JOICode` vs `Generated JOICode` 좌우 배치
- `DET`, `GT similarity`, `GT service coverage`, `receiver coverage`, `dataflow`, `numeric grounding`, `enum grounding`
- `prompt_tokens`, `completion_tokens`, `llm_latency_sec`, `total_pipeline_sec`, `tokens_per_sec`, `peak_vram_gb`
- `failure_reasons`, retrieval snippet source, retrieval top-k category
- summary 카드와 선택 row CSV

기본 출력:

- `results/model_suite_<timestamp>/side_by_side_report_<model_key>/report.html`
- `results/model_suite_<timestamp>/side_by_side_report_<model_key>/report.pdf`
- `results/model_suite_<timestamp>/side_by_side_report_<model_key>/report_summary.json`
- `results/model_suite_<timestamp>/side_by_side_report_<model_key>/selected_rows.csv`

## 주요 산출물

- `results/model_suite_<timestamp>/suite_manifest.json`
- `results/model_suite_<timestamp>/suite_summary.csv`
- `results/model_suite_<timestamp>/row_comparison.csv`
- `results/model_suite_<timestamp>/latency_breakdown.csv`
- `results/model_suite_<timestamp>/failure_reason_summary.csv`
- `results/model_suite_<timestamp>/generation_error_summary.csv`
- `results/model_suite_<timestamp>/category_summary.csv`
- `results/model_suite_<timestamp>/category_model_comparison.csv`
- `results/model_suite_<timestamp>/main_model_comparison.csv`
- `results/model_suite_<timestamp>/tradeoff_summary.csv`
- `results/model_suite_<timestamp>/latency_summary.csv`
- `results/model_suite_<timestamp>/vram_summary.csv`
- `results/model_suite_<timestamp>/tokenizer_summary.csv`
- `results/model_suite_<timestamp>/paper_metrics_summary.json`
- `results/model_suite_<timestamp>/paper_figures/det_vs_warm_latency.png`
- `results/model_suite_<timestamp>/paper_figures/det_vs_prompt_tokens.png`
- `results/model_suite_<timestamp>/paper_figures/category_det_vs_warm_latency.png`
- `results/model_suite_<timestamp>/paper_figures/category_det_vs_prompt_tokens.png`
- `results/model_suite_<timestamp>/paper_figures/category_metric_panels.png`

참고:

- `--repair-attempts 0`이면 raw same-prompt transfer 비교에 가깝습니다.
- `--strict-availability`를 함께 주면 선택한 모델 중 현재 runtime에서 쓸 수 없는 모델이 있을 때 benchmark를 시작하지 않습니다.
- 현재 기본 `worker` 경로는 `ollama`가 아니라 Hugging Face cache를 사용합니다.
- `--print-mode compare`는 row별 `GT code`, `Generated code`, `det_score`, `failure_reasons`, `prompt_tokens`, `llm_latency_sec`, `peak_vram_gb`, `diff summary`를 같이 보여줍니다.
- `--det-profile strict`를 주면 기존 legacy 점수는 그대로 보존한 채, GT service coverage, receiver coverage, dataflow, numeric grounding을 더 엄격하게 반영한 strict scoring으로 rerank와 summary를 계산합니다.
- strict benchmark 결과의 `row_comparison.csv`에는 `__det_profile`, `__det_gt_service_coverage`, `__det_gt_receiver_coverage`, `__det_dataflow_score`, `__det_numeric_grounding`, `__det_enum_grounding` 컬럼이 추가됩니다.

DET legacy/strict 비교 분석:

```bash
python gpt_mg/version0_15_update20260413/scripts/analyze_det_profiles.py \
  --results-dir gpt_mg/version0_15_update20260413/results/model_suite_20260423_142658 \
  --results-dir gpt_mg/version0_15_update20260413/results/model_suite_20260423_143911 \
  --out-dir gpt_mg/version0_15_update20260413/results/det_profile_analysis_current \
  --print-json
```
- `--llm-mode mock`을 주면 실제 모델 로딩 없이 결과 파일 구조나 category filter 동작을 smoke test할 수 있습니다.
- `paper_with_cloud_ref`에서 `GPT-4.1-mini`를 쓰려면 `--llm-mode openai`와 `--llm-endpoint` 또는 관련 env 설정이 필요합니다.
- `local_model_name`을 직접 줄 때는 placeholder가 아니라 실제 snapshot 절대경로를 써야 합니다.
- `export_paper_figures.py`는 `category_summary.csv`가 있으면 category별 `DET vs warm latency`, `DET vs prompt tokens`, category metric panel figure까지 함께 생성합니다.
- `--limit`은 전체 selected rows에 대한 global cap이고, `--limit-per-category`는 category별 cap입니다.

## 주의할 점

- `demo.py`에서는 `connected_devices == {}` 요청이 마지막 요청 재사용으로 동작합니다.
- 반대로 `version0_15/scripts/*`에서는 `connected_devices == {}` 가 기본적으로 schema fallback이고, retrieval pre-mapping을 명시적으로 켰을 때만 retrieval shortlist가 우선됩니다.
- 즉 API 테스트와 benchmark/GA 스크립트는 빈 `connected_devices`의 의미가 다릅니다.
