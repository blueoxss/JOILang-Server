# EXPERIMENT_SETUP

`version0_15_update20260413`에서 논문용 same-prompt benchmark를 바로 돌릴 때 필요한 실행 흐름을 정리합니다.

## 1. 기본 원칙

- benchmark runtime은 기본적으로 `Ollama`가 아니라 Hugging Face cache + local worker입니다.
- `paper_local5`는 논문 대상 모델군 정의입니다.
- 하지만 "현재 이 머신에서 즉시 성공적으로 compare까지 확인된 모델"은 더 좁을 수 있습니다.
- 현재 기준으로 바로 권장하는 runnable subset은 `qwen25_coder_7b`, `qwen25_coder_14b`입니다.

## 2. 현재 모델 상태

상세 readiness 리포트:

- `/home/mgjeong/Desktop/llm/JOILang-Server/gpt_mg/version0_15_update20260413/results/model_prep_20260420_180353/model_readiness.json`
- `/home/mgjeong/Desktop/llm/JOILang-Server/gpt_mg/version0_15_update20260413/results/model_prep_20260420_180353/model_readiness.csv`
- `/home/mgjeong/Desktop/llm/JOILang-Server/gpt_mg/version0_15_update20260413/results/model_prep_20260420_180353/model_readiness.txt`

현재 상태 요약:

- `qwen25_coder_7b`: ready and smoke-tested
- `qwen25_coder_14b`: ready and smoke-tested
- `phi35_mini`: cache 있음, worker load는 되지만 row 1 smoke에서 OOM
- `llama31_8b`: gated repo, access/login 필요
- `gemma2_9b_it`: gated repo, access/login 필요

## 3. 권장 환경 변수

```bash
cd /home/mgjeong/Desktop/llm/JOILang-Server

export JOI_V15_WORKER_PYTHON=/home/mgjeong/miniconda3/envs/l/bin/python
export JOI_V15_LOCAL_DEVICE=cuda:0
```

현재 검증된 worker runtime:

- python: `/home/mgjeong/miniconda3/envs/l/bin/python`
- torch: `2.9.1+cu128`
- transformers: `4.57.3`
- cuda: available

## 4. 지원 모델 키

`paper_local5`에서 쓰는 model key:

- `phi35_mini`
- `qwen25_coder_7b`
- `llama31_8b`
- `gemma2_9b_it`
- `qwen25_coder_14b`

## 5. 가장 먼저 할 점검

worker runtime과 cache 상태를 확인:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --preflight-only \
  --print-worker-info
```

모델 다운로드, cache 확인, one-row smoke까지 다시 실행:

```bash
python gpt_mg/version0_15_update20260413/scripts/prepare_local_models.py \
  --suite paper_local5 \
  --download-missing
```

## 6. 지금 바로 되는 실행 예시

single-model compare:

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

two-model same-prompt compare:

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

dataset subset compare:

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

repair까지 포함:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --model-key qwen25_coder_14b \
  --start-row 1 \
  --end-row 20 \
  --candidate-k 1 \
  --repair-attempts 1 \
  --print-mode summary
```

## 7. full suite를 부를 때 주의할 점

정의상 full suite 실행:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --skip-unavailable \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --print-mode summary
```

주의:

- `--skip-unavailable`는 preflight에서 `ready`가 아닌 모델만 건너뜁니다.
- 현재 `llama31_8b`, `gemma2_9b_it`는 skip 대상입니다.
- 현재 `phi35_mini`는 cache 기준으로는 `ready`이므로 자동 skip되지 않을 수 있습니다.
- 따라서 "지금 바로 성공해야 하는 실험"은 explicit subset 지정이 더 안전합니다.

## 8. `local_model_name` 직접 지정

placeholder 경로를 그대로 쓰면 안 됩니다.

잘못된 예:

```bash
--llm-extra-json '{"local_model_name":"/your/local/path/Phi-3.5-mini-instruct"}'
```

이 경로가 실제로 존재하지 않으면 `transformers`가 local path가 아니라 repo id 문자열로 해석해서 `Repo id must be in the form ...` 오류가 납니다.

실제로는 snapshot 절대경로를 써야 합니다.

예시:

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

## 9. compare 모드에서 보이는 내용

`--print-mode compare`를 쓰면 row마다 아래를 봅니다.

- row id
- input command
- GT schedule
- GT code
- generated schedule
- generated code
- DET score
- exact match 여부
- similarity
- failure reasons
- concise diff summary

## 10. 결과 파일

benchmark output directory 아래에 다음 파일이 생성됩니다.

- `suite_manifest.json`
- `suite_summary.json`
- `suite_summary.csv`
- `row_comparison.csv`
- `failure_reason_summary.csv`
- `category_summary.csv`
- 모델별 `*_candidates.csv`
- 모델별 `*_rerank.csv`
- 모델별 `*_summary.json`

## 11. 병렬 옵션

`--max-workers`를 줄 수는 있지만 local worker + GPU 메모리 사용량 때문에 보수적으로 쓰는 편이 좋습니다.

예시:

```bash
python gpt_mg/version0_15_update20260413/scripts/run_model_suite_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --model-key qwen25_coder_14b \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --print-mode compare \
  --max-workers 2
```

## 12. paper helper runner

준비 후 suite 실행:

```bash
gpt_mg/version0_15_update20260413/scripts/run_paper_local5_suite.sh \
  --model-key qwen25_coder_7b \
  --model-key qwen25_coder_14b \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --print-mode compare
```

## 13. GA generation progress

GA 탐색 로그를 generation 단위로 저장하고 plot helper로 요약할 수 있습니다.

GA 실행 후:

```bash
python gpt_mg/version0_15_update20260413/scripts/plot_generation_progress.py
```

기본 입력:

- `results/ga_generation_progress.csv`

기본 출력:

- `results/ga_generation_progress_summary.json`
- matplotlib가 있으면 PNG도 생성 가능

## 14. 알려진 제한사항

- `phi35_mini`는 현재 row 1 smoke에서 OOM입니다.
- `llama31_8b`, `gemma2_9b_it`는 Hugging Face gated access가 필요합니다.
- benchmark는 기본적으로 HF cache + worker를 사용하므로 Ollama 상태와 직접 연결되지 않습니다.
- `paper_local5`를 정의 그대로 실행하는 것과 "지금 즉시 성공 가능한 모델 subset"은 다를 수 있습니다.
