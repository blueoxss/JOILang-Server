import requests
import json
import pandas as pd

def google_translate(command, api_key = "AIzaSyBEGa9Y0Y9MeBs83fQjYuvAeGukQAfK3ak"):
    # print("translate")
    url = "https://translation.googleapis.com/language/translate/v2"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "q": command,
        "target": "ko",
        "format": "text"
    }
    params = {
        "key": api_key
    }
    # print(data)
    response = requests.post(url, headers=headers, params=params, data=json.dumps(data))
    # print("response")
    if response.status_code == 200:
        # print(response)

        translation = response.json()["data"]["translations"][0]["translatedText"]
        # print(translation)
        return translation
    else:
        print("Exception")
        raise Exception(f"Error: {response.status_code}, {response.text}")
    
# CSV 파일 불러오기
df = pd.read_csv('scenario_updated.csv')  

# English 열 번역 후 new_korean 열에 저장
df['new_korean'] = df['English'].apply(google_translate)
print(df['new_korean'])
# 결과를 저장 (선택 사항)
df.to_csv('translated_file.csv', index=False, encoding='utf-8-sig')

