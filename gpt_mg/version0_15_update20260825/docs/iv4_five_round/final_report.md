# IV-4 정합화·민감도·5라운드 검증 최종 보고 (2026-08-25)

마스터 프롬프트 §20 형식. 모든 수치는 실측·재채점 결과이며, 미실행 항목은 PAUSED/NOT_RUN으로 명시한다.

## 1. 5라운드 요약표

| 라운드 | 기준 SHA(동결) | 목표 | 판정 | 수정 반복 | 핵심 산출 |
|---|---|---|---|---|---|
| R1 | 2276a194cbe9e4bb | 논문 4종·코드·아티팩트 감사, 복사 기준선 | **PASS** (G5는 PASS_WITH_INCIDENT) | 0 (정정 1건) | 문서 5종, 69.9 오류 정정, 0.92643979 재현 |
| R2 | a9891ddc65f1f536 | paper_v1 평가기·적합도·CLI·테스트 | **PASS** (10/10 게이트) | 0 | det_paper_v1.py, fitness_paper_v1.py, configs 5종, 신규 24테스트, 141 green |
| R3 | 5affee069fc71683 | 경계·회귀 확대, no-LLM 보장, 스키마 | **PASS** (5/5) | 1 (반올림 결함 근본수정) | 경계 16 + 회귀 12행 동결 + no-LLM 증명, 174 green |
| R4 | 136dfde4b17e0ac0 | DET·GA 민감도 실험 + 자동표 | **PASS** (G3만 PARTIAL: checkpoints 3/8런 실존) | 1 (tex 이스케이프) | 192셀 DET 재채점 + GA rescore/rerank + CSV·tex 4종 |
| R5 | 2c5ccd5155dcbb46 | main_revised.tex 전면 개정·컴파일·검증 | **PASS** (9/9) | 2 (ICU 우회, 글리프) | 11p PDF 컴파일·전 페이지 시각 검증 |

규율 준수: 기준은 평가 전 SHA-256 동결, 완화 0회, 조기 종료 없음, R6 없음.

## 2. 교수님 질문 3에 대한 답

**Q1. DET/적합도는 어떤 식으로 계산하는가?**
논문 식(3)–(7)로 형식화(교수님 PDF 그대로 main_revised.tex IV-4에 반영): e_i=Σ8k w_k·s_ik (w0=(0.30,0.15,0.15,0.10,0.10,0.10,0.05,0.05)), D_i=1 iff 무치명∧e_i≥τ(=0.70), DETPass·S_DET는 평균, f=0.70·DETPass+0.20·S_DET−0.05·Tok̂−0.05·Lat̂(동일 모델 DirectTransfer 정규화). 이 정의의 실행 가능한 구현이 `utils/det_paper_v1.py`+`scripts/fitness_paper_v1.py`이며, 논문 worked example(외부온도 간결형 e=0.9264397905759162)을 전 자릿수 재현한다.

**Q2. 각 가중치의 근거는?**
"실행 결과에 직접 영향을 주는 차이(일정·서비스·대상·수치)를 문자열 표현·변수 선언 수보다 크게 반영하도록 **탐색 전에 정한 설계값**이며, **예비 실험으로 학습한 값이 아니고** 모든 모델에 동일 적용"(교수님 자구 유지). 여기에 R4 실측이 사후 정당화를 추가: LOO에서 대가중치 성분 제거만 sensitive(최대 6.07pp)이고 소가중치 성분 제거는 strong — **배분의 우선순위와 실제 판별 기여가 일치**.

**Q3. 가중치를 바꾸면 결과가 어떻게 변하는가?** (신규 V장 4절, 전부 실측 재채점)
- ±20% 섭동 16종: 전부 strong (max|ΔDETPass|≤1.07pp, ρ≥0.96, flip≤2.5%) — 결론 불변
- LOO 8종: service_coverage 6.07pp·code_sim·schedule·precision sensitive / receiver·enum·dataflow strong / numeric moderate
- 프로파일 교체: uniform 4.29pp·structure 4.64·no_code_sim 5.00 sensitive, execution_heavy 2.14 moderate
- τ∈{0.65,0.70,0.75}: 절대값 단조 변화, 순위 대체로 보존
- GA 계수: α↔β 재배분은 선발 불변(Kendall τ≥0.94, 우승자 변경 0%), 비용항 4배 강화 시 우승자 70% 변경(τ=0.32) — λ=0.05는 tie-breaker 설계 실증

## 3. 아키텍처 결정

1. **canonical 분리**: `gpt_mg/version0_15_update20260825` 신설(390파일 SHA 검증 복사), 원본·root 무변경. results 심볼릭 링크 미복제로 legacy 혼입 차단.
2. **paper_v1 = 별도 프로파일**: v15 strict 재라벨 금지(0.92643979 게이트가 강제). ROOT 8항 의미론을 0-1 스케일로 이식, hard gate·다중참조 max(단일 gt 자연 축약)·성분 벡터 보존. 기존 legacy/strict/score_main/AvgDET−αVar 4개 정의는 무변경 공존.
3. **재채점 우선**: 민감도는 저장 output에 평가기 재실행(LLM 호출 0) — suite row_metrics의 8성분·원문 보존이 이를 가능케 함. full-GA는 PAUSED_LONG_RUN.
4. **DT 정규화 fail-fast**: 실측 기준값만 등록(Q14·gpt-4.1-mini), 부재 모델은 명시적 오류(침묵 기본값 금지).
5. **논문 전면 재작성**: main_revised.tex가 구계보+mojibake로 증분 수정 불가 → main.tex 기반 + 교수님 형식화 + 민감도 신설. 표는 \input 자동화(수기 수치 금지).

