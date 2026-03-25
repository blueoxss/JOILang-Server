from fastapi import FastAPI
from fastapi.responses import JSONResponse

import json, os
import logging
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

#from ollama.run import generate_joi_code 
from gpt_mg.run import generate_joi_code 
from gpt_cap.run import generate_joi_code as generate_joi_code_cap
from gpt_mg.run import save_sentence_and_code 
from gpt_mg import run
#from .services.loader_gpt import load_all_resources
import uvicorn
# 사용할 모델
#MODEL_NAME = "ollama.version0_3"
MODEL_NAME = "gpt_mg.version0_6"
MODEL_NAME_KOR = "gpt_mg.version0_6_reconverted"

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 필요 시 특정 도메인으로 제한 가능
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def return_kor_prompt(sentence):
    kor_prompt = f"""You are a Korean linguist master.
Please rewrite the following JOI Lang code into a precise, clear Korean command up to 3 lines.

** Device and Service Range Specification (with Logical Conditions): **
- ✅ First, extract and display the following [Tag Mapping] before generating the final sentence:
  - For each expression like `(#Curtain).curtain_close()` or `all(#Curtain).curtain_close()`, extract:
    - Tag: `#Curtain`
    - Modifier: `all`, `any`, or `none` (if neither is present)

# [Tag Mapping] (must always show this section):
- Tag: `#Curtain`, Modifier: `none` → say: "임의의 커튼"
- Tag: `#Light`, Modifier: `all` → say: "모든 조명"
- Tag: `#Window`, Modifier: `any` → say: "전체 창문 중 하나라도"

- ✅ Use the following mappings for translation:
  - If the code uses `all(...)`: → say “모든 [장치명]”
  - If the code uses `any(...)`: → say “전체 중 하나의 [장치명]”
  - If the code uses just `(#Device)` with no `all` or `any`: → say “임의의 [장치명]”

- ✅ Apply this logic to both **conditions** and **actions**

                                                      
---
                                                      
                                                  
**Make sure to satisfy ALL of the following conditions:**
- ✅ Always **follow the actual execution order** of the code.
- ✅ If the command includes `break`, it **must be translated as a loop termination** (e.g., "반복을 종료한다").
- ✅ Use temporal connectors like:  
  > “먼저 ~하고, 그 다음 ~하면, 이후 ~한다”  
  to clearly express **time and logic flow**.

- ❗ Absolutely **no hallucination**:  
  Only use devices, conditions, or services that are **explicitly present in the JOI code**.
  Do NOT hallucinate or assume anything beyond what's shown in the JOI code. Use only what is explicitly provided.

**Only output the final sentence. Do not output anything else.**
- Do not show [Tag Mapping], labels, comments, or explanation.
- Only print the natural Korean sentence generated from the JOI Lang code below.
**Do not print labels or sections like [Tag Mapping] or [Final Rewritten...].**
[Final Rewritten Natural Korean Command (with correct logic order)]: \n
(✅ Only the **Korean sentence generated below** should be shown to the user.)

---

JOI Lang Code:
{sentence}

Generate the final Korean sentence here.

"""
    
    return kor_prompt

logger = logging.getLogger("uvicorn")

class GenerateJOICodeRequest(BaseModel):
    sentence: str
    model: str
    connected_devices: Dict[str, Any]
    current_time: str
    other_params: Optional[List[Dict[str, Any]]] = None

# 기본 연결된 장치 정보 로드
print("현재 작업 디렉토리:", os.getcwd())
things_path = "./datasets/things.json"
if os.path.isfile(things_path):
    with open(things_path, "r", encoding="utf-8") as f:
        DEFAULT_CONNECTED_DEVICES = json.load(f)
else:
    print(f"파일 {things_path} 이(가) 존재하지 않습니다. 빈 dict를 사용합니다.")
    DEFAULT_CONNECTED_DEVICES = {}
last_connected_devices = {}  # DEFAULT_CONNECTED_DEVICES.copy()
last_result = {}

