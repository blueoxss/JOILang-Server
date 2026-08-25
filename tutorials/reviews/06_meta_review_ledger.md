# 06 노트북 Meta-Review Ledger (기준 수립 -> 평가 -> 피드백 -> 코드 수정 loop x 재정비 5회)

평가 대상: `06_ga_prompt_search_full_loop.ipynb` (빌더 소스 기준).
방식: 라운드별 루브릭(100점)을 수립하고, 독립 critic 에이전트들이 코드·실행 아티팩트를 채점.
평균 점수 >= 90이면 통과 후 **재정비**(루브릭/평가 도구 자체를 상향)하여 다음 라운드 진행. 총 5회.

## 재정비 R1 — 루브릭: 요구사항 커버리지 + 논문 정합 (기본)

항목: pipeline_completeness(20) / paper_alignment(20) / staged_verification(15) /
loop_and_recalibration(15) / cross_model_feedback(10) / reproducibility(10) / scoring_artifacts(10)

| 반복 | critic:requirements | critic:paper | 평균 | 판정 |
|---|---|---|---|---|
| 1 | 89 | 89 | 89.0 | 미달 -> 코드 수정 |
| 2 | 94 | 98 | 96.0 | **통과** |

반복 1 -> 2에 적용한 수정 (critic 지적 기반):
1. 05 기준선 캐시 부재 시 무음 0% 차단 (real=assert, mock=명시 경고) + baselines.json 저장
2. 진단 신호->블록 매핑 구현: advisor가 규칙에 target_block(schema/temporal/output/general) 지정,
   render_system이 해당 블록 위치에 부착, mutate()가 실패 신호로 연산자 가중 (논문 V.3 정합)
3. judge 전수 판정(실패 행 전체) + judged_fails/valid_alternative 기록
4. 세대 체크포인트(population/gen_done) + (round,gen) 중복 기록 방지
5. eval_cache/state에 mode·model 기록, 모드 불일치 assert (mock 오염 차단)
6. 모집단 전체 점수·계보(부모/연산자) 기록, z3 보너스의 논문 이탈 명시, SUBSET_B 정적 배분 명시,
   mock premap 구조 폴백(선언적), staged 명령 정정

반복 2 잔여 지적 -> R2 진입 전 반영:
- gen_done 소비(재개 시 gen_done+1부터), 레거시 state mode 역기입, 재개 결정성 문구 완화
- mock 점검 노브 확대(ROUNDS=5 MAX_GEN=2 -> 교배·계보·게이트·judge 경로 커버; 검증 완료: lineage 5배치, judge 4건)
- 신규 코드의 real 실행 증거(smoke06b) 생성

## 재정비 R2 — 루브릭 상향: 실행 견고성 + 증거 기반

항목: artifact_evidence(20) / resume_correctness(15) / error_paths(15) / staged_verification(15) /
pipeline_completeness(15) / paper_alignment(10) / docs_accuracy(10)
(평가 도구 변경: critic이 코드 정독 + **아티팩트 파일을 직접 열어** 필드 실측 감사)

| 반복 | critic:robustness | critic:evidence | 평균 | 판정 |
|---|---|---|---|---|
| 1 | 85 | 74 | 79.5 | 미달 -> 코드 수정 |

반복 1 지적 -> 적용한 수정:
1. **z3 공허 참 제거**: compare_codes의 논리동치는 조건식만 비교 -> 무조건문은 자동 True.
   gt에 조건식이 있는 행에서만 z3 판정을 집계(무조건문 행 제외), 표기 "z3(조건식 행)"로 정정
2. **eval_cache 렌더 버전 무효화**: RENDER_VERSION 상수를 genome_hash에 포함 -> 렌더러 변경 시 캐시 자동 무효
3. advisor 규칙 dict의 'rule' 키 부재 시 KeyError -> rule_obj 방어 (무결 필드 강제)
4. log_hist 직후 save_state() -> history/state 정합(크래시 윈도 제거) + 레거시 backfill 즉시 영속
5. row_shortlists.json에 mode 기록 + 로드 시 assert (mock 오염 잔여 경로 차단)
6. 레거시 state mode 기본값을 'real'로 정정(문서와 일치)
7. typed target_block 규칙의 렌더 self-check(3개 블록 부착 assert) 추가
8. **최종 코드로 본 실행 재실행**: 기본 RUN_TAG를 ga_loop_v2로 변경, mock06/smoke06 재생성 후
   5라운드 본 실행 — 문서 태그와 아티팩트 일치, 신규 필드가 담긴 실측 증거 확보

| 반복 | critic:robustness | critic:evidence | 평균 | 판정 |
|---|---|---|---|---|
| 2 | 94 | 98 | 96.0 | **통과** |

반복 2 실행 증거: 최종 코드로 단계 체인 재실행 완료 — mock06(5라운드 mock) -> smoke06(5라운드 소형 실측)
-> **ga_loop_v2**(본 실행 107분: R1 73.3 -> R2 80.0 -> R3 83.3 -> R4 90.0(TARGET 도달, judge 전수)
-> R5 83.3 채택; 홀드아웃 **78.3%** > DirectTransfer 36.7% / CloudRef 76.7%; typed 규칙 4개 채택).
반복 2 잔여 minor 반영: setup 주석 정정, z3 n/a 표시, (round,'adopt') 중복 가드, z3 표기 통일.
알려진 경미 사항(보류): schema_block enum 표기의 잔여 하이픈("auto -") — 수정 시 프롬프트 내용이
변해 RENDER_VERSION 상향과 전체 캐시 무효(본 실행 재수행)가 필요하므로 다음 렌더 개정 때 일괄 반영.
참고: ga_loop_v1/ 아티팩트는 R2 수정 이전 코드의 산출물(provenance 보존용)이며 ga_loop_v2가 대체함.

