from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
import os
import time
#from gpt_mg.version0_1.config_loader import load_version_config
from version_code_to_command.config_loader import load_version_config

from dotenv import load_dotenv

load_dotenv()
# 하드코딩 대신 환경 변수에서 가져옵니다.
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY_SVC")

client = OpenAI()

def get_script_gpt(sentence, version_path):
    # 1. 메시지 구성
    start = time.perf_counter()
    config, model_input = load_version_config(sentence, version_path)
    logs={}

    # 2. 모델 호출
    response = client.chat.completions.create(**model_input)
    """
    client.chat.completions.create(
        model=model_input["model"],
        messages=messages,
        temperature=model_input.get("temperature", 0.3)
    )
    """
    # 3. 서버 전송을 위한 매핑
    best_code = response.choices[0].message.content.strip() #content
    logs["translated_sentence"] = ""
    logs["mapped_devices"] = ""
    logs["best_code"] = best_code
    
    end = time.perf_counter()
    logs["response_time"] = f"{end - start:.4f} seconds"

    print("Response Time: ", logs["response_time"])
    print("Created Code: \n", best_code)
    print("====")
    return logs


if __name__ == '__main__':
    df = pd.read_csv('translated_file.csv')
    df.reset_index(drop=True, inplace=True) 
    df['Command_O'] = ""

    for i, data in enumerate(df['Script']):
        command_O = get_script_gpt(data, 'version_code_to_command')
        df.loc[i, 'Command_O'] = command_O['best_code'] 

    df.to_csv('translated_file_Command_O.csv', index=False, encoding='utf-8-sig')

            