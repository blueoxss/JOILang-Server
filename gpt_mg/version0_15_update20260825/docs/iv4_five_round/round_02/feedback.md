# R2 feedback (2026-08-25)

## 발견 → R3·R4 계획 반영

1. **v15 후보 파서 기존 동작**: code 키 없는 후보(raw gt의 script 키)를 legacy/strict는 0.0 처리, paper_v1은 ROOT처럼 script fallback 수용 — 프로파일 간 정의 차이로 문서·테스트에 동결. R5 서술에서 paper_v1 기준으로만 서술(코드 필드 정규화 명시).
2. **DT 정규화 자기일관성**: 기준런 자신의 재채점에서 tok̂=lat̂≈1.0 — R4 민감도 표에서 이 성질을 sanity 열로 활용.
3. **재채점 성능**: 280행 paper_v1 재채점 <1초, LLM 호출 0 — R4의 5프로파일×LOO(8)×±20%(16)×τ(3) 전 조합 재채점이 수 분 내 가능함을 확인.
4. **재채점 실측치 vs 논문 앵커**: gpt41_mini 205513런 paper_v1 DETPass 0.9286 (v15 strict 집계 0.9107, 논문 앵커 94.5=avg_det 유사) — 평가기 선택이 집계에 유의미한 차이를 만듦 → R4 표에 3프로파일 병기, R5 서술 시 지표 정의 명확화 필수.
5. **feedback loop det_profile 미전달**(기존): R4 full-GA는 --feedback-attempts 0 또는 legacy 유지로 설계해 채점 기준 혼합 방지.

## 기준 강화 (R3에 적용)

- 경계 테스트 확대: 스케줄 부분일치(0.5), 서비스 다중도(Counter 의미론), 수치 리터럴 부호·소수, 빈 참조 코드, gt_refs 전원 파싱 실패, 후보 list 입력.
- no-LLM 보장: run_paper_v1_eval 실행 시 네트워크·LLM 클라이언트 임포트가 발생하지 않음을 정적/동적으로 증명.
- 회귀 fixture를 6→최소 12케이스로 확대(카테고리 다양화: cron 스케줄 케이스, wait-until, all() 리시버).
- 아티팩트 스키마 검증: rows.jsonl·summary.json 필수 키 스키마 테스트.
