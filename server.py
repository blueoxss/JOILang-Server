# ✅ server.py: 디바이스 WebSocket 연결, 메시지 브로드캐스트 및 웹서비스 실행 포함
# 마이크 활용 필수 : 도메인 없으므로, https 설정을 위해 self-signed openssl 인증서 발급
# openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes
# openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes 

# key.pem: 비밀 키
# cert.pem: 인증서
#Country Name (2 letter code)	KR
#State or Province Name	Seoul
#Locality Name	Seoul
#Organization Name	SeoulNationalUniversity
#Organizational Unit Name	AI 또는 빈칸
#Common Name (FQDN or IP)	147.46.114.205 ← 꼭 서버 외부 IP 입력!
#Email Address	빈칸 또는 example@snu.ac.kr


from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import json

# 서버 실행 시 자동으로 실행
from contextlib import asynccontextmanager
from gpt_mg.run import get_script_gpt 
import inspect

from difflib import SequenceMatcher
import socket
import requests
import time

MAX_CONNECTIONS = 10  # 최대 연결 수 제한
# TIMEOUT_SECONDS: 120 #디바이스 리턴 에러는 3분으로 여유있게 모델 자체가 1분이 넘기면 error 관련 메시지 보냄
TIMEOUT_SECONDS = 120
PING_INTERVAL = 60  # 10초마다 ping 테스트
# 전역 변수로 서버 디바이스 ID 저장
server_device_id = None

# 전역 변수로 첫 번째 응답 처리 여부를 저장
first_response_processed = False

def get_external_ip():
    try:
        return requests.get('https://api.ipify.org').text
    except Exception:
        return 'Unavailable'

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return 'Unavailable'
    
#limiter = Limiter(key_func=get_remote_address)

# WebSocket 연결된 디바이스 저장: device_id -> WebSocket
connected_devices: dict[str, WebSocket] = {}
device_response_done: dict[str, bool] = {}

# 디바이스 응답 저장
device_responses: dict[str, str] = {}
device_request_times: dict[str, float] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global server_device_id
    server_device_id = None  # 서버 시작 시 초기화
    asyncio.create_task(cleanup_disconnected_devices())  # 기존 startup 이벤트 실행
    yield  # 서버 실행 유지
    
#app = FastAPI()
app = FastAPI(lifespan=lifespan)

# CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/devices")
async def get_devices():
    return {"devices": list(connected_devices.keys())}

def get_connected_device_list():
    return list(connected_devices.keys())

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()

@app.get("/api/device_responses")
async def get_device_responses():
    now = time.time()
    result = {}
    for device_id in connected_devices:
        if device_response_done.get(device_id):
            response_data = device_responses.get(device_id, {"status": "✅ Completed"})
            # server_device_id인 경우 "Server"로 설정
            response_data["device_name"] = "Server" if device_id == server_device_id else response_data.get("device_name", device_id)
            result[device_id] = response_data
        elif device_id in device_responses:
            response_data = device_responses[device_id]
            response_data["device_name"] = "Server" if device_id == server_device_id else response_data.get("device_name", device_id)
            result[device_id] = response_data
        elif device_id in device_request_times and now - device_request_times[device_id] > TIMEOUT_SECONDS:
            result[device_id] = {
                "error": "⏰ Timeout: No response in 2 minutes",
                "device_name": "Server" if device_id == server_device_id else device_id
            }
        else:
            result[device_id] = {
                "status": "⏳ Waiting for response...",
                "device_name": "Server" if device_id == server_device_id else device_id
            }
    return JSONResponse(content=result)

async def track_completion(device_ids: list[str]):
    start_time = time.time()
    while True:
        if all(
            device_response_done.get(d) or
            (d in device_request_times and time.time() - device_request_times[d] > TIMEOUT_SECONDS)
            for d in device_ids
        ):
            print("✅ All device responses handled or timed out.")
            break
        if time.time() - start_time > TIMEOUT_SECONDS + 10:
            print("⚠️ Force stop: Monitoring timeout.")
            break
        await asyncio.sleep(1)

@app.post("/api/sentence_to_scenario") #@limiter.limit("10/minute")  # 1분에 최대 10번 요청 가능
async def sentence_to_scenario(request: Request):
    data = await request.json()
    sentence = data.get("sentence")
    device_ids = data.get("device_ids", get_connected_device_list())
    now = time.time()
    print(f"\nDevice list :: {device_ids}\n")
    print(f"Message to send: {sentence}")
    for device_id in device_ids:
        device_request_times[device_id] = now
        device_responses.pop(device_id, None)  # 이전 응답 삭제 권장
        device_response_done[device_id] = False
    asyncio.create_task(track_completion(device_ids))
    await broadcast_message(sentence, device_ids)

    return{"status": "sent", "to": device_ids}

