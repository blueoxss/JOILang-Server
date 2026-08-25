# R2 changes (2026-08-25)

전 변경이 canonical dir(`gpt_mg/version0_15_update20260825`) 내부. 원본·root 무변경.

## 신규 파일

- `configs/det_weights/paper_v1.json` — 식(3) w0, τ=0.70, hard gate 목록, 참조 의미론
- `configs/det_weights/{strict_v1,legacy_v1}.json` — v15 내장 dict의 기록 사본 (v15는 이 파일을 읽지 않음 — 동작 무변경, 문서화 목적)
- `configs/fitness_weights/paper_v1.json` — 식(7) 계수 0.70/0.20/0.05/0.05
- `configs/direct_transfer_baseline.json` — DT 정규화 기준값. **실측만 등록**: qwen25_coder_14b(34259.2036 tok / 12.3645 s; eval_pipeline_checks 280행), gpt41_mini(30275.1071 / 1.9772; model_suite_205513). Q7·L8은 실측 부재로 **의도적 부재 → fail-fast**
- `utils/det_paper_v1.py` — 식(3)-(6) 평가기. ROOT utils/det_evaluator.py(@463f092d) 8항 의미론 이식(0-1), 다중참조 max(gt_refs, 단일 gt 자연 축약), hard gate, 성분 벡터·메타데이터 보존, `score_from_components()`(R4 재가중 재채점 진입점)
- `scripts/fitness_paper_v1.py` — 식(7). DT 정규화(클리핑 없음 — 논문에 클리핑 없음), 기준값 부재 모델 fail-fast, 분해 항 보존
- `scripts/run_paper_v1_eval.py` — 단일 진입 재채점 CLI (6개 플래그 전부 파싱·소비, τ 임의값 지원, LLM 호출 0 보장)
- `scripts/build_direct_transfer_baseline.py` — 실측 CSV에서 DT 기준값 등록 (수기 값 금지)
- `tests/test_paper_v1.py` — 24 테스트 (G1-G10 직접 검증)

## 수정 파일 (canonical 내)

- `utils/det_evaluator.py` — `evaluate_candidate` 최상단에 paper_v1 dispatch(조기 반환) 추가. legacy/strict 경로 무접촉 — 회귀 fixture 6케이스 수치가 원본과 동일함을 테스트로 동결
- `scripts/run_feedback_loop.py` — `evaluate_genome_on_rows`에 선택 인자 `det_weights=None` 추가(기본값 시 기존 동작과 동일)
- `scripts/run_ga_search.py` —
  - `--det-profile`에 `paper_v1` 선택지, `--fitness-mode`에 `paper_v1` 선택지
  - 신규 플래그: `--det-weights`, `--det-threshold`, `--fitness-weights`, `--direct-transfer-baseline`
  - `_prepare_paper_v1()`: 가중치·기준값 선로딩 + fail-fast (GA 경로 τ≠0.70 시 명시적 거부 — τ 변형은 재채점 CLI 전용)
  - `_apply_redesign_metrics()`: fitness_mode=paper_v1이면 식(7)로 fitness 재정의(분해 항 `paper_v1_fitness` 보존)
  - `_sort_evaluated_population()`: paper_v1 모드에서 식(7) fitness가 모집단 순위 직접 결정(score_main 아님)
  - `_evaluate_one()` det_weights 스레딩(내부 3콜 + 외부 2콜사이트)

## 실검증 (재현 명령 포함)

1. **fixture**: 외부온도 간결형 → paper_v1 e=0.9264397905759162 (<1e-8), exact→1.0, oneliner→0.784615 (ROOT 의미론, 69.9 cap 없음) ✓
2. **회귀 동결**: 동일 6케이스를 원본 20260413(무변경)과 canonical 양쪽에서 실측 — 전부 동일 (exact_rawgt legacy/strict=0.0(v15 기존 동작: code 키 없는 후보 불인정), concise=100.0 exact, oneliner legacy=93.7135, strict=69.9) ✓
3. **280행 재채점**: model_suite_205513 gpt41_mini → DETPass 0.9286, S_DET 0.9265, hard_gate 0, llm_calls 0; fitness=0.7353, **tok̂=lat̂≈1.0** (자기 자신이 DT 기준런이므로 정규화 자기일관성 증명) ✓
4. **fail-fast**: --model-key qwen25_coder_7b → "DirectTransfer baseline missing" 명시 오류 ✓
5. **τ sweep 경로**: --det-threshold 0.75 → DETPass 0.9286→0.8929, S_DET 불변 ✓
6. **pytest**: canonical 전체 141 passed(신규 24 포함), 68.5s ✓
7. **--help**: run_ga_search에 6개 플래그 노출 확인 ✓

## 정정·한계 기록

- **R1 발견 기록 정정**: canonical 밖 기존 변경 목록에 `utils/ga_search/ga_engine.py`(주석 1줄, WI-09 상태 문구) 누락돼 있었음. mtime 2026-08-11 13:31(본 세션 개시 전) → **기존 사용자 변경**, 본 세션 소행 아님. tutorial 이미지/gif 삭제도 동일(기존).
- **한계(기존 동작, 무변경)**: `run_feedback_loop.run_feedback_loop()` 내부 평가는 원래 det_profile을 전달받지 않아 legacy 기본으로 채점(strict에도 동일하게 적용되던 기존 비일관). paper_v1 GA에서 feedback 주입 경로를 쓰면 채점 기준이 섞임 — R4 full-GA 설계 시 feedback 비활성 또는 별도 검토 필요.
- **채택 tiebreak**: `_best_by_redesign_tiebreak`(DETPass·AvgDET·tokens·latency 사전식)는 무변경 — paper_v1은 모집단 순위만 식(7)로 결정. 논문 서술과 정합(채택 게이트는 별도 규칙).
