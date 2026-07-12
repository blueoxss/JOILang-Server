# 진단 — 이 실행(20260712T180451Z)의 수치는 무효 (ledger 반영 금지)

## 증상
- graded/binary 양 모드, 전 세대에서 best_avg_det_score = 31.2645 로 동일, DETPass 0.0.
- 8개 상이한 명령(row 28~263, cat1~8)의 생성 코드가 **전부 동일**
  (`volume = (#Speaker).speaker_volume ...`).

## 원인 (원인 문장)
1. **cli 가 첫 행 명령으로 1회만 렌더한 패키지를 candidate_generation 이 행마다
   재구성하지 않아서, 모든 행이 row 28("Lower the speaker volume by one.")의
   user 메시지로 생성되었다.** 증거: `prompts/row_28_*.json` 과 `prompts/row_263_*.json`
   의 messages 완전 동일. greedy 디코딩이므로 동일 프롬프트 → 동일 출력.
   → WI-17 에서 `candidate_generation.package_for_row()` 로 수정, 회귀 테스트 고정.
2. 부차 요인: 초기 개체군이 동일한 fallback genome 3개(다양성 0)라 탐색 신호가
   퇴화하고, v13 모노리스(~53k 토큰)로 tok̂·lat̂ 이 1.0 포화(적합도 상수 페널티).

## 조치
- 이 실행은 ledger ingest 대상이 아니다: sync_ledger_to_tex.py 의 ingest 가
  meta.json `ledger_grade=true` 를 요구하도록 보강했고 이 실행에는 해당 표기가 없다.
- 산출물은 결함 재현 근거로 보존한다(P-3 원본 보존).
