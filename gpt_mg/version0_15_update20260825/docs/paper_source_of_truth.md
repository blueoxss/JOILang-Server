# paper_source_of_truth.md (R1, 2026-08-25)

목적: `Paper/drafted/2026_JOK/`의 4개 파일 중 **어떤 문서가 IV-4 방법론의 기준(source of truth)인지** 확정하고, 각 파일의 정체·계보·역할을 증거와 함께 고정한다.

## 결론 (한 줄)

**IV-4 방법론의 기준 = 교수님 수정 PDF(`main_professor_revision_v15_clean.pdf`)의 식 (3)–(7) 형식화**이며, 수치·서사의 뿌리는 `main.tex`(Before)이다. **편집 대상인 `main_revised.tex`는 이 계보가 아니라 더 오래된 ReplayFit 초안**으로, IV-4는 증분 수정이 아닌 **전면 교체**가 필요하다.

## 파일별 정체 (전수 감사 결과)

| 파일 | 정체 | 컴파일러/계보 | IV-4 상태 |
|---|---|---|---|
| `main.tex` (73KB, 읽기전용) | GPS-PromptOps 논문 Before본 | XeLaTeX 소스 | 8항 가중치 **산문** 서술(w0 일치), τ=0.70, 적합도 0.70/0.20/0.05/0.05 산문, 민감도=향후 과제(751행) |
| `main_professor_revision_v15_clean.pdf` (읽기전용) | 교수님 수정본. **소스 .tex는 폴더에 없음** (pdfinfo Creator=XeTeX 2026.08.24; main.tex에 없는 내용 포함 → main.tex의 교수 수정 후속본) | XeTeX, main.tex 계보 | **식 (3)–(7) 형식화**: e_i=Σw_k·s_ik, w=(0.30,0.15,0.15,0.10,0.10,0.10,0.05,0.05), D_i(τ=0.70), DETPass, S_DET, f=0.70·DETPass+0.20·S_DET−0.05·Tok−0.05·Lat |
| `main_revised.tex` (103KB, **유일 편집 대상**) | **구(舊) 초안**: 영문 제목 "Genetic Prompt Search … Rule-Based Validation and Failure-Case Feedback"(84행), ReplayFit 방법론 15회 등장, 상징적 적합도(α…λ₃, 숫자 없음), τ·가중치·수식 전무, TODO 주석 잔존 | pdfLaTeX/kotex 프리앰블. **한국어 전체가 mojibake 손상(U+FFFD 포함, 비가역)** | 교수님 형식화 내용 **전부 부재** — IV-4 전면 재작성 필요 |
| `_2026_JOK__Genetic_Prompt_Search_…_Failure_Case_Feedback.pdf` (3.9MB, 읽기전용) | **파일명은 구제목이지만 내용은 main.tex의 pdfTeX 컴파일본** (초록 축자 동일, ReplayFit 0회) | pdfTeX 1.40.27, 2026-08-25 19:29 | main.tex과 동일 (방법론 참조 가치는 main.tex과 중복) |

## 기준 채택 규칙 (R2–R5에서 적용)

1. **수식·기호·임계값**: 교수님 PDF 식 (3)–(7)을 그대로 따른다.
   - e_i(P,M)=Σ_{k=1..8} w_k·s_ik(y_i, r_i), Σw_k=1, w0=(0.30,0.15,0.15,0.10,0.10,0.10,0.05,0.05)
   - D_i = 1 iff (치명 오류 없음 ∧ e_i ≥ τ), τ=0.70
   - DETPass=(1/N)ΣD_i, S_DET=(1/N)Σe_i
   - f(C,M)=0.70·DETPass+0.20·S_DET−0.05·Tok−0.05·Lat (Tok/Lat: 동일 모델 DirectTransfer 정규화)
2. **가중치 근거 문구**: 교수님 개정 표현을 채택 — "실행 결과에 직접 영향을 주는 차이를 크게 반영하도록 **탐색 전에 정한 설계값**이며, **예비 실험으로 학습한 값은 아니고** 모든 모델에 동일 적용." (사전 실험 최적화 주장 금지 — 마스터 지시 §14와 일치)
3. **참조 의미론**: main.tex(복수 '허용 참조' max) vs 교수님 PDF(단일 기준 코드 r_i) 충돌 → **구현은 다중 참조 max 지원(gt_refs 부재 시 단일 gt로 자연 축약)**, 본문 서술은 R5에서 교수님 단일 참조 형식화를 기본으로 하되 데이터셋이 단일 gt이므로 두 정의가 실험상 동치임을 확인함 (JOICommands-280.csv는 gt 1열뿐, gt_refs 식별자 저장소 전체 0건).
4. **ReplayFit**: main.tex·교수님 PDF·4번 PDF 모두 0회. 코드도 미계산(run_ga_search.py:2488 `replay_fit=''`). → main_revised.tex의 ReplayFit 15개소(수치 7.9–17.0%p 포함)는 **현행 방법에서 전면 제거** 대상 (마스터 지시 확정사항과 일치).
5. **민감도 실험**: 4개 파일 어디에도 실제 민감도 실험 없음(main.tex 751행 향후과제 문구가 유일했고 교수님이 그 문장마저 삭제). → 본 과제의 민감도 절은 **완전 신규 기여**로 서술한다.

## 편집 시 주의 (R5 이관)

- main_revised.tex 한국어는 mojibake로 **손상 텍스트를 재활용할 수 없음** — 한국어 본문은 main.tex(정상 UTF-8)에서 재도입해야 한다.
- 프리앰블이 pdfLaTeX/kotex 스타일 — 격리 outdir 컴파일 시 엔진 선택(xelatex 권장)과 프리앰블 정합을 먼저 확정할 것.
- 교수님 PDF의 소스 .tex 부재 → 식 전사는 PDF 텍스트 추출본(pdftotext) 기준으로 하되 수식 기호는 눈검증 필수.

## 증거 인덱스

- main.tex:577-582(가중치 산문), 580·584-595(τ·DETPass·S_DET), 598-610(허용 참조·worked example), 614(적합도), 751(민감도 향후과제)
- prof PDF 추출본: p.6 식(3) 가중치 벡터·근거문, 식(4)-(7), 단일 r_i, JOICommands-280, 탐욕 디코딩
- main_revised.tex:84(구제목), 455-486(상징 적합도·RegPen), 112~601(ReplayFit 15개소), 503-509(TODO), U+FFFD 존재
- 4번 PDF: pdfinfo pdfTeX·초록 축자 대조, ReplayFit grep 0