"""
{
  "sentence": "불을 켜줘",
  "model": "gpt_mg.version0_5",
  "connected_devices": {},
  "current_time": "",
  "other_params": None #{
    'user_id': "noname"
    'user_feedback': ['yes', 'no', 'retry', 'retry', 'retry', ..., 'extra: ~~~~']

}

@app.post("/re_generate_joi_code")
async def re_generate_code(request: GenerateJOICodeRequest):
    global last_connected_devices
...

"""

"""
{
  "sentence": "불을 켜줘",
  "model": "gpt_mg.version0_5",
  "connected_devices": {},
  "current_time": "",
  "other_params": []
}
"""
import importlib

from dotenv import load_dotenv

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY_PROJ_DEMO")  # .env 파일에서 키 가져오기

from openai import OpenAI
client = OpenAI()

# 모델 리스트
AVAILABLE_MODELS = ['CAP_gpt4.1_mini_old', 'JOI_gpt4.1_mini', 'JOI_gpt5_mini']
selected_model_raw = ''

@app.get("/get_model_list")
async def get_model_list():
    """
    Return the list of available model names.
    """
    print("Send model list: ", AVAILABLE_MODELS)
    return {"models": AVAILABLE_MODELS}

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "active", "timestamp": datetime.now().isoformat()}

@app.post("/generate_joi_code")
async def generate_code(request: GenerateJOICodeRequest):
    global last_connected_devices
    global last_result
    # connected_devices가 빈 dict이면 이전 상태 유지
    if request.connected_devices == {}:
        connected_devices = last_connected_devices
    else:
        connected_devices = request.connected_devices
        last_connected_devices = connected_devices  # 상태 갱신

    if isinstance(request.other_params, dict):
        selected_model_raw = request.other_params.get('selected_model', '').strip()
    elif isinstance(request.other_params, list):
        for item in request.other_params:
            if isinstance(item, dict) and 'selected_model' in item:
                selected_model_raw = item['selected_model'].strip()
                break
   
    if selected_model_raw == 'CAP_gpt4.1_mini_old':
        selected_model = 'gpt4.1-mini'
    elif selected_model_raw == 'JOI_gpt4.1_mini':
        selected_model = 'gpt_mg.version0_6'
    else:
        selected_model = 'gpt_mg.version0_7'
        
    print("Request Model Name>> ", request.model)
    if selected_model_raw == 'CAP_gpt4.1_mini_old':
        result = generate_joi_code_cap(
            sentence=request.sentence,
            model=selected_model,  # 모델 이름을 서버에서 고정
            connected_devices=connected_devices,
            current_time=request.current_time,
            other_params=request.other_params,
        )
    elif selected_model_raw == 'JOI_gpt4.1_mini':
        result = generate_joi_code(
            sentence=request.sentence,
            # model=request.model,
            model=selected_model,  # 모델 이름을 서버에서 고정 (MODEL_NAME)에서 사용자로부터 받는걸로 수정
            connected_devices=connected_devices,
            current_time=request.current_time,
            other_params=request.other_params,
        )
    else:
        result = generate_joi_code(
            sentence=request.sentence,
            # model=request.model,
            model=selected_model,  # 모델 이름을 서버에서 고정 (MODEL_NAME)에서 사용자로부터 받는걸로 수정
            connected_devices=connected_devices,
            current_time=request.current_time,
            other_params=request.other_params,
        )