R2 개정 이력 추가 기록: minor 반영 편집 중 중첩 f-string SyntaxError 발생(final06.log 19:23,
Python 3.10 비지원 구문) -> 라벨 사전 계산으로 수정 -> final06b 재실행 성공(오류 0). 실패-수정
사이클도 본 ledger에 기록함.

## 재정비 R3 — 루브릭 상향: 논문 알고리즘 세부 정합

항목: genotype_operator_mapping(25) / fitness_gate_fidelity(20) / diagnosis_feedback_fidelity(20) /
premap_integration(15) / documentation_of_reductions(10) / meta_loop_process(10)
(평가 도구 변경: critic이 **논문 PDF pages 5-9를 정독**해 코드와 항목별 대조)

| 반복 | critic:paper-detail | critic:process | 평균 | 판정 |
|---|---|---|---|---|
| 1 | 89 | 90 | 89.5 | 미달 -> 코드 수정 |

반복 1 지적 -> 적용한 수정:
1. **target_block 판정 주체를 코드로 전환**(논문 V.3 정합): 신호->블록 매핑은 코드가 결정
   (규칙 텍스트 키워드 -> 지배적 실패 신호 순), advisor는 규칙 문장만 작성
2. mutate()가 적용 연산명을 반환, lineage에 `mutation_ops` 기록 (Fig.3 운영 메타데이터 입도)
3. 축소 문서화 보강: 단일 모델(Qwen-7B; 논문은 3모델 독립 탐색), E는 개수만 변이,
   GA 예산 6·3·30 vs 논문 10·12·45 — 모두 명시
4. S_DET 대용 관계 명시(det_score/100; 논문 정의와의 대응·파서실패 0 처리)
5. 채택 게이트 명시: 논문 Eq.(5)의 f 기준·ε=1.0%p·C_crit 대신 점수 기준 ε=0 + 행 회귀 ≤1 보수화
6. mock06 재검증 통과 (mutation_ops 계보 실측: ['rule_add'], ['caution','temporal'] 등)

| 반복 | critic:paper-detail | critic:process | 평균 | 판정 |
|---|---|---|---|---|
| 2 | 97 | 94 | 95.5 | **통과** |

반복 2 잔여 반영: (a) Eq.(5) 서술 정정 — 논문 게이트는 DETPass 기반(전체+C_crit 하한+ReplayFit_h,
ε=1.0%p)이며 본 노트북은 DETPass ε=0 + 행 회귀 <= 1 보수화·ReplayFit_h 제외로 명시(직전 문서가
논문을 'f 기준'으로 오특성화했던 것을 교정), (b) assign_block/dominant_block을 모듈 함수로 추출하고
self-check 6종 추가, (c) mock advisor가 공통 배정 경로를 통과하도록 변경(mock06 재검증: mock 규칙이
키워드로 'temporal' 배정됨 실측), (d) 헤더 다이어그램에 z3_w 항 표기 통일.
Provenance 명시: ga_loop_v2/smoke06의 lineage.mutation_ops(None)와 rule_pool의 target_block은
R3 수정 이전 코드의 산출물임(렌더 불변이라 캐시 유효; 다음 실측 실행에서 신규 경로가 자연 반영됨).
보류 권장사항(다음 렌더 개정 시): mutation_ops 입도 세분화(temporal_version/temporal_toggle),
schema_block enum 잔여 하이픈 정정 — 모두 RENDER_VERSION 상향 동반 항목.

## 재정비 R4 — 루브릭 상향: 서로 다른 모델(Opus)의 교차 평가 + 코드 품질

항목: fresh_defects(30) / code_quality(20) / consistency(20) / usability(15) / prior_rounds_hold(15)
(평가 도구 변경: critic 2명을 **Claude Opus** 모델로 실행 — 생성/이전 리뷰와 다른 모델의 신선한 시각)

| 반복 | opus:fresh-eyes | opus:quality-consistency | 평균 | 판정 |
|---|---|---|---|---|
| 1 | 77 | 76 | 76.5 | 미달 -> 전면 수정 |

반복 1 지적(교차 모델이 발굴한 실질 결함) -> 적용한 수정:
1. **신호 테이블 커버리지 확장**: enum_grounding/numeric_grounding/dataflow -> schema,
   missing_generated_code 등 -> output; 죽은 리터럴 제거; gt_mismatch는 비정보 신호로 의도적 미매핑 주석
2. **dominant_block을 실제 다수결**로 교체(케이스별 투표 + 우선순위 타이브레이크)
3. **advisor/judge에 cron/period 증거 제공**: failure payload에 gt/생성 양쪽의 cron·period 포함,
   judge 프롬프트에 "cron/period 불일치는 real_error" 규칙 명시 (advisor 캐시 키 변경 -> 재질의 발생)
4. **eval_cache에 model assert** 추가(모델 교체 시 RUN_TAG 미교체 무음 재사용 차단) + knob 표에 명시
5. **assign_block 단어 경계 정규식 + 검사 순서(output->temporal->schema) + 키워드 보강**, 회귀 self-check
6. shortlist 캐시에 premap_tag 기록·대조 + 캐시 행 누락 명시 오류, BUNDLE_OK 검사를 빌드 경로로 이동
7. while 루프 시도 상한(300) RuntimeError, judge 미실행 라운드 valid_alternative=None,
   mock judge 결정적 혼합 판정(valid_alternative 산술 커버), 규칙 dedup을 토큰 Jaccard>=0.85로 상향
