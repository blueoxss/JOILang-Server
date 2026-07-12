# PHASE 0 감사 보고서 — GPS-PromptOps 논문 ↔ 코드 정합

- 작성: 2026-07-13 (UTC 2026-07-12 세션)
- 대상 저장소: `/home/mgjeong/Desktop/llm/JOILang-Server` (branch `main`, 시작 스냅샷 `4867728b`)
- 감사 방법: 7개 병렬 정독 에이전트(지형 1 + 주장 판정 6) + 핵심 4개 파일(det_evaluator.py, ga_engine.py, rerank.py, dataset_runner.py 일부) 오케스트레이터 직접 정독 교차검증. 총 332개 도구 호출.
- 판정 상세와 근거는 `audit/claim_code_traceability.csv` (24행, 근거 = 파일경로:행번호 + 코드 인용).

## 1. 판정 분포 (C-01~C-24)

| verdict | 건수 | 항목 |
|---|---|---|
| IMPLEMENTED | 3 | C-02(DETPass 이진 평균), C-12(실패→블록 매핑), C-13(advisor 클라우드 위임·국소 패치·opt-in) |
| PARTIAL | 9 | C-01, C-05, C-10, C-11, C-15, C-16, C-22, C-23, C-24 |
| MISSING | 4 | C-09(층화 표본기), C-18(3회 반복 프로토콜), C-20(교차 전이 3×3), C-21(절제 사다리) |
| CONTRADICTS_PAPER | 8 | C-03, C-04, C-06, C-07, C-08, C-14, C-17, C-19 |

### CONTRADICTS_PAPER 목록 (핵심 근거)

| ID | 논문 서술 | 실측 | resolution |
|---|---|---|---|
| C-03 | S_DET = 치명 0, 그 외 1−정규화 구조 편집거리 | 8성분 가중합×100 (code_sim 0.30 + schedule 0.15 + svc_cov 0.15 + svc_prec 0.10 + receiver 0.10 + numeric 0.10 + enum 0.05 + dataflow 0.05), 치명(invalid_json/missing_gt)만 0 — `utils/det_evaluator.py:196-210` | FIX_PAPER (수식 문서화 = WI-04) |
| C-04 | S_DET 임계 0.8 | 전 계열 일관 70.0 (0~100 스케일, =0.70) — `det_evaluator.py:124`, `cli.py:87` | FIX_PAPER |
| C-06 | 유전형 g=(B,O,V,R,E,Θ), 메타데이터 분리 | 정본은 B·R·E·Θ만(O는 고정 순서 강제, V 부재), Θ는 저장만 되고 백엔드 호출에 미전달(실효 없음), advisor_metadata가 유전형 내부에 저장 | FIX_CODE (WI-09) |
| C-07 | 적합도 5항(α·DETPass+β·S_DET+γ·ReplayFit−λt·Tok̂−λl·Lat̂) | `fitness = avg_det + 10·pass_rate + 5·exact_rate − 0.0001·tokens − 0.01·latency` — ReplayFit 부재, 논문에 없는 gt_exact 항, 비용 비정규화 — `rerank.py:61` | FIX_CODE (WI-07) |
| C-08 | 가중치 0.50:0.15:0.20:0.10:0.05 config 외부화 | 해당 가중치 전역 부재, 정본 가중치 하드코딩 | FIX_CODE (WI-07) |
| C-14 | 리플레이 탐색/보류 30/30 분리 | 정본 런타임에 리플레이 개념 자체 부재(grep 0건). 레거시도 replay_fit="" placeholder. **분리 이전에 계산 자체가 없음** | NEW_WI (WI-05, 최우선) |
| C-17 | 벤치마크 180 / 리플레이 60 / 스트레스 40 | `JOICommands-280.csv` = 280행 8범주 (cat1~6 각 30 = 180, cat7 50, cat8 50). 분할 매니페스트 부재. 9범주는 구세대 170.csv에만 존재 | NEW_WI (WI-01에서 분할 설계·실측화) + 9범주 서술은 FIX_PAPER |
| C-19 | vLLM 서빙, max_model_len | vLLM 부재(requirements에도 없음). 실제는 HF transformers subprocess 워커(greedy) + OpenAI 호환 local HTTP 모드. max_model_len 전역 0건, 존재하는 것은 local_max_new_tokens(256/512) | FIX_PAPER (또는 vLLM 서빙 도입 시 FIX_CODE) |

## 2. 모듈 지도 (정본 vs 레거시)

