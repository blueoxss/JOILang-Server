# 원고 반영 메모 (2026-09-16)

- 이번 재채점의 "Before" 기준 자료 `Pasted text(2).txt`(SHA f376385b…)와 `Pasted text.txt`(SHA afc80b31…)는 로컬 어디에도 없어
  교수님 서술 문장의 정확한 Before 를 인용하지 못했다. After 문안은 det_sensitivity_results.md §5 에 두었다.
- 현재 원고(main_260914_reviewed.tex)에서 갱신할 위치:
  1. 표 `tab:det_weight_settings` 각주의 "대안 조건의 재채점은 미완료 상태이다." → DT 열은 재채점 완료, GPS 열은 자료 부족으로
     미완료(작업용 표)라는 실제 상태로 바꾼다.
  2. "재현성 확인 상태" 문단(§V.1) 다음에 민감도 표(`\input{.../tab_det_sensitivity.tex}`)와 결과 문단을 넣되,
     GPS 열이 채워지기 전에는 완료된 실험 문장으로 쓰지 않는다.
- 원문 표의 값(89.3/94.2 …)은 재계산값과 모두 불일치하며(DT 열), 그 값을 만든 원시 출력·실행 기록은 저장소·로컬에 없다
  (projected_results_ledger.csv 의 ANCHOR 값 계열). 원문 값은 original_vs_recomputed.csv 에서만 비교 기준으로 쓴다.
- 해석 주의: 임계값 상승 시 두 방법의 차이 증가는 자동으로 성립하지 않는다(진단 표에서는 커졌으나 교차 적용 GPS 기준).
  "기준 가중치가 두 방법 모두에서 가장 높은 통과율"은 성립하지 않는다(DT: 균등 23.0 > 기준 22.0).