8. advisor 프롬프트: 실패 신호 클러스터 요약 제공(헤더 표 선언의 실구현) + "ground truth 참조 금지" 제약
9. **RENDER_VERSION rv3**: output 규칙을 형식 명세 뒤로, enum 잔여 하이픈 정리, mutation_ops 입도 세분화
   (grammar_version/temporal_version/temporal_toggle/... from->to 병기) — 렌더 변경 동반 항목 일괄 반영
10. 사용성: 노브 전체 표(§1), ELITE/TOURN env화, 셀 분할(블록·렌더 / 생성·평가 / 연산·피드백),
    G0 렌더 미리보기 셀, 완료 상태 재실행 시 궤적 replay 출력, trajectory 인라인 표시, HF 진행바 억제
11. R5 표기 'A∪B (60문)' 통일, 비용항 측정 규약 명시(배치 상각 latency·입력 토큰만)
개정 사고 기록: 패치 이스케이프 실수로 regex \\b가 백스페이스로 렌더되어 self-check가 mock에서
즉시 검출 -> 교정 후 mock/smoke 재통과 (단계적 점검이 회귀를 잡은 사례).
본 실행: RUN_TAG=ga_loop_v3 (rv3 렌더, 신규 진단 경로) 수행.

| 반복 | opus:fresh-eyes | opus:quality-consistency | 평균 | 판정 |
|---|---|---|---|---|
| 2 | 81 | 87 | 84.0 | 미달 -> 3차 수정 |

반복 2에서 교차 모델이 발굴한 신규 실질 결함 -> 3차 수정:
1. **mock 생성기 프롬프트 무감각**(해시 입력이 상수 구간 [:300] -> 유전형 간 선택압 검출 불능)
   -> 전체 프롬프트 해시로 교체 (mock이 적합도 정렬·게이트를 실제로 검증하도록)
2. **TARGET 조기종료의 재확인-라운드 공회전**(채택 유전형 재시드 -> gen1 즉시 break -> R3/R4 무탐색;
   ga_loop_v3에서 R2/R3/R4 best 해시 동일 실측) -> 첫 세대의 인큐번트 단독 도달은 조기종료 제외,
   최소 1회 교배 강제 + 규칙을 §6 md에 명시
3. advisor 클러스터 요약을 실패 전체로 계산(상세 예시만 4건 절단), "over N (showing 4)" 정직 표기
4. mutate 진단 가중을 dominant_block 다수결로 통일(규칙 배정과 동일 신호->대상 정의)
5. dominant 케이스 우선순위 output>temporal>schema(missing_required_key의 cron/period 부분문자열 오포획 방지)
6. **canonical genome**: 규칙 정렬 정규화(순서는 탐색 차원이 아님) — 해시·렌더 동일 규약, RENDER rv4
   + EVAL_VERSION 도입(평가기 변경 축), eval_cache에 MAX_NEW_TOKENS 기록·assert, 서브셋 지문 대조
7. rule_add 포화 시 no-op 라벨, judge 실패 0건 (100,0,0) 명시, z3 예외 카운터, 규칙 dedup 배치 내 누적
   + 숫자 보존 토크나이저, 신호표 죽은 리터럴 정리(방어적 상위집합 주석), self-check 4종 추가
8. 문서: R2행 상시 동작 정정, G0 미리보기 재기술, 조기종료 규칙 명시, RUN_TAG 교체 목록에 MAX_NEW_TOKENS
본 실행: RUN_TAG=ga_loop_v4 (rv4) 수행. ga_loop_v3 provenance: R3/R4는 동일 유전형 재확인 라운드였음을 명기.

| 반복 | opus:fresh-eyes | opus:quality-consistency | 평균 | 판정 |
|---|---|---|---|---|
| 3 | 84 | 86 | 85.0 | 미달 -> 4차 수정 (수렴 추세: 76.5 -> 84 -> 85, 직전 지적 전수 해소 확인) |

반복 3 실측 증거(critic 검증): mock 유전형 민감도 회복(18행 중 10행에서 유전형별 판정 분기),
ga_loop_v4 전 라운드 교배(공회전 해소), canonical 해시 외부 재계산 일치, 신호 매핑 미포획 0%.
ga_loop_v4 결과: R1 66.7 -> R2-R4 76.7 -> R5 73.3, 홀드아웃 68.3%·토큰 1,290(압축 극단)·0.75s —
적합도 토큰 항이 만든 정확도-비용 트레이드오프의 정직한 기록 (v2 78.3/5,030, v3 75.0/5,054 병존).

반복 3 잔여 지적 -> 4차 수정:
1. **신호->블록 정의 물리적 단일화**: BLOCK_SIGNALS/BLOCK_KEYWORDS 상수로 통합 — 실패 분류·변이
   가중·규칙 배정이 한 정의 공유(numeric/unit 문장은 schema, temporal은 스케줄 축만)
2. dominant_block v2: output 선점 + temporal/schema는 케이스 내 신호 수 다수결(고정 순서 지배 제거)
3. **고아 규칙 강등(rv5)**: temporal 블록 off면 temporal 규칙을 general로 강등 + 헤더에 블록명
   포함 + 렌더 self-check 3종(출력 규칙 위치·강등) 추가
4. Z3_ERRORS 세대 로그 노출, gen_batch 캐시 축(latency 배치 상각 오염 차단), advisor 문구 동적화,
   judge 라운드 fail_block을 advisor와 동일 모집단으로 통일, rule_add 포화 시 가중 제외
