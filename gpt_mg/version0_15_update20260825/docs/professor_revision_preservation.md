# professor_revision_preservation.md (R1, 2026-08-25)

목적: 교수님 수정 PDF가 main.tex 대비 **무엇을 바꿨는지** 항목화하고, 각 항목이 편집 대상 main_revised.tex 개정(R5)에서 **보존/누락/역행/충돌** 중 어느 상태인지 분류 + 적용 규칙을 고정한다.

분류 기준:
- **PRESERVED**: main_revised.tex에 이미 반영됨
- **OMITTED**: main_revised.tex에 없음 → R5에서 반드시 반영
- **REVERTED**: main_revised.tex가 교수님 수정 이전(또는 다른 계보) 상태로 역행
- **CONFLICTED**: 마스터 지시·코드 현실과 충돌 → 해소 규칙 필요

| # | 교수님 수정 (main.tex → P) | 증거 | main_revised.tex 상태 | R5 적용 규칙 |
|---|---|---|---|---|
| 1 | DET 산문 → **식(3)** 형식화 + 명시적 가중치 벡터 w0 | prof p.6 | **OMITTED** (수식·수치 전무) | 식(3) 그대로 전사 |
| 2 | 가중치 근거 개정: "학습으로 얻은 값이 아니며" → "**예비 실험으로 학습한 값은 아니며** … 탐색 전에 정한 설계값 … 모든 모델에 동일 적용" | prof p.6 | **OMITTED** | 교수님 문구 채택 (사전 실험 최적화 주장 금지 — 마스터 §14와 일치) |
| 3 | D_i·τ=0.70 형식화 (식 4) + DETPass(식 5)·S_DET(식 6) | prof p.6 | **OMITTED** | 그대로 전사 |
| 4 | 적합도 **식(7)** 0.70/0.20/0.05/0.05 + "식(7)의 0.70은 식(4)의 τ와 역할이 다른 별도 설계값" | prof p.6-7 | **REVERTED** (상징식 α…λ₃ + ReplayFit/CatBal/SchemaRob/RegPen) | 식(7)로 교체, 상징식·RegPen 절 제거 |
| 5 | 복수 '허용 참조' max → **단일 기준 코드 r_i** | prof p.6 | CONFLICTED (R은 정성적 '참조 프로그램') | 본문은 단일 r_i 채택. 구현(paper_v1)은 다중참조 max 지원하되 단일 gt에서 동치 — 본문에 다중참조 주장 넣지 않음 |
| 6 | 유전자형 단순화 C=(A,R,F,S,Mt), 온도=탐욕 고정, max tokens {512,768,1024} | prof p.5 | **REVERTED** (R은 최다 변수 Q·M 포함) | 교수님 단순화 채택 |
| 7 | 데이터셋 명시: **JOICommands-280** + "독립 테스트셋 일반화 아님" 한계 명시 | prof | **OMITTED** (R은 Benchmark/Replay/Stress + 크기 TODO) | JOICommands-280 채택, Replay/Stress 서사 제거 |
| 8 | 비교 구성 축소: CloudRef·DirectTransfer 2개 | prof | **OMITTED** | 채택 |
| 9 | 결론 개정: 민감도 향후과제 문장 삭제, DETPass 보상 caveat 삭제, 새 한계(동일 벤치마크·정적 DET·Phi-3.5/Gemma-2 압축) | prof | **OMITTED** | **부분 CONFLICTED**: 본 과제가 민감도 실험을 신규 수행하므로, R5 결론은 교수님 새 한계 서술을 유지하되 민감도는 '향후과제'가 아닌 '**수행된 실험**'(신규 IV-4 하위절)으로 편입 — 교수님이 삭제한 이유(미수행 실험의 예고)를 실제 수행으로 해소 |
| 10 | 표 4에 '후보 간 변화' 열 추가 | prof | **OMITTED** | 채택 |
| 11 | 결과 수치(표 5·6) 무변경 유지 | prof | R은 자체 ReplayFit 열 포함 표 | 수치는 ledger ANCHOR 유지(마스터 §1: 수치 재측정은 별도 실험 범위), ReplayFit 열 제거, provenance는 감사 문서에 기록 |
| 12 | ReplayFit 미사용 유지 (B·P 모두 0회) | grep | **REVERTED** (R에 15개소) | 전면 제거 (마스터 확정사항) |

## 요약 통계

- PRESERVED: 0 / OMITTED: 7 / REVERTED: 3 / CONFLICTED: 2 (#5 참조 의미론, #9 민감도 결론 — 해소 규칙 상기 확정)
- 결론: main_revised.tex는 교수님 수정을 **하나도 반영하지 않은 구계보**다. R5의 IV-4 및 관련 절(초록·서론·V장 표·결론)은 증분 패치가 아니라 **교수님 PDF 기준 전면 재작성 + ReplayFit 제거 + 민감도 신규 절 추가**로 진행한다.

## 보존 원칙 (불변 헌장과 연결)

- 교수님이 **삭제**한 내용(민감도 예고 문장, DETPass 보상 caveat, 다중 허용 참조 서사)을 근거 없이 부활시키지 않는다. 민감도는 실측 결과로만 편입(#9 규칙).
- 교수님이 **개정한 문구**(#2)는 자구 수준으로 존중한다.
- 수치는 교수님도 무변경 유지(#11)했으므로 R5에서 수치 변경 없음 — 단 provenance 등급(ANCHOR/실측)은 감사 문서에 정직하게 남긴다.
