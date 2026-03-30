import copy
import json
import os
import sys
from datetime import datetime

try:
    from version0_12.qwen_local_backend import ensure_version012_backend_installed
except ImportError:
    from gpt_mg.version0_12.qwen_local_backend import ensure_version012_backend_installed


def _default_local_python() -> str:
    env_python = (
        os.getenv("JOI_VERSION012_PYTHON", "").strip()
        or os.getenv("JOI_VERSION013_PYTHON", "").strip()
    )
    if env_python:
        return env_python
    return sys.executable or "python"


def _default_local_worker() -> str:
    env_worker = (
        os.getenv("JOI_VERSION012_WORKER", "").strip()
        or os.getenv("JOI_VERSION013_WORKER", "").strip()
    )
    if env_worker:
        return env_worker
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "qwen_local_worker.py")


def parse_selected_device(connected_devices: dict, s_l: dict):
    if not connected_devices:
        return None, [], {}

    all_categories = set()
    cnt_others_tags = set()

    """
    if isinstance(connected_devices, str):
        try:
            connected_devices = json.loads(connected_devices.replace("'", '"'))
        except:
            return None, [], {}
    """
    for device_info in connected_devices.values():
        category = device_info.get('category')
        if category:
            if isinstance(category, list):
                all_categories.update(category)
            else:
                all_categories.add(category)

        tags = device_info.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        cat_set = set(category) if isinstance(category, list) else {category} if category else set()
        cnt_others_tags.update(tag for tag in tags if tag not in cat_set)

    # ✅ 문자열 리스트 형태로 결합: "[#Light, #Alarm, #Fan]"
    category_tags_str = "[" + ", ".join(f"#{cat}" for cat in sorted(all_categories)) + "]"

    # 선택된 장치 서비스
    selected_devices = {}
    for cat in all_categories:
        if cat in s_l:
            selected_devices[cat] = s_l[cat]

    return category_tags_str, list(cnt_others_tags), selected_devices

def parse_selected_device_simple(connected_devices: dict):
    if not connected_devices:
        return None, [], {}

    all_categories = set()
    cnt_others_tags = set()

    """
    if isinstance(connected_devices, str):
        try:
            connected_devices = json.loads(connected_devices.replace("'", '"'))
        except:
            return None, [], {}
    """
    for device_info in connected_devices.values():
        category = device_info.get('category')
        if category:
            if isinstance(category, list):
                all_categories.update(category)
            else:
                all_categories.add(category)

        tags = device_info.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        cat_set = set(category) if isinstance(category, list) else {category} if category else set()
        cnt_others_tags.update(tag for tag in tags if tag not in cat_set)

    # ✅ 문자열 리스트 형태로 결합: "[#Light, #Alarm, #Fan]"
    category_tags_str = "[" + ", ".join(f"#{cat}" for cat in sorted(all_categories)) + "]"

    # 선택된 장치 서비스
    """
    selected_devices = {}
    for cat in all_categories:
        if cat in s_l:
            selected_devices[cat] = s_l[cat]
    """
    return category_tags_str, list(cnt_others_tags), all_categories


