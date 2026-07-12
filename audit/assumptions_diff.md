# 논문 가정(AS-01~08) vs 저장소 실측 diff

- 생성: tools/build_settings_manifest.py @ fb409c42
- 실측 상세: audit/manifest.json

| ID | 논문 가정 | 실측 | 상태 | 매핑 WI |
|---|---|---|---|---|
| AS-01 | 벤치마크 N=180 | 정본 CSV 280행(8범주). cat1~6 합계 180으로 분할 설계 가능하나 분할 매니페스트 부재 | MISMATCH | WI-01/WI-05 |
| AS-02 | 리플레이 60건 (탐색 30 / 보류 30) | ReplayFit 계산 경로 자체 부재. 실사용 리플레이 원천: usr_rag 33행 + admin 로그 1건 | ABSENT | WI-05 |
| AS-03 | 스트레스 40건 | 스트레스 셋 전역 부재 (find/grep 0건) | ABSENT | WI-01 후속(스트레스 셋 확보 또는 FIX_PAPER) |
| AS-04 | GA 예산 pop 10 / gen 12 / elite 2 / tournament 3 / p_m 0.35 | 정본 기본 pop 2 / gen 1, elite 1 고정, tournament 없음, 100% 변이. 레거시 백업 pop 20 / gen 30 / elites 2 | MISMATCH | WI-16 |
| AS-05 | 적합도 가중치 0.50:0.15:0.20:0.10:0.05, config 외부화 | WI-07 완료: [0.5, 0.15, 0.2, 0.1, 0.05] @ configs/ga_search_fitness.json, 5항 정규화 구현(fitness.py). gamma(ReplayFit)는 WI-05 배선 전까지 missing 처리 | MATCH | WI-07 |
| AS-06 | 세대당 층화 표본 9범주×5=45 | 층화 표본기 구현됨(WI-07, --stratify-per-category). 단 실데이터는 8범주(×5=40) — 9범주(45) 서술은 FIX_PAPER 대상 | PARTIAL | WI-07 (+FIX_PAPER: 9범주→8범주) |
| AS-07 | 명령당 3회 반복 생성 평균, 비율 0.1% 반올림 | candidate_k 기본 1(정본)·2(레거시), 3 지정 스크립트/설정 전역 부재. 반올림 프로토콜 코드 부재 | ABSENT | WI-02/WI-03 실행 config에서 적용 |
| AS-08 | vLLM 서빙 + max_model_len 기록 | vLLM 부재(requirements 포함). 실서빙: HF transformers subprocess + OpenAI호환 local HTTP. max_model_len 전역 0건, local_max_new_tokens(256/512)만 존재 | MISMATCH | WI-11 (+FIX_PAPER) |