## 4. 변경 파일 (전량)

- **Paper**: `main_revised.tex` 1개 (백업: canonical artifacts/paper_20260825/main_revised_before_R5.tex)
- **canonical 신규**: utils/det_paper_v1.py, scripts/{fitness_paper_v1, run_paper_v1_eval, build_direct_transfer_baseline, run_det_weight_sensitivity, run_ga_fitness_sensitivity}.py, configs/det_weights/{paper_v1,strict_v1,legacy_v1}.json + variants/29종, configs/fitness_weights/paper_v1.json, configs/direct_transfer_baseline.json, tests/{test_paper_v1, test_paper_v1_boundary, test_paper_v1_regression_expanded}.py + fixtures 2종, generated_tables 7파일, docs 전체(감사 5종 + 라운드별 criteria/판정/피드백/변경/manifest + 본 보고서)
- **canonical 수정 3건**: utils/det_evaluator.py(paper_v1 dispatch 조기반환), scripts/run_feedback_loop.py(det_weights 선택 인자), scripts/run_ga_search.py(플래그 6종+_prepare_paper_v1+식(7) override+정렬 분기)

## 5. 검증 명령·결과

- `pytest tests/` (canonical) → **174 passed** (신규 57 포함), exit 0
- fixture: paper_v1 e=0.9264397905759162(<1e-8)·exact 1.0·hard gate 0.0·다중참조 max·τ 경계
- 회귀: 6+24케이스를 원본 20260413 실측과 동결 비교 — 전부 동일(69.9 cap·exact override 보존)
- 280행 실검증: model_suite_205513 재채점 DETPass 0.9286/S_DET 0.9265/fitness 0.7353, 기준런 자기일관성 tok̂=lat̂≈1.0
- 민감도: 29변형×6셋=174셀+τ 18셀(결측 0), GA 3런·50후보·10세대그룹×5프로파일
- LaTeX: tectonic 격리 컴파일 11p + 전 페이지 시각 검증(스크린샷 판독)
- 격리: git status 전수 — canonical·main_revised.tex 외 변경 0 (기존 사용자 변경은 mtime으로 판별·목록화)

## 6. 실패와 수정 (전량, 은폐 없음)

| # | 실패 | 근본 원인 | 수정 |
|---|---|---|---|
| 1 | R1 기록 "v15에 69.9 없음" | 잘못된 grep 단정 | 감사에서 적발→직접 재검증(1547-1555행)→당일 정정 + '부재 주장 증거 규칙' 신설 |
| 2 | τ 경계 테스트 실패 | 출력 e 12자리 반올림 vs 내부 원값 판정 불일치 | 반올림 제거(원 정밀도 보존) — R4 재채점 정확성에도 기여 |
| 3 | period 0 vs "" 테스트 실패 | ROOT normalize_text의 falsy 동치(의도 동작)를 오해 | 테스트 기대 수정 + 동작 문서 동결 |
| 4 | 민감도 tex 컴파일 실패 | 변형명 밑줄 미이스케이프 | tex_esc 추가, 재생성 |
| 5 | 논문 컴파일 실패 | tectonic ICU 로케일 데이터 부재(한글 문단 줄바꿈) | 최소 재현으로 격리 → \XeTeXlinebreaklocale "" (xetexko 자체 줄바꿈 유지, TeX Live 무해) |
| 6 | ref[14] ä→□ | 나눔명조 글리프 부재 | Rocktaschel 표기 |
| 7 | R1 격리 목록 불완전 | 초기 git 스냅샷 누락 | mtime 판별로 기존 변경 전수 목록화(ga_engine 등 4건+) |

## 7. 한계·미실행 (정직 목록)

- **full-GA 계수 민감도**: 미실행(PAUSED_LONG_RUN, 15런 매트릭스+resume 명령 문서화 — round_04/paused_long_run.md)
- **GA rescore 데이터**: checkpoints 보존 3/8런(50후보) — 나머지 5런은 아티팩트 자체 부재(latency 없는 progress로 대체하지 않음)
- **Q7/L8 DT 기준값**: 280행 실측 부재 → fail-fast 유지(신규 실측 시 build_direct_transfer_baseline.py로 등록)
- **주표 앵커 수치**(94.5/92.6/88.7/94.0): 재현 아티팩트 없는 ledger ANCHOR(R1 감사) — 교수님도 무변경 유지 원칙이므로 본 과제 범위 밖, provenance는 iv4_metric_provenance_audit.md에 기록
- **그림 2 png 부재**·표8 축소 폰트·p.9 단 공백·fonts/ 부재 시 나눔명조 대체 — 조판 사항
- feedback loop 내부 평가 det_profile 미전달(기존 동작) — paper_v1 full-GA 시 --feedback-attempts 0 필요
