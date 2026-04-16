# joi-llm

자연어 명령을 JOILang/JOI JSON 형태의 IoT 시나리오 코드로 변환하는 실험 저장소입니다.  
현재 코드 기준으로 실제로 많이 쓰이는 진입점은 아래 5개입니다.

| 목적 | 파일 | 설명 |
| --- | --- | --- |
| 가장 메인 API 서버 | `demo.py` | `/generate_joi_code`, `/re_generate_joi_code`, `/get_model_list`, `/health` 제공 |
| 단건 CLI 추론 | `gpt_mg/run.py` | 서버 없이 문장 1개를 바로 JOI 코드로 생성 |
| 모델 비교 + DET 평가 | `query_raw.sh`, `query_cat1.sh`, `query_cat8.sh` | 여러 모델 호출, 결과 저장, DET 평가 |
| WebSocket 디바이스 데모 | `server_test_by_jmg.py`, `device_gpt.py`, `device_ollama.py` | 브라우저 UI + 디바이스 연결 방식 테스트 |
| Slack DM 수집 | `slack_server.py` | Slack DM을 날짜별 JSONL 로그로 저장 |

아래 설명은 위 파일들을 실제 코드 기준으로 분석해서, 어떤 기능을 어떤 순서로 실행해야 하는지 중심으로 정리했습니다.

## 1. 저장소 구조

| 경로 | 역할 |
| --- | --- |
| `demo.py` | JOI/CAP/로컬 Qwen/PromptGA 모델을 한 API로 묶는 FastAPI 서버 |
| `gpt_mg/` | JOI 생성기의 메인 구현. `version0_6`, `0_7`, `0_12`, `0_13`, `0_14` 프롬프트/설정 포함 |
| `gpt_cap/` | CAP 계열 생성기와 static analyzer 기반 후처리 |
| `gpt_mg/version0_14/` | Prompt block + GA + DET 기반의 이전 PromptGA 워크스페이스 |
| `gpt_mg/version0_15/` | connected_devices binding + schema fallback + admin feedback/GA update 워크스페이스 |
| `datasets/` | 테스트셋, 서비스 스키마, `things.json` 연결 디바이스 목록 |
| `query_raw.sh` | 단일 문장/행 번호 기준으로 여러 모델 비교 + `version0_14` + DET 평가 |
| `server_test_by_jmg.py` | WebSocket 디바이스 서버 + `static/index.html` UI |
| `slack_server.py` | Slack Socket Mode 기반 DM 로거 |
| `admin_logs/slack/` | Slack DM JSONL 로그 저장 위치 |
| `results/` | query/DET 실행 결과 저장 위치 |

## 2. 설치

가장 무난한 시작은 루트에서 가상환경을 만든 뒤 의존성을 설치하는 방식입니다.

```bash
cd /home/andrew/joi-llm
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

`slack_server.py`는 루트 `requirements.txt`에 없는 `slack-bolt`가 추가로 필요합니다.

```bash
pip install slack-bolt
```

`gpt_cap`만 따로 돌리고 싶다면 별도 의존성도 있습니다.

```bash
pip install -r gpt_cap/requirements.txt
```

## 3. 환경 변수 `.env`

코드에서 직접 읽는 환경 변수 이름은 아래와 같습니다.  
모든 값을 한 번에 다 넣을 필요는 없고, 내가 쓰는 실행 경로에 맞는 값만 채우면 됩니다.

```env
# demo.py
OPENAI_API_KEY_PROJ_DEMO=...

# gpt_mg/run.py, GPTBenchmark, 여러 보조 스크립트
OPENAI_API_KEY_PROJ_BENCH=...

# gpt_cap/run.py
OPENAI_API_KEY_SVC=...

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# 오래된 pipeline 계열에서만 사용
GOOGLE_TRANSLATE_KEY=...

# local qwen backend override 예시
JOI_VERSION012_PYTHON=/abs/path/to/python
JOI_VERSION012_WORKER=/abs/path/to/gpt_mg/version0_12/qwen_local_worker.py
JOI_VERSION012_DEVICE=cuda:0

JOI_VERSION013_PYTHON=/abs/path/to/python
JOI_VERSION013_WORKER=/abs/path/to/gpt_mg/version0_13/qwen_local_worker.py
JOI_VERSION013_DEVICE=cuda:0