@app.websocket("/ws/device/{device_id}")
async def device_endpoint(websocket: WebSocket, device_id: str):
    global server_device_id, first_response_processed

    if len(connected_devices) >= MAX_CONNECTIONS:
        await websocket.close()
        print(f"🚫 Connection rejected: {device_id} (Too many connections)")
        return
    
    await websocket.accept()
    connected_devices[device_id] = websocket
    
    if server_device_id is None:
        server_device_id = device_id
        print(f"✅ Server device set to: {device_id}")
    else:
        print(f"✅ Device connected: {device_id}")

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=120)
                
                # ping 응답은 여기서 처리하고 바로 다음 반복으로
                if data == "ping":
                    await websocket.send_text("pong")  # ping에 대한 응답
                    continue
                
                # 실제 데이터 처리
                print(f"📩 Response from {device_id}: {data}")
                try:
                    json_data = json.loads(data)

                    # pong 응답 처리 추가
                    if json_data.get("type") == "pong":
                        # device_name 정보 업데이트
                        if "device_name" in json_data:
                            device_responses[device_id] = {
                                "device_name": json_data["device_name"],
                                "status": "✅ Connected"
                            }
                        continue
                    # 기존 메시지 처리
                    else:
                        device_responses[device_id] = json_data
                        device_response_done[device_id] = True
                        
                        if (device_id != server_device_id and 
                            not first_response_processed and 
                            'best_code' in json_data):
                            first_response_processed = True
                            reverse_input = f"{json_data['best_code']} SOPLang 코드를 다시 역으로 사람이 말하는 한글 명령어로 가급적 한 문장으로 만들어줘."
                            reversed_result = await get_script_gpt_async(reverse_input, model='version0_3')
                            if isinstance(reversed_result, dict) and 'best_code' in reversed_result:
                                json_data['reconverted'] = reversed_result['best_code']
                except json.JSONDecodeError:
                    device_responses[device_id] = {"best_code": data}
            except WebSocketDisconnect:
                print(f"👋 Device {device_id} disconnected normally")
                break
    except Exception as e:
        print(f"⚠️ Unexpected error for device {device_id}: {str(e)}")
    finally:
        if device_id in connected_devices:
            connected_devices.pop(device_id)
            print(f"❌ Device {device_id} removed from connected devices")

async def broadcast_message(message: str, device_ids: list[str]):
    print(f"📡 Attempting to send message to: {device_ids}")
    send_tasks = []
    for device_id in device_ids:
        ws = connected_devices.get(device_id)
        if ws:
            print(f"✅ Sending to {device_id}")
            #await ws.send_text(message)  # 메시지 전송
            send_tasks.append(ws.send_text(message))  # 메시지 전송 태스크 추가
        else:
            print(f"❌ Device {device_id} not found in connected_devices")

    if send_tasks:
        await asyncio.gather(*send_tasks)  # 모든 디바이스에 동시에 메시지 전송
        print(f"➡️ Message sent to devices: {device_ids}")
    else:
        print("⚠️ No active devices to send message.")


async def cleanup_disconnected_devices():
    #끊어진 WebSocket을 리스트에서 제거
    while True:
        await asyncio.sleep(5)  # 5초마다 체크
        to_remove = []
        for device_id, ws in connected_devices.items():
            try: #기존: #webSocket이 실제로 연결되어 있는지 확인  if ws.client_state.name == "CLOSED" or ws.client_state.name == "DISCONNECTED":
                # ping을 보내서 연결 상태 확인
                if device_id != server_device_id:
                    await ws.send_text("ping")
            except Exception:
                # ping 실패 시 연결이 끊긴 것으로 간주
                to_remove.append(device_id)
        for device_id in to_remove:
            print(f"Cleaning up disconnected device: {device_id}")
            connected_devices.pop(device_id, None)

@app.post("/api/similarity")
async def compute_similarity(payload: dict = Body(...)):
    sentence1 = payload.get("sentence1", "").strip()
    sentence2 = payload.get("sentence2", "").strip()

    if not sentence1 or not sentence2:
        return JSONResponse(status_code=400, content={"error": "Both sentences must be filled."})

    # 간단한 문자열 유사도 계산 (difflib 이용)
    similarity_ratio = SequenceMatcher(None, sentence1.lower(), sentence2.lower()).ratio()
    similarity_percent = round(similarity_ratio * 100, 2)

    return {"similarity": similarity_percent}

async def get_script_gpt_async(prompt: str, model='version0_3'):
    result = get_script_gpt(prompt, model)
    result['device_name'] = 'Server'

    if inspect.iscoroutine(result):
        return await result
    return result


if __name__ == "__main__":
    print(f"> Local IP address: http://{get_local_ip()}:8000")
    print(f"> External IP address: http://{get_external_ip()}:10004")
    #uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)    
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
#    uvicorn.run("server:app", host="0.0.0.0", port=8000, 
#                ssl_keyfile="./key.pem", ssl_certfile="./cert.pem")  # 프로덕션에

