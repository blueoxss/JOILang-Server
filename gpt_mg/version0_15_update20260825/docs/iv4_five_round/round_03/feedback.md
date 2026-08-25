# R3 feedback (2026-08-25)

## R4로의 이관

1. **재채점 파이프라인 검증 완료**: run_paper_v1_eval이 스키마·no-LLM·τ 임의값까지 보장 — R4의 전 조합(가중치 5프로파일 + LOO 8 + ±20% 16 + τ 3)을 이 CLI와 `score_from_components()` 재가중으로 수행한다.
2. **정밀도 보존 확정**: e·성분 무반올림 → 재가중 재채점의 수치 신뢰성 확보.
3. **재채점 대상 데이터 확정** (R1 §D·§E 실측 존재 목록):
   - GPT-4.1-mini 280행 suite 5종 (v07/v12/v13/v14/v15 프롬프트) — row_metrics에 gt·output 보존
   - Qwen14B 280행 strict run (2회 동일 재현) — row_comparison.csv에 gt·output 보존
   - GA 계수 민감도: manual 14B GA 8런의 ga_generation_progress.jsonl (fitness 분해 보존) → rescore/rerank
4. **robustness 분류 기준은 실행 전 R4 criteria에 고정** (사후 조정 금지): strong ≤2pp / moderate ≤5pp / sensitive >5pp (DETPass 순위 변동·flip율 포함).

## 기준 강화 (R4 적용)

- 민감도 산출물은 CSV(장표)+LaTeX(\input용) 쌍으로 자동 생성, 수기 표 금지.
- 각 표에 데이터 출처(run id·행수)·평가기 프로파일·τ를 각주 필드로 포함.
- full-GA 수준은 GPU 장기 실행 필요 시 PAUSED_LONG_RUN 규약(run matrix + resume 명령) 적용 — 실행 없이 '완료' 서술 금지.
- 결과 해석 문장은 실측 수치 인용 없이는 작성 금지.
