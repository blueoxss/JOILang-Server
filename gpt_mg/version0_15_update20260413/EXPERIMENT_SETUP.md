# EXPERIMENT_SETUP

`version0_15_update20260413`에서 같은 prompt를 유지한 채 paper local suite를 공정하게 비교하는 실험 절차를 정리합니다.

## 1. 핵심 원칙

- runtime은 기본적으로 `Ollama`가 아니라 Hugging Face cache + local worker입니다.
- same-prompt benchmarking이 중심입니다.
- latency 공정 비교는 여러 모델을 동시에 VRAM에 올린 상태로 하지 않습니다.
- 권장 비교 축:
  - `DET`
  - `warm latency`
  - `cold load time`
  - `prompt tokens`
  - `peak VRAM`
  - `OOM/failure rate`

## 2. cold vs warm 정의

- `cold_load_sec`
  - fresh worker에서 warmup 첫 요청에 걸린 시간
  - worker start + model load + 첫 요청 setup이 포함된 cold-start 지표
- `warm_latency_mean/p50/p95`
  - warmup 이후 evaluation rows만 기준
  - 같은 모델이 이미 메모리에 올라간 상태에서의 row-level LLM latency

## 3. prompt token 측정 방식

- `prompt_tokens`는 각 모델 tokenizer 기준으로 계산됩니다.
- 같은 문자열 prompt라도 모델마다 token 수가 다를 수 있습니다.
- row-level `prompt_tokens`는 그 row를 처리하는 동안 사용된 LLM call들의 총합입니다.
  - `candidate_k=1`, `repair_attempts=0`이면 사실상 단일 generation call과 같습니다.
  - `candidate_k>1` 또는 repair가 있으면 pipeline 전체 token cost가 합산됩니다.
- `--limit`은 전체 selected rows에 대한 global cap이고, `--limit-per-category`는 category별 balanced cap입니다.

## 4. VRAM / OOM 측정 방식

- worker가 `torch.cuda.max_memory_allocated` 기반 peak VRAM을 반환합니다.
- row-level `peak_vram_gb`는 그 row 처리 중 관찰된 최대값입니다.
- summary의 `peak_vram_gb_max`는 모델 전체 row 중 최대값입니다.
- OOM은 `cuda_oom`으로 분류됩니다.

주요 generation failure taxonomy:

- `cuda_oom`
- `cpu_fallback_timeout`
- `invalid_json`
- `worker_crash`
- `gated_model`
- `missing_cache`
- `incompatible_runtime`
- `local_llm_error`

## 5. 권장 환경 변수

```bash
cd /home/mgjeong/Desktop/llm/JOILang-Server

export JOI_V15_WORKER_PYTHON=/home/mgjeong/miniconda3/envs/l/bin/python
export JOI_V15_LOCAL_DEVICE=cuda:0
```

## 6. paper_local5 model key

- `phi35_mini`
- `qwen25_coder_7b`
- `llama31_8b`
- `gemma2_9b_it`
- `qwen25_coder_14b`

현재 바로 같은 prompt compare까지 확인된 runnable subset:

- `qwen25_coder_7b`
- `qwen25_coder_14b`

## 7. 가장 먼저 할 점검

preflight:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --preflight-only \
  --print-worker-info
```

model preparation:

```bash
python gpt_mg/version0_15_update20260413/scripts/prepare_local_models.py \
  --suite paper_local5 \
  --download-missing
```

## 8. 실행 예시

single row:

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

row range:

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

specific category:

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

fair latency mode:

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

explicit warmup control:

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

wall-clock-oriented parallel mode:

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

주의:

- 이 parallel 모드는 wall-clock 단축용입니다.
- fair latency 비교용 결과로 쓰면 안 됩니다.

export-paper-artifacts:

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
  --print-mode summary
```

standalone figure export:

```bash
python gpt_mg/version0_15_update20260413/scripts/export_paper_figures.py \
  --results-dir /home/mgjeong/Desktop/llm/JOILang-Server/gpt_mg/version0_15_update20260413/results/model_suite_20260421_121042
```

## 9. compare mode에서 보는 정보

`--print-mode compare`는 row마다 아래를 출력합니다.

- row id
- input command
- category
- GT code
- generated code
- DET score
- det pass / exact / similarity
- failure reasons
- prompt tokens
- llm latency
- peak VRAM
- concise diff summary

## 10. 결과 파일

기본 benchmark output:

- `suite_manifest.json`
- `suite_summary.json`
- `suite_summary.csv`
- `row_comparison.csv`
- `failure_reason_summary.csv`
- `generation_error_summary.csv`
- `category_summary.csv`
- `category_model_comparison.csv`
- `latency_breakdown.csv`
- `main_model_comparison.csv`
- `tradeoff_summary.csv`
- `latency_summary.csv`
- `vram_summary.csv`
- `tokenizer_summary.csv`
- `paper_metrics_summary.json`

모델별 raw outputs:

- `*_candidates.csv`
- `*_rerank.csv`
- `*_summary.json`
- fair mode일 때 `*_warmup_candidates.csv`
- fair mode일 때 `*_warmup_summary.json`

figure export:

- `paper_figures/det_vs_warm_latency.png`
- `paper_figures/det_vs_warm_latency.pdf`
- `paper_figures/det_vs_prompt_tokens.png`
- `paper_figures/det_vs_prompt_tokens.pdf`
- `paper_figures/det_vs_peak_vram.png`
- `paper_figures/paper_summary_bars.png`
- `paper_figures/category_det_vs_warm_latency.png`
- `paper_figures/category_det_vs_warm_latency.pdf`
- `paper_figures/category_det_vs_prompt_tokens.png`
- `paper_figures/category_det_vs_prompt_tokens.pdf`
- `paper_figures/category_metric_panels.png`
- `paper_figures/category_metric_panels.pdf`
- `paper_figures/paper_figures_summary.json`

카테고리 figure 참고:

- `category_summary.csv`가 존재하면 category별 trade-off figure가 같이 생성됩니다.
- `category_det_vs_warm_latency.*`
  - category별 subplot에서 모델 간 `DET vs warm latency`를 비교합니다.
- `category_det_vs_prompt_tokens.*`
  - category별 subplot에서 모델 간 `DET vs prompt tokens`를 비교합니다.
- `category_metric_panels.*`
  - category별 `avg_det_score`, `det_pass_rate`, `warm_latency_p50`, `avg_prompt_tokens`를 grouped bar로 비교합니다.

## 11. 지금 기준 추천 실험 순서

1. `--preflight-only`로 cache/runtime을 확인합니다.
2. `prepare_local_models.py --download-missing`로 local suite 준비 상태를 업데이트합니다.
3. `candidate-k=1`, `repair-attempts=0`으로 raw same-prompt transfer를 먼저 봅니다.
4. `--paper-fair-mode`로 cold/warm/prompt/VRAM 축을 같이 수집합니다.
5. 필요한 경우 repair를 켠 pipeline utility 비교를 별도 실험으로 분리합니다.

## 12. 알려진 제한사항

- `phi35_mini`는 현재 row 1 schema fallback prompt에서 OOM이 발생할 수 있습니다.
- `llama31_8b`, `gemma2_9b_it`는 Hugging Face gated access가 필요합니다.
- benchmark는 기본적으로 HF cache + worker를 사용하므로 Ollama 상태와 직접 연결되지 않습니다.
- `paper_local5` 정의와 “현재 즉시 runnable subset”은 다를 수 있습니다.
