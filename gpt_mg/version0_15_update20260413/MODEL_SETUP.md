# MODEL_SETUP

`version0_15_update20260413`의 paper local benchmark는 기본적으로 `Ollama`가 아니라 Hugging Face cache + local worker runtime을 사용합니다.

## 현재 상태

기준 리포트:

- `/home/mgjeong/Desktop/llm/JOILang-Server/gpt_mg/version0_15_update20260413/results/model_prep_20260420_180353/model_readiness.json`
- `/home/mgjeong/Desktop/llm/JOILang-Server/gpt_mg/version0_15_update20260413/results/model_prep_20260420_180353/model_readiness.csv`
- `/home/mgjeong/Desktop/llm/JOILang-Server/gpt_mg/version0_15_update20260413/results/model_prep_20260420_180353/model_readiness.txt`

즉시 같은 prompt benchmark에 사용할 수 있는 모델:

- `qwen25_coder_7b`
- `qwen25_coder_14b`

준비는 되었지만 현재 prompt 길이에서 바로 실험이 막히는 모델:

- `phi35_mini`
  - cache는 준비됨
  - worker load compatibility는 보정됨
  - dataset row 1의 schema fallback prompt가 약 31k token 수준이라 현재 GPU 메모리에서 one-row smoke가 `CUDA out of memory`로 실패

현재 접근 권한 때문에 준비되지 않은 모델:

- `llama31_8b`
  - Hugging Face gated repo
  - `meta-llama/Llama-3.1-8B-Instruct` access + login 필요
- `gemma2_9b_it`
  - Hugging Face gated repo
  - `google/gemma-2-9b-it` access + login 필요

## 정확한 snapshot 경로

현재 확인된 snapshot 경로:

- `phi35_mini`
  - `/home/mgjeong/.cache/huggingface/hub/models--microsoft--Phi-3.5-mini-instruct/snapshots/2fe192450127e6a83f7441aef6e3ca586c338b77`
- `qwen25_coder_7b`
  - `/home/mgjeong/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242`
- `qwen25_coder_14b`
  - `/home/mgjeong/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-14B-Instruct/snapshots/aedcc2d42b622764e023cf882b6652e646b95671`
- `llama31_8b`
  - `/home/mgjeong/.cache/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/0e9e39f249a16976918f6564b8830bc894c89659`
  - partial/gated cache라 완전한 모델 snapshot으로 쓰면 안 됨
- `gemma2_9b_it`
  - `/home/mgjeong/.cache/huggingface/hub/models--google--gemma-2-9b-it/snapshots/11c9b309abf73637e4b6f9a3fa1e92e615547819`
  - partial/gated cache라 완전한 모델 snapshot으로 쓰면 안 됨

## worker runtime

현재 자동 선택된 worker python:

- `/home/mgjeong/miniconda3/envs/l/bin/python`

이 environment에서 확인된 runtime:

- `torch 2.9.1+cu128`
- `transformers 4.57.3`
- `cuda_available=true`
- `GPU 2 x NVIDIA RTX A6000`

worker는 기본적으로 아래를 사용합니다.

- worker path:
  - `/home/mgjeong/Desktop/llm/JOILang-Server/gpt_mg/version0_13/qwen_local_worker.py`
- persistent worker path:
  - `/home/mgjeong/Desktop/llm/JOILang-Server/gpt_mg/version0_15_update20260413/utils/persistent_qwen_worker.py`
- HF modules cache:
  - `/tmp/joi_v15_hf_modules`

override가 필요하면:

```bash
export JOI_V15_WORKER_PYTHON=/home/mgjeong/miniconda3/envs/l/bin/python
export JOI_V15_LOCAL_DEVICE=cuda:0
```

## fair measurement runtime

논문용 공정 비교에서는 여러 모델을 동시에 VRAM에 상주시킨 뒤 latency를 비교하지 않습니다.