#        model_resources=MODEL_RESOURCES,
    last_result = result #copy.deepcopy(result)
    model_path = f"{MODEL_NAME_KOR}.config_loader"
    config_loader_module = importlib.import_module(model_path)
    load_version_config = getattr(config_loader_module, 'load_version_config')
    config, model_input = load_version_config(return_kor_prompt(result.get('code', ''))) 

    response_kor = client.chat.completions.create(**model_input)
    if response_kor:
        result['log']['translated_sentence'] = response_kor.choices[0].message.content.strip() #content
    else:
        print("No reconverted response, using original sentence.")
        result['log']['translated_sentence'] = request.sentence

    print("Reconverted Version of The Detailed Sentence: \n", result['log']["translated_sentence"])

    #[TODO] log model name parsing
    result['log']['model_name'] = request.model
    return result
    # return {
    #     "current_time": request.current_time,
    #     "code": [
    #         {
    #             "name": "Scenario1",
    #             "cron": "0 9 * * *",
    #             "period": -1,
    #             "code": "(#Light #livingroom).switch_on()"
    #         },
    #         {
    #             "name": "Scenario2",
    #             "cron": "0 9 * * *",
    #             "period": 10000,
    #             "code": "(#Light #livingroom).switch_on()"
    #         }
    #     ],
    #     "log": {
    #         "response_time": "0.321 seconds",
    #         "inference_time": "0.279 seconds",
    #         "translated_sentence": "translated",
    #         "mapped_devices": [
    #             "Light"
    #         ]
    #     }
    # }
import time

def retry_generate():
    start = time.perf_counter()
    logs = {
        "inference_time": "0 seconds",
        "translated_sentence": "",
        "mapped_devices": []       
    }
    print(run.choice_no, " : ", run.all_items)
    if (len(run.all_items)>1 and run.choice_no < len(run.all_items)):
        generated_code= run.all_items[run.choice_no]

        if isinstance(generated_code, str):
            best_code = generated_code#.strip()
        elif isinstance(generated_code, dict):
            best_code = json.dumps(generated_code, ensure_ascii=False)
        else:
            best_code = generated_code
        run.choice_no += 1
    else:
        best_code = "재시도할 코드가 없습니다. 요구사항을 추가하여 시도해주세요."
    end = time.perf_counter()
    logs["response_time"] = f"{end - start:.4f} seconds"
    return {
        "code": 
            best_code
        ,
        "log": logs
    }

