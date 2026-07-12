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
- [x] WI-01 설정 실측화 (audit/manifest.json + 가정 diff)
- [x] WI-07 적합도 5항 + 가중치 config + 층화 표본기
- [x] WI-05 리플레이 분리 + ReplayFit 구현
- [x] WI-06 채택 게이트 3조건
- [x] WI-16 GA 엔진 논문 정합(선택·교차·예산)
- [x] WI-04 S_DET 문서 + 추출 도구 + 이진vs등급 (실전 비교는 백그라운드 → ingest 대기)
- [x] WI-02 교차 전이 3×3 — 하네스 완성·검증 / 본실행 BLOCKED(승격물 부재+worker 재로드 비용)
- [x] WI-03 절제 사다리 A0~A4 — 하네스 완성·mock E2E / 본실행 BLOCKED(동일 사유)
- [x] WI-08 ledger 신설 + sync_ledger_to_tex.py
- [x] 회귀 가드: pytest 62 passed + 정본 체크 스크립트 2종 PASS

## 최종 리뷰 (세션 1)
- C-01~24 처리: CONTRADICTS 8건 중 코드 수정으로 해소 — C-06(부분: 연산·기록), C-07, C-08,
  C-14(+C-05), C-15/16(게이트), C-10/11(WI-16). FIX_PAPER 잔존 — C-03/C-04(S_DET 수식·임계),
  C-17(180/60/40 및 9범주), C-19(vLLM/max_model_len), C-01(정책·안전 검사 부재).
- 상세 상태표·재현 명령·다음 행동: STATE.md 및 최종 보고 참조.
- **교훈(lessons)**:
  1. 평가기의 code/script 이중 키 폴백은 조용한 무효화를 만든다 — gt 훼손·변형 도구는
     반드시 원본 키를 실측 후 조작할 것.
  2. `conda run` + heredoc 은 stdin 미전달 — 스크립트 파일 실행으로 통일.
  3. worker 백엔드의 호출당 모델 재로드가 실험 비용의 지배항 — 장시간 실험 설계 전에
     서빙 상주화를 먼저 해결해야 한다.
  4. 저장소 내 논문 PDF가 항상 최신 청사진은 아니다 — 주장 레지스트리를 기준으로 삼되
     PDF와의 차이 자체를 근거로 기록하면 감사가 강해진다.
  5. 백그라운드 장기 실행은 git worktree 스냅샷에서 돌려야 브랜치 전환과 충돌하지 않는다.