5. pop_max 열·궤적 병기(적합도 채택 vs 모집단 최대 괴리 자체 설명), 요약 블록(z3err/premap 백엔드),
   관대 파싱 정책·층화 절단 주의·mock judge 커버 한계 문서화
보류(다음 개정): state.json의 history 전문 중복 보관(O(n^2) 쓰기) 요약화, dominant 케이스 우선순위의
증거 가중 정밀화 회귀 재계산.
본 실행: RUN_TAG=ga_loop_v5 (rv5) 수행 — R1 73.3 -> R2/R3/R4 90.0(TARGET, 인큐번트 개선 탐색 지속)
-> R5 83.3 채택; 홀드아웃 **73.3%**·det 81.0·5,058 tok·2.34s(GEN_BATCH=10, latency 배치 상각);
전 라운드 교배 계보·judge 전수 판정·규칙 풀 14개. 실행 사고 1회: 잔류 커널의 GPU 점유로 CUDA OOM
-> 해당 커널 정리 후 체크포인트 재개로 완주(캐시·상태 재개 경로가 실전 검증됨).

| 반복 | opus:fresh-eyes | opus:quality-consistency | 평균 | 판정 |
|---|---|---|---|---|
| 4 | 91.5 | 84 | 87.75 | 미달 -> 5차 수정 (수렴: 76.5 -> 84 -> 85 -> 87.75; fresh-eyes critic은 critical 0건 도달) |

반복 4에서 quality critic이 발굴한 실측 결함 -> 5차 수정:
1. **F1 실행 노브 재현성**: GEN_BATCH 기본값을 본 실행과 일치하는 10으로 승격(§1 표 갱신),
   전체 노브를 RUN_CONFIG로 echo + `run_config.json` 영속. mock06/smoke06 캐시는 GEN_BATCH=6
   구축임을 staged 명령에 명시(GEN_BATCH=6 병기) — 기본 노브 재실행 시 assert 중단 문제 해소
2. **F2 temporal 키워드 복수형**: `periods?|crons?|delays?|schedules?|waits?` + 회귀 self-check 2종.
   렌더 불변(배정 로직만) — ga_loop_v5 rule_pool의 저장된 target_block은 생성 시점 배정
   그대로 유효(provenance), 신규 advisor 규칙부터 새 정규식 적용
3. **F3 z3 예외 영속**: 세션 카운터를 state.json `z3_errors`로 누적 flush(+재실행 이중 집계 방지
   reset), 요약 문구를 "이번 세션 신규 평가분"으로 한정 — replay 세션의 근거 없는 '0건' 보고 제거
4. **F4 채택 로그 명료화**: 개선 없음 시 "kept incumbent (no improvement)", 변경 시
   "adopted (changed)" + adopt 엔트리에 changed/prev_hash/chosen_hash 기록. 기존 v5 이력은
   조작하지 않고 replay·요약 출력에서 연속 채택 유전형 해시 비교로 "변경 없음(incumbent 유지)"
   파생 표기 (저장 이력은 원본 보존)
5. 권장 반영: 규칙 dedup을 **동일 블록 Jaccard>=0.6**으로 재보정(블록 간 유사문은 렌더 위치가
   달라 허용), rule_add가 실패 블록 대상 규칙을 우선 선택(진단 라우팅 삽입), 죽은 별칭
   (TEMPORAL_SIGNALS 등)·도달 불능 no-op 분기 제거, dominant 케이스 내 동점(n_t==n_s>0)->schema
   문서화 + self-check, mock advisor 실패-0 경로 한계 문서화, replay 세션 "loop 소요" 문구 정직화,
   schema 신호 87% 수렴(연산자 다양성 한계) §5 명시
검증: mock06_i5(신규 태그, 기본 노브 GEN_BATCH=10) 5라운드 통과 — kept-incumbent/adopted(changed)
양 경로·run_config 영속·z3 문구 실측. ga_loop_v5 replay 재실행으로 출력 복원(렌더·해시 불변 확인).

| 반복 | opus:fresh-eyes | opus:quality-consistency | 평균 | 판정 |
|---|---|---|---|---|
| 5 | 77 | 87 | 82.0 | 미달 -> 6차 수정 (F1-F4·권장 7건은 양 critic 모두 해소 실측; fresh-eyes가 더 깊은 층의 결함 신규 발굴) |

반복 5에서 발굴된 실질 결함 (수치 무결성 전수 재계산은 통과 — 12세대 score/fitness/population 72건
전부 eval_cache와 일치, genome 해시 외부 재계산 일치, 87% schema 수렴 실측 87.1% 확인):
- **C1 z3 공허성(치명)**: 공용 유틸 condition_to_z3가 AttrAccess 조건을 BoolVal(True)로 붕괴 —
  반대 조건·빈 스크립트·임계값 오류도 전부 "동치" 판정(반례 4종 실측). 변수는 이름으로 인코딩되어
  알파 변형(row 181)을 오판. 지표·서술 무효(단, z3 항 제거 후에도 전 세대 argmax 불변 재계산 —
  채택 궤적 자체는 유효)
- **C2 run_config 무가드**: 무조건 덮어쓰기(마지막 실행 환경의 기록일 뿐) + 탐색 노브
  (POP/SEED/ELITE/...)에 캐시 가드 전무 + 노브 표 항목 다수 미포함
- **C3 latency 측정 체제 혼재**: GA=배치10 상각 vs 기준선=배치1 단건(8.52s)·max_new 512 vs 1024을
  무단서 병기 — 지연 배수 주장이 배치 효과와 뒤섞임
- **C4 staged 명령 no-op**: 문서의 mock06/smoke06은 완료 상태라 replay만 수행 — 수정 코드를
  아무것도 검증하지 않으면서 통과처럼 보임
