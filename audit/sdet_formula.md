# S_DET 채점기 실수식 문서 (WI-04a, 감사 C-03/C-04 근거)

- 채점기 단일 소스: `utils/det_evaluator.py` (`strict_det_evaluate_row`)
- 이 문서는 코드에서 그대로 옮긴 실수식이다. 논문 정의와의 차이는 §3.

## 1. 실수식

`det_score`(=S_DET, 0~100 스케일)는 **8성분 가중합**이다 ([utils/det_evaluator.py:196-205](../utils/det_evaluator.py)):

```python
det_score = 100.0 * (
    0.30 * code_sim            # gt 코드와의 difflib SequenceMatcher 유사도 (공백 제거 후)
    + 0.15 * schedule_score    # cron·period 일치 (둘 다=1.0, 하나=0.5, 없음=0.0)
    + 0.15 * service_coverage  # gt 서비스 호출의 재현율 (멀티셋)
    + 0.10 * service_precision # 생성 서비스 호출의 정밀도 (멀티셋)
    + 0.10 * receiver_coverage # gt 리시버 태그 재현율
    + 0.10 * numeric_grounding # gt 숫자 리터럴 재현율
    + 0.05 * enum_grounding    # gt 문자열 인자 재현율
    + 0.05 * dataflow_score    # 변수 할당 개수 휴리스틱
)
```

치명 실패 시 0점 처리 ([utils/det_evaluator.py:206-207](../utils/det_evaluator.py)):

```python
if "invalid_json" in failure_reasons or "missing_official_gt" in failure_reasons:
    det_score = 0.0
```

DETPass 판정 ([utils/det_evaluator.py:208-210](../utils/det_evaluator.py)):

```python
det_pass = det_score >= float(det_threshold) and not any(
    reason in failure_reasons for reason in {"invalid_json", "missing_official_gt", "missing_generated_code"})
```

- 임계값 실측: **70.0** (0~100 스케일, = 0.70) — `det_evaluator.py:124`, `cli.py:87`,
  체크 스크립트 `--det-threshold 70`. 저장소 어디에도 0.8 임계는 없다.
- DETPass는 명령 단위 이진 판정의 평균으로 집계된다(`evaluation.py` det_pass_rate) — C-02는 논문과 일치.

## 2. 실측 예시

### 실주행 예시 (Qwen2.5-Coder-7B worker, row 1, results/phase1_worker_probe/20260712T172618Z)
- 생성: `(#Dishwasher).dishwasherMode_setDishwasherMode("dry")` → det_score **65.15**, det_pass=False
  (임계 70 미달 — 구조는 유사하나 인자/스케줄 축 감점)
- 동일 명령 3후보 S_DET 실값 비교는 `tools/extract_sdet_examples.py` 실행으로 재현:
  `conda run -n sg python tools/extract_sdet_examples.py --row-no 1` → `audit/sdet_examples.json`

## 3. 논문 정의와의 차이 (FIX_PAPER 지시)

| 축 | 논문(최종 청사진) 서술 | 코드 실측 |
|---|---|---|
| S_DET 본체 | 치명=0, 그 외 1−정규화 **구조 편집 거리** | 8성분 **가중합**. 편집거리류(code_sim)는 30% 성분일 뿐 |
| 값域 | [0,1] | 0~100 (보고 시 /100 환산 필요) |
| 치명 조건 | 파싱 불가 / **안전 위반** | invalid_json / missing_official_gt — **안전 위반 축 부재** |
| 임계 | 0.8 (수동 보정) | 70.0 (=0.70) |

**논문 수정 지시(FIX_PAPER)**: 방법론 S_DET 정의 문단을 다음으로 교체할 것 —
"S_DET는 치명 실패(JSON 파싱 불가, 공식 GT 부재) 시 0, 그 외에는 코드 유사도(0.30),
스케줄 일치(0.15), 서비스 커버리지(0.15)/정밀도(0.10), 리시버 커버리지(0.10),
숫자(0.10)·열거형(0.05) 근거 일치, 데이터플로 휴리스틱(0.05)의 가중합으로 정의되는
[0,1] 등급 점수다(수동 보정 임계 0.70)." 또한 '안전 위반 시 0' 서술은 안전 검사가
구현될 때까지 제거하거나 '설계상 지원'으로 완화할 것(감사 C-01 참조).

## 4. 이진 vs 등급 적합도 모드 (WI-04c)
- `--fitness-mode graded`(기본): 5항 적합도 그대로 (β·S_DET 포함)
- `--fitness-mode binary`: β항을 0으로 두고 DETPass 신호만 사용 (`utils/ga_search/fitness.py`)
- 비교 러너: `tools/run_binary_vs_graded.py` → `results/search_signal/<ts>/binary_vs_graded.csv`