# demo.py 또는 gpt_mg/run.py 에서 version0_14를 직접 호출할 때 사용
JOI_VERSION014_PYTHON=/abs/path/to/python
JOI_VERSION014_WORKER=/abs/path/to/gpt_mg/version0_13/qwen_local_worker.py
JOI_VERSION014_GENOME=/abs/path/to/gpt_mg/version0_14/results/best_genome_after_feedback.json

# demo.py 또는 gpt_mg/run.py 에서 version0_15를 직접 호출할 때 사용
JOI_VERSION015_PYTHON=/abs/path/to/python
JOI_VERSION015_WORKER=/abs/path/to/gpt_mg/version0_13/qwen_local_worker.py
JOI_VERSION015_GENOME=/abs/path/to/gpt_mg/version0_15/results/best_genome_after_feedback.json

# gpt_mg/version0_14/scripts/* 를 직접 돌릴 때 사용
JOI_V14_LLM_MODE=worker
JOI_V14_WORKER_PATH=/abs/path/to/gpt_mg/version0_13/qwen_local_worker.py
JOI_V14_PYTHON=/abs/path/to/python
JOI_V14_LOCAL_DEVICE=cuda:0
JOI_V14_OPENAI_ENDPOINT=http://127.0.0.1:8000/v1/chat/completions

# gpt_mg/version0_15/scripts/* 를 직접 돌릴 때 사용
JOI_V15_LLM_MODE=worker
JOI_V15_WORKER_PATH=/abs/path/to/gpt_mg/version0_13/qwen_local_worker.py
JOI_V15_PYTHON=/abs/path/to/python
JOI_V15_LOCAL_DEVICE=cuda:0
JOI_V15_OPENAI_ENDPOINT=http://127.0.0.1:8000/v1/chat/completions
```

### 환경 변수 해설

- `demo.py`는 항상 `OPENAI_API_KEY_PROJ_DEMO`를 읽습니다.
- `gpt_mg/run.py`는 `OPENAI_API_KEY_PROJ_BENCH`를 읽습니다.
- `gpt_cap/run.py`는 `OPENAI_API_KEY_SVC`를 읽습니다.
- `slack_server.py`는 `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`이 없으면 바로 종료합니다.
- `version0_12`, `version0_13`, `version0_14`, `version0_15`의 로컬 Qwen 계열은 내부적으로 `qwen_local_worker.py`를 subprocess로 실행합니다.
- `version0_12`, `version0_13`, `version0_14`, `version0_15`의 `model_config.json`은 `Qwen/Qwen2.5-Coder-7B-Instruct`와 `local_files_only=true`를 기본값으로 갖고 있으므로, 로컬 캐시에 모델이 없으면 실패할 수 있습니다.

## 4. 가장 많이 쓰는 실행: `demo.py` API 서버

### 4-1. 서버 켜기

가장 간단한 실행 방법:

```bash
cd /home/andrew/joi-llm
python demo.py
```

이렇게 실행하면 기본적으로 `0.0.0.0:8000`에서 FastAPI 서버가 올라갑니다.  
원하면 직접 uvicorn으로 실행해도 됩니다.

```bash
uvicorn demo:app --host 0.0.0.0 --port 8000 --reload
```

### 4-2. 서버 확인

```bash
curl http://localhost:8000/health
curl http://localhost:8000/get_model_list
```

- `/health`: 서버 생존 확인
- `/get_model_list`: 프런트/스크립트에서 보여줄 모델 display 이름 반환
- `/run_admin_feedback_update`: `version0_15` admin feedback + benchmark + GA update 실행
- `/docs`: FastAPI Swagger UI

### 4-3. `demo.py`가 지원하는 모델

`demo.py`는 display 이름, alias, 실제 runtime model을 분리해서 처리합니다.  
가장 안전한 방식은 `model`과 `other_params[0].selected_model`을 둘 다 넣는 것입니다.

| display / selected_model | 내부 runtime model | 생성기 |
| --- | --- | --- |
| `CAP-old_gpt4.1-mini_svc-v1.5.4` | `gpt4.1-mini` | `gpt_cap.run.generate_joi_code` |
| `JOI_gpt4.1-mini_v1.5.4` | `gpt_mg.version0_6` | `gpt_mg.run.generate_joi_code` |
| `Local5080_qwen-7b_svc-v1.5.4` | `gpt_mg.version0_13` | `gpt_mg.run.generate_joi_code` |
| `Local5080_qwen-7b_svc-v2.0.1` | `gpt_mg.version0_12` | `gpt_mg.run.generate_joi_code` |
| `PromptGA_v0.14_svc-v2.0.1` | `gpt_mg.version0_14` | `gpt_mg.run.generate_joi_code` |
| `PromptGA_v0.15_svc-v2.0.1_cd` | `gpt_mg.version0_15` | `gpt_mg.run.generate_joi_code` |
| `JOI5_gpt5-mini_svc-v1.5.4` | `gpt_mg.version0_7` | `gpt_mg.run.generate_joi_code` |

추가 alias 예:

- `gpt4.1-mini`
- `gpt_mg.version0_6`
- `gpt_mg.version0_7`
- `gpt_mg.version0_12`
- `gpt_mg.version0_13`
- `gpt_mg.version0_14`
- `gpt_mg.version0_15`
- `version0_14`
- `version0_15`
- `local_8b`

추가로 `gpt_mg/version0_15_updateYYYYMMDD*` 폴더가 있으면 `demo.py`가 이를 자동으로 모델 목록에 추가합니다.

### 4-4. `connected_devices` 준비

대부분의 스크립트는 `datasets/things.json` 전체를 그대로 넣습니다.

```bash
CONNECTED_DEVICES="$(python3 - <<'PY'
import json
with open('./datasets/things.json', encoding='utf-8') as f:
    print(json.dumps(json.load(f), ensure_ascii=False, separators=(',', ':')))
