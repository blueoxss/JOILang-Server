from dotenv import load_dotenv
from openai import OpenAI
import os
import sys
import time
import importlib

client = OpenAI(
    api_key="AIzaSyAmC3AAdu7o7mL0c8bXWBp2KAOc4tKq-NI",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#os.environ["OPENAI_API_KEY"] = "AIzaSyAmC3AAdu7o7mL0c8bXWBp2KAOc4tKq-NI"

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#from gpt_mg.version0_1.config_loader import load_version_config
from gemini_mg.version0_1.config_loader import load_version_config

#client = OpenAI()

def get_script_gemini(sentence, version_path='version0_1'): #[TODO] 경로 입력받도록 수정
    # 1. 메시지 구성
    start = time.perf_counter()
    #from version0_1.config_loader import load_version_config
    config_loader_module = importlib.import_module(f"gemini_mg.{version_path}.config_loader")
    load_version_config = getattr(config_loader_module, 'load_version_config')
    path_tmp = '.'#os.path.join("gpt_mg",version_path,"config_loader")
    config, model_input = load_version_config(sentence, path_tmp)
    logs={}

    # 2. 모델 호출
    response = client.chat.completions.create(**model_input)
    print(response.choices[0].message)

    # 3. 서버 전송을 위한 매핑
    logs["device_name"] = config["device_name"]
    best_code = response.choices[0].message.content.strip() #content
    logs["translated_sentence"] = ""
    logs["mapped_devices"] = ""
    logs["best_code"] = best_code
    
    end = time.perf_counter()
    logs["response_time"] = f"{end - start:.4f} seconds"
    logs["prompt_tokens"] = response.usage.prompt_tokens
    logs["completion_tokens"] = getattr(response.usage, "completion_tokens", "")
    logs["total_tokens"] = response.usage.total_tokens

    print(best_code)
    print("Prompt tokens:", logs["prompt_tokens"])
    print(f"Completion tokens: {logs["completion_tokens"]}")
    print("Total tokens:", logs["total_tokens"])

    # STS 부분 추가 (서버에서 별도 분리 관리)
    """
    response_kor = ""
    #config, model_input = load_version_config(f"{best_code}를 다시 한글 명령어로 바꿔줘.", path_tmp)
    #response_kor = client.chat.completions.create(**model_input)
    if response_kor:
        logs["reconverted"] = response_kor.choices[0].message.content.strip() #content
    else:
        logs["reconverted"] = sentence

    print("Response Time: ", logs["response_time"])
    print("Created Code: \n", best_code)
    print("====")
    """
    return logs

if __name__ == '__main__':
    args = sys.argv[1:]
    dataset = ['1시간마다 TV mute 토글해줘',
    '화요일 목요일 금요일 오후 2시에 눈이오면 에어컨을 heat 모드로 틀어줘']
    if len(args) == 2:
        selected_model = args[0]
        dataset = [args[1]]
        paths = [selected_model]
    elif len(args) == 1:
        selected_model = args[0]
        paths = [selected_model]
    else:
        base_dir = "."
        paths = []
        for name in os.listdir(base_dir):
            tmp_path = os.path.join(base_dir, name)
            if os.path.isdir(tmp_path):
                config_path = os.path.join(tmp_path, "model_config.json")
                if os.path.isfile(config_path):
                    paths.append(name)

    # 실행
    for data in dataset:
        for model in paths:
            print("\n", model)
            get_script_gemini(data, model)
