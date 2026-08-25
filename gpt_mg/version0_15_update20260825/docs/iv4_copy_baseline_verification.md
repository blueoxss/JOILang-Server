# iv4_copy_baseline_verification.md (R1, 2026-08-25)

## 복사
- 원본: gpt_mg/version0_15_update20260413 (읽기 전용; git상 사용자 미커밋 수정 `utils/pipeline_common.py` +17줄 포함 상태 그대로 복사됨)
- 신규: gpt_mg/version0_15_update20260825 (canonical)
- 제외: __pycache__/.pytest_cache/*.pyc, `logs`·`results`(**/data로의 심볼릭 링크** — legacy artifact 혼입 방지 위해 미복제, 신규는 빈 실디렉터리 생성), worker_crash_debug_4.log
- 심볼릭/하드링크 미사용 (rsync 일반 복사)

## 검증 결과
1. 소스·설정 인벤토리: src=390, dst=390, only_src=0, only_dst=0 — 동일 ✓
2. SHA-256: 전 파일 일치 (sha_diff=0) ✓ (상세: docs/_copy_inventory.json)
3. golden fixture(외부온도 exact 케이스)를 **별도 subprocess**로 두 버전 실행:
   - 두 버전 모두 profiles={legacy,strict}, det_score=100.0, det_gt_exact=true — 동일 ✓
   - import된 모듈 __file__이 각자 자기 버전 경로임을 확인 ✓ (module cache 오염 없음)
4. 원본 무변경: `git status -- version0_15_update20260413` = 복사 전과 동일(M pipeline_common.py 1건뿐) ✓

## 발견 사항 (R1 감사로 이관)
- v15 평가기는 이미 profile 기반(`PROFILE_WEIGHTS={legacy,strict}`), exact-override 경로 실존(§6.2 확인)
- ~~`69.9` cap은 v15 det_evaluator.py에 문자열 없음~~ → **정정(2026-08-25, R1 감사)**: `69.9` cap은 v15 det_evaluator.py **1547/1549/1551/1553/1555행에 실존** (strict profile 5개 조건에서 `score = min(score, 69.9)`; 두 버전 diff-동일, 직접 grep 재확인). 최초 기록은 잘못된 grep 결과였음 — G5 위반 방지 위해 즉시 정정.
- 루트 `utils/det_evaluator.py`(252줄) = 8항 w0=(0.30,0.15,0.15,0.10,0.10,0.10,0.05,0.05) **정확 일치**(§6.1 확인)
- `utils/det_paper.py`(478줄) 실존 — paper 평가기 후보, 감사 필요
