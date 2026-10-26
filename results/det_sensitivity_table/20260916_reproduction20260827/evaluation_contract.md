# 재채점 평가 계약 (8항 DET)

- 구현: 저장소 루트 `utils/det_evaluator.py` 의 구성 함수(similarity, extract_services, extract_receivers,
  extract_numeric_literals, extract_string_args, coverage_score, precision_score, dataflow_heuristic_score,
  compare_bool, normalize_candidate, parse_json_object). 점수 계산식은 `strict_det_evaluate_row` 와 같다.
- s1: `difflib.SequenceMatcher(None, u_r, u_y).ratio()` (기본 설정, autojunk 기본값, 인자 순서 기준→생성).
  원문 코드 중 하나라도 빈 문자열이면 0. 두 원문이 비어 있지 않고 공백 제거 후 모두 비면 ratio()=1.
- s2: cron, period 각각 `str(value or "")` 에서 공백 제거 후 일치 여부의 평균(None·""·0 → ""). 생성 JSON 의 period
  기본값은 0(원본 normalize_candidate), cron 기본값 "".
- S: `\([^)]*\)\.([A-Za-z_][A-Za-z0-9_]*)` 의 member 목록. T: `\(([^)]*)\)\.` 괄호 내부 공백 제거 목록.
  N: `(?<![A-Za-z_])-?\d+(?:\.\d+)?` 문자열 그대로(23 ≠ 23.0). L: `['"]([^'"]+)['"]` 내부 공백 제거·소문자.
- c(A,B)=Σmin/|A| (A 비면 1), p(A,B)=Σmin/|B| (B 비면: A 비면 1, 아니면 0). 중복 출현 반영(Counter).
- s8: `\b(?:var|let|const)\s+[A-Za-z_][A-Za-z0-9_]*\s*=` 선언 수; 기준 0 → 1, 아니면 min(1, 생성/기준).
- 파싱: 저장 출력에서 첫 JSON 객체 추출 + json.loads(strict=False) (원본 파이프라인 parse_candidate). 실패 시 e=0, v=0.
  파싱 성공 후 code 가 비면 v=0, 나머지 비교값은 유지.
- e = Σ w_k s_k 를 반올림 없이 계산, D = 1[v=1 ∧ e ≥ τ] (epsilon 없음).
- Python: 이 실행의 manifest.json 참조. 가중치 재정규화 없음.
