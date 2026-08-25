# R4 changes (2026-08-25)

## 신규

- `scripts/run_det_weight_sensitivity.py` — DET 가중치 민감도 (재채점 전용). 성분 1회 추출·캐시 후 재가중; 변형 config 29종 자동 생성
- `scripts/run_ga_fitness_sensitivity.py` — GA 계수 민감도 rescore/rerank (checkpoints 재계산)
- `configs/det_weights/variants/*.json` — 29 변형 (base/uniform/execution_heavy/structure_heavy/no_code_sim + loo_8 + m20/p20_16)
- `artifacts/sensitivity/components_{6데이터셋}.jsonl` — 행별 8성분 캐시 (280행×6)
- `artifacts/sensitivity/ga_rescore_rows.csv` — 후보×프로파일 재계산 원시(250행)
- `generated_tables/det_weight_sensitivity_by_model.csv`(174행) / `det_weight_sensitivity_summary.csv`(29행) / `tau_sensitivity.csv`(18행) / `ga_fitness_sensitivity.csv`(5행) + 대응 `.tex` 3종
- `docs/iv4_five_round/round_04/paused_long_run.md` — full-GA run matrix + resume 명령
- (수정 1건) `run_det_weight_sensitivity.py` tex 밑줄 이스케이프 — tectonic 컴파일 오류 근본 수정 후 재생성

## 실행 결과 요약 (전부 실측 재채점, LLM 호출 0)

### DET 가중치 (29변형 × 6데이터셋 = 174셀 + τ 18셀, 결측 0)

| 변형군 | 결과 |
|---|---|
| ±20% 섭동 16종 | **전부 strong** (max\|Δ\|≤1.07pp, ρ≥0.96, flip≤2.5%) — 국소 섭동에 결론 불변 |
| LOO | code_sim/schedule/service_coverage/service_precision 제거 → **sensitive** (최대 6.07pp, flip 8.9%); receiver/enum/dataflow 제거 → strong; numeric → moderate |
| 프로파일 교체 | uniform·structure_heavy·no_code_sim → sensitive; execution_heavy → moderate |
| τ | 0.65/0.70/0.75에서 cloud DETPass 95.0~97.5 / 91.4~95.0 / 84.3~89.3 (단조 감소, 순위 대체로 보존) |

**해석**: w0가 큰 가중치를 준 성분일수록 제거 시 결과가 크게 흔들리고(설계 배분의 실증적 정당화), 배분 근방의 ±20% 변형에는 강건 — "가중치를 바꾸면 결과가 어떻게 변하는가"에 대한 직접 답.

### GA 계수 (3런·50후보·10세대그룹 × 5프로파일)

| 프로파일 | 우승자 변경률 | Kendall τ |
|---|---|---|
| pass_heavy | 0% | 1.000 |
| graded_heavy | 0% | 0.940 |
| quality_only | 20% | 0.760 |
| cost_heavy | **70%** | **0.320** |

**해석**: 품질항 간 재배분(α↔β)은 선발에 거의 무영향, 비용항을 3~4배로 키우면 선발이 뒤집힘 — λ=0.05는 '동률 시 저비용 선호' 역할의 의도적 소가중치임을 실증.

## 데이터 가용성 제약 (정직 기록)

- 사전 등록 설계는 "manual 14B GA 8런"을 가정했으나 **checkpoints 보존 런은 3/8** (5런은 checkpoints/ 빈 디렉터리 — `ls .../checkpoints | wc -l` = 0 확인). 가용 checkpoints의 population은 100% 재계산(50후보). G3는 PARTIAL.
- ga_generation_progress.jsonl만 있는 런은 latency 필드가 없어 식(7) 완전 재계산 불가 — 대체 추정치 사용하지 않음.
- full-GA 수준: 미실행, PAUSED_LONG_RUN(run matrix + resume 명령 문서화). 어떤 결과도 실측으로 서술하지 않음.

## 컴파일 검증

- tectonic 0.15.0(자체완비 XeTeX)으로 3표 스모크 컴파일 → PDF 생성·시각 확인 완료 (시스템에 latexmk/xelatex 부재 — R5 컴파일도 tectonic 사용 예정)
- 시각 확인에서 summary 표의 폭 초과 발견 → R5에서 `\resizebox` 또는 열 축약 필요 (기록)
