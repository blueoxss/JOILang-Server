import json
import os

def load_version_config(user_input, base_path):
    # 1. 모델 구성 정보 로드
    with open(os.path.join(base_path, "model_config.json"), "r", encoding="utf-8") as f:
        config = json.load(f)
    model_input = config["model_input"]  # <- 여기서 딕셔너리 통째로 받아옴

    # 2. knowledge 파일 로드
    with open(os.path.join(base_path, "SoP_Lang_Description.md"), "r") as f: #, encoding="utf-8") as f:
        description = f.read()
    with open(os.path.join(base_path, "Sop_Lang_Example.md"), "r") as f: #, encoding="utf-8") as f:
       examples = f.read()
    with open(os.path.join(base_path, "service_list_ver1.5.2.json"), "r") as f: #, encoding="utf-8") as f:
        service_list = f.read()
    with open(os.path.join(base_path, "grammar_ver1.3.0.md"), "r") as f: #, encoding="utf-8") as f:
        grammar = f.read()
    # 3. 시스템 프롬프트 구성
    system_prompt = f"""
You are a SoPLang programmer. SoPLang is a programming language used to control IoT devices.
Use the following knowledge to convert natural language into valid SoPLang code.

Make sure to follow syntax rules strictly. You should include cron, period and script. Only use allowed keywords:
if, else if, else, >=, <=, ==, !=, not, and, or, wait until, (#clock).delay(ms), MSEC, SEC, MIN, HOUR, DAY

---
[Description]
{description}
---
[Grammar]
{grammar}
---
[Examples]
{examples}
---
[Service List]
{service_list}
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
