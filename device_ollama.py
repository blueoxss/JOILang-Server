# ✅ device.py: 서버 WebSocket에 연결되어 LLM 실행 결과를 전송하는 디바이스 역할
import asyncio
import sys
import uuid
import websockets
from pipeline.run import pipeline_with_logs  # 기존 run.py의 로직 사용

import os
import json
from datetime import datetime
TIMEOUT_SECONDS = 60  # 5분 제한

#os.environ['GOOGLE_TRANSLATE_KEY'] = "AIzaSyBOIwWE_ZaUl4R8Yhl4XQW7uBvbVQRFNr0"
#nohup ollama serve & ollama create soplang

async def run_device(server_url):
    device_id = f"device-{uuid.uuid4().hex[:6]}"
    print("This Device ID :: ")
    ws_url = server_url.replace("http", "ws").rstrip("/") + f"/ws/device/{device_id}"
    print(f"🔌 Connecting to {ws_url} as {device_id}...")

    async with websockets.connect(ws_url) as websocket:
        print("✅ Connected. Waiting for tasks...")
        while True:
            try:
                message = await websocket.recv()
                if message == "ping":
                    await websocket.send("pong")  # ✅ ping에 대한 응답 추가
                    continue  # ping은 처리 안 하고 넘어감
                
                print(f"📥 Received task: {message}")

                # LLM 실행을 비동기적으로 실행 (블로킹 방지)
                task = asyncio.create_task(
                    asyncio.to_thread(pipeline_with_logs, message)
                )
                try:
                    result = await asyncio.wait_for(task, timeout=TIMEOUT_SECONDS)
                    result = result.get("fixed_code", "")  # ✅ 값이 없으면 "" 빈 문자열 설정
                except asyncio.TimeoutError:
                    result = "timeout"
                    print(f"⏳ Task timed out after {TIMEOUT_SECONDS} seconds.")
                except Exception as e:
                    result = f"error: {e}"  # ✅ 에러 발생 시 메시지 전달
                    print(f"⚠️ Error during processing: {e}")

                await websocket.send(result if result else "")  # ✅ 빈 값이라도 보내기
                print(f"📤 Sent result:\n{result}\n")
                
            except websockets.ConnectionClosed:
                print("❌ Disconnected from server.")
                await asyncio.sleep(5)  # 재연결을 위한 대기 후 루프 계속
                break
            except Exception as e:
                print(f"⚠️ Error during processing: {e}")
def load_test_sentences(file_path: str):
    dataset = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # 주석이거나 빈 줄은 무시
            if not line or line.startswith("#"):
                continue

            # 문자열로 감싸진 문장만 추출
            if line.startswith('"') and line.endswith('",'):
                sentence = line[1:-2]  # 맨 앞/뒤 따옴표와 콤마 제거
                dataset.append(sentence)
            elif line.startswith('"') and line.endswith('"'):
                sentence = line[1:-1]  # 따옴표만 제거
                dataset.append(sentence)

    return dataset
def run_test():
    testset_path = "datasets/testset_ver0.1.txt"
    results = []
    total_response_time = 0.0
    total_inference_time = 0.0

    # 테스트셋 읽기
    sentences = load_test_sentences(testset_path)

    for sentence in sentences:
        print(f"테스트 중: {sentence}")
        logs = pipeline_with_logs(sentence)

        # 결과 추출
        response_time = float(logs["reponse_time"].replace(" seconds", ""))
        inference_time = float(logs["inference_time"].replace(" seconds", ""))
        total_response_time += response_time
        total_inference_time += inference_time

        results.append({
            "sentence": sentence,
            "response_time": round(response_time, 4),
            "inference_time": round(inference_time, 4),
            "translated_sentence": logs["translated_sentence"],
            "mapped_devices": logs["mapped_devices"],
            "code": logs["code"],
            "fixed_code": logs["fixed_code"]
        })

    avg_response_time = total_response_time / len(results)

    model_config = {
        "model_name": "ollama8b_ver0.1",
        "device_id": "a6000",
        "model_version": "0.1",
        "model_description": "This version is designed for basic IoT control using SoPLang language. It includes strict syntax rules and core services.",
        "model_create": "2025-03-15",
        "author": {
            "first_name": "Mingi",
            "last_name": "Jeong"
        },
        "model_input": {
            "model": "ollama"
        },
        "test_result": {
            "testset": testset_path,
            "last_tested": datetime.now().strftime("%Y-%m-%d"),
            "avg_response_time": round(avg_response_time, 4),
            "results": results
        }
    }

    # 저장
    os.makedirs("pipeline", exist_ok=True)
    with open("pipeline/model_config.json", "w", encoding="utf-8") as f:
        json.dump(model_config, f, indent=2, ensure_ascii=False)

    print("테스트 완료 및 model_config.json 저장 완료")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Test Mode")
        run_test()
    else:
        arg = sys.argv[1]
        if arg == "test":
            print("Test Mode")
            run_test()
        else:
            server_url = sys.argv[1]  # example: http://147.46.114.205:17774/, http://147.46.114.253:8000/
            print("Connecting to ... ", server_url)
            asyncio.run(run_device(server_url))