@app.post("/re_generate_joi_code")
async def re_generate_code(request: GenerateJOICodeRequest):
    global last_connected_devices
    global last_result
    result = {}
    # connected_devices가 빈 dict이면 이전 상태 유지
    if request.connected_devices == {}:
        connected_devices = last_connected_devices
    else:
        connected_devices = request.connected_devices
        last_connected_devices = connected_devices  # 상태 갱신

        # user_feedback 처리
    print("REQUEST >> ", request.other_params)
    if (len(request.other_params)>=1):
        request.other_params = request.other_params[0]  # 첫 번째 요소만 사용
        user_id = request.other_params.get('user_id')
        if user_id:
            print(f"[User ID] {user_id}의 요청입니다.")
            filename=f"../datasets/usr_rag/sentence_best_code_log_{user_id}.csv"
        else:
            filename=f"../datasets/usr_rag/sentence_best_code_log_server.csv"

    if request.other_params and 'user_feedback' in request.other_params:
        feedback_list = request.other_params['user_feedback'][-1]  # 마지막 피드백만 사용
        try_kor = 0
        for feedback in [feedback_list]:
            if feedback == 'yes':
                # 최종 확정 처리 로직
                current_sentence = request.sentence
                print("[Feedback] 유저가 YES를 선택했습니다. 결과를 확정합니다.")
                save_sentence_and_code(current_sentence, last_result.get('code', ''), filename=filename)
                # 확정 처리 함수 호출 가능 (예: finalize_result())
                return {}
            elif feedback == 'no':
                # 취소 처리 로직
                print("[Feedback] 유저가 NO를 선택했습니다. 결과를 취소합니다.")
                # 취소 처리 함수 호출 가능 (예: cancel_result())
                return {}
            elif feedback == 'retry':
                # 재생성 처리
                print("[Feedback] 유저가 RETRY를 요청했습니다. 재생성을 수행합니다.")
                result = retry_generate()
                try_kor=1

            elif feedback.startswith('extra:'):
                extra_content = feedback.split('extra:')[1].strip()
                print(f"[Feedback] 추가 피드백: {extra_content}")
                run.all_items = {}
                run.choice_no = 0
                # extra 처리 (예: 로그 저장, DB 기록 등)
                current_sentence = request.sentence
                current_sentence += " " + f"\n+ add condition: {extra_content}"
                
                new_dataset = [f"Regenerate the JOI Lang code based on **current sentence** and **the added conditions**.: {current_sentence}"]
                selected_model_raw = request.other_params.get('selected_model', '').strip() if request.other_params else ''
                if selected_model_raw == 'CAP_gpt4.1_mini_old':
                    selected_model = 'gpt4.1-mini'
                elif selected_model_raw == 'JOI_gpt4.1_mini':
                    selected_model = 'gpt_mg.version0_6'
                else:
                    selected_model = 'gpt_mg.version0_7'

                if selected_model_raw == 'CAP_gpt4.1_mini_old':
                    result = generate_joi_code_cap(
                        sentence=request.sentence,
                        model=selected_model,  # 모델 이름을 서버에서 고정
                        connected_devices=connected_devices,
                        current_time=request.current_time,
                        other_params=request.other_params,
                    )
                elif selected_model_raw == 'JOI_gpt4.1_mini':
                    result = generate_joi_code(
                        sentence=request.sentence,
                        # model=request.model,
                        model=selected_model,  # 모델 이름을 서버에서 고정 (MODEL_NAME)에서 사용자로부터 받는걸로 수정
                        connected_devices=connected_devices,
                        current_time=request.current_time,
                        other_params=request.other_params,
                    )
                else:
                    result = generate_joi_code(
                        sentence=request.sentence,
                        # model=request.model,
                        model=selected_model,  # 모델 이름을 서버에서 고정 (MODEL_NAME)에서 사용자로부터 받는걸로 수정
                        connected_devices=connected_devices,
                        current_time=request.current_time,
                        other_params=request.other_params,
                    )
                try_kor+=1
        if try_kor: 
            last_result = result
            model_path = f"{MODEL_NAME_KOR}.config_loader"
            config_loader_module = importlib.import_module(model_path)
            load_version_config = getattr(config_loader_module, 'load_version_config')

            config, model_input = load_version_config(return_kor_prompt(result.get('code', ''))) 
            response_kor = client.chat.completions.create(**model_input)
            if response_kor:
                result['log']['translated_sentence'] = response_kor.choices[0].message.content.strip() #content
            else:
                print("No reconverted response, using original sentence.")
                result['log']['translated_sentence'] = request.sentence

            print("Reconverted Version of The Detailed Sentence: \n", result['log']["translated_sentence"])
    return result

import sys

def joi_retry_module(code_generator_func, sentence, model, 
                     connected_devices: dict = None,
                     current_time: str = None,
                     other_params: dict = None
):
    """
    재시도 모듈을 위한 함수
    """
    try:
        all_items = []
        choice_no=0
        try_no=1
        
        resp = code_generator_func(
            sentence=sentence,
            model=model,
            connected_devices=connected_devices,
            current_time=current_time,
            other_params=other_params #'user_id': "noname"'
        )
        
        generated_code = resp.get("code", "")
        all_items.append(generated_code)
        current_sentence = sentence
        while True:
#            print(f"---\nCandidate #{choice_no+1}: {all_items[choice_no]}")
            ###########################
            ### re-converted sentence
            response_kor = ""
            model_path = f"{MODEL_NAME_KOR}.config_loader"
            config_loader_module = importlib.import_module(model_path)
            load_version_config = getattr(config_loader_module, 'load_version_config')
            config, model_input = load_version_config(return_kor_prompt(all_items[choice_no]))
