# ✅ device.py: 서버 WebSocket에 연결되어 LLM 실행 결과를 전송하는 디바이스 역할
import asyncio
import sys
import uuid
import websockets
import json
import ssl
import os

from gpt_mg.run import get_script_gpt
from gpt_mg.GPTBenchmark import GPTBenchmark
import time
ssl_context = ssl._create_unverified_context()
TIMEOUT_SECONDS = 120  # 2분 제한

def load_test_sentences(file_path: str):
    dataset = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith('"') and line.endswith('",'):
                sentence = line[1:-2]
                dataset.append(sentence)
            elif line.startswith('"') and line.endswith('"'):
                sentence = line[1:-1]
                dataset.append(sentence)
    return dataset

def generate_device_name():
    return "device-cloud-chatgpt_ver0.1"

""" #수동으로 보내는 ping/pong
async def keepalive_ping(websocket):
    while True:
        try:
            await asyncio.sleep(30)
            pong_waiter = await websocket.ping()
            await asyncio.wait_for(pong_waiter, timeout=10)
        except Exception as e:
            print("💥 Ping failed, closing socket:", e)
            #ping 실패해도 종료하지 않음
            #await websocket.close()
            #break
"""

async def run_device(server_url, model='version0_3'):
    print(f"Running device with server address: {server_url}")
    print("Connecting to ... ", server_url)

    device_id = f"device-{uuid.uuid4().hex[:6]}"
    device_name = generate_device_name()  # 디바이스 이름 생성

    print("This Device ID :: ", device_id)
    print("This Device Name :: ", device_name)

    if server_url.startswith("https"):
        ws_url = server_url.replace("https", "wss")
    else:
        ws_url = server_url.replace("http", "ws")
    ws_url = ws_url.rstrip("/") + f"/ws/device/{device_id}"
    print(f"🔌 Connecting to {ws_url} as {device_id}...")
    reconnect_delay = 5  # 초기 선언 위치 이동
    max_reconnect_delay = 30
    while True:
        try:
            async with websockets.connect(ws_url) as websocket: #ssl=ssl_context) arg deleted
            #ping_interval=30,  # 30초마다 ping 전송
            #ping_timeout=60    # 10초 동안 pong 응답이 없으면 끊음
                                          
                #ping_task = asyncio.create_task(keepalive_ping(websocket))
                print("✅ Connected. Waiting for tasks...")
                reconnect_delay = 5  # 연결 성공 시 재연결 대기 시간 초기화

                #while True:
                try:
                    #message = await asyncio.wait_for(websocket.recv(), timeout=TIMEOUT_SECONDS)
                    #디바이스는 서버 메시지를 무제한으로 기다림
                    message = await websocket.recv()
                    if message == "ping":
                        pong_data = {
                            "type": "pong",
                            "device_id": device_id,
                            "device_name": device_name
                        }
                        await websocket.send(json.dumps(pong_data))
                        continue
                
                    else:
                        print(f"📥 Received task: {message}")

                        print("1:: Before running get_script_gpt")
                        start_time = time.perf_counter()
                        result = get_script_gpt(message, model)
                        duration = time.perf_counter() - start_time

                        print(f"2:: After running get_script_gpt ({duration:.2f} sec):\n", result)

                        if isinstance(result, dict):
                            result["device_name"] = device_name
                            json_result = json.dumps(result)
                            await websocket.send(json_result)
                            print(f"3:: 📤 Sent result: {json_result}")
                        else:
                            print("⚠️ Invalid result format from get_script_gpt")
                            error_response = {
                                "error": "Invalid result format",
                                "device_name": device_name
                            }
                            await websocket.send(json.dumps({"error": "Invalid result format"}))
                except Exception as e:
                    print(f"⚠️ Unexpected error for device {device_id}: {str(e)}")
                    #ping_task.cancel()
                    break
                    #print(f"⚠️ Error processing message: {e}")
                    #await websocket.send(json.dumps({"error": str(e)}))
                """#디바이스는 서버 메시지를 무제한으로 기다림
                except asyncio.TimeoutError:
                    print("⏳ Timeout waiting for message.")
                    continue  # 타임아웃 시 다음 메시지 대기
                except websockets.ConnectionClosed as e:
                    print(f"❌ Connection closed by server: {e.code} - {e.reason}")
                    break  # 연결 종료 시 재연결
                    except Exception as e:
                """
        except Exception as e:
            print(f"⚠️ Connection error: {e}. Retrying in {reconnect_delay} seconds...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)  # 지수 백오프

def run_test():
    print("Running test mode")
    testset_path = "./datasets/testset_ver0.1.txt"

    dataset = load_test_sentences(testset_path)
    base_dir = "./gpt_mg"
    paths = []
    for name in os.listdir(base_dir):
        tmp_path = os.path.join(base_dir, name)
        if os.path.isdir(tmp_path):
            config_path = os.path.join(tmp_path, "model_config.json")
            if os.path.isfile(config_path):
                paths.append(tmp_path)

    for model_path in paths:
        print("Model:: ", model_path)
        benchmark = GPTBenchmark(model_path, testset_name=os.path.basename(testset_path))
        for sentence in dataset:
            benchmark.run(sentence)
        for sentence in dataset:
            benchmark.run_stream(sentence)
        benchmark.finalize_results()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        arg = sys.argv[1]
        if arg == "test":
            run_test()
        else:
            asyncio.run(run_device(arg))
    else:
        default_url = "http://147.46.219.127:10004/"
        print(f"Connect default url >> {default_url}")
        asyncio.run(run_device(default_url))
