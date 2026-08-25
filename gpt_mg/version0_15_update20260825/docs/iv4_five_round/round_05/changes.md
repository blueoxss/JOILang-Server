# R5 changes (2026-08-25)

## Paper 폴더 (유일 편집 파일)
- `main_revised.tex` 전면 개정 (77KB; 개정 전 103KB mojibake 초안은 artifacts/paper_20260825/main_revised_before_R5.tex 백업, SHA16 06a51f5571d85b83)
  - 상세: before_after.md (절별 변경표 + 교수님 12항목 체크)

## canonical 신규
- artifacts/paper_20260825/{main_revised_before_R5.tex, main_revised.tex(스테이징 사본), generated_tables/(3 tex), main_revised.pdf(11p, 286KB)}
- docs/iv4_five_round/round_05/{criteria.yaml, before_after.md, initial_evaluation.json, feedback.md, changes.md, manifest.json}
- docs/iv4_five_round/final_report.md

## 수정 반복 2건 (기록)
1. tectonic ICU linebreak iterator 실패 → 최소 재현(t1/t2/t3) 격리 후 \XeTeXlinebreaklocale "" 우회 (주석 명시)
2. ref[14] ä 글리프 부재 → Rocktaschel 표기, 재컴파일·재검증
