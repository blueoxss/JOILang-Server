# STATE — GPS-PromptOps 감사·자가수리 (마스터 프롬프트 세션)

- 최종 갱신: 2026-07-13 세션 1 종료 시점
- PHASE 0 산출물: `audit/claim_code_traceability.csv`, `audit/phase0_report.md`,
  `audit/manifest.json`, `audit/assumptions_diff.md`, `audit/sdet_formula.md`
- 판정 분포(감사 시점): IMPLEMENTED 3 / PARTIAL 9 / MISSING 4 / CONTRADICTS_PAPER 8
- 회귀 가드(세션 종료 시): pytest 62 passed + run_eval_pipeline_check smoke2 PASS + run_ga_search_check smoke PASS

## 환경 메모
- conda `sg`: Python 3.9.21, pytest 8.4.2, accelerate 1.10.1(세션 1 설치).
- GPU: RTX A6000 48GB ×2. HF 캐시에 Qwen2.5-Coder-7B/14B, Llama-3.1-8B, gemma-2-9b, Phi-3.5 존재.
- worker 백엔드는 **호출마다 모델을 subprocess 재로드**(~13s/호출) — 논문 예산 실험의 병목.
  persistent local 서버(local 모드 + vLLM/자체 서버) 도입이 실질 해제 조건.
- **저장소의 논문 PDF(gpt_mg/version0_15/_JOK__2026.pdf)는 구버전 초안** — 8항 적합도(식 2)·
  유전자 8튜플(식 1)·데이터 170/50/30. 감사·구현 기준은 마스터 프롬프트의 최종 청사진.
  앵커 수치는 초안 Table 7과 완전 일치(출처 확인됨).
- heredoc + `conda run` 조합은 stdin 미전달 — 스크립트 파일로 실행할 것.
- git worktree `/data/mgjeong/joilang_run_snapshot` (WI-04 머지 커밋 스냅샷) — 백그라운드
  실행용. **실행 종료 후 `git worktree remove`로 정리할 것.**

## 백로그

| WI | 내용 | 우선 | 상태 | 비고 |
|---|---|---|---|---|
| WI-01 | 설정 실측화 manifest + AS diff | P0 | DONE | tools/build_settings_manifest.py 재생성 가능 |
| WI-07 | 적합도 5항 + config 외부화 + 층화 표본기 | P0 | DONE | configs/ga_search_fitness.json |
| WI-05 | 리플레이 15/15 분리 + ReplayFit | P0 | DONE | datasets/replay_split.json, ReplayLeakError |
| WI-06 | 채택 게이트 3조건 하드 게이트 | P0 | DONE | 안전 부분집합은 데이터 부재로 구성 불가(FIX_PAPER) |
| WI-16 | GA 엔진 논문 정합(교차·6연산·예산) | P0 | DONE | O·V·E 렌더 반영은 WI-09 |
| WI-04 | S_DET 문서·3후보 도구·이진vs등급 | P0 | DONE(구현) / DOING(실측) | 실전 비교 백그라운드 실행 중 → 완료 시 `--ingest` |
| WI-02 | 교차 전이 3×3 러너 | P0 | DONE(하네스) / BLOCKED(본실행) | 사유: P_Q7/L8/Q14 승격물 부재(GA 3회 선행) + worker 재로드 비용 |
| WI-03 | 절제 사다리 A0~A4 러너 | P0 | DONE(하네스) / BLOCKED(본실행) | WI-02와 동일 비용 사유. mock E2E 완료 |
| WI-08 | ledger 신설 + sync_ledger_to_tex.py | P0 | DONE | PROJECTED 37 잔존, †해제는 ingest 전용 |
| WI-09 | 유전형 O·V·E 렌더 실배선 + 메타 분리 | P1 | TODO | ga_operators가 유전자 조작·기록까지는 완료 |
| WI-10 | 회귀 스위트(C_crit 고정 목록) | P1 | TODO | gate config의 critical_subsets 재사용 |
| WI-11 | 재현성 팩(seed·argv·config 스냅샷) | P1 | TODO | ga_summary에 fitness/budget 스냅샷은 WI-07/16에서 반영됨; seed·argv 기록 남음 |
| WI-12 | 클라우드 역방향 교차 | P1 | TODO | ledger에 PROJECTED 행 예약됨 |
| WI-13~15 | self-repair E2 / 분산·무작위 대조 / 라우터 | P2 | TODO | - |

## 재개 절차 (새 세션)
1. 이 파일 + `audit/phase0_report.md` 를 읽는다. PHASE 0 재수행 금지.
2. `git log --oneline -5` 로 HEAD 확인 (세션 1 종료 HEAD: WI-08 머지 이후 + 최종화 커밋).
3. 백그라운드 실전 비교(results/search_signal/20260712T180451Z)가 완료돼 있으면:
   `conda run -n sg python tools/sync_ledger_to_tex.py --ingest` 로 ledger 반영 후
   worktree 정리(`git worktree remove /data/mgjeong/joilang_run_snapshot`).
4. 다음 우선 행동 3개:
   ① persistent 로컬 서빙 도입(worker 재로드 병목 해소) → 논문 예산 GA 실행 가능화
   ② 모델 3종(Q7/L8/Q14) GA 본실행 → best_genome 3종 확보 → WI-02/03 본실행 + ingest
   ③ WI-09(유전형 렌더 실배선)·WI-11(재현성 팩) 착수
