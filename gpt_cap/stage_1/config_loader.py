import json
import os

def load_version_config(user_input, base_path):
    # 1. 모델 구성 정보 로드
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),base_path)

    with open(os.path.join(base_path, "model_config.json"), "r", encoding="utf-8") as f:
        config = json.load(f)
    model_input = config["model_input"]  # <- 여기서 딕셔너리 통째로 받아옴
    
    # 2. knowledge 파일 로드
    # with open(os.path.join(base_path, "SoP_Lang_Description.md"), "r") as f: #, encoding="utf-8") as f:
    #     description = f.read()
    with open(os.path.join(base_path, "short_service_list_ver1.5.3.json"), "r") as f: #, encoding="utf-8") as f:
        service_list = f.read()
    # with open(os.path.join(base_path, "grammar_ver1.5.1.md"), "r") as f: #, encoding="utf-8") as f:
    #     grammar = f.read()
    # with open(os.path.join(base_path, "Sop_Lang_Example.md"), "r") as f: #, encoding="utf-8") as f:
    #    examples = f.read()
    # 3. 시스템 프롬프트 구성
    system_prompt = f"""
You are tasked with converting input commands into IoT script code. To do this, you must identify the correct device and service by referring to the descriptions in the service list.
Only return the device and the corresponding function or value in service_list file.
---
[Example] 
input: "관개 장치의 급수량을 5리터로 설정해줘"
Return: 
"#Irrigator_irrigatorPortion_setWaterPortion & #Irrigator_irrigatorPortion_waterPortion"

input: "사료 공급기의 상태가 급식 중이면 알람의 사이렌을 울려줘"
Return:
"#Feeder_feederPortion_setFeedPortion & #Feeder_feederPortion_feedPortion"

input: "비가 감지되면 말해줘"
Return:
"#WeatherProvider_weatherProvider_weather & #Speaker_mediaPlayback_speak"
Description:
Only WeatherProvider_weather serivce can detect rain.
 
input: "커튼이 닫혀있고 블라인드가 열려 있으며 움직임이 감지되면 조명을 끄고 사이렌을 울려줘"
Return:
"#Curtain_curtain_curtain & #Blind_blind_blind & #MotionSensor_motionSensor_motion & #Light_switch_off & #Alarm.alarm_siren

input: "창문이 열려 있고 조명이 꺼져 있으며 커튼이 닫혀 있으면 조명을 켜고 커튼을 열어 줘"
Return:
"#Window_windowControl_window, #Light_switch_switch, #Curtain_curtain_curtain, #Light_switch_on, #Curtain_curtain_open
Description:
In this case, it's important to clearly separate conditions from actions.
"조명이 꺼져있으면" is a condition, so you should use switch_switch to get the value.
On the other hand, "조명을 꺼" is an action, so you should use the switch_off function.

input: "관개장치를 작동시켜"
Return: 
"#Irrigator_switch_on"
Description:
Distinguish between 관개장치 and 급수기. Use switch_on for "관수기를 작동" or "관개장치를 켜".

input: "이메일을 "test@example.com" 주소로 ~"
Return:
"#EmailProvider_emailProvider_sendMail"

input: "급수기를 작동해줘"
Return:
"#Irrigator_irrigatorOperatingState_startWatering"
Description:
Use it for "급수기를 작동" or "급수기를 시작"

input: "버튼3이 눌렸으면 알람의 사이렌을 울려줘"
Return:
"Buttonx4_buttonx4_button3 & Buttonx4_buttonx4_button1 & #Alarm_alarm_siren"
Description:
If there is an index behind button, use Buttonx4 to choose index.
In this case, buttonx4_button1 is always needed.
If not, just use Button.

input: "경광등을 켜줘"
Return:
"#Siren_sirenMode_setSirenmode & #Alarm_alarm_strobe"
Desciption:
Use strobe for "경광등"

input: "에어컨이 꺼져있고 온도가 30도 이상이면"
Return:
"#AirConditioner_switch_switch & #TemperatureSensor_temperatureMeasurement_temperature"
Description:
에어컨의 목표 온도라고 명시하지 않으면, 온도는 다 TemperatureSensor를 써라.

input: "TV의 음소거 상태를 음소거로 설정해줘."
Return:
"#Television_audioMute_setMute"
Description:
굳이 상태를 설정하라고 하면 setMute를 써.

input: "습도가 70% 이상이면"
Return: 
"#HumiditySensor_relativeHumidityMeasurement_humidity"

input: "사이렌을 울려줘"
Return:
"#Alarm_alarm_siren"

input: "사이렌과 경광등을 동시에 끄고 켜줘."
Return:
"#Alarm_alarm_both & #Siren_sirenMode_setSirenMode & #Alarm_alarm_off"

input: "문이 열려있으면"
Return:
"#DoorLock_doorControl_door"
Description:
Only DoorLock is related to door.

input: "10초마다 알람과 사이렌을 껐다 켰다 반복해줘"
Return:
"#Alarm_alarm_siren & #Siren_switch_on & #Siren_switch_off & #Alarm_alarm_off & #Alarm_alarm_siren"
Description:
Use switch_toggle for "토글해줘" and "깜빡여줘".

input: "블라인드를 10퍼센트씩 닫아줘.
Return:
"#Blind_blindLevel_setBlindLevel & #Blind_blindLevel_blindLevel
Description:
For set functions such as setBlindLevel and setVolume, bring the value service that checks current value together.

input: "커튼이 3번 열렸다 닫히면 조명을 꺼줘"
Return:
"#Curtain_curtain_curtain & #Light_switch_off"
Description:
Most items used in condition statements should be value attributes, not functions.

input: "재실 센서가 감지 상태이면 블라인드를 닫아줘. 또한 실시간으로 확인하여 알람의 사이렌이 울리고 있지 않다면 즉시 알람의 사이렌을 울려."
Return:
"#PresenceSensor_presenceSensor_presence & #Blind_blind_close & #Alarm_alarm_alarm & #Alarm_alarm_siren

input: "문이 처음 열릴 때 환풍기를 켜고, 이후 3초마다 습도를 확인해서 70% 이하가 될 때까지 환풍기를 켜고 끄는 동작을 반복해 줘."
Return:
"#DoorLock_doorControl_door & #Fan_switch_on & #HumiditySensor_relativeHumidityMeasurement_humidity & #Fan_switch_toggle 

input: "창문이 닫혔을 때부터 5초마다 블라인드를 열었다 닫았다 반복해줘"
Return:
"#Window_windowControl_window & #Blind_blind_open & #Blind_blind_close & #Blind_blind_blind
Description:
If you have to alternate between 2 options, add state checking service (blind_blind) to check currenct state.

input: "실시간으로 확인해서 관개장치가 꺼졌다 켜진 횟수가 3번이면 불을 켜줘"
Return:
"#Irrigator_switch_switch & #Light_switch_on
Description:
If you need to check how many the binary option changed, return state value to compare previous and current states.

input: "15초동안 감지해줘"
Return:
"#Clock_clock_timestamp"
Description:
If there is a duration, use clock_timestamp.

input: "날 우울하게 만드는 뉴스를 감지하면 위로의 말을 해", "스마트폰 배터리가 20% 이하가 되면 커튼을 닫아 줘."
Return:
"#Speaker_mediaPlayback_speak"
Description:
If there are no available devices to use or you are aksed for something you cannot determine, return speaker to say error messages.
---
If the user asks for a value to be report or check, always use the Speaker device to deliver the response.
[Error] If there is not a requested service in service files, return nothing. 
---
[Service List]
{service_list}

Always strictly follow the knowledge files. Do not invent new services or syntax. Only valid Joi must be generated.
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
            # print("user_input:: ", user_input)
        else:
            content = ""  # fallback 처리

        final_messages.append({
            "role": role,
            "content": content
        })


    # 5. messages 교체
    model_input["messages"] = final_messages

    return config, model_input
