import json
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from pprint import pprint
from fastapi import FastAPI
from pydantic import BaseModel

from run import generate_joi_code  

app = FastAPI()

class GenerateJOICodeRequest(BaseModel):
    sentence: str
    model: str
    connected_devices: Dict[str, Any]
    current_time: str
    other_params: Optional[List[Dict[str, Any]]] = None

@app.post("/Joi")
def generate(request: GenerateJOICodeRequest):
    result = generate_joi_code(
        sentence=request.sentence,
        model=request.model,
        connected_devices=request.connected_devices,
        current_time=request.current_time,
        other_params=request.other_params
    )
    return result

# === 로컬 디바이스 실행 ===
def run_device_local(sentence: str, model, \
                      cd, now="", options={}):
    result = generate_joi_code(
        sentence=sentence,
        model=model,
        connected_devices=cd,
        current_time=now,
        other_params=options
    )
    print("✅ Final Result")
    print(result["code"])

if __name__ == "__main__":
    sentence = input("Input: ")
    model = "gpt4.1-mini"
    # with open("current_device_list.txt", "r", encoding="utf-8") as f:
        # cd = json.load(f)
    cd = None
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_device_local(sentence, model, cd, now)
