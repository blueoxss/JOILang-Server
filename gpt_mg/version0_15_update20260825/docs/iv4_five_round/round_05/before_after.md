# R5 개정 전후 대조 (main_revised.tex, 2026-08-25)

개정 전 백업: `artifacts/paper_20260825/main_revised_before_R5.tex` (SHA16 06a51f5571d85b83, 631줄, 103KB)
개정 후: 77KB, 11페이지 컴파일 (tectonic, artifacts/paper_20260825/main_revised.pdf)

## 개정 전 상태 (R1 감사 확정)

구제목 영문 초안("Genetic Prompt Search … Rule-Based Validation and Failure-Case Feedback"), 한국어 전체 mojibake(U+FFFD) 손상, 상징적 적합도(α…λ₃, 숫자 없음), ReplayFit 15개소·RegPen·CatBal·SchemaRob, τ·가중치·수식 전무, TODO 주석, 교차전이표 없음, pdfLaTeX 프리앰블.

## 개정 방법

증분 수정이 불가능한 상태(잘못된 계보 + 비가역 손상)였으므로, **main.tex(정상 한국어, GPS-PromptOps 계보)를 기반으로 교수님 수정 PDF의 형식화를 적용하고 민감도 절을 신설**하는 전면 재작성. 결과 수치는 전부 main.tex=교수님 PDF 값 그대로(무변경).

## 절별 변경 목록

| 절 | 변경 | 근거 |
|---|---|---|
| 프리앰블 | main.tex XeLaTeX 구성 + fonts/ 부재 시 시스템 나눔 서체 fallback + `\XeTeXlinebreaklocale ""`(tectonic ICU 우회, TeX Live에서 무해) | 컴파일 재현성 |
| 제목·초록·요약 | main.tex 유지 + 민감도 1문장 추가(영·국문) | 신규 V.4 반영 |
| I·II장 | main.tex 유지 (기여 4번째 항목에 '민감도 분석' 추가; '블록 순서·버전' 문구는 교수님 단순화에 맞춰 제거) | 교수님 #6 |
| III.2 | 식(1) C=(A,R,F,S,Mt) 단순화 + temperature 탐욕 고정 문단 + 식(2) 단순화 | 교수님 #6 (V·순서·Θ 제거) |
| 표4 | '후보 간 변화' 열(입력별 구성(비탐색)·핵심 고정·규칙 탐색), 예제 1–3개 | 교수님 #10 |
| IV.2 유전 연산 | 블록 버전 문구 제거, 예제 수·최대 토큰 상속으로 개정 | 교수님 #6 |
| **IV.4** | **전면 교체**: 단일 기준 코드 r_i, 식(3) w0=(0.30,0.15,0.15,0.10,0.10,0.10,0.05,0.05), 근거 자구("예비 실험으로 학습한 값은 아니며…"), 식(4) τ=0.70, 식(5)(6), Tok/Lat 정의, 식(7) 0.70/0.20/0.05/0.05 + "역할이 다른 별도 설계값" + V.4 전방 참조 2문장 | 교수님 #1-#5 |
| V.1 | JOICommands-280 문단(280개, 범주 구성, 독립 시험집합 아님 명시) | 교수님 #7 |
| 표5·6 | 수치 무변경, ReplayFit 열 없음(main.tex 형태 유지) | 교수님 #11·#12 |
| **V.4 (신설)** | 가중치·계수 민감도: 재채점 방법·사전 고정 판정 기준 서술 + 표7(\input det_weight_sensitivity_summary)·표8(\input tau_sensitivity)·표9(\input ga_fitness_sensitivity) + 실측 수치 해석 + "재채점 기반, full-GA 재실행은 후속 과제" 한계 명시 | R4 실측; 교수님 #9 충돌 해소(미수행 예고 삭제 → 실제 수행으로 편입) |
| VI 결론 | 교수님 개정본 채택 + 민감도 결과 1문장 | 교수님 #9 |
| 참고문헌 | references.bib 부재 → 교수님 PDF References [1]–[20]을 thebibliography로 전사 (\cite 키 전부 해소; Rocktäschel→Rocktaschel: 나눔명조 ä 글리프 부재) | 컴파일 성립 |
| 삭제 | ReplayFit 15개소·RegPen·CatBal·SchemaRob·Benchmark/Replay/Stress 서사·TODO 주석·상징 적합도 전부 | 마스터 확정사항 |

## 교수님 12항목 반영 체크

#1 식(3) ✓ / #2 근거 자구 ✓ / #3 식(4)-(6) ✓ / #4 식(7) ✓ / #5 단일 r_i ✓(구현은 다중참조 지원하되 본문 무주장) / #6 유전자형 단순화 ✓ / #7 JOICommands-280 ✓ / #8 비교 2구성 ✓ / #9 결론 개정 ✓(민감도는 실측 수행으로 편입) / #10 표4 열 ✓ / #11 수치 무변경 ✓ / #12 ReplayFit 0회 ✓

## 잔여 사항 (정직 기록)

- 그림 2 png(figure_ga_based_joilang_pipeline_diagram.png)는 Paper 폴더·저장소 전체에 부재 → \IfFileExists 가드로 placeholder 렌더(main.tex와 동일 동작). 원본 그림 파일 확보 시 자동 포함.
- 표 8(τ)은 \resizebox로 축소되어 글자가 작음 — 조판 단계에서 열 축약본 고려 가능.
- p.9 우측 단이 float 배치로 비어 있음(표7·8·9가 p.10으로 밀림) — 내용 오류 아님, 조판 미세조정 여지.
- fonts/NotoSerifKR 부재 환경에서는 나눔명조로 렌더(내용 동일) — fonts/ 배포 시 원 서체 사용.
