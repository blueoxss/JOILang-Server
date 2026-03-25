import json
import os
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
            all_categories.add(category)

        tags = device_info.get('tags', [])
        cnt_others_tags.update(tag for tag in tags if tag != category)

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
            all_categories.add(category)

        tags = device_info.get('tags', [])
        cnt_others_tags.update(tag for tag in tags if tag != category)

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
    #print(os.path.dirname(os.path.abspath(__file__)))
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),base_path)

    with open(os.path.join(base_path, "model_config.json"), "r", encoding="utf-8") as f:
        config = json.load(f)
    model_input = config["model_input"]  # <- 여기서 딕셔너리 통째로 받아옴
    
    # 2. knowledge 파일 로드

    with open(os.path.join(base_path, "grammar_ver1.5.10.md"), "r") as f: #, encoding="utf-8") as f:
        grammar = f.read()
    with open(os.path.join(base_path, "service_prompt_10.md"), "r") as f: #, encoding="utf-8") as f:
        service_prompt = f.read()
    with open(os.path.join(base_path, "service_list_ver1.5.4_value_converted.json"), "r") as f: #, encoding="utf-8") as f:
        service_list_value = json.load(f)
    with open(os.path.join(base_path, "service_list_ver1.5.4_function_converted.json"), "r") as f: #, encoding="utf-8") as f:
        service_list_function = json.load(f)
    with open(os.path.join(base_path, "tempo_prompt_9.md"), "r") as f: #, encoding="utf-8") as f:
        tempo = f.read()
    with open(os.path.join(base_path, "caution_prompt_8.md"), "r") as f: #, encoding="utf-8") as f:
        caution = f.read()

    category_tags_str, cnt_others_tag, service_list = parse_selected_device_simple(connected_devices)
    if category_tags_str:
        connected_devices = f"\n\n---\n[connected_devices]\n {category_tags_str}"
    else:
        connected_devices = ""

    if other_params:
        other_params = json.dumps(other_params, separators=(",", ":"), ensure_ascii=False) #indent=2, 
        other_params = f"\n\n---\n[userinfo]\n {other_params}"
        other_params = other_params.replace('\\"', '"').replace('\\n', '').replace('    ', '').replace('   ', '').strip()
    else:
        other_params = ""

    with open(os.path.join(base_path, "response_prompt_6.md"), "r") as f: #, encoding="utf-8") as f:
        responsestep = f.read()
    # 3. 시스템 프롬프트 구성
    system_prompt = f"""
You are a JOILang programmer. JOILang is a programming language used to control IoT devices.
Use the following knowledge to convert natural language into valid JOILang code.

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
{connected_devices}
{other_params}

---
{responsestep}
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
    #with open(os.path.join(base_path, "merged_system_prompt.md"), "w", encoding="utf-8") as f:
    #    f.write(system_prompt)

    return config, model_input