- 권장 fair mode:
  - `--paper-fair-mode`
  - 내부적으로 모델별 fresh worker를 시작
  - warmup request 후 evaluation rows를 실행
  - 모델이 끝나면 worker를 종료해서 메모리를 해제
- wall-clock 단축용 parallel mode:
  - `--max-workers 2` 같은 형태
  - latency 공정 비교용 숫자로 해석하면 안 됨

현재 worker는 row별로 아래 메트릭을 반환하도록 보강되어 있습니다.

- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `latency_sec`
- `peak_vram_gb`
- `load_sec`
- `prompt_prep_sec`
- `generate_sec`
- `decode_sec`

benchmark runner는 이를 바탕으로 아래 paper 축을 계산합니다.

- `DET`
- `warm_latency_mean/p50/p95`
- `cold_load_sec`
- `avg_prompt_tokens`
- `peak_vram_gb_max`
- `oom_count`
- `generation_error_rate`
- `failure_rate`
- `row_success_rate`

## 현재 fair-mode smoke 기준

대표 smoke output:

- `/home/mgjeong/Desktop/llm/JOILang-Server/gpt_mg/version0_15_update20260413/results/model_suite_20260421_121042`

여기서 확인된 값 예시:

- `qwen25_coder_7b`
  - `avg_det_score=98.8980`
  - `cold_load_sec=17.8122`
  - `warm_latency_p50=7.8561`
  - `peak_vram_gb_max=20.1218`
- `qwen25_coder_14b`
  - `avg_det_score=89.8937`
  - `cold_load_sec=30.9921`
  - `warm_latency_p50=17.5017`
  - `peak_vram_gb_max=37.0264`

이 값들은 fresh worker + warmup 후에 측정된 결과라, raw same-process multi-model 실행보다 더 공정한 비교에 가깝습니다.

## 중요한 동작 메모

- `--llm-extra-json '{"local_model_name":"/your/local/path/..."}'`의 `/your/local/path/...`는 예시 placeholder입니다.
- 이 값은 실제로 존재하는 절대경로여야 합니다.
- 경로가 존재하지 않으면 `transformers`가 이를 local path가 아니라 repo id 문자열로 해석하려고 해서 `Repo id must be in the form ...` 오류가 납니다.

즉 아래처럼 placeholder를 그대로 쓰면 안 됩니다.

```bash
--llm-extra-json '{"local_model_name":"/your/local/path/Phi-3.5-mini-instruct"}'
```

실제로 쓰려면 존재하는 snapshot 절대경로를 써야 합니다.

```bash
--llm-extra-json '{"local_model_name":"/home/mgjeong/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/c03e6d358207e414f1eca0bb1891e29f1db0e242"}'
```

## 모델 준비 명령

현재 상태를 다시 점검하고 missing/gated/download/smoke 결과를 다시 생성하려면:

```bash
cd /home/mgjeong/Desktop/llm/JOILang-Server

JOI_V15_WORKER_PYTHON=/home/mgjeong/miniconda3/envs/l/bin/python \
JOI_V15_LOCAL_DEVICE=cuda:0 \
python gpt_mg/version0_15_update20260413/scripts/prepare_local_models.py \
  --suite paper_local5 \
  --download-missing
```

paper-fair smoke 예시:

```bash
cd /home/mgjeong/Desktop/llm/JOILang-Server

JOI_V15_WORKER_PYTHON=/home/mgjeong/miniconda3/envs/l/bin/python \
JOI_V15_LOCAL_DEVICE=cuda:0 \
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

`Llama`와 `Gemma`를 실제로 준비하려면 먼저 Hugging Face login + access 승인이 필요합니다.

예시:

```bash
huggingface-cli login
huggingface-cli download meta-llama/Llama-3.1-8B-Instruct
huggingface-cli download google/gemma-2-9b-it
```

승인되지 않은 계정에서는 `401 / gated repo` 오류가 납니다.
