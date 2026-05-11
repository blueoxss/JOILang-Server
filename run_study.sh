#!/bin/bash

# 에러 발생 시 스크립트 실행을 즉시 중단합니다 (권장 옵션)
set -e

# 작업 디렉토리로 이동
cd /home/mgjeong/Desktop/llm/JOILang-Server

# 변수 설정
#MODEL="phi35_mini"
MODEL="qwen25_coder_7b"
#MODEL="llama31_8b"
#MODEL="gemma2_9b_it"
#MODEL="qwen25_coder_14b"
OUT="gpt_mg/version0_15_update20260413/results/paper_study_${MODEL}_$(date +%Y%m%d_%H%M%S)"

echo "실행 모델: $MODEL"
echo "결과 저장 경로: $OUT"
echo "파이썬 스크립트 실행을 시작합니다..."

# 파이썬 스크립트 실행
python gpt_mg/version0_15_update20260413/scripts/run_paper_full_study.py \
  --suite paper_local5 \
  --models "$MODEL" \
  --categories 1,2,3,4,5,6,7,8 \
  --limit-per-category 5 \
  --paper-fair-mode \
  --resume \
  --full-run \
  --output-root "$OUT" \
  --quiet-final-summary

echo "실행이 완료되었습니다."