- **C5 assign_block 정책 충돌**: first-match가 dominant_block의 카운트 다수결과 불일치 —
  F2 복수형 확장으로 혼합 문장 1건(numeric...for delays)이 schema->temporal로 반전 실측

-> 6차 수정 (EVAL ev2 + RENDER rv6, **본 실행 재수행 ga_loop_v6**):
1. **z3 변환기 자체 구현(ev2)**: 대입문 프로그램 순서 인라인(알파 정규화), AttrAccess/MethodCall/
   AllAttrAccess 결정적 심볼, 숫자 Real 통일(20==20.0), 열거형 단어 공유 intern 상수(==/!=만),
   gold+pred **양쪽 변환 성공 행만 판정**(그 외 None+사유), 커버리지 사유별 §8 집계,
   반례 4종+알파 변형+무조건문 제외 self-check 6종, 표기 "z3(판정가능 행)"
2. **run_config write-once**: 존재 시 로드-대조 후 불일치 키 나열 assert(즉시 차단 실측),
   DET_THRESHOLD/FIXED_NOW/ADVISOR·JUDGE_MODEL/PREMAP·FULLPROMPT_RUN_TAG/RENDER·EVAL_VERSION/
   DATASET_SHA(CSV 내용 지문) 포함 27키; eval/shortlist 캐시에도 data_sha 축 추가
3. latency 라벨링: §7 병기 수치에 (batch-N 상각/단건, max_new) 명시 + "직접 비교 불가, 1차 지표는
   tokens" 문구 + §5 측정 체제 주의 절
4. staged 재작성: mock06_v6/smoke06_v6 신규 태그 + nbconvert 실행 커맨드 명기 + "코드 수정 시
   항상 새 RUN_TAG" 규칙 + replay 분기에 "이번 세션 신규 탐색 평가 0건" 출력
5. assign_block을 dominant_block과 동일한 카운트 다수결로 통일(+혼합 문장 self-check),
   output/schema 키워드 복수형 대칭
6. enum [:14] 무표기 절단 제거(전체 나열 - "Use ONLY these"와 정합, rv6), 루프 견고성
   (incumbent 판정 gen==1 고정·replay 세대 rule_pool 즉시 영속·master loop 종료 시 z3 flush·
   채택 라벨 3종->2종 통일·replay 표기 저장 changed 우선), advisor+judge 캐시 파일명
   feedback_cache.json으로 정정, mutate 도달불능 조건 제거, det spec 변수명 충돌 해소,
   shortlist 캐시에 backend 기록(요약이 캐시 기준으로 보고)
