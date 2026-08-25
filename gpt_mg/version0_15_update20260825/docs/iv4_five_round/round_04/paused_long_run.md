# PAUSED_LONG_RUN — GA 계수 민감도 full-GA 수준 (R4, 2026-08-25)

## 상태

**미실행 (PAUSED)** — rescore/rerank 수준은 완료(기존 checkpoints 재계산, LLM 호출 0).
full-GA 수준(계수 프로파일별 신규 GA 탐색)은 GPU 장기 실행이 필요해 규약에 따라 일시중지한다.
이 수준의 어떤 결과도 본 라운드 산출물·논문에 **실측으로 서술하지 않는다**.

## 필요 자원 추정

- 모델: Qwen2.5-Coder-14B-Instruct (로컬 worker, `joi` env)
- 1런 = pop 6 × gens 5 × 검증 40행 ≈ 1,200 생성 ≈ A6000 1대 기준 4–6시간
- 전체 매트릭스: 5 계수 프로파일 × 3 seed = 15런 ≈ 60–90 GPU·시간 (2대 병렬 시 실벽시계 ~2일)

## Run matrix

| run id | fitness-weights | seed | device | 상태 |
|---|---|---|---|---|
| fga_base_s0 | configs/fitness_weights/paper_v1.json | 0 | cuda:0 | NOT_RUN |
| fga_base_s1/s2 | 〃 | 1/2 | cuda:0 | NOT_RUN |
| fga_passheavy_s0..2 | variants/pass_heavy.json* | 0-2 | cuda:0 | NOT_RUN |
| fga_gradedheavy_s0..2 | variants/graded_heavy.json* | 0-2 | cuda:1 | NOT_RUN |
| fga_costheavy_s0..2 | variants/cost_heavy.json* | 0-2 | cuda:1 | NOT_RUN |
| fga_qualityonly_s0..2 | variants/quality_only.json* | 0-2 | cuda:1 | NOT_RUN |

\* fitness_weights variant JSON은 실행 개시 시 `configs/fitness_weights/variants/`에 생성
(rescore에 쓴 PROFILES 계수를 그대로 — scripts/run_ga_fitness_sensitivity.py PROFILES 참조).

## Resume 명령 (run 하나의 예)

```bash
cd /home/mgjeong/Desktop/llm/JOILang-Server/gpt_mg/version0_15_update20260825
~/miniconda3/envs/joi/bin/python scripts/run_ga_search.py \
  --det-profile paper_v1 --fitness-mode paper_v1 \
  --fitness-weights configs/fitness_weights/variants/pass_heavy.json \
  --direct-transfer-baseline configs/direct_transfer_baseline.json \
  --model-key qwen25_coder_14b --seed 0 \
  --population 6 --generations 5 --feedback-attempts 0 \
  --output-root results/fga_passheavy_s0
```

주의: `--feedback-attempts 0` 필수 (feedback loop 내부 평가의 det_profile 미전달 — R2 한계 기록 참조).
Q7/L8로 확장하려면 DT 기준값 실측 선행(`scripts/build_direct_transfer_baseline.py`), 그 전에는 fail-fast가 정상.

## 재개 후 처리

1. 각 런의 checkpoints를 `scripts/run_ga_fitness_sensitivity.py`와 동일 방식으로 집계(스크립트가 신규 런 경로를 받도록 --runs-glob 인자 추가)
2. 프로파일별 최종 best 프롬프트의 280행 paper_v1 평가 → 계수 선택이 최종 성능에 주는 효과
3. generated_tables/ga_fitness_sensitivity_fullga.csv 로 별도 표 (rescore 표와 혼합 금지)
