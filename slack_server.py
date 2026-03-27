import os
import json
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Slack 전용 공식 라이브러리
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# 1. 환경 변수 로드 (.env 파일)
load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    print("❌ 에러: .env 파일에 SLACK_BOT_TOKEN 또는 SLACK_APP_TOKEN이 없습니다.")
    exit(1)

# 2. Slack 앱 초기화
app = App(token=SLACK_BOT_TOKEN)
ADMIN_LOG_DIR = Path("admin_logs/slack")

def ensure_admin_log_dir() -> None:
    ADMIN_LOG_DIR.mkdir(parents=True, exist_ok=True)

def append_slack_dm_log(event: dict) -> dict:
    ensure_admin_log_dir()
    now_utc = datetime.now(timezone.utc)
    date_key = now_utc.strftime("%Y-%m-%d")
    log_file = ADMIN_LOG_DIR / f"{date_key}.jsonl"

    slack_user_id = event.get("user", "unknown")
    
    # Slack API를 통해 유저의 실제 이름 가져오기
    user_name = "unknown"
    real_name = "unknown"
    try:
        if slack_user_id != "unknown":
            user_info = app.client.users_info(user=slack_user_id)
            user_name = user_info["user"].get("name", "unknown")
            real_name = user_info["user"].get("profile", {}).get("real_name", "unknown")
    except Exception as e:
        print(f"⚠️ 유저 정보 조회 실패: {e}")

    record = {
        "saved_at_utc": now_utc.isoformat(),
        "event_ts": event.get("ts"),
        "channel": event.get("channel"),
        "slack_user_id": slack_user_id,
        "slack_user_name": user_name,
        "slack_real_name": real_name,
        "text": event.get("text", ""),
        "raw_event": event,
    }

    # 파일에 JSONL 형식으로 한 줄씩 추가
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"✅ [저장 완료] {real_name}({user_name}): {record['text']}")
    return record

# 3. 메시지 이벤트 리스너 (DM 수신 시 자동 실행)
# 3. 메시지 이벤트 리스너 (DM 수신 시 자동 실행)
@app.event("message")
def handle_message_events(body, logger, say, client):
    event = body.get("event", {})
    
    # 봇이 보낸 메시지는 무시하고, 사용자가 보낸 DM(im) 채널인 경우만 처리
    if event.get("channel_type") == "im" and not event.get("bot_id"):
        print(f"📩 새로운 DM 수신: {event.get('text')}")
        
        # 1. 메시지를 파일에 저장 (아까 만든 함수)
        record = append_slack_dm_log(event)
        
        # 2. [Reaction] 사용자가 보낸 메시지에 ✅ 이모지 달아주기
        try:
            client.reactions_add(
                channel=event["channel"],
                timestamp=event["ts"],
                name="white_check_mark"  # V표시 이모지 (원하는 이모지 이름으로 변경 가능)
            )
        except Exception as e:
            print(f"⚠️ 이모지 리액션 실패 (권한 확인 필요): {e}")

        # 3. [Reply] 사용자 이름(Real Name)을 불러와서 친절하게 답장해주기
        user_name = record.get("slack_real_name", "사용자")
        say(
            text=f"확인했습니다, {user_name}님! 서버에 안전하게 기록해 두었습니다.",
            # thread_ts=event["ts"]  # 만약 스레드(답글)로 남기고 싶다면 이 주석을 해제하세요!
        )

if __name__ == "__main__":
    print("🚀 Slack Socket Mode 전용 서버를 시작합니다...")
    # Socket Mode 핸들러 시작 (이 코드가 실행되면 서버가 꺼지지 않고 계속 대기합니다)
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()