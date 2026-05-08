# GPT-4.1-mini Category Failure Analysis

- Condition: `retrieval`
- Model: `gpt41_mini`
- Category runs: `8`
- Total failed rows: `13`

## Category Summary

| Category | Rows | Failures | Avg DET | Pass Rate | Exact Rate | Avg Prompt Tokens | Avg LLM Latency (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 30 | 2 | 97.9030 | 0.9333 | 0.8667 | 18340.23 | 1.8380 |
| 2 | 30 | 0 | 99.3643 | 1.0000 | 0.8667 | 14193.90 | 2.2931 |
| 3 | 30 | 0 | 96.0321 | 1.0000 | 0.3667 | 15493.43 | 2.6777 |
| 4 | 30 | 2 | 93.2633 | 0.9333 | 0.1667 | 15480.57 | 2.4300 |
| 5 | 30 | 0 | 96.5959 | 1.0000 | 0.5333 | 16205.53 | 1.9402 |
| 6 | 30 | 3 | 93.0093 | 0.9000 | 0.2000 | 15787.77 | 2.5570 |
| 7 | 50 | 3 | 93.8887 | 0.9400 | 0.4000 | 16561.34 | 2.1676 |
| 8 | 50 | 3 | 93.3591 | 0.9400 | 0.2400 | 16106.50 | 2.4555 |

## Failure Reason Distribution

- `gt_mismatch`: 13
- `gt_receiver_coverage`: 9
- `gt_service_coverage`: 9
- `extraneous`: 8
- `numeric_grounding`: 6
- `semantic`: 5
- `dataflow`: 2
- `enum_grounding`: 1
- `precondition`: 1

## Failure Case Analysis

### Category 1 · Row 2

- Command (EN): Add 5 minutes to the oven.
- Command (KO): 오븐의 작동 시간을 5분 늘려줘.
- DET: `69.9000`
- Failure reasons: `["gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: Add 5 minutes to the oven.: 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
(#Oven).oven_addmoretime(300)

# Generated
(#Oven).oven_addmoretime(5)
```

### Category 1 · Row 13

- Command (EN): Announce the fine dust level through the speaker.
- Command (KO): 미세먼지 농도를 스피커로 알려줘.
- DET: `69.9000`
- Failure reasons: `["extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: Announce the fine dust level through the speaker.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
dust = (#AirQualitySensor).airqualitysensor_dustlevel

(#Speaker).speaker_speak("미세먼지 농도는 " + dust + "입니다")

# Generated
level = (#WeatherProvider).weatherprovider_pm10weather
(#Speaker).speaker_speak("현재 미세먼지 농도는 " + level + "입니다")
```

### Category 4 · Row 94

- Command (EN): When it rains, turn on the dehumidifier.
- Command (KO): 비가 오면 제습기를 켜줘.
- DET: `69.9000`
- Failure reasons: `["extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: When it rains, turn on the dehumidifier.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
wait until ((#RainSensor).rainsensor_rain == true)

(#Dehumidifier).switch_on()

# Generated
prev := (#RainSensor).rainsensor_rain
curr = (#RainSensor).rainsensor_rain
if (prev == false and curr == true) {
    (#Dehumidifier).dehumidifier_setdehumidifiermode("dehumidifying")
}
prev = curr
```

### Category 4 · Row 118

- Command (EN): When any presence sensor in the hallway detects presence, set all hallway lights to purple.
- Command (KO): 복도에 재실 센서가 하나라도 감지되면 모든 복도 조명을 보라색으로 설정해줘.
- DET: `69.9000`
- Failure reasons: `["extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: When any presence sensor in the hallway detects presence, set all hallway lights to purple.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
wait until (all(#Hallway #PresenceSensor).presencesensor_presence ==| true)

all(#Hallway #Light).colorcontrol_setcolor("128,0,128")

# Generated
prev := all(#Hallway #PresenceSensor).presencesensor_presence
curr = all(#Hallway #PresenceSensor).presencesensor_presence
if (prev == false and curr == true) {
    all(#Hallway #Light).light_movetorgb(128, 0, 128)
}
prev = curr
```

### Category 6 · Row 157

- Command (EN): If the weather is rainy and no one is being detected, lock the door and close the valve.
- Command (KO): 비가 오고 아무도 없는 상태면, 도어락을 잠그고 밸브를 차단해줘.
- DET: `69.9000`
- Failure reasons: `["extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: If the weather is rainy and no one is being detected, lock the door and close the valve.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#WeatherProvider).weatherprovider_weather == "rain" and (#PresenceSensor).presencesensor_presence == false) {

    (#DoorLock).doorlock_lock()

    (#Valve).valve_close()

}

# Generated
if ((#RainSensor).rainsensor_rain == true and (#PresenceSensor).presencesensor_presence == false) {
    (#DoorLock).doorlock_lock()
    (#Valve).valve_close()
}
```

### Category 6 · Row 175

- Command (EN): If the server room temperature is 30 degrees or higher and the AC is off, turn it on and sound the main emergency siren.
- Command (KO): 서버실 온도가 30도 이상이고 에어컨이 꺼져 있으면, 에어컨을 냉방 모드로 켜고 메인 사이렌을 긴급 모드로 울려줘.
- DET: `69.9000`
- Failure reasons: `["enum_grounding", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "precondition"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md, service_prompt_10.md`
- Analysis: If the server room temperature is 30 degrees or higher and the AC is off, turn it on and sound the main emergency siren.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
if ((#ServerRoom #TemperatureSensor).temperaturesensor_temperature >= 30 and (#ServerRoom #AirConditioner).switch_switch == false) {

    (#ServerRoom #AirConditioner).airconditioner_setairconditionermode("cool")

    (#Main #Siren).siren_setsirenmode("emergency")

}

# Generated
wait until ((#ServerRoom #TemperatureSensor).temperaturesensor_temperature >= 30 and (#ServerRoom #Switch).switch_switch == false)
(#ServerRoom #Switch).switch_on()
(#Main #Siren).siren_setsirenmode("emergency")
```

### Category 6 · Row 178

- Command (EN): If the warehouse fine dust level is 100 or higher and the air purifier is in auto mode, switch it to high mode and say through the warehouse speaker "Switching to high mode".
- Command (KO): 창고 미세먼지가 100 이상이고 공기청정기가 자동 모드이면, 모드를 강풍 모드로 바꾸고 창고 스피커로 "강풍 모드로 전환합니다"라고 말해줘.
- DET: `69.9000`
- Failure reasons: `["gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: If the warehouse fine dust level is 100 or higher and the air purifier is in auto mode, switch it to high mode and say through the warehouse speaker "Switching to high mode".: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#Warehouse #AirQualitySensor).airqualitysensor_finedustlevel >= 100 and (#Warehouse #AirPurifier).airpurifier_airpurifiermode == "auto") {

    (#Warehouse #AirPurifier).airpurifier_setairpurifiermode("high")

    (#Warehouse #Speaker).speaker_speak("강풍 모드로 전환합니다")

}

# Generated
if ((#Warehouse #AirQualitySensor).airqualitysensor_dustlevel >= 100 and (#Warehouse #AirPurifier).airpurifier_airpurifiermode == "auto") {
    (#Warehouse #AirPurifier).airpurifier_setairpurifiermode("high")
    (#Warehouse #Speaker).speaker_speak("강풍 모드로 전환합니다")
}
```

### Category 7 · Row 187

- Command (EN): From 10 PM to midnight every 10 minutes, sound the emergency siren.
- Command (KO): 밤10시부터 자정까지 10분마다 긴급 사이렌을 울려줘.
- DET: `58.8013`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: From 10 PM to midnight every 10 minutes, sound the emergency siren.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#Clock).clock_hour == 0) {

    break

}

(#Siren).siren_setsirenmode("emergency")

# Generated
(#Siren).siren_setsirenmode("emergency")
```

### Category 7 · Row 212

- Command (EN): Check all door locks in Sector 1 every hour; if any one is open, change all lights in that sector to red.
- Command (KO): 섹터1의 모든 도어락을 1시간마다 확인해서, 하나라도 열려 있으면 해당 섹터의 모든 조명을 빨간색으로 바꿔줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Check all door locks in Sector 1 every hour; if any one is open, change all lights in that sector to red.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if (all(#Sector1 #DoorLock).doorlock_doorlockstate ==| "open") {

    all(#Sector1 #Light).light_movetorgb(255, 0, 0)

}

# Generated
doorlockStates := [
    (#Sector1 #DoorLock).doorlock_doorlockstate,
    (#Sector1 #DoorLock).doorlock_doorlockstate
]
anyOpen := false
for state in doorlockStates {
    if (state == "open" or state == "opening") {
        anyOpen = true
        break
    }
}
if (anyOpen) {
    all(#Sector1 #Light).light_movetorgb(255, 0, 0)
}
```

### Category 7 · Row 218

- Command (EN): Every hour from midnight to 5 AM, if at least one door is open, turn all hallway lights to 50%.
- Command (KO): 자정부터 오전 5시까지 1시간마다 체크해서 문이 하나라도 열려있으면, 복도의 조명을 모두 50%로 켜줘.
- DET: `69.9000`
- Failure reasons: `["extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: Every hour from midnight to 5 AM, if at least one door is open, turn all hallway lights to 50%.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if (all(#Door).door_doorstate ==| "open") {

    all(#Hallway #Light).levelcontrol_movetolevel(50, 0)

}

# Generated
if ((#Clock).clock_hour == 5) {
    break
}
if (all(#Door).door_doorstate == "open" or all(#Door).door_doorstate == "opening") {
    all(#Hallway #Light).light_movetobrightness(50, 0)
}
```

### Category 8 · Row 247

- Command (EN): When the contact sensor is closed, sound the police siren every 10 seconds.
- Command (KO): 접촉센서가 닫히면 10초마다 경찰 사이렌을 울려줘.
- DET: `69.9000`
- Failure reasons: `["gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: When the contact sensor is closed, sound the police siren every 10 seconds.: 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#ContactSensor).contactsensor_contact == true)

    active = 1

}

(#Siren).siren_setsirenmode("police")

# Generated
prev := (#ContactSensor).contactsensor_contact
curr = (#ContactSensor).contactsensor_contact
if (prev == false and curr == true) {
    active = 1
}
if (active == 1) {
    (#Siren).siren_setsirenmode("police")
    delay(10 SEC)
}
prev = curr
```

### Category 8 · Row 259

- Command (EN): Whenever the button with the 'Light' tag is pressed, set the brightness of all lights with 'Odd' tags to maximum.
- Command (KO): 조명 태그가 붙은 버튼이 눌릴때마다, 홀수 태그가 붙은 모든 조명의 밝기를 최대로 밝혀줘.
- DET: `69.9000`
- Failure reasons: `["extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: Whenever the button with the 'Light' tag is pressed, set the brightness of all lights with 'Odd' tags to maximum.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
prev := (#Light #Button).button_button

curr = (#Light #Button).button_button

if (prev != "pushed" and curr == "pushed") {

    all(#Odd #Light).light_movetobrightness(100, 0)

}

prev = curr

# Generated
prev := (#Light #Button).button_button
curr = (#Light #Button).button_button
if (prev != "pushed" and curr == "pushed") {
    all(#Odd #Light).levelcontrol_movetolevel(100, 0)
}
prev = curr
```

### Category 8 · Row 271

- Command (EN): When motion is detected in the lobby, capture an image of the lobby every 30 seconds.
- Command (KO): 로비에서 움직임이 감지되면 30초마다 로비 사진을 찍어줘.
- DET: `69.9000`
- Failure reasons: `["gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `tempo_prompt_9.md, grammar_ver1.5.10.md, caution_prompt_8.md, response_prompt_baseline_cot.md`
- Analysis: When motion is detected in the lobby, capture an image of the lobby every 30 seconds.: 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#Lobby #MotionSensor).motionsensor_motion == true)

    active = 1

}

(#Lobby #Camera).camera_captureimage()

# Generated
prev := (#Lobby #MotionSensor).motionsensor_motion
curr = (#Lobby #MotionSensor).motionsensor_motion
if (prev == false and curr == true) {
    (#Lobby #Camera).camera_captureimage()
}
prev = curr
```
