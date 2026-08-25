# iv4_metric_provenance_audit.md (R1, 2026-08-25)

목적: IV-4 관련 **모든 평가기·적합도 구현체**와 **모든 결과 수치**의 출처를 분류한다. 등급: VERIFIED(아티팩트로 재현/확인), UNVERIFIED(문서상 주장, 재현 아티팩트 없음), NOT_RUN(실험 자체 미수행), CONFLICT(상호 모순), MISSING(존재하지 않음).

## A. DET 평가기 — 3개 구현체 공존 (전부 VERIFIED)

| 구현체 | 위치 | 공식 | 논문과의 관계 |
|---|---|---|---|
| **ROOT 8항** | `utils/det_evaluator.py:196-210` (252줄) | det_score=100·(0.30 code_sim+0.15 schedule+0.15 svc_cov+0.10 svc_prec+0.10 receiver+0.10 numeric+0.05 enum+0.05 dataflow); cap 없음; pass=score≥70 ∧ 치명사유 없음 | **논문 w0와 정확 일치.** worked example 재현됨(§C) → 논문의 DET는 사실상 이 구현체 |
| **v15 profile형** | `gpt_mg/version0_15_update20260825/utils/det_evaluator.py` (1607줄; 20260413과 diff-동일) | legacy 7항(gt_similarity 0.30 등, 합1.0) / strict 12항(gt_similarity **0.05**, coverage 0.20 등, 합1.0); gt_exact override→100.0(1511-1544); **strict 5개 조건에서 `score=min(score,69.9)` cap(1547-1555행)** — 69.9<70이므로 설계된 hard-fail | 가중치·구조 모두 논문과 다름. run_ga_search·run_paper_full_study의 **기본값(strict)** |
| **det_paper.py** | `utils/det_paper.py` (478줄) | 치명 위반→pass=False·sdet=0.0; 그 외 sdet=공백정규화 SequenceMatcher∈[0,1]; 단일 참조(gt_converted→gt 첫 파싱본) | "치명=0, 그 외 유사도" 서사와 유일하게 부합하나 **가중 8항이 아님**. 사용처: query_raw.sh, build_profile_csv.py뿐 (GA 미사용) |

**정정 기록**: R1 초기 문서의 "v15에 69.9 없음"은 오류였고 즉시 정정함(`iv4_copy_baseline_verification.md` 참조; 직접 grep 재확인 1547/1549/1551/1553/1555행).

## B. GA 적합도 — 논문 식(7)의 구현체는 **어디에도 없음** (VERIFIED)

| 구현체 | 위치 | 공식 | 식(7)과의 차이 |
|---|---|---|---|
| root ga_search fitness | `utils/ga_search/fitness.py:74-114` + `configs/ga_search_fitness.json` | α·DETPass+β·S_DET+**γ·ReplayFit**−λt·Tok̂−λl·Lat̂; **(0.50,0.15,0.20,0.10,0.05)**; Tok̂=tokens/4096, Lat̂=lat/5.0s | 계수 상이, ReplayFit 항 존재, **고정상수 정규화(DirectTransfer 아님)**. test_wi07_fitness.py가 이것을 'paper weights'로 단언(잘못된 명명) |
| v15 legacy | `run_ga_search.py:2732` | AvgDET − α·VarDET (α=0.5) | 완전 별개 |
| v15 score_main | `scripts/ga_metrics.py:296-312` | DETPass(계수 1.0)+0.20·AvgDET+0.05·CatBal+min(5, comp_gain·10)−2.0·token_pen−0.05·var−2.0·RegPen; **latency_pen 하드코딩 0.0(297행)** | 완전 별개 (main_revised.tex 상징식에 더 가까움) |
| run_local_prompt_ga_study | `:113,814-815` | AvgDET − 0.25·Var | 완전 별개 |

→ **R2에서 paper_v1 적합도(0.70/0.20/0.05/0.05 + DirectTransfer 정규화)는 완전 신규 구현**이며, 기존 4개 정의와 명확히 구분되는 별도 모드로 추가한다(기존 경로 무변경).

## C. 논문 worked example — **정확 재현** (VERIFIED)

- JOICommands-280 row index 9 ("외부 온도를 스피커로 출력해줘"), 변수 유지 간결 후보 → **ROOT 평가기**: 0.65+0.30·0.9214659686 = **0.9264397905759162** = 논문 e_i=0.9264 (main.tex:605-606) 전 자릿수 일치.
- 동일 fixture를 v15로 채점 시: legacy·strict 모두 gt_exact=100.0 (한줄 변형은 strict에서 69.9 cap→fail). → **0.9264는 v15에서 도달 불가** — 논문 서사는 ROOT 평가기하고만 정합. paper_v1 구현의 회귀 fixture 기준값으로 채택.
- 주의: `artifacts/ga_prompt_search/ga_loop_v4/holdout_rows.csv`의 92.6471은 다른 행(카테고리 6) — 혼동 금지.

## D. 결과 수치 provenance (아티팩트 전수 대조)