#'/geners~/{url_id, setnece0}
#'/regenerated/{url_id, sentence0}

            response_kor = client.chat.completions.create(**model_input)
            if response_kor:
                resp['log']['translated_sentence'] = response_kor.choices[0].message.content.strip() #content
            else:
                print("No reconverted response, using original sentence.")
                resp['log']['translated_sentence'] = current_sentence

            print("Reconverted Version of The Detailed Sentence: \n", resp['log']["translated_sentence"])
            ###########################
            answer = input("최종 결과에 만족하는가? (y: 저장 / n: 종료 / 엔터: 다음 / 요구사항: 요구사항 추가) >>> ")#.strip()
            if answer.lower() == 'y':
                save_sentence_and_code(current_sentence, all_items[choice_no])
                break
            elif answer.lower() == 'n':
                print("종료합니다.")
                break 
            elif answer == "":
                # 빈칸 엔터: 다음 후보로 이동
                choice_no += 1
                if choice_no >= len(all_items):
                    choice_no = 0
                    print("후보가 더 이상 없습니다.")
                    #break
            else:
                # 어떤 문자열이든 요구사항으로 누적
                current_sentence += " " + f"\n+ add condition {try_no}: {answer}"
                #new_dataset = [current_sentence]
                if (try_no<3):
                    new_dataset = [f"""You are a JOI Lang expert and time-sensitive logic resolver.

When generating a new JOI Lang code based on user feedback, you must not simply re-output the previous code `{all_items[choice_no]}`.

Instead:

---

# ✅ Rewriting and Integration Rules

## [1] Combine Old and New Conditions
- Integrate **all new feedback** with the original `current_sentence` logically and sequentially.
- Final code must satisfy **all combined intents** and maintain **correct time and action flow**.

## [2] Maintain Relative Time Offsets Between Actions
- If an original action includes delays (e.g., “3 seconds after A, do B”), and a **new action is added after B**, then:
  - You must calculate and preserve the **cumulative delay** from the original event.
  - ❗ Do **not** restart delays from scratch unless the user explicitly says so.

### ✅ Example:
- Original: “If light is off, wait 3 sec → turn off pump, then wait 5 sec → close blind”
- Feedback: “After turning off the pump, wait 5 sec then close the blind”
- Final result: `close blind` happens **8 sec after light turns off**  
  (3 sec for pump + 5 sec additional delay)

## [3] Device Restriction: Only Use Referenced Categories
- When the user says broad terms like “모든 장치” (all devices):
  - You must **not include all known other devices not mentioned** matching the function.
  - Instead, only include:
    - Devices **explicitly mentioned in the input**, OR
    - Devices whose **services were used** in earlier code blocks.
  - ✅ In such cases, use `all(#DeviceType)` for each device:
    - If multiple instances of the device may exist (as with typical IoT deployments), `all(...)` must be used.
    - Do **not** use singular forms like `(#Device)` unless the user specifies a single device instance.

### ✅ Example:
- Input: `"조명을 꺼줘 + 모든 장치 꺼줘"`
- Only `Light` was mentioned → Valid output: `all(#Light).switch_off()`
- ❌ Do NOT auto-include AirConditioner, Fan, Alarm, etc.
- ❌ Do NOT omit `all(...)` when the user says “모든 장치” or “모든 ~”

## [4] Validate Service per Device
- When applying a function (e.g., `switch_on`, `alarm_siren`, etc.) to devices due to commands like "모든 장치를 켜줘":
  - You must **only apply the service to devices that actually support it**, as defined in `[service_list]` or `[connected_devices]`.
  - ❌ Do **NOT** invent or assume a service exists for a device just because it was mentioned.
  - ✅ Check each service-function mapping explicitly.

### ✅ Example:
- Input: `"알람과 사이렌의 알림을 켜줘 + 모든 장치를 켜줘"`
- Valid Services:
  - `#Alarm` → `alarm_siren()`
  - `#Siren` → `sirenMode_setSirenMode("siren")`
- Final code:
    [Invalid code]:
    ```
    all(#Alarm).alarm_siren()
    all(#Siren).sirenMode_setSirenMode("siren")
    ```
    [Not a valid code]:
    ```
    all(#Alarm).switch_on()       
    all(#Siren).switch_on()       
    ```

- ⚠️ If a device does **not support `switch_on()`** or `switch_switch`, but the user says “켜줘”,
→ Then identify the most **appropriate "on" equivalent** function for that device (e.g., `alarm_siren()` for Alarm, `sirenMode_setSirenMode("siren")` for Siren).
→ Do **NOT** fallback to invalid generic functions like `switch_on()` unless they are present in that device's service list.


---


# ✅ General Enforcement
- Keep temporal connectors in Korean output: “먼저 ~하고, 그 다음 ~하면, 이후 ~한다”
- Ensure final JOI Lang code maintains strict **logical and chronological execution**
- Do not hallucinate devices or services. Only use those explicitly present or inferred from services.

---


current_sentence = {current_sentence}

"""]
                else:
                    print("\n ... New algorithm added ... \n")
                    new_dataset = [f"""You are given a natural language command and conditions to apply.

Your task: Combine all of them into **one single, accurate, natural language command**.

Instructions:
- If any device, service, or condition overlaps, always give priority to the **last condition**.
- Do not add anything extra — only combine and rewrite based on the given parts.
- Use **"all"** for **"모든 장치들"**, **"any"** for **"어느 하나라도"**, and use neither if unspecified.
- If the command includes **"turn on everything"**, and there are multiple services, include all of them explicitly.
- If **"status light (경과등)"** is mentioned, make sure **#light** is present in the final output.
- Do not hallucinate any device or service not present in the original sentence or added conditions.
                                    
[Input to combine]
{current_sentence}

---

[Intermediate step — your single combined sentence so far]:
(Write the final command here, as one natural sentence.)


[Final output — just one sentence]:
(Repeat the same sentence here.)


---


[Example]
[Input to combine]
Trigger the alarm and siren of the alert and siren.
+ add condition 1: Also turn on the status light.
+ add condition 2: Turn on everything.
+ add condition 3: All devices.

[Final output — just one sentence]:
Turn on all alerts’ alarms and all sirens for #siren and #light of all devices.

"""

]
                #new_dataset = [f"Regenerate the JOI Lang code based on **current sentence** and **the added conditions**.: {current_sentence}"]
                #print("Feedback Sentence: ", new_dataset[0])
                all_items = []
                choice_no = 0

                resp = code_generator_func(
                    sentence=new_dataset[0],
                    model=model,
                    connected_devices=connected_devices,
                    current_time=current_time,
                    other_params=other_params #'user_id': "noname"'
                )
                generated_code = resp.get("code", "")
                all_items.append(generated_code)

                print(f"요구사항 {try_no} '{answer}'을(를) 반영하여 재시작")
                try_no += 1
        return resp
    except Exception as e:
        print(f"Error during code generation: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2:
        selected_model = args[0]
        mode = args[1]
        if (selected_model == 'cap'):
            selected_model ='gpt4.1-mini'
            print("Running in CAP mode with model...")
            joi_retry_module(generate_joi_code_cap, sentence=mode, model=selected_model)
        elif (selected_model == 'joi'):
            selected_model ='gpt_mg.version0_6'
            print("Running in JOI mode with model...")
            joi_retry_module(generate_joi_code, sentence=mode, model=selected_model)
        else:
            selected_model ='gpt_mg.version0_7'
            print("Running in MG mode with model...")
            joi_retry_module(generate_joi_code, sentence=mode, model=selected_model)

    elif len(args) == 1:
        selected_model ='gpt_mg.version0_6'
        mode = args[0]
        print("Running in MG mode with model...")
        joi_retry_module(generate_joi_code, sentence=mode, model=selected_model)

    else:
        __port__ = 8000
        uvicorn.run("demo:app", host="0.0.0.0", port=__port__, reload=True)    
    #    uvicorn.run("server:app", host="0.0.0.0", port=8000)
    #     print(f"> Local IP address: http://{get_local_ip()}:8000")