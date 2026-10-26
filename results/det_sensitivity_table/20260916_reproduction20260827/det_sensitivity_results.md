# DET 민감도 재채점 결과 — 20260916_reproduction20260827

## 1. 재계산한 여섯 행(대상 모델 평균 DETPass, %) — 논문 표 형식

| 구분 | 민감도 조건 | DT (%) | GPS (%) | 차이 (%p) |
|---|---|---:|---:|---:|
| 임계값 / 기준 가중치 | τ=0.85 | 33.1 | N/A | N/A |
| 임계값 / 기준 가중치 | τ=0.90 (기준) | 22.0 | N/A | N/A |
| 임계값 / 기준 가중치 | τ=0.95 | 1.5 | N/A | N/A |
| 가중치 / τ=0.90 | 균등 | 23.0 | N/A | N/A |
| 가중치 / τ=0.90 | 실행 의미 중심 | 19.3 | N/A | N/A |
| 가중치 / τ=0.90 | 전체 구조 중심 | 21.1 | N/A | N/A |

GPS 열의 N/A: Qwen2.5-Coder-7B 와 Llama-3.1-8B 는 자기 모델을 대상으로 탐색한 최종 프롬프트의 280행 출력이 없다.
14B 의 GPS 값은 아래 모델별 표에 있다. 이 표는 **작업용 표 상태**이며 완성된 논문 표가 아니다.

## 2. 진단(별도 분석): 14B 용 GPS 프롬프트를 7B·L8 에 교차 적용한 출력을 GPS 로 넣은 평균

| 조건 | DT (%) | GPS* (%) | 차이* (%p) |
|---|---:|---:|---:|
| τ=0.85 | 33.1 | 47.1 | +14.0 |
| τ=0.90 (기준) | 22.0 | 38.3 | +16.3 |
| τ=0.95 | 1.5 | 27.9 | +26.3 |
| 균등 | 23.0 | 37.9 | +14.9 |
| 실행 의미 중심 | 19.3 | 38.5 | +19.2 |
| 전체 구조 중심 | 21.1 | 38.3 | +17.3 |

\* 논문의 GPS-PromptOps 정의(모델별 탐색 프롬프트)와 다르므로 논문 표에 넣지 않는다.

## 3. 모델별 통과수·분모·DETPass·S_DET (단일 run, seed 0, repeat 0)