PY
)"
```

`things.json`에는 현재 612개의 가상 디바이스가 들어 있고, 각 항목은 대략 아래 구조입니다.

```json
{
  "virtual_airconditioner_('SectorA', 'Upper', 'Even')": {
    "id": "virtual_airconditioner_('SectorA', 'Upper', 'Even')",
    "category": "AirConditioner",
    "tags": ["AirConditioner", "SectorA", "Upper", "Even"]
  }
}
```

주의:

- `demo.py`에서 `connected_devices`를 `{}`로 보내면 마지막 요청의 값을 재사용합니다.
- 첫 요청부터 `{}`를 보내면 실질적으로 빈 디바이스 컨텍스트가 됩니다.
- 그래서 첫 요청은 `datasets/things.json`을 넣는 쪽이 안전합니다.
- 다만 `gpt_mg/version0_15/scripts/*` 또는 `gpt_mg.version0_15.config_loader`를 직접 쓸 때는 동작이 다릅니다.
- `version0_15`에서는 `connected_devices == {}` 이면 `service_schema_fallback` 모드로 바뀌고, `datasets/service_list_ver2.0.1.json`의 전체 category/service 목록을 prompt에 매핑해서 넣습니다.
- 즉 benchmark/GA 스크립트에서 dataset row의 `connected_devices`가 비어 있어도, `version0_15`는 전체 서비스 스키마를 기준으로 prompt를 구성할 수 있습니다.

### 4-5. 가장 기본적인 API 호출

```bash
curl -s -X POST http://localhost:8000/generate_joi_code \
  -H "Content-Type: application/json" \
  -d '{
    "sentence": "불을 켜줘",
    "model": "gpt_mg.version0_6",
    "connected_devices": '"$CONNECTED_DEVICES"',
    "current_time": "2026-03-31T12:00:00",
    "other_params": [
      {
        "selected_model": "JOI_gpt4.1-mini_v1.5.4"
      }
    ]
  }'
```

응답 형식은 대략 아래 구조입니다.

```json
{
  "code": [
    {
      "name": "불켜기",
      "cron": "",
      "period": -1,
      "code": "(#Light).switch_on()"
    }
  ],
  "log": {
    "response_time": "...",
    "inference_time": "...",
    "translated_sentence": "...",
    "best_code": "...",
    "model_name": "..."
  }
}
```

### 4-6. `other_params`에서 자주 쓰는 값

`demo.py`와 `gpt_mg/version0_14`, `gpt_mg/version0_15` 기준으로 실제로 읽는 값들:

| 키 | 용도 |
| --- | --- |
| `selected_model` | `demo.py`에서 사용할 모델 선택 |
| `user_id` | `re_generate_joi_code`에서 저장 파일명 분기 |
| `user_feedback` | `re_generate_joi_code` 동작 제어 |
| `genome_json` | `version0_14`, `version0_15` 호출 시 사용할 genome 파일 지정 |
| `service_schema` | `version0_14`, `version0_15` 서비스 스키마 override |
| `candidate_strategy` | `version0_14`, `version0_15` candidate strategy 지정 |
| `temperature` | `version0_14`, `version0_15` temperature override |
| `max_tokens` | `version0_14`, `version0_15` 최대 토큰 override |
| `cron`, `period` | `version0_14`, `version0_15` prompt 값 주입용 |

### 4-7. `/re_generate_joi_code` 사용법

이 엔드포인트는 이전 결과를 기준으로 재시도/추가조건/확정/취소를 처리합니다.

#### `retry`

```bash
curl -s -X POST http://localhost:8000/re_generate_joi_code \
  -H "Content-Type: application/json" \
  -d '{
    "sentence": "불을 켜줘",
    "model": "gpt_mg.version0_6",
    "connected_devices": '"$CONNECTED_DEVICES"',
    "current_time": "2026-03-31T12:00:00",
    "other_params": [
      {
        "user_id": "demo-user",
        "selected_model": "JOI_gpt4.1-mini_v1.5.4",
        "user_feedback": ["retry"]
      }
    ]
  }'
```

- 내부적으로 `gpt_mg.run.all_items`의 다음 candidate를 꺼냅니다.
- 더 이상 candidate가 없으면 `"재시도할 코드가 없습니다..."` 메시지를 반환합니다.

#### `extra:`

```bash
curl -s -X POST http://localhost:8000/re_generate_joi_code \
  -H "Content-Type: application/json" \
  -d '{
    "sentence": "불을 켜줘",
    "model": "gpt_mg.version0_6",
    "connected_devices": '"$CONNECTED_DEVICES"',
    "current_time": "2026-03-31T12:00:00",
    "other_params": [
      {
        "user_id": "demo-user",
        "selected_model": "JOI_gpt4.1-mini_v1.5.4",
        "user_feedback": ["extra: 거실 조명만 켜고 다른 방은 제외해줘"]
      }
    ]
  }'
```

- 마지막 피드백이 `extra:`로 시작하면 추가 조건을 붙여 다시 생성합니다.
- `version0_14`를 선택한 경우에도 같은 엔드포인트로 재생성 가능합니다.

#### `yes` / `no`

```bash
"user_feedback": ["yes"]
"user_feedback": ["no"]
```

- `yes`: 현재 결과를 확정하고 저장
- `no`: 취소하고 빈 응답 반환

저장 위치:

- `user_id`가 있으면 `datasets/usr_rag/sentence_best_code_log_<user_id>.csv`
- 없으면 `datasets/usr_rag/sentence_best_code_log_server.csv`

## 5. query 사용법

### 5-1. 가장 범용적인 스크립트: `query_raw.sh`

이 스크립트는 아래를 한 번에 합니다.

1. 입력 문장을 결정
2. `demo.py` 서버의 여러 모델 호출
3. `version0_14`는 별도 스크립트로 직접 생성 + rerank
4. 결과를 `generation.jsonl`로 저장
5. 가능하면 DET 평가까지 수행

실행 전에는 보통 `demo.py` 서버를 먼저 띄워 두는 것이 좋습니다.

```bash
python demo.py
```

다른 터미널에서:

```bash
bash query_raw.sh 1
bash query_raw.sh 183
bash query_raw.sh "아침 9시마다 사람이 있으면 블라인드를 열어줘."
bash query_raw.sh "불을 켜줘" "2026-03-31T12:00:00"
```

입력 규칙:

- 숫자 1개: `datasets/JOICommands-280.csv`의 행 번호 또는 `index`
- 문자열 1개: raw command
- 두 번째 인자: `current_time`, 기본값은 `2026-03-31T12:00:00`

#### `query_raw.sh`가 호출하는 모델

1. `CAP-old_gpt4.1-mini_svc-v1.5.4`
2. `JOI_gpt4.1-mini_v1.5.4`
3. `Local5080_qwen-7b_svc-v1.5.4`
4. `Local5080_qwen-7b_svc-v2.0.1`
5. `PromptGA_v0.14_svc-v2.0.1`

#### 출력 위치

- `results/generation/<RUN_ID>/generation.jsonl`
- `results/generation/<RUN_ID>/merged_value_services.json`
- `results/generation/<RUN_ID>/merged_function_services.json`
- `results/generation/<RUN_ID>/version0_14_row.csv`
- `results/generation/<RUN_ID>/version0_14_candidates.csv`
- `results/generation/<RUN_ID>/version0_14_rerank.csv`
- `results/det_paper/...`

#### DET 평가가 되는 조건

- 입력이 dataset 행 번호이거나
- raw command가 dataset의 `command_kor` 또는 `command_eng`와 정확히 일치할 때

정확히 매칭되지 않으면 generation은 수행되지만 DET는 건너뜁니다.

#### `query_raw.sh`에서 바꿔볼 수 있는 환경 변수

```bash
V14_GENOME_JSON=/abs/path/to/genome.json \
V14_CANDIDATE_K=5 \
V14_REPAIR_THRESHOLD=99 \
V14_REPAIR_ATTEMPTS=2 \
bash query_raw.sh 183
```

### 5-2. 고정 예제 스크립트: `query_cat1.sh`, `query_cat8.sh`

둘 다 내부에 문장이 하드코딩된 간단 비교 스크립트입니다.

```bash
bash query_cat1.sh
bash query_cat8.sh
```

용도:

- `query_cat1.sh`: `"불을 켜줘"` 예제
- `query_cat8.sh`: 카테고리 8 계열 예제

주의:

- 두 스크립트 모두 `demo.py` 서버가 켜져 있어야 합니다.
- `query_cat1.sh`의 3번째 요청은 현재 코드상 `147.46.215.237:10004`라는 하드코딩 주소를 사용합니다.
- 모든 모델을 로컬로 테스트하려면 해당 URL을 내 서버 주소로 수정해서 쓰는 편이 안전합니다.

## 6. 서버 없이 직접 실행하는 방법

### 6-1. `gpt_mg/run.py`

가장 단순한 단건 생성기입니다.

기본 모델(`version0_6`)로 실행:

```bash
python gpt_mg/run.py "불을 켜줘"
```

모델을 명시해서 실행:

```bash
python gpt_mg/run.py gpt_mg.version0_6 "불을 켜줘"
python gpt_mg/run.py gpt_mg.version0_7 "매일 아침 9시에 조명을 켜줘"
python gpt_mg/run.py gpt_mg.version0_13 "온도가 28도 이상이면 에어컨을 켜줘"
python gpt_mg/run.py gpt_mg.version0_14 "비가 오면 창문을 닫아줘"
```

동작 방식:

- `generate_joi_code()`가 선택한 version의 `config_loader.py`를 import해서 prompt를 구성
- OpenAI 또는 local Qwen backend 호출
- 결과를 JSON 파싱 후 반환
- 후보 결과와 확정 결과 일부를 CSV로 저장

출력/로그:

- 현재 작업 디렉터리에 `output_each_command.csv`
- `gpt_mg/sentence_best_code_log.csv`
- feedback 모드일 때 `joi_outputs/choices_result.joi`

주의:

- `version0_12`, `version0_13`, `version0_14`는 local Qwen worker 설정이 맞아야 합니다.
- `version0_14`는 genome이 없으면 기본 후보 경로를 순서대로 찾다가 마지막에 `gpt_mg/version0_14/genomes/example_genome.json`을 사용합니다.

### 6-2. `demo.py`를 CLI로만 사용

`demo.py`는 서버 모드 외에도 터미널 인터랙션 모드를 갖고 있습니다.

```bash
python demo.py "불을 켜줘"
python demo.py joi "불을 켜줘"
python demo.py cap "불을 켜줘"
```

이 모드에서는:

- 후보를 하나씩 보여주고
- 역변환된 한국어 설명을 출력한 뒤
- `y`, `n`, 엔터, 추가 요구사항 입력으로 계속 재시도할 수 있습니다

주의:

- 현재 코드상 2인자 alias 파서는 일부 실험용 분기가 남아 있습니다.
- 특히 `local_7b` 분기는 이름과 달리 실제로 `gpt_mg.version0_6`로 연결되어 있어, 로컬 Qwen 테스트 용도로는 권장하지 않습니다.

### 6-3. CAP만 따로 실행

`demo.py`에서 CAP 모델을 고르면 내부적으로 `gpt_cap.run.generate_joi_code()`를 호출합니다.  
CAP만 단독으로 보고 싶으면 아래 방식도 가능합니다.

직접 입력형:

```bash
cd gpt_cap
python main.py
```

FastAPI 앱으로 띄우기:

```bash
cd gpt_cap
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

엔드포인트:

- `POST /Joi`

주의:

- `gpt_cap/main.py`는 같은 디렉터리의 `run.py`를 직접 import하므로, API로 띄울 때도 `gpt_cap` 디렉터리 안에서 실행하는 쪽이 안전합니다.

## 7. WebSocket + 브라우저 UI 모드

이 경로는 `demo.py`와는 별도입니다.  
브라우저에서 문장을 입력하고, 연결된 디바이스(WebSocket 클라이언트)들에게 작업을 보내는 구조입니다.

### 7-1. 서버 실행

```bash
python server_test_by_jmg.py
```

서버가 뜨면:

- `http://localhost:8000/` 에서 `static/index.html` UI 제공
- `/api/devices` 에서 현재 연결된 디바이스 목록 확인
- `/api/device_responses` 에서 응답 상태 확인
- `/api/sentence_to_scenario` 에 문장을 전송
- `/ws/device/{device_id}` 로 디바이스 연결

### 7-2. GPT 디바이스 연결

```bash
python device_gpt.py http://localhost:8000
```

이 스크립트는:

- WebSocket 서버에 디바이스처럼 접속
- 작업을 받으면 `gpt_mg.run.get_script_gpt()`로 처리
- 결과를 다시 서버로 JSON 전송

오프라인 테스트 모드:

```bash
python device_gpt.py test
```

### 7-3. Ollama 기반 옛 파이프라인 디바이스 연결

```bash
python device_ollama.py http://localhost:8000
```

이 스크립트는:

- `pipeline.run.pipeline_with_logs()`를 사용
- 오래된 pipeline 기반 변환 결과를 서버에 전송

테스트 모드:

```bash
python device_ollama.py test
```

### 7-4. 브라우저에서 무엇을 할 수 있나

`static/index.html` 기준으로:

- 입력 문장 변환 버튼
- 마이크 버튼
- Similarity 비교
- 연결 디바이스 선택
- hypothetical device 버튼
- 디바이스 응답 상태 모니터링

참고:

- 코드 주석에는 마이크 사용을 위해 HTTPS/self-signed 인증서 발급 예시가 남아 있습니다.
- 현재 `__main__` 기본 실행은 HTTP `:8000`입니다.
- 브라우저 음성 기능은 환경에 따라 HTTPS가 필요할 수 있습니다.

## 8. Slack DM 로깅 서버: `slack_server.py`

이 기능은 Slack 봇으로 받은 DM을 날짜별 JSONL로 기록하는 용도입니다.  
원래 메모는 `SlackBot.md`에 있고, 여기서는 실제 실행 절차를 정리합니다.

### 8-1. Slack 앱 설정

Slack App에서 아래를 설정합니다.

1. Bot Token Scopes 추가
   - `im:history`
   - `chat:write`
2. Event Subscriptions 활성화
3. Bot events에 `message.im` 추가
4. Workspace에 앱 설치
5. `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` 발급
6. App Home에서 DM 허용

### 8-2. 실행

```bash
pip install slack-bolt
python slack_server.py
```

정상 실행되면 Socket Mode로 대기합니다.

### 8-3. 동작 방식

사용자가 봇에게 DM을 보내면:

1. `channel_type == "im"` 인지 확인
2. 봇 메시지는 무시
3. Slack API로 보낸 사람의 `name`, `real_name` 조회
4. `admin_logs/slack/YYYY-MM-DD.jsonl`에 한 줄 append
5. 사용자 메시지에 `:white_check_mark:` reaction 추가 시도
6. `"확인했습니다, ...님! 서버에 안전하게 기록해 두었습니다."` 답장 전송

저장 레코드에는 아래 정보가 들어갑니다.

- 저장 시각
- event timestamp
- channel
- slack user id
- slack user name
- slack real name
- text
- raw event 전체

### 8-4. 로그 확인

```bash
ls admin_logs/slack
tail -n 5 admin_logs/slack/2026-03-25.jsonl
```

## 9. `version0_14` 독립 실험 워크스페이스

`gpt_mg/version0_14/`는 PromptGA/DET 전용 독립 워크스페이스입니다.  
루트의 `query_raw.sh`도 일부 여기 스크립트를 호출합니다.

상세 문서는 `gpt_mg/version0_14/README.md`에 있고, 가장 많이 쓰는 명령만 요약하면 아래와 같습니다.

### 9-1. 빠른 생성

```bash
cd /home/andrew/joi-llm/gpt_mg/version0_14

python3 scripts/run_generate.py \
  --profile version0_14 \
  --genome-json genomes/example_genome.json \
  --limit 5 \
  --candidate-k 2
```

### 9-2. rerank + repair

```bash
python3 scripts/run_rerank.py \
  --profile version0_14 \
  --genome-json genomes/example_genome.json \
  --candidates-csv results/candidates_gen-example-version0-14.csv
```

### 9-3. feedback loop

```bash
python3 scripts/run_feedback_loop.py \
  --profile version0_14 \
  --genome-json genomes/example_genome.json \
  --validation-size 5 \
  --limit 5
```

### 9-4. GA search

```bash
python3 scripts/run_ga_search.py \
  --profile version0_14 \
  --genome-json genomes/example_genome.json \
  --population 4 \
  --gens 3 \
  --sample-size 5 \
  --validation-size 5 \
  --limit 5
```

### 9-5. 전체 파이프라인

```bash
bash scripts/run_full_pipeline.sh --profile version0_14 --mode quick
bash scripts/run_full_pipeline.sh --profile version0_14 --mode full
```

### 9-6. 특정 row / 문장 조회

```bash
bash scripts/query_generations.sh 183
bash scripts/query_generations.sh --row-no 275 --category 8
bash scripts/query_generations.sh "Lock the doorlock every day at midnight."
```

### 9-7. `version0_14`에서 헷갈리기 쉬운 환경 변수 차이

두 경로의 환경 변수 이름이 다릅니다.

| 실행 경로 | 주로 읽는 환경 변수 |
| --- | --- |
| `demo.py` 또는 `python gpt_mg/run.py gpt_mg.version0_14 ...` | `JOI_VERSION014_*` |
| `gpt_mg/version0_14/scripts/*` | `JOI_V14_*` |

즉:

- API 서버에서 `PromptGA_v0.14_svc-v2.0.1`을 호출할 때는 `JOI_VERSION014_GENOME`이 중요
- `run_full_pipeline.sh`, `run_generate.py` 등을 직접 돌릴 때는 `JOI_V14_LLM_MODE`, `JOI_V14_WORKER_PATH`, `JOI_V14_LOCAL_DEVICE` 등이 중요

### 9-8. `version0_15` connected_devices fallback + benchmark/GA

`gpt_mg/version0_15/`는 `connected_devices`를 category/tag/location binding으로 prompt에 넣고, 값이 비어 있으면 `datasets/service_list_ver2.0.1.json` 전체를 schema fallback으로 사용합니다.

즉 아래 명령은 `admin_logs`가 비어 있거나 아예 없어도 돌아갑니다.

빠른 benchmark + GA search:

```bash
cd /home/andrew/joi-llm/gpt_mg/version0_15

bash scripts/run_full_pipeline.sh \
  --mode quick \
  --llm-mode worker \
  --seed 31
```

`admin_logs`가 있으면 실패 케이스를 반영하고, 없어도 benchmark/GA만 수행하는 통합 업데이트:

```bash
cd /home/andrew/joi-llm

python gpt_mg/version0_15/scripts/run_admin_feedback_update.py \
  --admin-log-root admin_logs \
  --benchmark-limit 20 \
  --llm-mode worker \
  --seed 31
```

정말 `admin_logs`가 없거나 쓰고 싶지 않다면 존재하지 않는 경로를 넣으면 됩니다.

```bash
python gpt_mg/version0_15/scripts/run_admin_feedback_update.py \
  --admin-log-root /tmp/no-admin-logs \
  --benchmark-limit 20 \
  --llm-mode worker \
  --seed 31
```

빠른 smoke 용도로 더 작게 돌리려면:

```bash
python gpt_mg/version0_15/scripts/run_admin_feedback_update.py \
  --admin-log-root /tmp/no-admin-logs \
  --benchmark-limit 1 \
  --ga-population 2 \
  --ga-gens 1 \
  --ga-sample-size 1 \
  --ga-validation-size 1 \
  --benchmark-candidate-k 1 \
  --skip-category-sweep \
  --llm-mode worker \
  --seed 31
```

`demo.py` 서버에서 트리거하는 방법:

```bash
curl -s -X POST http://localhost:8000/run_admin_feedback_update \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt_mg.version0_15",
    "admin_log_root": "/tmp/no-admin-logs",
    "benchmark_limit": 20,
    "llm_mode": "worker",
    "seed": 31
  }'
```

출력 위치:

- `gpt_mg/version0_15/results/admin_feedback_update_<timestamp>/summary.json`
- `gpt_mg/version0_15/results/admin_feedback_update_<timestamp>/report.md`
- `gpt_mg/version0_15/results/best_genome_from_ga.json`
- `gpt_mg/version0_15/results/best_genome_after_feedback.json`
- promotion이 성공하면 `gpt_mg/version0_15_updateYYYYMMDD*/`

## 10. 결과 파일이 어디에 쌓이는가

| 경로 | 내용 |
| --- | --- |
| `gpt_mg/sentence_best_code_log.csv` | `gpt_mg/run.py` 계열 확정 결과 로그 |
| `output_each_command.csv` | 단건 CLI 실행 결과 |
| `joi_outputs/choices_result.joi` | feedback/candidate 모드 출력 |
| `results/generation/<RUN_ID>/` | `query_raw.sh` 생성 결과 |
| `results/det_paper/` | DET/SDET 평가 결과 |
| `gpt_mg/version0_14/results/` | PromptGA 결과물, rerank CSV, best genome 등 |
| `gpt_mg/version0_14/logs/` | prompt/response trace |
| `gpt_mg/version0_15/results/` | connected_devices binding PromptGA 결과물, admin update summary, promoted genome |
| `gpt_mg/version0_15/logs/` | prompt/response trace, admin feedback snapshot |
| `admin_logs/slack/YYYY-MM-DD.jsonl` | Slack DM 로그 |
| `datasets/usr_rag/` | `/re_generate_joi_code` 확정 결과 저장 |

## 11. 자주 겪는 문제

### `slack_server.py`가 import 에러로 시작 안 됨

`slack-bolt`가 빠졌을 가능성이 큽니다.

```bash
pip install slack-bolt
```

### 로컬 Qwen 모델이 안 뜸

확인 순서:

1. `JOI_VERSION012_*`, `JOI_VERSION013_*`, `JOI_VERSION014_*` 경로가 맞는지
2. GPU 디바이스 번호가 맞는지
3. 로컬에 `Qwen/Qwen2.5-Coder-7B-Instruct` 캐시가 있는지
4. worker 파일 경로가 실제 파일과 일치하는지

### `demo.py` 첫 요청에서 결과가 이상함

첫 요청인데 `connected_devices`를 `{}`로 보낸 경우일 수 있습니다.  
처음부터 `datasets/things.json`을 넣어 보내는 쪽이 안전합니다.

### `version0_15` benchmark를 돌리는데 `connected_devices`가 비어 있음

정상일 수 있습니다.  
`gpt_mg/version0_15/scripts/*` 경로에서는 `connected_devices == {}` 이면 `service_schema_fallback`으로 바뀌고, `datasets/service_list_ver2.0.1.json` 전체를 prompt에 넣도록 설계되어 있습니다.

반대로 `demo.py`는 `{}`를 보내면 마지막 요청의 `connected_devices`를 재사용합니다.

즉:

- API 서버 테스트: 첫 요청부터 실제 `connected_devices`를 보내는 편이 안전
- benchmark/GA 스크립트: 비어 있어도 `version0_15`가 전체 schema fallback으로 처리

### `query_raw.sh`는 돌았는데 DET가 안 찍힘

raw command가 dataset row와 정확히 매칭되지 않으면 DET 평가를 건너뜁니다.  
행 번호로 주거나, dataset의 `command_kor`/`command_eng`와 완전히 같은 문장을 써야 합니다.

### `device_gpt.py test` 또는 오래된 benchmark 코드가 에러남

`gpt_mg/GPTBenchmark.py` 계열은 추가 패키지와 예전 파일 구조를 가정하는 부분이 있습니다.  
메인 실행 경로는 `demo.py`, `gpt_mg/run.py`, `query_raw.sh`, `server_test_by_jmg.py`, `slack_server.py`부터 확인하는 것을 권장합니다.

## 12. 추천 시작 순서

처음 저장소를 만졌다면 아래 순서가 가장 덜 헷갈립니다.

1. `pip install -r requirements.txt`
2. `.env`에 `OPENAI_API_KEY_PROJ_DEMO`, `OPENAI_API_KEY_PROJ_BENCH`부터 넣기
3. `python demo.py`
4. `curl http://localhost:8000/get_model_list`
5. `curl ... /generate_joi_code`로 단건 테스트
6. `bash query_raw.sh 1`로 모델 비교 + DET 확인
7. 필요하면 `python server_test_by_jmg.py` + `python device_gpt.py http://localhost:8000`
8. Slack 연동이 필요하면 마지막에 `python slack_server.py`

---

추가로 깊게 봐야 할 파일:

- `gpt_mg/version0_14/README.md`
- `SlackBot.md`
- `demo.py`
- `gpt_mg/run.py`
- `query_raw.sh`
