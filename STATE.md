# STATE — GPS-PromptOps 감사·자가수리 (마스터 프롬프트 세션)

- 최종 갱신: 2026-07-13 세션 1
- HEAD 기준: PHASE 0 완료 커밋 직후 (아래 백로그 표의 "마지막 커밋" 참조)
- PHASE 0 산출물: `audit/claim_code_traceability.csv`, `audit/phase0_report.md`, 스모크 `results/phase0_smoke/20260712T170819Z/`
- 판정 분포: IMPLEMENTED 3 / PARTIAL 9 / MISSING 4 / CONTRADICTS_PAPER 8 (상세는 audit/)

## 환경 메모
- conda env `sg` (Python 3.9.21). pytest 8.4.2, accelerate 1.10.1 설치 완료(세션 1).
- GPU: RTX A6000 48GB ×2. HF 캐시에 Qwen2.5-Coder-7B/14B, Llama-3.1-8B, gemma-2-9b, Phi-3.5 존재.
  7-6 프로브 성공: worker 모드 Qwen7B 1건 생성(RC=0, results/phase1_worker_probe/20260712T172618Z).
  → GPU 실행형 WI(02/03/04c) UNBLOCKED.
- 결함 메모: worker 백엔드가 usage 토큰을 0으로 보고 → 적합도 토큰 항 실효 없음(WI-07에서 처리).
- heredoc + `conda run` 조합은 stdin이 전달되지 않음 — 스크립트 파일로 실행할 것.

## 백로그

| WI | 내용 | 우선 | 상태 | 마지막 커밋 | 다음 행동 |
|---|---|---|---|---|---|
| WI-01 | 설정 실측화: manifest.json + 논문 가정 diff 표 | P0 | DONE | 266788a0 | (완료) 재생성: tools/build_settings_manifest.py |
| WI-07 | 적합도 5항 정리 + 가중치 config 외부화 + 층화 표본기 | P0 | DONE | (wi-07 브랜치 머지) | (완료) γ항 실배선은 WI-05에서, --fitness-mode 배선은 WI-04c에서 |
| WI-05 | 리플레이 search/holdout 분리 + ReplayFit 계산 신규 구현 | P0 | DONE | (wi-05 브랜치 머지) | (완료) 실측 30건→15/15. holdout 게이트 소비는 WI-06에서 |
| WI-06 | 채택 게이트 3조건 하드 게이트 (레거시 regression_gate 이식+확장) | P0 | DONE | (wi-06 브랜치 머지) | (완료) 안전 부분집합은 데이터 부재로 구성 불가 — FIX_PAPER 기록 |
| WI-16 | (신규) 정본 GA 엔진 논문 정합: elite 2·tournament 3·p_m 0.35·블록 교차·6연산 (레거시 ga_selection/ga_mutation 이식) | P0 | TODO | - | WI-07 config 체계 위에서 이식 |
| WI-04 | S_DET 정합: 수식 문서 + 3후보 실측 추출 도구 + 이진vs등급 비교 모드 | P0 | TODO | - | (a) 문서는 즉시 가능, (c)는 WI-07 이후 |
| WI-02 | 교차 전이 3×3 러너 + 실행 | P0 | TODO | - | 엔진 정합(WI-16) 후. 실행은 GPU 프로브 결과 종속 |
| WI-03 | 절제 사다리 A0~A4 토글 + 실행 | P0 | TODO | - | WI-05/06/07/16 완료 후 |
| WI-08 | ledger 신설(저장소에 원본 부재) + sync_ledger_to_tex.py | P0 | TODO | - | ledger 스키마 정의부터 (†해제는 스크립트만) |
| WI-09 | 유전형 g=(B,O,V,R,E,Θ) 완성 + 메타데이터 분리 + Θ 실배선 | P1 | TODO | - | - |
| WI-10 | 회귀 스위트(C_crit 고정 목록 + pytest) | P1 | TODO | - | - |
| WI-11 | 재현성 팩: seed·argv·config 스냅샷 자동 기록 | P1 | TODO | - | - |
| WI-12 | 클라우드 역방향 교차(3 프롬프트 → GPT-4.1-mini) | P1 | TODO | - | - |
| WI-13 | self-repair E2 (로컬 vs GPT-4.1-mini 수정문) | P2 | TODO | - | - |
| WI-14 | seed 3회 분산 + 동일 예산 무작위 탐색 비교 | P2 | TODO | - | - |
| WI-15 | 카테고리 라우터 프로토타입 | P2 | TODO | - | - |

## VERIFY-ONLY (PHASE 0에서 IMPLEMENTED 판정)
- C-02 DETPass 이진 평균, C-12 실패→블록 매핑, C-13 advisor 위임·국소·opt-in — WI 진행 중 회귀만 감시.

## 재개 절차 (새 세션)
1. 이 파일과 `audit/phase0_report.md`를 읽는다. PHASE 0은 재수행하지 않는다.
2. `git log --oneline -5`로 HEAD가 마지막 기록과 일치하는지 확인. 다르면 차이 감사 후 이 표를 조정.
3. 상태가 DOING/TODO인 최상단 WI부터 §5 자가 수리 루프로 재개.