def load_version_config(user_input, connected_devices: dict=None, other_params: dict=None, base_path: str="."):
    # 1. 모델 구성 정보 로드
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), base_path)
    ensure_version012_backend_installed()

    with open(os.path.join(base_path, "model_config.json"), "r", encoding="utf-8") as f:
        config = json.load(f)
    model_input = copy.deepcopy(config["model_input"])
    model_input["local_python"] = _default_local_python()
    model_input["local_worker"] = _default_local_worker()

    # 2. knowledge 파일 로드

    with open(os.path.join(base_path, "grammar_ver1.5.10.md"), "r", encoding="utf-8") as f:
        grammar = f.read()
    with open(os.path.join(base_path, "service_prompt_10.md"), "r", encoding="utf-8") as f:
        service_prompt = f.read()
    with open(os.path.join(base_path, "service_list_ver2.0.1_value.json"), "r", encoding="utf-8") as f:
        service_list_value = json.load(f)
    with open(os.path.join(base_path, "service_list_ver2.0.1_function.json"), "r", encoding="utf-8") as f:
        service_list_function = json.load(f)
    with open(os.path.join(base_path, "tempo_prompt_9.md"), "r", encoding="utf-8") as f:
        tempo = f.read()
    with open(os.path.join(base_path, "caution_prompt_8.md"), "r", encoding="utf-8") as f:
        caution = f.read()

    category_tags_str, _cnt_others_tag, _service_list = parse_selected_device_simple(connected_devices)
    if category_tags_str:
        connected_devices_str = f"\n\n---\n[connected_devices]\n {category_tags_str}"
    else:
        connected_devices_str = ""

    if other_params:
        other_params_str = json.dumps(other_params, separators=(",", ":"), ensure_ascii=False)
        other_params_str = f"\n\n---\n[userinfo]\n {other_params_str}"
        other_params_str = (
            other_params_str
            .replace('\\"', '"')
            .replace('\\n', '')
            .replace('    ', '')
            .replace('   ', '')
            .strip()
        )
    else:
        other_params_str = ""

    with open(os.path.join(base_path, "response_prompt_baseline_cot.md"), "r", encoding="utf-8") as f:
        responsestep = f.read()

    reasoning_contract = """
---
[Baseline-CoT Internal Reasoning Contract]
This version corresponds to the `gen_baseline_cot` profile.

Before writing the final answer, reason step by step internally using this hidden checklist:
[REASONING]
INTENT: <one sentence>
DEVICES_AND_SERVICES:
- <device/service candidates>
TIMING:
- <cron/period implications or none>
CONDITIONS:
- <if / wait until logic or none>
STATE:
- <persistent vars, flags, reset rules, or none>
PLAN:
- <ordered JOILang construction plan>
[/REASONING]

Output rules:
- Keep the reasoning completely hidden.
- Return ONLY one final JOILang JSON object.
- Do not print markdown fences, analysis, bullet lists, or explanations.
- The final JSON must be directly parseable by Python json.loads().
"""

    # 3. 시스템 프롬프트 구성
    system_prompt = f"""
You are a JOILang programmer. JOILang is a programming language used to control IoT devices.
Use the following knowledge to convert natural language into valid JOILang code.
This prompt uses a baseline-CoT style workflow, but the chain-of-thought must stay private.

Make sure to follow syntax rules strictly. Only use allowed keywords:
if, else if, else, >=, <=, ==, !=, not, and, or, wait until, (#Clock).clock_delay() 
The delay function (#Clock).clock_delay() only accepts values in milliseconds (ms).
Do not use while or any unlisted constructs. 
**Never use `while` in code**
[Incorrect Example]
while (blinkCount < 10)

---

[Device and Service Mapping]
IMPORTANT: You MUST extract **all device tags mentioned as subjects or objects in the input sentence**, including those connected by conjunctions such as "and" or "with".  
For each extracted device tag, retrieve **all associated services** (both value and function names) exactly as defined in the [Service List].  
**Do not omit any device or service even if their names overlap or repeat.**  
If multiple devices share similar service names (e.g., "alarm" function on both Alarm and Siren devices), include the services for each device separately and comprehensively.  
CRITICAL FOR v2.0.1: the schema stores `device` and `service` separately, but the final JOI code must use the composed identifier `{{device}}_{{service}}` for both values and functions.
Examples:
- device=`Television`, service=`SetChannel` -> `(#Television).Television_SetChannel(30)`
- device=`Television`, service=`Channel` -> `(#Television).Television_Channel`
- device=`Speaker`, service=`Speak` -> `(#Speaker).Speaker_Speak("hello")`
Never output only the bare service name such as `SetChannel(30)` or `Channel`.
{service_prompt}
[service_list_value]
{service_list_value}
[service_list_function]
{service_list_function}

---
[Grammar]
{grammar}


---
[Condition Combination Rules]
{tempo}


---
[Important Cautions]
{caution}
{connected_devices_str}
{other_params_str}

---
{responsestep}
{reasoning_contract}
- **Never use `while` in code**

--- JOILang Code Output Format Guide ---
Every scenario generated will follow this structure:
```json
{{
  "name": "<명령의 의도를 한국어로 **축약하여**, 띄어쓰기 없이 간결한 형태로 작성하세요. 너무 길게 쓰지 말고, 조합된 단어로 의미만 담아내세요.>",
  "cron": "<Time-based trigger to start execution>",
  "period": <Execution interval in milliseconds or -1>,
  "code": "<Main logic block written in JOILang>"
}}
```

"""
    #  "name": "<A brief and intuitive name describing the command in korean>",

    # 4. messages 가공: content_from을 기준으로 content 채움
    final_messages = []
    for msg in model_input["messages"]:
        role = msg["role"]
        content_key = msg.get("content")

        if content_key == "system_prompt":
            content = system_prompt
        elif content_key == "sentence":
            content = user_input
        else:
            content = ""  # fallback 처리
        final_messages.append({
            "role": role,
            "content": content
        })


    # 5. messages 교체
    model_input["messages"] = final_messages

    today_str = datetime.now().strftime("%y%m%d")

    with open(os.path.join(base_path, f"merged_system_prompt_{today_str}.md"), "w", encoding="utf-8") as f:
        f.write(system_prompt)

    return config, model_input
