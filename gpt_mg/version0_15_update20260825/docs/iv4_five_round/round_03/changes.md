# R3 changes (2026-08-25)

## 신규

- `tests/fixtures/regression_expanded.json` — 12행(cron 3·wait-until 3·all() 3·다중호출 3)×2후보(exact/perturbed)×2프로파일을 **원본 20260413 별도 subprocess 실측으로 동결** (strict 중간값 케이스 7건 포함 — 자명하지 않은 경로 커버)
- `tests/fixtures/paper_v1_expanded_baseline.json` — 동일 케이스의 paper_v1 e·pass를 R3 시점 동결 (R4·R5의 로직 불변 감시)
- `tests/test_paper_v1_boundary.py` — 경계 16 + no-LLM 2 + 스키마 1 = 19 테스트
- `tests/test_paper_v1_regression_expanded.py` — 14 테스트 (12행 파라미터라이즈 + 형태 + paper_v1 baseline)

## 수정 (1건, 근본 원인 수정 — 근거)

- `utils/det_paper_v1.py`: 출력 `e`·`components`의 12자리 반올림 제거(원 정밀도 보존).
  - **원인**: det_pass는 내부 원값으로 판정하는데 출력 e는 반올림돼, τ 경계(threshold=출력 e)에서 판정 불일치 발생. 반올림 값은 R4 재가중 재채점에도 오차 유입.
  - **영향**: 표시용 det_score(round 4)는 유지. 기존 테스트 전부 통과(허용오차 내 동일). 회귀 fixture와의 비교도 1e-9 내 동일.

## 경계 동작 분류 (G1 질적 게이트)

| 동작 | 분류 |
|---|---|
| period 0 ≡ "" ≡ None (normalize_text의 falsy 처리) | **의도된 ROOT 동작** — '스케줄 없음'의 표기 자유. 이식 보존, 테스트 동결 |
| 빈 참조 code → missing_gt_code(비치명), 빈 참조 목록 coverage=1.0 | ROOT 동일. hard gate 아님 — 데이터셋에 빈 gt 없음(280행 전수), 한계로만 기록 |
| 후보 list 입력 → 첫 원소 사용 | ROOT parse_json_object 동작 보존 |
| 서비스 다중도 Counter 의미론(2회 요구·1회 생성→0.5) | 의도 — coverage/precision 대칭 |
| 수치 부호 구분(-5≠5), 소수 매칭 | 의도 |
| enum 소문자 정규화 | 의도 |
| τ 경계 e==τ → 통과(>= 비교) | 의도, 식(4) 정의와 일치 |

## 검증

- pytest: paper_v1 스택 57, canonical 전체 **174 passed** exit 0
- no-LLM: 정적(소스 내 local_llm_client/openai/anthropic/requests 부재) + 동적(subprocess 실행 후 sys.modules 검사, summary.llm_calls==0)
- 격리: canonical 밖 신규 변경 0건. 추가 발견된 M(ga_operators.py 8/12, prompt_patch_apply.py 8/11)·?? (artifacts/fullprompt_runs 7/31)은 **mtime이 세션 개시 전** — 기존 사용자 변경으로 분류, 목록 완성: {pipeline_common.py, ga_engine.py, ga_operators.py, prompt_patch_apply.py, tutorial 삭제 다수, fullprompt_runs/}