**정본 런타임** — `utils/ga_search/` (README가 canonical 선언, `model_resolver.py`가 레거시 import 차단):
- `cli.py` — 엔트리포인트: render / eval / search / advisor / check
- `dataset_runner.py` — CSV 로드·선택(row_no/category/limit_per_category/sample_size, `random.Random(seed)`), gt 컬럼 필수
- `model_resolver.py` + `render_adapter.py` — 모델 패키지(model_config.json + config_loader.py) 해석·렌더
- `ga_engine.py` — GA 루프. **자칭 skeleton**: 교차 없음(변이 4종만), elite 1, top-3 균등 선택, 게이트 없음 (`ga_engine.py:305-308` known_limitations)
- `candidate_generation.py` + `llm_backends.py`(worker/local/openai) + `local_worker.py`(HF transformers) + `repair_loop.py`
- `evaluation.py` → **`utils/det_evaluator.py`** (strict DET 단일 소스)
- `rerank.py` — 적합도 집계(하드코딩 수식)
- `advisor_evidence/integration/modes.py` + `utils/prompt_advisor/` — 진단→패치(GPT-4.1-mini 위임, opt-in)
- `prompt_patch_apply.py` — 패치→genome 오버레이
- `artifacts.py` — manifest.json(schema `ga_search.foundation.v1`) 등 기록. **seed·argv·config 스냅샷 미기록**
- `model_suite_benchmark.py` — 고정 프롬프트 × N모델 스위트(교차 전이의 절반 재료)
- `local_model_registry.py` — 로컬 모델 5종 키(phi35_mini, qwen25_coder_7b, llama31_8b, gemma2_9b_it, qwen25_coder_14b)

**모델 패키지**: `gpt_mg/version0_13`(모노리스 정본), `version0_15`(블록·genome), `version0_16`(최신 모노리스). `version0_15_update20260413`은 레거시 백업(정본 import 금지) — 단 그 안의 `run_ga_search.py`(4,610행)에 **논문에 가까운 GA 정식 구현**(elite 2, tournament 3, 블록 단위 균등 교차, regression_gate, ga_run_manifest 기록)이 있음. 이식 원천으로 사용.

**데이터**: `datasets/JOICommands-280.csv`(정본 280행 8범주), `service_list_ver2.0.1.json`, `usr_rag/*.csv`(사용자 리플레이 원천 후보), `admin_logs/slack/`(admin 리플레이 1건).

**레거시(감사 참고만)**: gpt_cap/, gemini_mg/, gpt_mg/version0_1~0_14, utils/evaluation*(SoPLang 파서·클라우드 judge), pipeline/, demo.py 등 서비스 코드.

## 3. 데이터 흐름 (정본 `cli search`)

```
datasets/JOICommands-280.csv + service_list_ver2.0.1.json
  → dataset_runner.select_dataset_rows(seed 결정적)
  → model_resolver → render_adapter (모델 패키지 렌더)
  → ga_engine.run_search  [mock → gt copy fixture / 그 외 real skeleton]
      세대 루프:
        prompt_patch_apply.rendered_prompt_with_genome (GA Prompt Patch Overlay)
        → candidate_generation (llm_backends: worker=HF transformers 서브프로세스
                                 / local=OpenAI호환 HTTP / openai=SDK; repair_loop)
        → evaluation → det_evaluator.strict_det_evaluate_row
                        (S_DET=8성분 가중합, det_pass = score≥70 ∧ 치명사유 없음)
        → rerank.aggregate_genome_scores (fitness 하드코딩)
        → elite 1 + top-3 rng.choice 부모 → _mutate_genome(4종)
  → best_genome.json, ga_summary.json, promotion_decisions.*, mutation_events.*
  (선택) advisor_evidence → prompt_advisor(GPT-4.1-mini) → prompt_patches.json
         → apply_prompt_patches(population 12) → --prompt-patches 재주입
```

## 4. 설정값 실측표

