# R1 feedback (2026-08-25)

R1 감사가 후속 라운드 계획을 바꾸는 사실 5가지와, 기준 강화 사항.

## 계획을 바꾸는 발견

1. **main_revised.tex는 교수님 계보가 아님** (구제목·상징 적합도·ReplayFit 15개소·한국어 mojibake·pdfLaTeX 프리앰블). → R5 스코프 확대: IV-4 증분 수정 → **전면 재작성 + 한국어 본문 main.tex 재도입 + 컴파일 엔진 확정**. R5 기준에 mojibake-잔존 0건 게이트 추가 예정.
2. **0.92643979 재현 성공 (ROOT 평가기)** → paper_v1의 의미론적 기준은 ROOT 8항으로 확정, 해당 fixture를 R2의 필수 회귀 게이트로 채택 (v15 strict로는 도달 불가함을 확인했으므로 paper_v1을 strict 개명으로 때우는 우회로가 원천 차단됨 — 헌장 금지사항과 정합).
3. **식(7) 적합도는 완전 신규 구현** (기존 4개 적합도 어느 것과도 다름; DirectTransfer 정규화도 전무). → R2에서 별도 모드로 추가, 기존 경로(legacy/strict/score_main) 무변경 회귀 게이트 필수.
4. **민감도 재채점 데이터 확보**: suite row_metrics에 8성분 저장 + 원문 output 보존 → R4는 LLM 호출 0회의 재채점(저장 output에 paper_v1 평가기 재실행)으로 수행 가능. GA 계수 민감도의 rescore/rerank도 ga_generation_progress.jsonl 분해값으로 가능. full-GA 수준만 신규 실행(PAUSED_LONG_RUN 후보).
5. **69.9 사건**: 부재 주장을 grep 1회로 단정했다가 오류 — 감사에서 적발, 당일 정정.

## 기준 강화 (R2부터 적용, 완화 아님)

- **부재 주장 증거 규칙**: "X가 없다"는 모든 주장은 실행한 명령과 출력 요지를 문서에 병기해야 VERIFIED로 인정 (69.9 사건 재발 방지). G5를 '거짓 VERIFIED 0건 + 거짓 부재 주장 0건'으로 확장.
- **fixture 정밀도 규칙**: 수치 재현 게이트는 abs 오차 한계를 명시 (0.92643979는 <1e-8).
- **회귀 게이트**: 기존 profile(legacy/strict) 출력 무변경을 fixture 집합으로 수치 증명해야 코드 라운드(R2·R3) 통과.

## R2로의 이관 지시

- paper_v1 DET: 0-1 스케일, w0, τ=0.70, hard gate(치명 오류→0), 다중참조 max(단일 gt 자연 축약), 성분 벡터 보존 출력.
- paper_v1 fitness: 0.70/0.20/0.05/0.05, Tok̂·Lat̂=동일 모델 DirectTransfer 정규화(기준값 파일 신규, 실측 아티팩트 우선), 기준값 부재 시 fail-fast.
- CLI: --det-profile paper_v1 / --det-weights / --det-threshold / --fitness-mode paper_v1 / --fitness-weights / --direct-transfer-baseline (v15 어휘 확장 방식).
- 테스트: 신규 ≥15, 전체 pytest green, 원본 폴더·root 경로 무변경 증명(git status).
