# todo — GPS-PromptOps 감사·자가수리

## PHASE 0 (완료)
- [x] 환경 검증(conda sg, env vars, pytest 부재 기록) + 시작 스냅샷 커밋
- [x] 지형 파악(모듈 지도·엔트리포인트·config·데이터 흐름)
- [x] C-01~C-24 판정 (7 병렬 에이전트 + 직접 정독 교차검증)
- [x] audit/claim_code_traceability.csv + audit/phase0_report.md
- [x] 평가기 스모크(벤치마크 10건, det_pass_rate 산출 확인)

## PHASE 1 (완료 조건: 백로그 확정 + STATE.md)
- [x] 백로그 조정: WI-16 신설, C-12/13 VERIFY-ONLY, WI-05 최우선, WI-08 재정의
- [x] STATE.md 생성
- [ ] GPU/로컬 모델 프로브(7-6) → BLOCKED 판단 근거 기록
- [ ] pytest 설치(테스트 러너 확보)

## PHASE 2 — P0 실행 순서 (의존성 순)
- [ ] WI-01 설정 실측화 (audit/manifest.json + 가정 diff)
- [ ] WI-07 적합도 5항 + 가중치 config + 층화 표본기
- [ ] WI-05 리플레이 분리 + ReplayFit 구현
- [ ] WI-06 채택 게이트 3조건
- [ ] WI-16 GA 엔진 논문 정합(선택·교차·예산)
- [ ] WI-04 S_DET 문서 + 추출 도구 + 이진vs등급
- [ ] WI-02 교차 전이 3×3 (실행은 GPU 종속)
- [ ] WI-03 절제 사다리 A0~A4 (실행은 GPU 종속)
- [ ] WI-08 ledger 신설 + sync_ledger_to_tex.py
- [ ] 회귀 가드: 전체 테스트 + 평가기 스모크 재실행

## 최종 리뷰 (작업 종료 시 작성)
- [ ] C-01~24 최종 상태, WI 상태표, MEASURED 전환 목록, FIX_PAPER 목록, 재현 명령어, 다음 세션 3행동