| 조건 | 모델 | 방법 | 역할 | 통과/분모 | DETPass (%) | S_DET |
|---|---|---|---|---:|---:|---:|
| τ=0.85 | Qwen2.5-Coder-7B | DT | paper_dt | 88/280 | 31.43 | 0.7448 |
| τ=0.85 | Qwen2.5-Coder-7B | GPS | diagnostic_gps_cross_applied | 115/280 | 41.07 | 0.7862 |
| τ=0.85 | Llama-3.1-8B | DT | paper_dt | 67/280 | 23.93 | 0.6855 |
| τ=0.85 | Llama-3.1-8B | GPS | diagnostic_gps_cross_applied | 76/280 | 27.14 | 0.5355 |
| τ=0.85 | Qwen2.5-Coder-14B | DT | paper_dt | 123/280 | 43.93 | 0.7922 |
| τ=0.85 | Qwen2.5-Coder-14B | GPS | paper_gps | 205/280 | 73.21 | 0.8901 |
| τ=0.90 (기준) | Qwen2.5-Coder-7B | DT | paper_dt | 61/280 | 21.79 | 0.7448 |
| τ=0.90 (기준) | Qwen2.5-Coder-7B | GPS | diagnostic_gps_cross_applied | 85/280 | 30.36 | 0.7862 |
| τ=0.90 (기준) | Llama-3.1-8B | DT | paper_dt | 47/280 | 16.79 | 0.6855 |
| τ=0.90 (기준) | Llama-3.1-8B | GPS | diagnostic_gps_cross_applied | 58/280 | 20.71 | 0.5355 |
| τ=0.90 (기준) | Qwen2.5-Coder-14B | DT | paper_dt | 77/280 | 27.50 | 0.7922 |
| τ=0.90 (기준) | Qwen2.5-Coder-14B | GPS | paper_gps | 179/280 | 63.93 | 0.8901 |
| τ=0.95 | Qwen2.5-Coder-7B | DT | paper_dt | 5/280 | 1.79 | 0.7448 |
| τ=0.95 | Qwen2.5-Coder-7B | GPS | diagnostic_gps_cross_applied | 58/280 | 20.71 | 0.7862 |
| τ=0.95 | Llama-3.1-8B | DT | paper_dt | 3/280 | 1.07 | 0.6855 |
| τ=0.95 | Llama-3.1-8B | GPS | diagnostic_gps_cross_applied | 33/280 | 11.79 | 0.5355 |
| τ=0.95 | Qwen2.5-Coder-14B | DT | paper_dt | 5/280 | 1.79 | 0.7922 |
| τ=0.95 | Qwen2.5-Coder-14B | GPS | paper_gps | 143/280 | 51.07 | 0.8901 |
| 균등 | Qwen2.5-Coder-7B | DT | paper_dt | 66/280 | 23.57 | 0.7664 |
| 균등 | Qwen2.5-Coder-7B | GPS | diagnostic_gps_cross_applied | 87/280 | 31.07 | 0.8046 |
| 균등 | Llama-3.1-8B | DT | paper_dt | 48/280 | 17.14 | 0.7015 |
| 균등 | Llama-3.1-8B | GPS | diagnostic_gps_cross_applied | 58/280 | 20.71 | 0.5619 |
| 균등 | Qwen2.5-Coder-14B | DT | paper_dt | 79/280 | 28.21 | 0.8056 |
| 균등 | Qwen2.5-Coder-14B | GPS | paper_gps | 173/280 | 61.79 | 0.8988 |
| 실행 의미 중심 | Qwen2.5-Coder-7B | DT | paper_dt | 50/280 | 17.86 | 0.7141 |
| 실행 의미 중심 | Qwen2.5-Coder-7B | GPS | diagnostic_gps_cross_applied | 88/280 | 31.43 | 0.7801 |
| 실행 의미 중심 | Llama-3.1-8B | DT | paper_dt | 44/280 | 15.71 | 0.6521 |
| 실행 의미 중심 | Llama-3.1-8B | GPS | diagnostic_gps_cross_applied | 60/280 | 21.43 | 0.5386 |
| 실행 의미 중심 | Qwen2.5-Coder-14B | DT | paper_dt | 68/280 | 24.29 | 0.7633 |
| 실행 의미 중심 | Qwen2.5-Coder-14B | GPS | paper_gps | 175/280 | 62.50 | 0.8870 |
| 전체 구조 중심 | Qwen2.5-Coder-7B | DT | paper_dt | 57/280 | 20.36 | 0.7502 |
| 전체 구조 중심 | Qwen2.5-Coder-7B | GPS | diagnostic_gps_cross_applied | 85/280 | 30.36 | 0.7819 |
| 전체 구조 중심 | Llama-3.1-8B | DT | paper_dt | 48/280 | 17.14 | 0.6934 |
| 전체 구조 중심 | Llama-3.1-8B | GPS | diagnostic_gps_cross_applied | 57/280 | 20.36 | 0.5236 |
| 전체 구조 중심 | Qwen2.5-Coder-14B | DT | paper_dt | 72/280 | 25.71 | 0.7964 |
| 전체 구조 중심 | Qwen2.5-Coder-14B | GPS | paper_gps | 180/280 | 64.29 | 0.8878 |

정합성: 파싱 실패(e=0, v=0) 91행, 저장 성분과 재계산 성분 불일치 0행, 단조성 성립, S_DET ≥ τ·DETPass 성립.

## 4. 기존 표와의 대조

