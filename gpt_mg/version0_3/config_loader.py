import json
import os

def load_version_config(user_input, base_path):
    # 1. 모델 구성 정보 로드
    print(os.path.dirname(os.path.abspath(__file__)))
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),base_path)

    with open(os.path.join(base_path, "model_config.json"), "r", encoding="utf-8") as f:
        config = json.load(f)
    model_input = config["model_input"]  # <- 여기서 딕셔너리 통째로 받아옴
    
    # 2. knowledge 파일 로드
    with open(os.path.join(base_path, "SoP_Lang_Description.md"), "r") as f: #, encoding="utf-8") as f:
        description = f.read()
    with open(os.path.join(base_path, "service_list_ver1.5.3.json"), "r") as f: #, encoding="utf-8") as f:
        service_list = f.read()
    with open(os.path.join(base_path, "grammar_ver1.5.1.md"), "r") as f: #, encoding="utf-8") as f:
        grammar = f.read()
    #with open(os.path.join(base_path, "Sop_Lang_Example.md"), "r") as f: #, encoding="utf-8") as f:
    #    examples = f.read()
    # 3. 시스템 프롬프트 구성
    system_prompt = f"""
You are a SoPLang programmer. SoPLang is a programming language used to control IoT devices.
Use the following knowledge to convert natural language into valid SoPLang code.

Make sure to follow syntax rules strictly. Only use allowed keywords:
if, else if, else, >=, <=, ==, !=, not, and, or, wait until, (#clock).delay() 
The delay function (#clock).delay() only accepts values in milliseconds (ms).
Do not use while or any unlisted constructs.

1. If the scenario is single-use (no cyclic behavior, no periodic checks), set cron = "".
   Example: wait until(sensor() < threshold); ...
2. If cyclic repetition is required (regular schedule or periodic check), use cron with valid expression.
3. For loops within a scenario, use period (ms). If wait until or delay cannot be used, use default period = 100.

---
[Description]
{description}
---
[Grammar]
{grammar}
---
[Service List]
{service_list}

Always strictly follow the knowledge files. Do not invent new services or syntax. Only valid SoPLang must be generated.
"""
    # 4. messages 가공: content_from을 기준으로 content 채움
    final_messages = []
    for msg in model_input["messages"]:
        role = msg["role"]
        content_key = msg.get("content")

        if content_key == "system_prompt":
            content = system_prompt
        elif content_key == "sentence":
            content = user_input
            print("user_input:: ", user_input)
        else:
            content = ""  # fallback 처리

        final_messages.append({
            "role": role,
            "content": content
        })


    # 5. messages 교체
    model_input["messages"] = final_messages

    return config, model_input