| 수치군 | 논문 위치 | 등급 | 근거 |
|---|---|---|---|
| 주표 CloudRef DETPass 94.5 | B·P·G 표5, R 표 | **CONFLICT** | 최근접 아티팩트 model_suite_20260616_205513: avg_det_score=94.4732(≈94.5)·det_pass_rate=**0.9107** — 앵커는 '평균 DET점수'와 일치하고 'DETPass'와 불일치(지표명 혼동 의심) |
| 주표 DT→GPS (87.8→92.6 / 81.7→88.7 / 90.1→94.0) | B·P·G·R | **UNVERIFIED** | ledger ANCHOR(출처 '§3 수치 앵커'), 재현 아티팩트 0건. 실측과 괴리: Q14 280행 실측 det_pass 82.5%(avg_det 85.71, 2회 동일 재현) vs 앵커 DT 90.1; Q7 GA 실측 best 85.0(det 83.2, seed 2025) vs 앵커 92.6 |
| 교차전이 3×3 | B·P·G | **NOT_RUN** | 유일 런 = llm_mode='mock', genome_json=null placeholder; 대각은 GPS 앵커 복사(PROJECTED) |
| ReplayFit 열 (79.2→90.9 등) | R 전용 | **UNVERIFIED+제거 대상** | 코드가 replay_fit 미계산(`run_ga_search.py:2488` 빈 문자열) — 산출 경로 자체 부재 |
| 가중치·임계값 민감도 | 어디에도 없음 | **NOT_RUN** | 아티팩트 0건 (§6.5 가설 확정) — R4가 최초 수행 |
| A0-A4 ablation | ledger 40-59행 | **NOT_RUN** | mockdry 2건뿐 |
| seed 분산(WI-14) | ledger 67행 | **NOT_RUN** | 전 GA 런 단일 seed(2025 또는 미기록); suite manifest에 git commit·seed 부재 |
| det_paper 배치(v06/v12/v13, 20260331) | — | VERIFIED_LEGACY | local_8b 280행, v13 det_pass 0.8107·mean_sdet 0.4907; 8성분 미저장(예측 스크립트는 저장 → 재채점 시 평가기 재실행 필요) |
| GPT-4.1-mini 280행 suite 5종 | — | **VERIFIED** | avg_det 92.38~95.86, det_pass 0.868~0.968 (v07/v12/v13/v14/v15 프롬프트) |
| Qwen14B 280행 strict | — | **VERIFIED** | avg_det 85.71 / det_pass 82.5% (2회 동일) |

## E. R2–R4에 결정적인 사실

1. **재채점 가능성 확보**: v15 suite row_metrics가 **8개 DET 성분을 0-1 float로 전부 저장**(det_gt_similarity, det_gt_service_coverage, det_gt_service_precision, det_gt_receiver_coverage, det_dataflow_score, det_numeric_grounding, det_enum_grounding, det_valid_json) + 원문 gt·output 보존 → **DET 가중치 민감도(R4)는 재생성 없이 성분 벡터 재가중으로 수행 가능**. 대상: GPT-4.1-mini suite 5종 + Qwen14B strict 280행. 단, 이 성분들은 v15 strict 정의이므로 paper_v1 8항으로의 재채점은 **저장된 output 문자열에 평가기 재실행**(LLM 호출 0회)으로 수행한다.
2. **GA 계수 민감도(R4)**: manual 14B GA 8런의 ga_generation_progress.jsonl이 적합도 분해(score_main/accuracy/…/token_penalty/regression_penalty)를 보존 → rescore/rerank 수준은 기존 아티팩트로 가능. full-GA 수준은 신규 실행 필요(PAUSED_LONG_RUN 후보).
3. **DirectTransfer 정규화 기준**: 코드 어디에도 없음 → R2에서 `--direct-transfer-baseline`(모델별 Tok·Lat 기준값 파일) 신규 도입, 기준값 산출은 실측 아티팩트(suite·eval_pipeline_checks) 우선.
4. **CLI 현황**: `--det-profile` v15에서 소비(기본 strict; root cli.py:87은 dead flag), `--det-weights` **전무**, `--fitness-mode` 어휘 상이(root: strict_det/graded/binary; v15: legacy/detpass_token/phase_aware). R2 플러밍은 v15 어휘를 확장(paper_v1 추가)하는 방식으로.
5. **다중 참조**: gt_refs 식별자 저장소 전체 0건, 데이터셋 gt 단일 열 → paper_v1은 다중참조 max를 지원하되 단일 gt에서 자연 축약(동작 동치).

## F. 코드-논문 불일치 종합 목록 (R2 수정 대상 ○ / R5 서술 정합 대상 ◆)

1. ○ 식(7) 적합도 미구현 (4개 상이한 적합도만 존재)
2. ○ Tok·Lat 정규화: 고정상수(4096/5.0s) vs 논문 DirectTransfer — paper_v1에서 DirectTransfer 정규화 구현
3. ○ 다중 허용 참조 미지원 — paper_v1에서 gt_refs max 지원(기본 단일 gt)
4. ◆ pass 규칙: 코드 'gt_exact OR ≥70' vs 논문 'e_i≥τ ∧ 무치명' — gt_exact bypass는 e_i=1.0≥τ와 동치이므로 실질 충돌 아님(단 서술 명시 여부 R5 결정)
5. ◆ v15 strict 69.9 cap·12항 가중치 — 논문 미기재; paper_v1은 별도 프로파일로 공존(strict 무변경), 논문은 paper_v1(=ROOT 의미론)만 서술
6. ◆ ReplayFit: R 15개소 제거
7. ◆ 지표명: 94.5가 avg_det로 보임(DETPass 아님) — R5에서 표 라벨·정의 정합 확인 필요
8. ◆ test_wi07_fitness.py가 (0.50,0.15,0.20,0.10,0.05)를 'paper weights'로 단언 — root 경로는 본 과제 범위 밖(무변경)이지만 혼동 근원으로 기록