| 키 | 실값 | 출처 |
|---|---|---|
| N_benchmark | 280행(8범주: 1~6 각 30, 7~8 각 50). 180/60/40 분할 부재 | `datasets/JOICommands-280.csv` 실측 |
| N_replay | 계산 경로 부재. 원천 후보: `usr_rag/*.csv` 26파일, `admin_logs/slack/` 1건 | 전역 탐색 |
| N_stress | NOT_FOUND (스트레스 셋 부재) | find/grep 0건 |
| GA pop/gen (정본 기본) | 2 / 1 | `cli.py:98-99` |
| GA pop/gen (check full) | 16 / 10 | `run_ga_search_check.sh:113-114` |
| GA pop/gen (레거시 기본) | 20 / 30 | 레거시 `run_ga_search.py:251-252` |
| elite | 정본 1(고정) / 레거시 `--elites` 기본 2 | `ga_engine.py:369` |
| tournament | 정본 없음(top-3 rng.choice) / 레거시 3 | `ga_engine.py:371` |
| p_m | 정본: 비엘리트 100% 변이 / 레거시 mutation-rate 0.2 | `ga_engine.py:372` |
| 적합도(정본) | avg_det + 10·pass + 5·exact − 1e-4·tok − 0.01·lat (하드코딩) | `rerank.py:61` |
| S_DET 성분 | 0.30/0.15/0.15/0.10/0.10/0.10/0.05/0.05 ×100 | `det_evaluator.py:196-205` |
| det_threshold | 70.0 | `det_evaluator.py:124`, `cli.py:87` |
| candidate_k(반복 생성) | 정본 기본 1, 레거시 2. **3회 프로토콜 부재** | `cli.py:84` |
| max_model_len | NOT_FOUND. 유사 개념 local_max_new_tokens=256(워커)/512(레지스트리) | `local_worker.py:239`, `local_model_registry.py:113` |
| seed 정책 | 정본 `--seed` 기본 0, 샘플링·변이 결정적. **결과에 seed/argv/config 미기록** | `cli.py:78`, `dataset_runner.py:64`, `ga_engine.py:294` |
| 서빙 | vLLM 아님 — HF transformers subprocess(greedy) + OpenAI호환 local HTTP | `local_worker.py`, `llm_backends.py:130,208,257` |

## 5. 스모크 테스트 (0-5)

- 명령: `conda run -n sg python -m utils.ga_search.cli eval --model gpt_mg.version0_13 --dataset datasets/JOICommands-280.csv --service-schema datasets/service_list_ver2.0.1.json --llm-mode mock --det-profile strict --det-threshold 70 --sample-size 10 --out-dir results/phase0_smoke/20260712T170819Z`
- 결과: rows=10, det_pass_rate=1.0, avg_det_score=100.0, rc=0 (mock=gt copy이므로 기대값). 행 단위 det_pass/det_score, 프롬프트 스냅샷, raw_responses, manifest 산출 확인.
- 앵커 지표 대응: DETPass↔det_pass_rate, S_DET↔avg_det_score(0-100), tokens↔generation_*_tokens_total, latency↔latency_sec 모두 파이프라인에 존재. **ReplayFit만 파이프라인에 부재.**

## 6. 환경 실측 (7-1, 7-3)

- conda env `sg`: Python 3.9.21, pip 24.3.1, **pytest 미설치**(WI 착수 전 설치)
- 환경변수: OPENAI_API_KEY, JOI_V15_OPENAI_API_KEY, JOI_V15_OPENAI_ENDPOINT, JOI_EVAL_OPENAI_API_KEY, HF_HOME 모두 SET
- 부재 자산(전역 탐색 확정): `projected_results_ledger.csv`, `result_values.tex`(.tex 자체 0건 — WI-08은 ledger·tex 신규 생성부터), STATE.md(본 감사에서 생성), `results/cross_transfer/`, `results/ablation/`, 스트레스 데이터셋

## 7. 백로그 조정 결론 (PHASE 1 입력)

- **C-12, C-13 → VERIFY-ONLY** (advisor 매핑·위임·opt-in 이미 구현)
- **WI-05가 최우선 P0**: 리플레이는 "분리"가 아니라 "계산 자체"부터 구현 필요 (C-05, C-14)
- **신규 WI-16 추가**: 정본 GA 엔진 논문 정합(elite 2·tournament 3·p_m·블록 교차 6연산 — 레거시 `version0_15_update20260413/scripts/{ga_selection,ga_mutation}.py`에서 이식) — WI-02/03이 이것에 의존
- **WI-04에 C-01 반영**: 정책·안전 검사는 실행 가능한 형태로 부재(det_paper.py forbidden_actions는 데이터 파일 부재로 항상 비활성) — 논문 목록 수정 필요를 sdet_formula.md에 포함
- **WI-08**: ledger/tex가 저장소에 없으므로 "동기화"가 아니라 ledger 스키마 신설 + sync 스크립트 신규 작성으로 재정의
- 교차 전이(WI-02)·절제(WI-03)·이진vs등급(WI-04c)의 **실행**은 GPU/로컬 모델 가용성에 종속 — 7-6 프로브 후 BLOCKED(GPU/모델) 여부 결정