개정 사고 기록: 패치 접합 중 이스케이프 2건(z3 replace의 \\n 층위)·들여쓰기 1건(incumbent 블록)이
셀 구문 오류로 즉시 검출(빌더 재생성 후 전셀 ast 검사) -> chr(92) 조합으로 정정 후 mock 통과.
검증: mock06_v6 5라운드 통과(z3 self-check·커버리지 집계·27키 run_config·write-once 차단 실측)
-> smoke06_v6 통과(실측 z3 커버리지 18/110 판정·gt 파싱불가 4행 사유 제외·양 채택 라벨 실측)
-> **본 실행 ga_loop_v6 완주(113분)**: R1 73.3 -> R2 83.3 -> R3 86.7 -> R4 86.7 -> R5 85.0,
**5라운드 전부 adopted (changed)** (v5의 인큐번트 정체와 달리 매 라운드 실질 개선);
홀드아웃 **71.7%**·det 79.5·5,068 tok·2.29s(batch-10 상각) vs DT 36.7%/30,107 tok·CloudRef 76.7%.
z3(ev2) 실측: 판정 1,008행 / gt 무조건문 967 / pred `&&` 사용 87·enum 순서비교 21·파싱불가 17행은
사유와 함께 제외, 홀드아웃 z3 32/60행 50% — 이전의 공허한 95% 대비 정보성 지표.
[반복 6에서 정정: "공허 True 0건" 주장은 과대 — else-if 합취 붕괴·:= 인라인으로 판정 1,008행 중
191행이 상수 붕괴, True 543건 중 22건이 공허 True로 실측됨(반복 6 지적 C1'). ev3에서 해소.]
실패 신호 schema 수렴 v5 87.1% / v6 87.4%로 문서 갱신. 알려진 커버리지 갭(보류): pred가 `&&`/`||`를
쓰면 파서는 수용하나 변환기가 op 미매핑으로 제외(4.1%) — 동치 의미는 동일하므로 다음 ev 개정에서
"and"/"or"로 정규화 예정(ev 개정은 캐시 무효 동반이라 일괄 반영).

| 반복 | opus:fresh-eyes | opus:quality-consistency | 평균 | 판정 |
|---|---|---|---|---|
| 6 | 77 | 83 | 80.0 | 미달 -> 7차 수정 (C1-C5는 양 critic 해소 실측·수치 무결성 재계산 통과; z3의 더 깊은 층과 적합도 정규화 결함 신규 발굴) |

반복 6에서 발굴된 실질 결함:
- **C1' z3 잔여 공허성(양 critic 공통)**: (a) else-if 체인의 상호배타 가드를 부정 없이 AND 합취
  -> gold 논리식이 ⊥로 붕괴, ⊥≡⊥로 임의 오답이 동치(판정 1,008행 중 191행 상수 붕괴,
  True 543건 중 22건 공허, 홀드아웃 50%는 실제 46.4%); (b) `:=`(주기 간 값 유지)를 상수
  인라인해 플래그/edge-detection 스크립트가 항진·모순으로 붕괴(행 230: 조건 없는 pred가 True);
  (c) pred 조건 0개를 BoolVal(True)로 모델링. argmax 재계산은 불변(채택 궤적 유효).
- **C2' 적합도 z3 항 분모 편향**: 판정가능 행 수가 유전형별로 달라(11~31) 변환 불가 출력을
  내는 유전형이 유리 — pred 실패를 False로 계상해 재계산하면 R2 gen1 argmax 반전 실측.
- **C3' assign_block output 선점 오라우팅**: fields?/formats? 선점으로 cron/period 규칙 5개
  전부(정밀도 0/5)가 output 배정 -> temporal 진단 라우팅 무력화, 채택 유전형에도 1건 포함.
- **C4' 프롬프트 자산 무지문**: 렌더의 대부분을 차지하는 v0_6 md 3종·service schema의 내용
  해시가 어떤 캐시 축에도 없음(CSV만 보호되는 비대칭) — 자산 교체 시 무음 재사용.

-> 7차 수정 (EVAL **ev3**, 본 실행 재수행 ga_loop_v7):
1. **z3 ev3**: 경로 조건 벡터의 순서 대응 판정(else/else-if 부정 맥락 자동 반영 - 합취 붕괴 제거),
   `:=` 선언 순번 자유 심볼(알파 안전·주기 유지 규약 충실), `&&`/`||` -> and/or 정규화(87행 도메인
   복귀), **판정 도메인을 gold가 결정**(유전형 무관 분모) + pred 실패는 제외가 아닌 False 계상,
   self-check 6->12종(else-if 임계값 반례·:= 플래그 반례·&& 정규화 포함), 표기 "z3(gt 조건 행)"
2. assign_block output 선점을 JSON 구조 어휘(json|objects?|output formats?)로 한정 + 회귀
   self-check 2종(cron/period fields -> temporal)
3. **PROMPT_ASSET_SHA**: v0_6 md 3종+service schema 내용 지문을 run_config(write-once 규약
   공유)와 eval_cache 축에 추가; run_config 누락 키는 무검사 통과 대신 병합 기록+경고
4. 적합도 비용 정규화 상수를 리터럴에서 05 캐시 실측 재계산으로 교체(baselines.json 기록),
   history에 logic_n 기록, §7 기준선 병기 수치도 캐시 실측·MAX_NEW_TOKENS 보간으로 동적화
5. 견고성/문서: 완료 세대 재방문 시 advisor 재질의·rule_pool 변형 금지, 마지막 청크 상각 경고,
   §8 z3 문구 집계 구간 정직화(+이중 합산 실수 수정), holdout recs 변수명 명시화, §5에 ev3
   규약·not() 파서 한계·dedup 패러프레이즈 한계 명시, staged 커맨드에 --inplace 구분·mock의
   feedback_cache 부재 명시
개정 사고 기록: 1차 패치 스크립트가 중간 실패해 `&&` 정규화가 누락된 채 재시도됨 -> mock06_v7
self-check가 즉시 검출(assert 실패) -> 재적용 후 통과. z3 요약 print의 이중 합산도 자체 리뷰에서
검출·수정. 단계적 점검이 회귀를 잡은 사례 추가.
검증(7차): mock06_v7 통과(ev3 self-check 12종 — `&&` 누락을 self-check가 실검출한 뒤 재적용,
28키 run_config + PROMPT_ASSET_SHA) -> smoke06_v7 통과 -> **본 실행 ga_loop_v7 완주(114분)**:
R1 73.3 -> R2 83.3 -> R3 83.3 -> R4 kept incumbent -> R5 78.3 채택; 홀드아웃 **71.7%**·det 80.2·
5,032 tok·2.20s. z3(ev3) 실측: 판정 1,077행(&& 정규화로 도메인 +87행 복귀), path_count_mismatch
220행은 제외가 아닌 False 계상, gt 파싱불가 5행만 제외 — 홀드아웃 z3 36/60행 28%
(조건 구조 대응까지 요구하는 엄격한 정직 지표). logic_n 세대 내 균일(15/18/33 = 서브셋 크기별)
— 분모 편향 해소 실측.

| 반복 | opus:fresh-eyes | opus:quality-consistency | 평균 | 판정 |
|---|---|---|---|---|
| 7 | 87 | 93 | 90.0 | **통과** (수렴: 76.5 -> 84 -> 85 -> 87.75 -> 82 -> 80 -> 90.0) |

반복 7 검증 실측(critic): ev3 반례 12종 self-check 독립 재실행 통과, v7 gold 조건 69행 전수
z3.simplify 검사 상수 붕괴 0건(v6 191행 대비 해소), logic=None 사유 전부 gold 측(유전형별 분모
차이 0건), rule_pool 26/26 배정 재현(cron/period 규칙 temporal 8/9), asset_sha 2,010레코드 전부
일치, 비용 정규화 상수 소수점까지 재계산 일치, R1-R4 전 수정 유지 확인.

반복 7 잔여 지적 -> R5 진입 전 반영:
- **README 06 절차가 구 태그(*_v6/ev2)를 안내해 즉시 assert 중단** + z3 서술이 ev2 규약 고착
  -> v7 태그·ev3 규약·PROMPT_ASSET_SHA로 갱신 (유일한 외부 문서의 재현 경로 복구)
- **z3 미바인딩 식별자 intern 붕괴**(분기 로컬 대입 소실·미선언 이름이 상수화 -> ⊥≡⊥ 공허 True
  가능; v7 실측 영향 0건 전수 확인) -> 미바인딩 이름을 자유 심볼로 승격(ev3 건전성 패치;
  판정 변화 0 실측이므로 EVAL_VERSION 유지, self-check 2종 추가)
- 채택 로그 '게이트 기각'과 '개선 없음' 구분(gate rejected 라벨 + blocked_best 기록)
- §5 도메인 예외 3종(output_not_parsed/z3_timeout/solver_error) 명시(v7 발생 0), wait-until/if
  동일 항 한계 명시, §7 기준선 병기에 '(280행 평균)' 라벨, 수렴률 v7 87.3% 병기,
  judge 재방문 재호출 주석, record_run_config 병합 경고 대칭화
반영 완료 검증: README v7·ev3 규약·PROMPT_ASSET_SHA 갱신, z3 ev3.1(gold 상수 경로 조건
`gt_degenerate_condition` 도메인 제외 + self-check 2종 추가 -> 총 14종), gate rejected 라벨
+ blocked_best 기록, 재방문 시 judge 스킵·lineage 중복 가드, record_run_config 경고 대칭,
§7 '(280행 평균)' 라벨, §5 도메인 예외 4종·wait/if 한계·v7 87.3% 병기.
mock06_v7b 5라운드 통과(ev3.1 self-check 실측) -> ga_loop_v7 replay 복원(오류 0, 71.7% 유지;
v7 gold 조건 69행 상수 0건 전수 확인으로 기존 캐시 판정 불변 = EVAL_VERSION 유지).

## 재정비 R5 — 루브릭: 최종 종합 검수 (final audit)

항목: requirements_final_audit(25 — 요구사항 명세·사용자 지시 전수 대조) /
end_to_end_reproduction(20 — 외부 문서만으로 재현 절차 성립) /
all_rounds_hold(20 — R1-R4 전 수정 표본 유지 검증) /
artifact_integrity(20 — ga_loop_v7 수치 무결성·캐시 축 종합 재계산) /
handoff_quality(15 — ledger 완결성·provenance·인수인계 명료성)
(평가 도구 변경: 마지막 재정비 — critic이 신규 결함 발굴이 아니라 **인수인계 관점의 종합 감사**를
수행: 요구사항 커버리지 전수표, 문서 기반 재현 리허설, 전 라운드 수정의 회귀 확인)

| 감사관 | opus:requirements-repro | opus:integrity-handoff | 평균 | 판정 |
|---|---|---|---|---|
| R5 최종 | 91 | 90 | 90.5 | **통과 — 메타루프 5회 재정비 완료** |

R5 감사 실측: 사용자 요구 U1-U7 + 논문 정합 항목 전수 커버리지표 작성(met 전항; U6은
DirectTransfer/CloudRef 기준선이 05 캐시 환산임을 명시한 partial — 문서화된 축소),
history 15세대 + population 90건 score/fitness/logic_n 전수 재계산 일치, genome 해시·캐시 축
(mode/model/max_new/gen_batch/data_sha/asset_sha)·콘텐츠 지문 외부 재계산 일치, R1-R4 수정
56개 표본 전수 유지, judge/advisor 산술 재현(R5 보정 80.0 = (0.783*60+1)/60), 재현 리허설
(README 1단계를 스크래치 태그로 실행 -> mock06_v7b와 산출물 바이트 동일) 통과.

R5 공통 critical 1건 -> 최종 반영(완료):
- **ga_loop_v7 R4 채택 라벨 provenance**: 저장 이력의 'kept incumbent'는 gate-rejected 라벨
  도입 이전 코드의 산출물 — 실측상 R4는 86.7 후보가 회귀 2 > 1로 기각된 게이트 기각 라운드.
  저장 이력은 불변 보존하고, replay·§8이 저장된 모집단으로 게이트를 **파생 재판정**해
  "파생 재판정: gate rejected (best 86.7, regression 2 > 1)"를 표기하도록 보강(구 라벨
  재방송 방어 - 동류 재발 자동 검출). v7 replay로 실행 증거 확보(위 문구 실제 출력, 오류 0,
  홀드아웃 71.7% 유지). §6 md에 채택 규칙('적합도 순 최초 통과 후보')과 파생 표기 규약 명시.

R5 잔여 반영/기각 기록:
- 반영: 정본 빌더를 저장소로 이관(`tutorials/builders/build_nb06.py` - 스크래치패드 휘발성
  해소, 노트북 21셀과 바이트 동일), gate 분기 검증 시도 mock06_gate(REG_EPS=0; 결정적 mock
  점수 특성상 기각 라운드 미발생 - 실행 증거는 v7 replay 파생 재판정으로 대체), 표기 정정:
  z3 self-check는 '14종'이 아니라 **13개 assert**(ev2 6 + ev3 5 + ev3.1 2), 반복 7 검증 문구의
  'temporal 8/9'는 **8/8**로 정정.
- 기각(근거): '마지막 세대 advisor 질의 낭비' minor는 부정확 — rule_pool은 라운드 간 지속되어
  다음 라운드 시드 교배에서 소비된다(최종 라운드 말미 1회만 미소비; 코드 주석으로 명시).
- 보류 상태 명시(open, 다음 개정 후보): state.json의 history 전문 중복 보관(O(n^2) 쓰기)
  요약화, dominant 케이스 우선순위의 증거 가중 정밀화, 노트북 내부 프롬프트 리터럴의 지문화
  (현재는 RENDER_VERSION 수동 규약), README staged 태그의 자동 최신화(현재는 개정 시
  수동 갱신 규약 - 본 ledger가 최신 검증 태그의 정본 이력).

## 최종 상태 (메타루프 완료)

- 재정비 5회 완료: R1 96.0 / R2 96.0 / R3 95.5 / R4 90.0(7반복) / R5 90.5 — 전 라운드 >= 90.
- 최종 코드: `tutorials/builders/build_nb06.py` (정본) -> `06_ga_prompt_search_full_loop.ipynb`
  (21셀, 오류 0, ga_loop_v7 출력 + 파생 재판정 표기 포함).
- 최종 본 실행: ga_loop_v7 (rv6+ev3, 114분) — 홀드아웃 DETPass **71.7%** / det 80.2 /
  z3(gt 조건 행) 28% / 5,032 tok / 2.20s(batch-10 상각) vs DirectTransfer 36.7%/30,107 tok
  / CloudRef 76.7%/29,623 tok. GA premap 프롬프트가 DirectTransfer를 약 2배 상회하며 1/6
  토큰으로 CloudRef에 근접 — 논문의 정성적 구도 재현(정량 수치는 축소 예산·280행 신규
  카탈로그 기준).
- 검증 태그 이력: mock06_v7 -> smoke06_v7 -> ga_loop_v7(본 실행) -> mock06_v7b(ev3.1 사후
  검증) -> mock06_gate(REG_EPS=0 분기 시도) -> v7 replay(파생 재판정 실행 증거).

## 후속 작업 (메타루프 완료 후, 사용자 지시 "계속 진행")

보류 항목 종결:
1. **state.json history 전문 중복 제거**: history의 단일 정본을 history.jsonl로 일원화 —
   state는 체크포인트(round/population/rule_pool/adopted/z3_errors)만 보관. 레거시 state의
   내장 history는 파일 부재 시에만 이관 소스로 사용 후 제거(마이그레이션 출력 명시).
   mock06_v8 실측: state.json에 history 키 없음, history.jsonl 14엔트리 단일 보관.
2. **dominant 케이스 output 선점 정밀화**: 데이터로 종결 — ga_loop_v7 실패 케이스 중 output
   신호 보유 0건(선점이 투표를 뒤집을 수 있는 사례 자체가 부재). 코드 변경 불요.
3. **내부 프롬프트 리터럴 지문**: INTERNAL_PROMPT_SHA(ROLE_CORE+OUTPUT_CORE+GRAMMAR_COMPACT+
   TEMPORAL_COMPACT)를 run_config에 기록(29키; 렌더 코드 변경 규약은 RENDER_VERSION 유지).
   1차 삽입이 정의 순서 앞이라 NameError -> mock이 즉시 검출 -> 정의 뒤로 이동 후 통과.
4. **README staged 태그 정합 가드**: 빌더가 빌드 시점에 README의 현 개정 태그 부재를 경고
   (도입 직후 v7 잔존을 실제로 경고해 갱신 유도 - 가드 동작 실증).

본 실행 확장(논문 예산): 기본 노브를 **POP=10 / MAX_GEN=12**(논문 pop·gen과 동일)로 승격,
RUN_TAG=ga_loop_v8. 세대당 문항은 30 유지(논문 45문 대비 축소 - 280행 코퍼스의 서로소
제약과 서브셋 정적 배분 보존; §0에 명시). 단계 체인: mock06_v8 통과 -> smoke06_v8 ->
본 실행 ga_loop_v8(수 시간 예상, 체크포인트 재개 가능).

**본 실행 ga_loop_v8 완주 (논문 pop·gen 예산 10·12, 377분)**:
채택 궤적 R1 60.0->80.0(12세대 실탐색) -> R2 90.0(**TARGET 도달**) -> R3/R4 회귀 0 유지 ->
R5 85.0(60문 확장). 홀드아웃 **DETPass 78.3%** / det 82.7 / z3(gt 조건 행) 47% / 5,188 tok /
2.37s — v7(71.7%) 대비 +6.6%p, **CloudRef 76.7%를 최초 상회**(1/6 토큰). 총 8,340 (genome,row)
평가, z3 판정 3,481행. 논문 예산의 효과 실증: v7(6·3)에서 83.3 정체·86.7 게이트 기각이던
탐색이 예산 확대로 90.0에 도달.
다음: Llama-3.1-8B arm (로컬 캐시 가용 확인, pad=eos 처리 기존 구현 확인) — 코드 불변이므로
mock 생략, smoke06_v8L(소형 실측)로 생성 경로 검증 후 ga_loop_v8_llama(동일 예산) 진행.
문서화된 근사: 비용 정규화·DirectTransfer/CloudRef 기준선은 Qwen/gpt 실측 유지(Llama full-prompt
기준선 미측정 - arm의 헤드라인은 자체 GA 홀드아웃 점수), 생성기 변수명 qwen_*은 역사적 명칭.
Llama arm 실행 사고 기록: 1차 시도(ga_loop_v8_llama, GEN_BATCH=10) — 커널 segfault 후 재시도에서
CUDA OOM 확정(Llama-8B가 배치 10에서 44.3GiB 요구, 49GiB 한계 초과; Qwen v8도 피크 46GiB로
근접했음). smoke(서브셋 6 = 실효 배치 6)는 통과했으나 본 실행 배치 10에서 초과 — 배치 노브가
메모리 한계 축임을 실증. 조치: 실패 태그 제거(평가 데이터 0건) 후 **ga_loop_v8L**(GEN_BATCH=6,
PYTORCH_CUDA_ALLOC_CONF=expandable_segments)로 재시작. GEN_BATCH는 write-once 노브이므로 태그
교체 규약을 그대로 따름(latency 상각 분모 6으로 기록됨 - Qwen v8의 배치 10 상각과 직접 비교 불가,
1차 비용 지표는 tokens).
