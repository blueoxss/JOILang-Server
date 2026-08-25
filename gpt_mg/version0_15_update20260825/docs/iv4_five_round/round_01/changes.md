# R1 changes (2026-08-25)

코드 변경 0건 (R1 허용 범위 = docs only). 원본 `version0_15_update20260413` 및 root/`utils` 무변경 (git status로 확인 — 유일 변경은 기존 사용자 미커밋 `pipeline_common.py`).

## 생성

- `gpt_mg/version0_15_update20260825/` 전체 (rsync 복사, 390파일 SHA 일치; results/artifacts/generated_tables/docs 빈 실디렉터리)
- `docs/iv4_copy_baseline_verification.md`
- `docs/paper_source_of_truth.md`
- `docs/paper_four_way_comparison.md`
- `docs/professor_revision_preservation.md`
- `docs/iv4_metric_provenance_audit.md`
- `docs/iv4_five_round/immutable_research_charter.yaml`
- `docs/iv4_five_round/round_01/{criteria.yaml, initial_evaluation.json, feedback.md, changes.md, manifest.json}`

## 수정

- `docs/iv4_copy_baseline_verification.md`: '69.9 없음' 오류 정정 (취소선 + 정정 사유·행번호·재검증 방법 명기)

## 감사 실행 기록

- 병렬 감사 3종 (papers / code / artifacts), 총 107 tool calls. 산출은 위 docs 4종으로 종합.
- fixture 실행: ROOT·v15 평가기 별도 subprocess 채점 (외부온도 exact + 간결형 2변형) — 0.92643979 ROOT 재현, v15 strict 69.9 cap 실증.