| 조건 | 열 | 원문 | 재계산 | 차이(%p) | 상태 |
|---|---|---:|---:|---:|---|
| base_t085 | dt | 89.3 | 33.1 | -56.2 | 실제 불일치 |
| base_t085 | gps | 94.2 | N/A |  | N/A: 자료 부족(자기 모델용 GPS 최종 프롬프트 출력 없음) |
| base_t085 | diff | 4.9 | N/A |  | N/A: 자료 부족(자기 모델용 GPS 최종 프롬프트 출력 없음) |
| base_t090 | dt | 86.5 | 22.0 | -64.5 | 실제 불일치 |
| base_t090 | gps | 91.8 | N/A |  | N/A: 자료 부족(자기 모델용 GPS 최종 프롬프트 출력 없음) |
| base_t090 | diff | 5.2 | N/A |  | N/A: 자료 부족(자기 모델용 GPS 최종 프롬프트 출력 없음) |
| base_t095 | dt | 80.9 | 1.5 | -79.4 | 실제 불일치 |
| base_t095 | gps | 86.4 | N/A |  | N/A: 자료 부족(자기 모델용 GPS 최종 프롬프트 출력 없음) |
| base_t095 | diff | 5.5 | N/A |  | N/A: 자료 부족(자기 모델용 GPS 최종 프롬프트 출력 없음) |
| uniform_t090 | dt | 85.9 | 23.0 | -62.9 | 실제 불일치 |
| uniform_t090 | gps | 91.1 | N/A |  | N/A: 자료 부족(자기 모델용 GPS 최종 프롬프트 출력 없음) |
| uniform_t090 | diff | 5.2 | N/A |  | N/A: 자료 부족(자기 모델용 GPS 최종 프롬프트 출력 없음) |
| execution_t090 | dt | 86.2 | 19.3 | -66.9 | 실제 불일치 |
| execution_t090 | gps | 91.6 | N/A |  | N/A: 자료 부족(자기 모델용 GPS 최종 프롬프트 출력 없음) |
| execution_t090 | diff | 5.4 | N/A |  | N/A: 자료 부족(자기 모델용 GPS 최종 프롬프트 출력 없음) |
| structure_t090 | dt | 86.8 | 21.1 | -65.7 | 실제 불일치 |
| structure_t090 | gps | 91.4 | N/A |  | N/A: 자료 부족(자기 모델용 GPS 최종 프롬프트 출력 없음) |
| structure_t090 | diff | 4.6 | N/A |  | N/A: 자료 부족(자기 모델용 GPS 최종 프롬프트 출력 없음) |

## 5. 논문용 국문 결과 문단(초안; 수치는 CSV 자동 삽입)

식~(\ref{eq:det_item_score})의 가중치와 식~(\ref{eq:det_item_pass})의 통과 임계값이 비교 결과에 주는 영향을 확인하기 위해, 자연어 명령·서비스 문맥·기준 코드와 모델별 최종 프롬프트·생성 출력을 고정한 채 DET 내부 가중치 또는 통과 임계값만 바꾸어 재채점하였다. 재채점은 저장된 출력에서 여덟 비교값을 다시 추출해 가중합을 계산하며, LLM 추론·출력 수정·프롬프트 재선택·GA 재탐색을 하지 않는다.

기준 가중치에서 임계값을 0.85, 0.90, 0.95 로 바꾸면 DirectTransfer 의 대상 모델 평균 DETPass 는 각각 33.1\%, 22.0\%, 1.5\% 였다. GPS-PromptOps 의 대상 모델 평균은 세 모델 중 한 모델(Qwen2.5-Coder-14B)의 모델별 최종 프롬프트 출력만 확보되어 계산하지 않았다(작업용 표 상태). 

임계값 0.90 에서 가중치를 균등, 실행 의미 중심, 전체 구조 중심 배분(표~\ref{tab:det_weight_settings})으로 바꾸면 DirectTransfer 는 각각 23.0\%, 19.3\%, 21.1\% 로, 기준 배분(22.0\%) 대비 변화는 임계값 변화보다 작았다.

검토한 여섯 조건에서 GPS-PromptOps 의 우위 여부는 세 모델 모두의 모델별 최종 프롬프트 출력이 확보된 뒤에 판정한다. GA 를 다시 실행하지 않았으므로 이 표는 탐색 경로와 최종 선택의 안정성을 검증하지 않는다.
