# GPT-4.1-mini Category Failure Analysis

- Condition: `retrieval`
- Model: `gpt41_mini`
- Category runs: `8`
- Total failed rows: `174`

## Category Summary

| Category | Rows | Failures | Avg DET | Pass Rate | Exact Rate | Avg Prompt Tokens | Avg LLM Latency (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 30 | 6 | 92.7365 | 0.8000 | 0.5000 | 20353.43 | 3.3622 |
| 2 | 30 | 3 | 88.8629 | 0.9000 | 0.0000 | 17117.70 | 2.2413 |
| 3 | 30 | 19 | 78.8333 | 0.3667 | 0.2667 | 18701.20 | 2.8143 |
| 4 | 30 | 23 | 75.2193 | 0.2333 | 0.2333 | 18511.93 | 2.7559 |
| 5 | 30 | 26 | 70.2005 | 0.1333 | 0.0000 | 18683.73 | 3.1247 |
| 6 | 30 | 29 | 69.3754 | 0.0333 | 0.0333 | 18958.03 | 3.9703 |
| 7 | 50 | 28 | 74.3361 | 0.4400 | 0.0400 | 19194.32 | 3.0429 |
| 8 | 50 | 40 | 73.0330 | 0.2000 | 0.0600 | 18916.40 | 3.2445 |

## Failure Reason Distribution

- `gt_mismatch`: 173
- `dataflow`: 136
- `numeric_grounding`: 83
- `semantic`: 79
- `gt_receiver_coverage`: 78
- `extraneous`: 71
- `gt_service_coverage`: 69
- `arg_type`: 44
- `service_match`: 20
- `precondition`: 18
- `enum_grounding`: 17
- `unknown_service:temperaturemeasurement_temperature`: 13
- `unknown_service:mediaplayback_speak`: 3
- `unknown_service:blind_open`: 2
- `unknown_service:sirenmode_setsirenmode`: 2
- `unknown_service:blind_blind`: 1
- `invalid_json`: 1
- `unknown_service:multibutton_button2`: 1

## Failure Case Analysis

### Category 1 · Row 3

- Command (EN): Start the rice cooker on cooking mode for 30 minutes.
- Command (KO): 밥솥을 조리 모드로 30분 작동시켜.
- DET: `69.9000`
- Failure reasons: `["arg_type", "enum_grounding", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Start the rice cooker on cooking mode for 30 minutes.: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
(#RiceCooker).ricecooker_setcookingparameters("cooking", 1800)

# Generated
(#RiceCooker).ricecooker_setcookingparameters("cooking" | 30)
```

### Category 1 · Row 8

- Command (EN): Announce the temperature through the speaker.
- Command (KO): 현재 온도를 스피커로 알려줘.
- DET: `63.1183`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "service_match", "unknown_service:temperaturemeasurement_temperature"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md`
- Analysis: Announce the temperature through the speaker.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
temp = (#TemperatureSensor).temperaturesensor_temperature

(#Speaker).speaker_speak("현재 온도는 " + temp + "도입니다")

# Generated
temp = (#TemperatureSensor).temperaturemeasurement_temperature
(#Speaker).speaker_speak(temp)
```

### Category 1 · Row 13

- Command (EN): Announce the fine dust level through the speaker.
- Command (KO): 미세먼지 농도를 스피커로 알려줘.
- DET: `69.9000`
- Failure reasons: `["gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: Announce the fine dust level through the speaker.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
dust = (#AirQualitySensor).airqualitysensor_dustlevel

(#Speaker).speaker_speak("미세먼지 농도는 " + dust + "입니다")

# Generated
fineDust = (#AirQualitySensor).airqualitysensor_finedustlevel
(#Speaker).speaker_speak(fineDust)
```

### Category 1 · Row 14

- Command (EN): Announce the outdoor fine dust level using the speaker.
- Command (KO): 외부 미세먼지 농도를 스피커로 알려줘.
- DET: `69.9000`
- Failure reasons: `["extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: Announce the outdoor fine dust level using the speaker.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
dust = (#WeatherProvider).weatherprovider_pm10weather

(#Speaker).speaker_speak("외부 미세먼지 농도는 " + dust + "입니다")

# Generated
pm25 = (#WeatherProvider).weatherprovider_pm25weather
(#Speaker).speaker_speak(pm25)
```

### Category 1 · Row 18

- Command (EN): Tell me the lunch menu for Building 301 today through the speaker.
- Command (KO): 오늘의 301동 점심 메뉴를 스피커로 알려줘.
- DET: `69.9000`
- Failure reasons: `["gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: Tell me the lunch menu for Building 301 today through the speaker.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
menu = (#MenuProvider).menuprovider_getmenu("오늘 301동식당 점심")

(#Speaker).speaker_speak("오늘의 메뉴는 " + menu + "입니다")

# Generated
menu = (#MenuProvider).menuprovider_todaymenu
(#Speaker).speaker_speak(menu)
```

### Category 1 · Row 20

- Command (EN): Set the hue of the light to 200 and the saturation to 50.
- Command (KO): 조명의 색조를 200, 채도는 50으로 설정해줘.
- DET: `61.3545`
- Failure reasons: `["gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: Set the hue of the light to 200 and the saturation to 50.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
(#Light).light_movetohueandsaturation(200, 50)

# Generated
(#Light).light_movetohue(200)
(#Light).light_movetosaturation(50)
```

### Category 2 · Row 31

- Command (EN): Set the living room light to yellow.
- Command (KO): 거실 조명을 노란색으로 설정해줘.
- DET: `55.9387`
- Failure reasons: `["arg_type", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, response_prompt_baseline_cot.md`
- Analysis: Set the living room light to yellow.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다

```joi
# GT
(#LivingRoom #Light).colorcontrol_setcolor("255|255|0")

# Generated
(#Light #livingroom).light_movetorgb(255 | 255 | 0)
```

### Category 2 · Row 46

- Command (EN): Close all windows in the living room.
- Command (KO): 거실에 있는 창문을 모두 닫아줘.
- DET: `69.9000`
- Failure reasons: `["gt_mismatch", "gt_receiver_coverage"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: Close all windows in the living room.: GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
all(#LivingRoom #Window).windowcovering_downorclose()

# Generated
(#WindowCovering #living_room).windowcovering_downorclose()
```

### Category 2 · Row 53

- Command (EN): In Group 1, change all upper-level lights to blue.
- Command (KO): 그룹1에서 상단부에 있는 조명들을 모두 파란색으로 변경해줘.
- DET: `46.5833`
- Failure reasons: `["extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "precondition", "semantic"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, response_prompt_baseline_cot.md`
- Analysis: In Group 1, change all upper-level lights to blue.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다

```joi
# GT
all(#Group1 #Top #Light).light_movetorgb(0, 0, 255)

# Generated
all(#Light #Group1 #Upper).colorcontrol_setcolor("0|0|255")
```

### Category 3 · Row 62

- Command (EN): Stop charging if the voltage is 220V or higher.
- Command (KO): 충전 전압이 220볼트 이상이면, 충전을 멈춰줘.
- DET: `61.2484`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Stop charging if the voltage is 220V or higher.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#Charger).charger_voltage >= 220000) {

    (#Charger).switch_off()

}

# Generated
if ((#Charger).charger_voltage >= 220.0) {
  (#Charger).safe_lock()
}
```

### Category 3 · Row 63

- Command (EN): If the cloud service is activated, upload test.png file to the cloud.
- Command (KO): 클라우드 서비스가 활성화되어있으면, test.png 파일을 클라우드에 업로드해줘.
- DET: `69.9000`
- Failure reasons: `["gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: If the cloud service is activated, upload test.png file to the cloud.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#CloudServiceProvider).cloudserviceprovider_isavailable == true) {

    (#CloudServiceProvider).cloudserviceprovider_uploadfile("test.png")

}

# Generated
if ((#CloudServiceProvider).cloudserviceprovider_chatsession != "") {
  (#CloudServiceProvider).cloudserviceprovider_uploadfile("test.png")
}
```

### Category 3 · Row 64

- Command (EN): If the oven is in grill mode, add 4 more minutes.
- Command (KO): 오븐이 그릴 모드이면, 시간을 4분 더 추가해줘
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: If the oven is in grill mode, add 4 more minutes.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#Oven).oven_ovenmode == "grill") {

    (#Oven).oven_addmoretime(240)

}

# Generated
if ((#Oven).oven_ovenmode == "grill") {
  (#Oven).oven_addmoretime(4)
}
```

### Category 3 · Row 74

- Command (EN): If the button is in the pushed state, raise the blind.
- Command (KO): 버튼이 눌려진 상태면, 블라인드를 올려줘.
- DET: `59.2874`
- Failure reasons: `["arg_type", "dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic", "service_match", "unknown_service:blind_open"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md`
- Analysis: If the button is in the pushed state, raise the blind.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다

```joi
# GT
if ((#Button).button_button == "pushed") {

    (#Blind).windowcovering_uporopen()

}

# Generated
if ((#Button).button_button == "pushed") {
  (#Blind).blind_open()
}
```

### Category 3 · Row 76

- Command (EN): If face recognition at the entrance is off, start it.
- Command (KO): 입구의 얼굴 인식이 꺼져있으면, 얼굴 인식을 시작해줘
- DET: `63.5886`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "precondition", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If face recognition at the entrance is off, start it.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#Entrance #FaceRecognizer).switch_switch == false) {

    (#Entrance #FaceRecognizer).facerecognizer_start()

}

# Generated
if ((#FaceRecognizer).facerecognizer_recognizedresult == "off") {
  (#FaceRecognizer).facerecognizer_start()
}
```

### Category 3 · Row 77

- Command (EN): If the shade is closed to 30% or less, close it to 50%.
- Command (KO): 쉐이드가 30%이하로 닫혀있으면, 50%만큼 닫아줘.
- DET: `61.8872`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the shade is closed to 30% or less, close it to 50%.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#Shade).armrobot_currentposition <= 30) {

    (#Shade).windowcovering_setlevel(50)

}

# Generated
if ((#WindowCovering).windowcovering_windowcoveringtype == "shade" and (#WindowCovering).windowcovering_currentposition <= 30) {
  (#WindowCovering).windowcovering_setlevel(50)
}
```

### Category 3 · Row 78

- Command (EN): If the sound sensor level in livingroom is over 50, stop the speaker.
- Command (KO): 거실의 소리 센서로 감지한 수치가 50보다 크면, 스피커 재생을 멈춰줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the sound sensor level in livingroom is over 50, stop the speaker.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#LivingRoom #SoundSensor).soundsensor_sound > 50) {

    (#LivingRoom #Speaker).speaker_stop()

}

# Generated
if ((#SoundSensor #livingroom).soundsensor_sound > 50) {
  (#Speaker #livingroom).speaker_stop()
}
```

### Category 3 · Row 79

- Command (EN): If the air conditioner is in cool mode, switch it to auto mode.
- Command (KO): 거실의 에어컨 모드가 냉방 모드이면, 자동 모드로 바꿔줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the air conditioner is in cool mode, switch it to auto mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#LivingRoom #AirConditioner).airconditioner_airconditionermode == "cool") {

    (#LivingRoom #AirConditioner).airconditioner_setairconditionermode("auto")

}

# Generated
if ((#AirConditioner).airconditioner_airconditionermode == "cool") {
  (#AirConditioner).airconditioner_setairconditionermode("auto")
}
```

### Category 3 · Row 80

- Command (EN): If any presence sensor in the house is currently in the detected state, set the siren to emergency mode.
- Command (KO): 집에 있는 재실 센서중 하나라도 감지 상태이면, 긴급 사이렌을 울려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If any presence sensor in the house is currently in the detected state, set the siren to emergency mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if (all(#House #PresenceSensor).presencesensor_presence ==| true) {

    (#Siren).siren_setsirenmode("emergency")

}

# Generated
if (any(#PresenceSensor).presencesensor_presence == true) {
  (#Siren).siren_setsirenmode("emergency")
}
```

### Category 3 · Row 81

- Command (EN): If the contact sensor at the entrance is in detected state, sound the emergency siren.
- Command (KO): 입구의 접촉 센서가 감지 상태이면, 긴급 사이렌을 울려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the contact sensor at the entrance is in detected state, sound the emergency siren.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#Entrance #ContactSensor).contactsensor_contact == true) {

    (#Siren).siren_setsirenmode("emergency")

}

# Generated
if ((#ContactSensor).contactsensor_contact == true) {
  (#Siren).siren_setsirenmode("emergency")
}
```

### Category 3 · Row 82

- Command (EN): If it is raining, set all dehumidifiers in the house to drying mode.
- Command (KO): 지금 비가 오고 있으면, 집안의 모든 제습기를 건조 모드로 설정해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If it is raining, set all dehumidifiers in the house to drying mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#RainSensor).rainsensor_rain == true) {

    all(#House #Dehumidifier).dehumidifier_setdehumidifiermode("drying")

}

# Generated
if ((#RainSensor).rainsensor_rain == true) {
  (#Dehumidifier).dehumidifier_setdehumidifiermode("drying")
}
```

### Category 3 · Row 83

- Command (EN): If the livingroom brightness is 200 lux or higher, turn off the livingroom light.
- Command (KO): 거실 조도가 200 럭스 이상이면, 거실 불을 꺼줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "precondition"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the livingroom brightness is 200 lux or higher, turn off the livingroom light.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#LivingRoom #LightSensor).lightsensor_brightness >= 200) {

    (#LivingRoom #Light).switch_off()

}

# Generated
if ((#LightSensor #livingroom).lightsensor_brightness >= 200) {
  (#Light #livingroom).switch_off()
}
```

### Category 3 · Row 84

- Command (EN): If the temperature is 36.5 degrees or higher, set the target temperature to 30.
- Command (KO): 구역1의 온도가 36.5도 이상이면, 에어컨을 30도로 설정해줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: If the temperature is 36.5 degrees or higher, set the target temperature to 30.: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#Sector1 #TemperatureSensor).temperaturesensor_temperature >= 36.5) {

    (#Sector1 #AirConditioner).airconditioner_settargettemperature(30)

}

# Generated
if ((#TemperatureSensor).temperaturesensor_temperature >= 36.5) {
  targetTemp = 30.0
  (#AirConditioner).airconditioner_settargettemperature(targetTemp)
}
```

### Category 3 · Row 85

- Command (EN): If the carbon dioxide concentration in the farm is 800ppm or higher, sound the emergency siren.
- Command (KO): 농장의 이산화탄소 농도가 800ppm 이상이면, 긴급 사이렌을 울려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the carbon dioxide concentration in the farm is 800ppm or higher, sound the emergency siren.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#Farm #AirQualitySensor).airqualitysensor_carbondioxide >= 800) {

    (#Siren).siren_setsirenmode("emergency")

}

# Generated
if ((#AirQualitySensor).airqualitysensor_carbondioxide >= 800) {
  (#Siren).siren_setsirenmode("emergency")
}
```

### Category 3 · Row 86

- Command (EN): If the temperature on the airquality sensor is below 20 degrees, close the door.
- Command (KO): 회의실 온도가 20도 미만이면, 회의실 문을 닫아줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the temperature on the airquality sensor is below 20 degrees, close the door.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#MeetingRoom #AirQualitySensor).airqualitysensor_temperature < 20) {

    (#MeetingRoom #Door).door_close()

}

# Generated
if ((#AirQualitySensor).airqualitysensor_temperature < 20) {
  (#Door).door_close()
}
```

### Category 3 · Row 87

- Command (EN): If the light in the meeting room is off, turn it on.
- Command (KO): 회의실 조명이 꺼져 있으면, 조명을 켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "precondition", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the light in the meeting room is off, turn it on.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#MeetingRoom #Light).switch_switch == false) {

    (#MeetingRoom #Light).switch_on()

}

# Generated
if ((#Light #MeetingRoom).switch_switch == false) {
  (#Light #MeetingRoom).switch_on()
}
```

### Category 3 · Row 88

- Command (EN): If the temperature in the bedroom is 36.5 degrees or higher, set the bedroom air conditioner to 30 degrees.
- Command (KO): 안방 온도가 36.5도 이상이면, 에어컨을 30도로 설정해줘.
- DET: `60.7099`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "service_match", "unknown_service:temperaturemeasurement_temperature"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: If the temperature in the bedroom is 36.5 degrees or higher, set the bedroom air conditioner to 30 degrees.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#Bedroom #TemperatureSensor).temperaturesensor_temperature >= 36.5) {

    (#Bedroom #AirConditioner).airconditioner_settargettemperature(30)

}

# Generated
if ((#TemperatureSensor #bedroom).temperaturemeasurement_temperature >= 36.5) {
  (#AirConditioner #bedroom).airconditioner_settargettemperature(30.0)
}
```

### Category 3 · Row 89

- Command (EN): If motion is being detected in the living room, turn on the living room light.
- Command (KO): 거실에 움직임이 감지되고 있으면, 조명을 켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If motion is being detected in the living room, turn on the living room light.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#LivingRoom #MotionSensor).motionsensor_motion == true) {

    (#LivingRoom #Light).switch_on()

}

# Generated
if ((#MotionSensor #LivingRoom).motionsensor_motion == true) {
  (#Light #LivingRoom).switch_on()
}
```

### Category 3 · Row 90

- Command (EN): If the lab humidity is 50 or higher, turn on the dehumidifier, and if it's below 50, turn on the humidifier.
- Command (KO): 연구실 습도가 50 이상이면 제습기를 켜고 50 미만이면 가습기를 켜줘.
- DET: `68.6366`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: If the lab humidity is 50 or higher, turn on the dehumidifier, and if it's below 50, turn on the humidifier.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#Lab #HumiditySensor).humiditysensor_humidity >= 50) {

    (#Lab #Dehumidifier).switch_on()

} else {

    (#Lab #Humidifier).switch_on()

}

# Generated
if ((#HumiditySensor).humiditysensor_humidity >= 50) {
  (#Dehumidifier).dehumidifier_setdehumidifiermode("dehumidifying")
} else if ((#HumiditySensor).humiditysensor_humidity < 50) {
  (#Humidifier).humidifier_sethumidifiermode("auto -")
}
```

### Category 4 · Row 91

- Command (EN): When the contact sensor is detected, turn on the light.
- Command (KO): 접촉 센서가 감지되면 조명을 켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When the contact sensor is detected, turn on the light.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
wait until ((#ContactSensor).contactsensor_contact == true)

(#Light).switch_on()

# Generated
triggered := false
if ((#ContactSensor).contactsensor_contact == true) {
  if (triggered == false) {
    (#Light).switch_on()
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 4 · Row 92

- Command (EN): When the presence sensor detects someone, turn on the TV.
- Command (KO): 재실 센서가 감지되면 TV를 켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When the presence sensor detects someone, turn on the TV.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
wait until ((#PresenceSensor).presencesensor_presence == true)

(#Television).switch_on()

# Generated
triggered := false
if ((#PresenceSensor).presencesensor_presence == true) {
  if (triggered == false) {
    (#Television).switch_on()
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 4 · Row 97

- Command (EN): When smoke is detected, sound the fire alarm with the siren.
- Command (KO): 연기가 감지되면 사이렌으로 화재경보를 울려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When smoke is detected, sound the fire alarm with the siren.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
wait until ((#SmokeDetector).smokedetector_smoke == true)

(#Siren).siren_setsirenmode("fire")

# Generated
if ((#SmokeDetector).smokedetector_smoke == true) {
  (#Siren).siren_setsirenmode("fire")
}
```

### Category 4 · Row 99

- Command (EN): When the temperature reaches 35 degrees or higher, set the air conditioner to 30 degrees.
- Command (KO): 온도가 35도 이상이 되면 에어컨의 목표 온도를 30도로 설정해줘.
- DET: `58.7426`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "service_match", "unknown_service:temperaturemeasurement_temperature"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: When the temperature reaches 35 degrees or higher, set the air conditioner to 30 degrees.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
wait until ((#TemperatureSensor).temperaturesensor_temperature >= 35)

(#AirConditioner).airconditioner_settargettemperature(30)

# Generated
wait until ((#TemperatureSensor).temperaturemeasurement_temperature >= 35.0)
(#AirConditioner).airconditioner_settargettemperature(30.0)
```

### Category 4 · Row 100

- Command (EN): When the safe is unlocked, sound the police siren.
- Command (KO): 금고가 열리면 경찰 사이렌을 울려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When the safe is unlocked, sound the police siren.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
wait until ((#Safe).safe_safestate == "unlocked")

(#Siren).siren_setsirenmode("police")

# Generated
wait until ((#Safe).safe_safestate == "open")
(#Siren).siren_setsirenmode("police")
```

### Category 4 · Row 102

- Command (EN): When the humidity exceeds 80%, start the dehumidifier in drying mode.
- Command (KO): 습도가 80%보다 커지면 제습기를 건조 모드로 작동시켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: When the humidity exceeds 80%, start the dehumidifier in drying mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
wait until ((#HumiditySensor).humiditysensor_humidity > 80)

(#Dehumidifier).dehumidifier_setdehumidifiermode("drying")

# Generated
wait until ((#HumiditySensor).humiditysensor_humidity > 80.0)
(#Dehumidifier).dehumidifier_setdehumidifiermode("drying")
```

### Category 4 · Row 103

- Command (EN): When motion is detected, turn on the light.
- Command (KO): 움직임이 감지되면 조명을 켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When motion is detected, turn on the light.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
wait until ((#MotionSensor).motionsensor_motion == true)

(#Light).switch_on()

# Generated
triggered := false
if ((#MotionSensor).motionsensor_motion == true) {
  if (triggered == false) {
    (#Light).switch_on()
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 4 · Row 105

- Command (EN): When the charging voltage exceeds 250V, stop charging.
- Command (KO): 충전 전압이 250V보다 높아지면 충전을 중단해줘.
- DET: `61.2728`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: When the charging voltage exceeds 250V, stop charging.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
wait until ((#Charger).charger_voltage > 250000)

(#Charger).switch_off()

# Generated
wait until ((#Charger).charger_voltage > 250.0)
(#Charger).safe_lock()
```

### Category 4 · Row 106

- Command (EN): When the entrance door lock is unlocked, turn on the living room light.
- Command (KO): 현관 도어락이 잠금해제되면 거실 조명을 켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When the entrance door lock is unlocked, turn on the living room light.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
wait until ((#Entrance #DoorLock).doorlock_doorlockstate == "unlocked")

(#LivingRoom #Light).switch_on()

# Generated
wait until ((#DoorLock).doorlock_doorlockstate == "open")
(#Light).switch_on()
```

### Category 4 · Row 107

- Command (EN): When motion is detected in the bedroom, turn on the bedroom air conditioner.
- Command (KO): 침실에 움직임이 감지되면 침실 에어컨을 켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When motion is detected in the bedroom, turn on the bedroom air conditioner.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
wait until ((#Bedroom #MotionSensor).motionsensor_motion == true)

(#Bedroom #AirConditioner).airconditioner_setairconditionermode("auto")

# Generated
wait until ((#MotionSensor #bedroom).motionsensor_motion == true)
(#AirConditioner #bedroom).airconditioner_setairconditionermode("auto")
```

### Category 4 · Row 108

- Command (EN): When a smoke is detected in the kitchen, close the kitchen valve.
- Command (KO): 주방에 연기가 감지되면 주방 벨브를 잠궈줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When a smoke is detected in the kitchen, close the kitchen valve.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
wait until ((#Kitchen #SmokeDetector).smokedetector_smoke == true)

(#Kitchen #Valve).valve_close()

# Generated
wait until ((#SmokeDetector #Kitchen).smokedetector_smoke == true)
(#Valve #Kitchen).valve_close()
```

### Category 4 · Row 109

- Command (EN): When the fine dust level in the study reaches 30 or higher, turn on the study air purifier.
- Command (KO): 서재 미세먼지 농도가 30 이상이 되면 서재 공기청정기를 켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When the fine dust level in the study reaches 30 or higher, turn on the study air purifier.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
wait until ((#Study #AirQualitySensor).airqualitysensor_finedustlevel >= 30)

(#Study #AirPurifier).switch_on()

# Generated
wait until ((#AirQualitySensor #study).airqualitysensor_finedustlevel >= 30)
(#AirPurifier #study).airpurifier_setairpurifiermode("auto")
```

### Category 4 · Row 110

- Command (EN): When a water leak is detected in the basement, sound the main siren in emergency mode.
- Command (KO): 지하에 누수가 감지되면 메인 사이렌을 비상모드로 울려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When a water leak is detected in the basement, sound the main siren in emergency mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
wait until ((#Basement #LeakSensor).leaksensor_leakage == true)

(#Main #Siren).siren_setsirenmode("emergency")

# Generated
wait until ((#LeakSensor).leaksensor_leakage == true)
(#Siren).siren_setsirenmode("emergency")
```

### Category 4 · Row 111

- Command (EN): When the terrace illuminance falls below 50, turn on the terrace light.
- Command (KO): 테라스 조도가 50 미만이 되면 테라스 조명을 켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When the terrace illuminance falls below 50, turn on the terrace light.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
wait until ((#Terrace #LightSensor).lightsensor_brightness < 50)

(#Terrace #Light).switch_on()

# Generated
wait until ((#LightSensor #terrace).lightsensor_brightness < 50)
(#Light #terrace).switch_on()
```

### Category 4 · Row 112

- Command (EN): When the garage door is opened, take a picture with the garage camera.
- Command (KO): 차고 문이 열리면 차고 카메라로 사진을 찍어줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When the garage door is opened, take a picture with the garage camera.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
wait until ((#Garage #Door).door_doorstate == "open")

(#Garage #Camera).camera_captureimage()

# Generated
wait until ((#Door).door_doorstate == "open")
(#Camera).camera_captureimage()
```

### Category 4 · Row 113

- Command (EN): When the baby room sound exceeds 40 dB, output "Noise detected in the baby room" through the living room speaker.
- Command (KO): 아기방 소리가 40dB보다 커지면 거실 스피커로 아기방에 소음이 감지되었다고 말해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When the baby room sound exceeds 40 dB, output "Noise detected in the baby room" through the living room speaker.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
wait until ((#BabyRoom #SoundSensor).soundsensor_sound > 40)

(#LivingRoom #Speaker).speaker_speak("아기방에 소음이 감지되었습니다.")

# Generated
wait until ((#SoundSensor).soundsensor_sound > 40)
(#Speaker).speaker_speak("Noise detected in the baby room")
```

### Category 4 · Row 114

- Command (EN): When the laundry room dryer's spin speed drops to 5 or below, announce through the living room speaker that the laundry is done.
- Command (KO): 세탁실 건조기 회전 속도가 5 이하가 되면 거실 스피커로 세탁이 끝났다고 알려줘.
- DET: `57.2490`
- Failure reasons: `["arg_type", "dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic", "service_match", "unknown_service:mediaplayback_speak"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md`
- Analysis: When the laundry room dryer's spin speed drops to 5 or below, announce through the living room speaker that the laundry is done.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다

```joi
# GT
wait until ((#LaundryRoom #LaundryDryer).laundrydryer_spinspeed <= 5)

(#LivingRoom #Speaker).speaker_speak("세탁이 완료되었습니다.")

# Generated
triggered := false
spinSpeed = (#LaundryDryer).laundrydryer_spinspeed
if (spinSpeed <= 5) {
  if (triggered == false) {
    (#Speaker).mediaplayback_speak("The laundry is done")
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 4 · Row 115

- Command (EN): When the temperature in the pantry reaches 25 degrees or higher, turn on the pantry air conditioner.
- Command (KO): 창고 온도가 25도 이상이 되면 창고 에어컨을 켜줘.
- DET: `55.4329`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic", "service_match", "unknown_service:temperaturemeasurement_temperature"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: When the temperature in the pantry reaches 25 degrees or higher, turn on the pantry air conditioner.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
wait until ((#Pantry #TemperatureSensor).temperaturesensor_temperature >= 25)

(#Pantry #AirConditioner).switch_on()

# Generated
wait until ((#TemperatureSensor #pantry).temperaturemeasurement_temperature >= 25.0)
(#AirConditioner #pantry).switch_on()
```

### Category 4 · Row 116

- Command (EN): When the bathroom humidity exceeds 70%, set the bathroom dehumidifier to freeze protection mode.
- Command (KO): 욕실 습도가 70%보다 높아지면 욕실 제습기를 동결 방지 모드로 설정해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: When the bathroom humidity exceeds 70%, set the bathroom dehumidifier to freeze protection mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
wait until ((#Bathroom #HumiditySensor).humiditysensor_humidity > 70)

(#Bathroom #Dehumidifier).dehumidifier_setdehumidifiermode("freezeProtection")

# Generated
wait until ((#HumiditySensor).humiditysensor_humidity > 70.0)
(#Dehumidifier).dehumidifier_setdehumidifiermode("freezeProtection")
```

### Category 4 · Row 117

- Command (EN): When the office button is pushed, turn on all humidifiers in office.
- Command (KO): 사무실 버튼이 눌리면 사무실 가습기를 모두 켜줘.
- DET: `65.6828`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When the office button is pushed, turn on all humidifiers in office.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
wait until ((#Office #Button).button_button == "pushed")

all(#Office #Humidifier).switch_on()

# Generated
wait until ((#Button #office).button_button == "pushed")
(#Humidifier #office).humidifier_sethumidifiermode("auto -")
```

### Category 4 · Row 118

- Command (EN): When any presence sensor in the hallway detects presence, set all hallway lights to purple.
- Command (KO): 복도에 재실 센서가 하나라도 감지되면 모든 복도 조명을 보라색으로 설정해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md`
- Analysis: When any presence sensor in the hallway detects presence, set all hallway lights to purple.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다

```joi
# GT
wait until (all(#Hallway #PresenceSensor).presencesensor_presence ==| true)

all(#Hallway #Light).colorcontrol_setcolor("128|0|128")

# Generated
if (any(#PresenceSensor #hallway).presencesensor_presence == true) {
  all(#Light #hallway).colorcontrol_setcolor("128|0|128")
}
```

### Category 4 · Row 119

- Command (EN): When the carbon monoxide level in the server room becomes 5000 ppm or above, sound all sirens in emergency mode.
- Command (KO): 서버실 일산화탄소 농도가 5000 ppm 이상이되면 모든 사이렌을 비상모드로 울려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When the carbon monoxide level in the server room becomes 5000 ppm or above, sound all sirens in emergency mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
wait until ((#ServerRoom #AirQualitySensor).airqualitysensor_carbondioxide >= 5000)

all(#Siren).siren_setsirenmode("emergency")

# Generated
wait until ((#AirQualitySensor).airqualitysensor_carbondioxide >= 5000)
(#Siren).siren_setsirenmode("emergency")
```

### Category 4 · Row 120

- Command (EN): When the bedroom shade button is pushed, lower the shade.
- Command (KO): 안방 쉐이드 버튼이 눌리면 쉐이드를 내려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When the bedroom shade button is pushed, lower the shade.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
wait until ((#Bedroom #Shade #Button).button_button == "pushed")

(#Bedroom #Shade).windowcovering_downorclose()

# Generated
wait until ((#Button #bedroom).button_button == "pushed")
(#WindowCovering #bedroom).windowcovering_downorclose()
```

### Category 5 · Row 122

- Command (EN): Set the air conditioner to cool mode and switch to auto mode after 30 minutes.
- Command (KO): 에어컨을 냉방 모드로 설정하고 30분 뒤에 자동 모드로 설정해줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "enum_grounding", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Set the air conditioner to cool mode and switch to auto mode after 30 minutes.: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
(#AirConditioner).airconditioner_setairconditionermode("cool")

delay(30 MIN)

(#AirConditioner).airconditioner_setairconditionermode("auto")

# Generated
(#AirConditioner).airconditioner_setairconditionermode("cool")
(#Clock).clock_delay(1800000)
(#AirConditioner).airconditioner_setairconditionermode("auto")
```

### Category 5 · Row 123

- Command (EN): Set the air purifier to auto mode and switch to sleep mode after 2 hours.
- Command (KO): 공기청정기를 자동 모드로 설정하고 2시간 뒤에 수면 모드로 설정해줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "enum_grounding", "extraneous", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Set the air purifier to auto mode and switch to sleep mode after 2 hours.: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
(#AirPurifier).airpurifier_setairpurifiermode("auto")

delay(2 HOUR)

(#AirPurifier).airpurifier_setairpurifiermode("sleep")

# Generated
(#AirPurifier).airpurifier_setairpurifiermode("auto")
(#Clock).clock_delay(7200000)
(#AirPurifier).airpurifier_setairpurifiermode("sleep")
```

### Category 5 · Row 125

- Command (EN): Set the oven mode to Bake and change it to warming mode after 10 minutes.
- Command (KO): 오븐 모드를 베이크로 설정하고 10분 뒤에 데우기 모드로 바꿔줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "enum_grounding", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Set the oven mode to Bake and change it to warming mode after 10 minutes.: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
(#Oven).oven_setovenmode("Bake")

delay(10 MIN)

(#Oven).oven_setovenmode("warming")

# Generated
(#Oven).oven_setovenmode("Bake")
(#Clock).clock_delay(600000)
(#Oven).oven_setovenmode("warming")
```

### Category 5 · Row 126

- Command (EN): When the presence sensor detects someone, take a picture after 1 minute.
- Command (KO): 재실 센서에 감지가 되면 1분 뒤에 사진을 찍어줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "dataflow", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: When the presence sensor detects someone, take a picture after 1 minute.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
wait until ((#PresenceSensor).presencesensor_presence == true)

delay(1 MIN)

(#Camera).camera_captureimage()

# Generated
wait until ((#PresenceSensor).presencesensor_presence == true)
(#Clock).clock_delay(60000)
(#Camera).camera_captureimage()
```

### Category 5 · Row 127

- Command (EN): When the oven enters heating mode, switch it to microwave mode after 3 seconds.
- Command (KO): 오븐이 가열 모드가 되면 3초 뒤에 전자레인지 모드로 바꿔줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "dataflow", "extraneous", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: When the oven enters heating mode, switch it to microwave mode after 3 seconds.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
wait until ((#Oven).oven_ovenmode == "heating")

delay(3 SEC)

(#Oven).oven_setovenmode("Microwave")

# Generated
wait until ((#Oven).oven_ovenmode == "heating")
(#Clock).clock_delay(3000)
(#Oven).oven_setovenmode("Microwave")
```

### Category 5 · Row 128

- Command (EN): When the humidity falls below 30%, output "Humidity is low" through the speaker after 3 seconds.
- Command (KO): 습도가 30%보다 낮아지면 3초 뒤에 스피커로 "습도가 낮습니다"를 출력해.
- DET: `69.9000`
- Failure reasons: `["arg_type", "dataflow", "extraneous", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: When the humidity falls below 30%, output "Humidity is low" through the speaker after 3 seconds.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
wait until ((#HumiditySensor).humiditysensor_humidity < 30)

delay(3 SEC)

(#Speaker).speaker_speak("습도가 낮습니다")

# Generated
wait until ((#HumiditySensor).humiditysensor_humidity < 30.0)
(#Clock).clock_delay(3000)
(#Speaker).speaker_speak("Humidity is low")
```

### Category 5 · Row 129

- Command (EN): When it rains, close the door and check again after 1 hour; if it's not raining then, open the door again.
- Command (KO): 비가 오면 문을 닫고 1시간 뒤에 체크해서 비가 안오면 문을 다시 열어줘.
- DET: `68.6218`
- Failure reasons: `["arg_type", "dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: When it rains, close the door and check again after 1 hour; if it's not raining then, open the door again.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
wait until ((#RainSensor).rainsensor_rain == true)

(#Door).door_close()
delay(1 HOUR)

if ((#WeatherProvider).weatherprovider_weather != "rain") {

    (#Door).door_open()

}

# Generated
wait until ((#RainSensor).rainsensor_rain == true)
(#Door).door_close()
(#Clock).clock_delay(3600000)
if ((#RainSensor).rainsensor_rain == false) {
  (#Door).door_open()
}
```

### Category 5 · Row 130

- Command (EN): If the dust level concentration is 2000ppm or above, close the door and close the valve after 4 hours.
- Command (KO): 외부 미세먼지 농도가 2000 이상이면 문을 닫고 4시간 뒤에 밸브를 잠궈줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: If the dust level concentration is 2000ppm or above, close the door and close the valve after 4 hours.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#WeatherProvider).weatherprovider_pm10weather >= 2000) {

    (#Door).door_close()

    delay(4 HOUR)

    (#Valve).valve_close()
 
}

# Generated
if ((#AirQualitySensor).airqualitysensor_dustlevel >= 2000) {
  (#Door).door_close()
  (#Clock).clock_delay(14400000)
  (#Valve).valve_close()
}
```

### Category 5 · Row 131

- Command (EN): Sound the siren in emergency mode and change it to fire mode after 5 seconds.
- Command (KO): 사이렌을 응급 모드로 울리고 5초 뒤에 사이렌 모드를 화재 모드로 바꿔줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "enum_grounding", "extraneous", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Sound the siren in emergency mode and change it to fire mode after 5 seconds.: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
(#Siren).siren_setsirenmode("emergency")

delay(5 SEC)

(#Siren).siren_setsirenmode("fire")

# Generated
(#Siren).siren_setsirenmode("emergency")
(#Clock).clock_delay(5000)
(#Siren).siren_setsirenmode("fire")
```

### Category 5 · Row 133

- Command (EN): Start the robot vacuum cleaner in auto mode and switch to manual mode after 30 minutes.
- Command (KO): 로봇 청소기를 자동 모드로 시작하고 30분 뒤에 수동 모드로 바꿔줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "enum_grounding", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Start the robot vacuum cleaner in auto mode and switch to manual mode after 30 minutes.: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
(#RobotVacuumCleaner).robotvacuumcleaner_setrobotvacuumcleanermodemode("auto")

delay(30 MIN)

(#RobotVacuumCleaner).robotvacuumcleaner_setrobotvacuumcleanermodemode("manual")

# Generated
(#RobotVacuumCleaner).robotvacuumcleaner_setrobotvacuumcleanermodemode("auto")
(#Clock).clock_delay(1800000)
(#RobotVacuumCleaner).robotvacuumcleaner_setrobotvacuumcleanermodemode("manual")
```

### Category 5 · Row 135

- Command (EN): Start the dehumidifier in drying mode and change to refreshing mode after 1 hour.
- Command (KO): 제습기를 건조 모드로 작동시키고 1시간 뒤에 리프레쉬 모드로 바꿔줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "enum_grounding", "extraneous", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Start the dehumidifier in drying mode and change to refreshing mode after 1 hour.: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
(#Dehumidifier).dehumidifier_setdehumidifiermode("drying")

delay(1 HOUR)

(#Dehumidifier).dehumidifier_setdehumidifiermode("refreshing")

# Generated
(#Dehumidifier).dehumidifier_setdehumidifiermode("drying")
(#Clock).clock_delay(3600000)
(#Dehumidifier).dehumidifier_setdehumidifiermode("refreshing")
```

### Category 5 · Row 136

- Command (EN): Turn on all lights in the living room and turn them off after 1 hour.
- Command (KO): 거실의 모든 전등을 켜고 1시간 뒤에 꺼줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Turn on all lights in the living room and turn them off after 1 hour.: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
all(#LivingRoom #Light).switch_on()

delay(1 HOUR)

all(#LivingRoom #Light).switch_off()

# Generated
all(#Light #LivingRoom).switch_on()
(#Clock).clock_delay(3600000)
all(#Light #LivingRoom).switch_off()
```

### Category 5 · Row 137

- Command (EN): When any presence sensor in the house detects presence, sound all emergency sirens after 10 seconds.
- Command (KO): 집안의 재실 센서가 하나라도 감지되면 10초 뒤에 모든 긴급 사이렌을 울려줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "dataflow", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: When any presence sensor in the house detects presence, sound all emergency sirens after 10 seconds.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
wait until (all(#House #PresenceSensor).presencesensor_presence ==| true)

delay(10 SEC)

all(#Siren).siren_setsirenmode("emergency")

# Generated
wait until (any(#PresenceSensor).presencesensor_presence == true)
(#Clock).clock_delay(10000)
(#Siren).siren_setsirenmode("emergency")
```

### Category 5 · Row 138

- Command (EN): Open all valves in the kitchen and close them again after 5 minutes.
- Command (KO): 주방의 모든 벨브를 열고 5분 뒤에 다시 잠궈줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Open all valves in the kitchen and close them again after 5 minutes.: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
all(#Kitchen #Valve).valve_open()

delay(5 MIN)

all(#Kitchen #Valve).valve_close()

# Generated
all(#Valve #kitchen).valve_open()
(#Clock).clock_delay(300000)
all(#Valve #kitchen).valve_close()
```

### Category 5 · Row 139

- Command (EN): Close all blinds in the bedroom and open them again after 2 hours.
- Command (KO): 안방의 모든 블라인드를 닫고 2시간 뒤에 다시 열어줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "extraneous", "gt_mismatch", "gt_receiver_coverage", "numeric_grounding"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, response_prompt_baseline_cot.md, tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: Close all blinds in the bedroom and open them again after 2 hours.: GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
all(#Bedroom #Blind).windowcovering_downorclose()

delay(2 HOUR)

all(#Bedroom #Blind).windowcovering_uporopen()

# Generated
all(#WindowCovering #bedroom).windowcovering_downorclose()
(#Clock).clock_delay(7200000)
all(#WindowCovering #bedroom).windowcovering_uporopen()
```

### Category 5 · Row 140

- Command (EN): When any light in the hallway is turned on, turn off all lights in the living room after 5 minutes.
- Command (KO): 복도의 조명이 하나라도 켜지면 5분 뒤에 거실의 모든 조명을 꺼줘.
- DET: `69.3978`
- Failure reasons: `["arg_type", "dataflow", "extraneous", "gt_mismatch", "numeric_grounding", "precondition", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: When any light in the hallway is turned on, turn off all lights in the living room after 5 minutes.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
wait until (all(#Hallway #Light).switch_switch ==| true)

delay(5 MIN)

all(#LivingRoom #Light).switch_off()

# Generated
wait until (any(#Light #Hallway).switch_switch == true)
(#Clock).clock_delay(300000)
all(#Light #LivingRoom).switch_off()
```

### Category 5 · Row 141

- Command (EN): Turn on all dehumidifiers in the lab and turn them off after 4 hours.
- Command (KO): 연구실의 모든 제습기를 켜고 4시간 뒤에 꺼줘.
- DET: `65.9876`
- Failure reasons: `["arg_type", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, response_prompt_baseline_cot.md, tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: Turn on all dehumidifiers in the lab and turn them off after 4 hours.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
all(#Lab #Dehumidifier).switch_on()

delay(4 HOUR)

all(#Lab #Dehumidifier).switch_off()

# Generated
(#Dehumidifier #lab).dehumidifier_setdehumidifiermode("dehumidifying")
(#Clock).clock_delay(14400000)
(#Dehumidifier #lab).switch_off()
```

### Category 5 · Row 142

- Command (EN): When any air purifier in the office switches to sleep mode, turn off the light after 10 minutes.
- Command (KO): 사무실의 공기청정기가 하나라도 수면모드로 바뀌면 10분 뒤에 조명을 꺼줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "dataflow", "extraneous", "gt_mismatch", "numeric_grounding", "precondition", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: When any air purifier in the office switches to sleep mode, turn off the light after 10 minutes.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
wait until (all(#Office #AirPurifier).airpurifier_airpurifiermode ==| "sleep")

delay(10 MIN)

(#Office #Light).switch_off()

# Generated
wait until (any(#AirPurifier #office).airpurifier_airpurifiermode == "sleep")
(#Clock).clock_delay(600000)
(#Light).switch_off()
```

### Category 5 · Row 143

- Command (EN): Lock all warehouse door locks and sound the emergency siren 1 minute later.
- Command (KO): 창고의 모든 도어락을 잠그고 1분 뒤에 긴급 사이렌을 울려줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Lock all warehouse door locks and sound the emergency siren 1 minute later.: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
all(#Warehouse #DoorLock).doorlock_lock()

delay(1 MIN)

(#Siren).siren_setsirenmode("emergency")

# Generated
(#DoorLock).doorlock_lock()
(#Clock).clock_delay(60000)
(#Siren).siren_setsirenmode("emergency")
```

### Category 5 · Row 144

- Command (EN): When any illuminance sensor on the terrace reaches 100 lux or higher, raise all blinds after 5 seconds.
- Command (KO): 테라스의 어느 조도 센서라도 100 럭스 이상이 되면 5초 뒤에 모든 블라인드를 올려줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "dataflow", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: When any illuminance sensor on the terrace reaches 100 lux or higher, raise all blinds after 5 seconds.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
wait until (all(#Terrace #LightSensor).lightsensor_brightness >=| 100)

delay(5 SEC)

all(#Terrace #Blind).windowcovering_uporopen()

# Generated
wait until (any(#LightSensor #terrace).lightsensor_brightness >= 100)
(#WindowCovering #terrace).windowcovering_uporopen()
(#Clock).clock_delay(5000)
```

### Category 5 · Row 145

- Command (EN): When any temperature sensor in the data center reaches 30 degrees or higher, set all air conditioners to cool mode after 1 minute.
- Command (KO): 데이터 센터의 어느 온도 센서라도 30도 이상이 되면 1분 뒤에 모든 에어컨을 냉방 모드로 작동시켜줘.
- DET: `52.8074`
- Failure reasons: `["arg_type", "dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic", "service_match", "unknown_service:temperaturemeasurement_temperature"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: When any temperature sensor in the data center reaches 30 degrees or higher, set all air conditioners to cool mode after 1 minute.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
wait until (all(#DataCenter #TemperatureSensor).temperaturesensor_temperature >=| 30)

delay(1 MIN)

all(#DataCenter #AirConditioner).airconditioner_setairconditionermode("cool")

# Generated
if (any(#TemperatureSensor #DataCenter).temperaturemeasurement_temperature >= 30.0) {
  (#Clock).clock_delay(60000)
  (#AirConditioner).airconditioner_setairconditionermode("cool")
}
```

### Category 5 · Row 146

- Command (EN): Turn on the kitchen light and turn on the kitchen dehumidifier 10 seconds later.
- Command (KO): 주방 조명을 켜고 10초 뒤에 주방 제습기를 켜줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Turn on the kitchen light and turn on the kitchen dehumidifier 10 seconds later.: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
(#Kitchen #Light).switch_on()

delay(10 SEC)

(#Kitchen #Dehumidifier).switch_on()

# Generated
(#Light #kitchen).switch_on()
(#Clock).clock_delay(10000)
(#Switch #kitchen).switch_on()
```

### Category 5 · Row 147

- Command (EN): Set the study air purifier to high and turn it off after 2 hours.
- Command (KO): 서재 공기청정기를 강풍으로 틀고 2시간 뒤에 꺼줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, response_prompt_baseline_cot.md, tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: Set the study air purifier to high and turn it off after 2 hours.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
(#Study #AirPurifier).airpurifier_setairpurifiermode("high")

delay(2 HOUR)

(#Study #AirPurifier).switch_off()

# Generated
(#AirPurifier).airpurifier_setairpurifiermode("high")
(#Clock).clock_delay(7200000)
(#AirPurifier).airpurifier_setairpurifiermode("off")
```

### Category 5 · Row 148

- Command (EN): Turn off the bathroom light and turn on after 5 minutes.
- Command (KO): 욕실 조명을 끄고 5분 뒤에 켜줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Turn off the bathroom light and turn on after 5 minutes.: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
(#Bathroom #Light).switch_off()

delay(5 MIN)

(#Bathroom #Light).switch_on()

# Generated
(#Light #Bathroom).switch_off()
(#Clock).clock_delay(300000)
(#Light #Bathroom).switch_on()
```

### Category 5 · Row 149

- Command (EN): Close the meeting room door. After 3 seconds take a picture with the meeting room camera.
- Command (KO): 회의실 문을 닫고 3초 뒤에 회의실 카메라로 촬영해줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "extraneous", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: Close the meeting room door. After 3 seconds take a picture with the meeting room camera.: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
(#MeetingRoom #Door).door_close()

delay(3 SEC)

(#MeetingRoom #Camera).camera_captureimage()

# Generated
(#Door).door_close()
(#Clock).clock_delay(3000)
(#Camera).camera_captureimage()
```

### Category 5 · Row 150

- Command (EN): Check the wine cellar temperature now and again in 10 minutes. If it has changed by 1 degree or higher, announce through the speaker that the wine cellar temperature has changed rapidly.
- Command (KO): 지금 와인 셀러 온도를 체크하고 10분뒤에 다시 체크해서 1도 이상 차이가 나면, 스피커로 온도가 급변했다고 안내해줘.
- DET: `18.5350`
- Failure reasons: `["arg_type", "dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "precondition", "semantic", "service_match", "unknown_service:mediaplayback_speak", "unknown_service:temperaturemeasurement_temperature"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: Check the wine cellar temperature now and again in 10 minutes. If it has changed by 1 degree or higher, announce through the speaker that the wine cellar temperature has changed rapidly.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
original_temp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature

delay(10 MIN)

temp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature

if (temp >= original_temp + 1 or temp <= original_temp - 1) {

    (#Speaker).speaker_speak("와인셀러의 온도가 급변했습니다")
}

# Generated
prevTemp := (#TemperatureSensor).temperaturemeasurement_temperature
if (prevTemp != (#TemperatureSensor).temperaturemeasurement_temperature) {
  currTemp = (#TemperatureSensor).temperaturemeasurement_temperature
  diff = currTemp - prevTemp
  if ((diff >= 1) or (diff <= -1)) {
    (#Speaker).mediaplayback_speak("The wine cellar temperature has changed rapidly")
  }
  prevTemp = currTemp
}
```

### Category 6 · Row 151

- Command (EN): If the temperature is 28 degrees or higher and the humidity is 70% or higher, set the air conditioner to cool mode and 24 degrees.
- Command (KO): 온도가 28도 이상이고 습도가 70% 이상이면, 에어컨을 냉방 모드로 설정하고 온도를 24도로 맞춰줘.
- DET: `69.1766`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "service_match", "unknown_service:temperaturemeasurement_temperature"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md`
- Analysis: If the temperature is 28 degrees or higher and the humidity is 70% or higher, set the air conditioner to cool mode and 24 degrees.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#TemperatureSensor).temperaturesensor_temperature >= 28 and (#HumiditySensor).humiditysensor_humidity >= 70) {

    (#AirConditioner).airconditioner_setairconditionermode("cool")

    (#AirConditioner).airconditioner_settargettemperature(24)
 
}

# Generated
if ((#TemperatureSensor).temperaturemeasurement_temperature >= 28 and (#AirQualitySensor).airqualitysensor_humidity >= 70) {
  (#AirConditioner).airconditioner_setairconditionermode("cool")
  (#AirConditioner).airconditioner_settargettemperature(24)
}
```

### Category 6 · Row 152

- Command (EN): If the carbon dioxide concentration is 1200ppm or higher and person is being detected, set the air purifier to high mode and announce a warning using the speaker.
- Command (KO): 이산화탄소 농도가 1200ppm 이상이고 사람이 감지되고 있으면, 공기청정기를 강풍으로 바꾸고 스피커로 경고해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the carbon dioxide concentration is 1200ppm or higher and person is being detected, set the air purifier to high mode and announce a warning using the speaker.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#AirQualitySensor).airqualitysensor_carbondioxide >= 1200 and (#PresenceSensor).presencesensor_presence == true) {

    (#AirPurifier).airpurifier_setairpurifiermode("high")

    (#Speaker).speaker_speak("이산화탄소 농도가 높습니다.")

}

# Generated
if ((#CarbonDioxideSensor).carbondioxidesensor_carbondioxide >= 1200 and (#PresenceSensor).presencesensor_presence == "present") {
  (#AirPurifier).airpurifier_setairpurifiermode("high")
  (#Speaker).speaker_speak("Warning: High carbon dioxide concentration detected.")
}
```

### Category 6 · Row 153

- Command (EN): If it is raining and the humidity is 80% or higher, set the dehumidifier to drying mode and output "It's raining and himidity is high" through the speaker.
- Command (KO): 비가 오고 있고 습도가 80% 이상이면, 제습기를 건조 모드로 작동시키고 "비가 오고 습도가 높습니다"라고 스피커로 출력해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If it is raining and the humidity is 80% or higher, set the dehumidifier to drying mode and output "It's raining and himidity is high" through the speaker.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#RainSensor).rainsensor_rain == true and (#HumiditySensor).humiditysensor_humidity >= 80) {

    (#Dehumidifier).dehumidifier_setdehumidifiermode("drying")

    (#Speaker).speaker_speak("비가 오고 습도가 높습니다.")

}

# Generated
if ((#RainSensor).rain == true and (#HumiditySensor).humiditysensor_humidity >= 80) {
  (#Dehumidifier).dehumidifier_setdehumidifiermode("drying")
  (#Speaker).speaker_speak("It's raining and himidity is high")
}
```

### Category 6 · Row 154

- Command (EN): If the noise level is 70 or higher and no one is home, take a photo with the camera and sound the police siren.
- Command (KO): 소음 수치가 70 이상이고 집에 아무도 없으면, 카메라로 사진을 찍고 경찰 사이렌을 울려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the noise level is 70 or higher and no one is home, take a photo with the camera and sound the police siren.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#SoundSensor).soundsensor_sound >= 70 and (#PresenceSensor).presencesensor_presence == false) {

    (#Camera).camera_captureimage()

    (#Siren).siren_setsirenmode("police")

}

# Generated
if ((#SoundSensor).soundsensor_sound >= 70 and (#PresenceVitalSensor).presencevitalsensor_presence == false) {
  (#Camera).camera_captureimage()
  (#Siren).siren_setsirenmode("police")
}
```

### Category 6 · Row 155

- Command (EN): If the illuminance is 100 lux or lower and a person is being detected, set the speaker volume to 30 and play relax.mp3 music.
- Command (KO): 조도가 100 럭스 이하이고 사람이 감지되고 있으면, 스피커 볼륨을 30으로 설정하고 relax.mp3 음악을 재생해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the illuminance is 100 lux or lower and a person is being detected, set the speaker volume to 30 and play relax.mp3 music.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#LightSensor).lightsensor_brightness <= 100 and (#PresenceSensor).presencesensor_presence == true) {

    (#Speaker).speaker_setvolume(30)

    (#Speaker).speaker_play("relax.mp3")

}

# Generated
if ((#LightSensor).lightsensor_brightness <= 100 and (#PresenceVitalSensor).presencevitalsensor_presence == true) {
  (#Speaker).speaker_setvolume(30)
  (#Speaker).speaker_play("relax.mp3")
}
```

### Category 6 · Row 157

- Command (EN): If the weather is rainy and no one is being detected, lock the door and close the valve.
- Command (KO): 비가 오고 아무도 없는 상태면, 도어락을 잠그고 밸브를 차단해줘.
- DET: `68.0888`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the weather is rainy and no one is being detected, lock the door and close the valve.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#WeatherProvider).weatherprovider_weather == "rain" and (#PresenceSensor).presencesensor_presence == false) {

    (#DoorLock).doorlock_lock()

    (#Valve).valve_close()

}

# Generated
if ((#RainSensor).rainsensor_rain == true and (#PresenceVitalSensor).presencevitalsensor_presence == false) {
  (#DoorLock).doorlock_lock()
  (#Valve).valve_close()
}
```

### Category 6 · Row 158

- Command (EN): If the oven is heating and no one is being detected, change the oven mode to warming and notify that the oven mode has been changed to warming.
- Command (KO): 오븐이 가열 중이고 아무도 없으면, 오븐을 보온 모드로 변경하고 스피커로 보온 모드로 변경했다고 알려줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic", "service_match", "unknown_service:mediaplayback_speak"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md`
- Analysis: If the oven is heating and no one is being detected, change the oven mode to warming and notify that the oven mode has been changed to warming.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다

```joi
# GT
if ((#Oven).oven_ovenmode == "heating" and (#PresenceSensor).presencesensor_presence == false) {

    (#Oven).oven_setovenmode("warming")

    (#Speaker).speaker_speak("오븐을 보온 모드로 변경합니다.")

}

# Generated
if ((#Oven).oven_ovenmode == "heating" and (#PresenceSensor).presencesensor_presence != "present") {
  (#Oven).oven_setovenmode("warming")
  (#Speaker).mediaplayback_speak("The oven mode has been changed to warming.")
}
```

### Category 6 · Row 159

- Command (EN): If the noise level is 80 or higher and no person is being detected, stop speaker playbackand sound the emergency siren.
- Command (KO): 소음이 80 이상이고 사람이 없으면, 스피커 재생을 멈추고 긴급 사이렌을 울려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the noise level is 80 or higher and no person is being detected, stop speaker playbackand sound the emergency siren.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#SoundSensor).soundsensor_sound >= 80 and (#PresenceSensor).presencesensor_presence == false) {

    (#Speaker).speaker_stop()

    (#Siren).siren_setsirenmode("emergency")

}

# Generated
if ((#SoundSensor).soundsensor_sound >= 80 and (#PresenceVitalSensor).presencevitalsensor_presence == false) {
  (#Speaker).speaker_stop()
  (#Siren).siren_setsirenmode("emergency")
}
```

### Category 6 · Row 160

- Command (EN): If the carbon dioxide is 1500ppm or higher and the blind is closed, set the air purifier to auto and raise the blind.
- Command (KO): 이산화탄소가 1500ppm 이상이고 블라인드가 닫혀있으면, 공기청정기를 자동 모드로 켜고 블라인드를 올려줘.
- DET: `52.9690`
- Failure reasons: `["arg_type", "dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "service_match", "unknown_service:blind_blind", "unknown_service:blind_open"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: If the carbon dioxide is 1500ppm or higher and the blind is closed, set the air purifier to auto and raise the blind.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#AirQualitySensor).airqualitysensor_carbondioxide >= 1500 and (#Blind).armrobot_currentposition == 0) {

    (#AirPurifier).airpurifier_setairpurifiermode("auto")

    (#Blind).windowcovering_uporopen()

}

# Generated
if ((#CarbonDioxideSensor).carbondioxide >= 1500 and (#Blind).blind_blind == "closed") {
  (#AirPurifier).airpurifier_setairpurifiermode("auto")
  (#Blind).blind_open()
}
```

### Category 6 · Row 161

- Command (EN): If the temperature is 18 degrees or below and someone is detected, set the air conditioner to heat mode and 22 degrees.
- Command (KO): 온도가 18도 이하이고 사람이 감지되고있으면, 에어컨을 난방 모드로 설정하고 22도로 조절해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "service_match", "unknown_service:temperaturemeasurement_temperature"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: If the temperature is 18 degrees or below and someone is detected, set the air conditioner to heat mode and 22 degrees.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#TemperatureSensor).temperaturesensor_temperature <= 18 and (#PresenceSensor).presencesensor_presence == true) {

    (#AirConditioner).airconditioner_setairconditionermode("heat")

    (#AirConditioner).airconditioner_settargettemperature(22)

}

# Generated
if ((#TemperatureSensor).temperaturemeasurement_temperature <= 18.0 and (#PresenceSensor).presencesensor_presence == "present") {
  (#AirConditioner).airconditioner_setairconditionermode("heat")
  (#AirConditioner).airconditioner_settargettemperature(22.0)
}
```

### Category 6 · Row 162

- Command (EN): If it is raining and the door is open, close the door and set the dehumidifier to internal Care mode.
- Command (KO): 비가 오고 문이 열려 있으면, 문을 닫고 제습기를 내부케어 모드로 작동시켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "enum_grounding", "extraneous", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md`
- Analysis: If it is raining and the door is open, close the door and set the dehumidifier to internal Care mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
if ((#RainSensor).rainsensor_rain == true and (#Door).door_doorstate == "open") {

    (#Door).door_close()

    (#Dehumidifier).dehumidifier_setdehumidifiermode("auto")

}

# Generated
if ((#RainSensor).rainsensor_rain == true and (#Door).door_doorstate == "open") {
  (#Door).door_close()
  (#Dehumidifier).dehumidifier_setdehumidifiermode("internalCare")
}
```

### Category 6 · Row 163

- Command (EN): If a person is detected and smoke is detected, sound the siren in fire mode and announce "Evacuate" through the speaker.
- Command (KO): 사람이 있는데 연기가 감지되고 있으면, 사이렌을 화재 모드로 울리고 스피커로 "대피하세요"라고 해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If a person is detected and smoke is detected, sound the siren in fire mode and announce "Evacuate" through the speaker.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#PresenceSensor).presencesensor_presence == true and (#SmokeDetector).smokedetector_smoke == true) {

    (#Siren).siren_setsirenmode("fire")

    (#Speaker).speaker_speak("대피하세요")

}

# Generated
if ((#PresenceVitalSensor).presencevitalsensor_presence == true and (#SmokeDetector).smokedetector_smoke == true) {
  (#Siren).siren_setsirenmode("fire")
  (#Speaker).speaker_speak("Evacuate")
}
```

### Category 6 · Row 164

- Command (EN): If the pressure is 100 or higher and no one is home, close the valve and sound emergency siren.
- Command (KO): 수압이 100 이상이고 사람이 없으면, 밸브를 잠그고 긴급 사이렌을 울려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the pressure is 100 or higher and no one is home, close the valve and sound emergency siren.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#PressureSensor).pressuresensor_pressure >= 100 and (#PresenceSensor).presencesensor_presence == false) {

    (#Valve).valve_close()

    (#Siren).siren_setsirenmode("emergency")

}

# Generated
if ((#PressureSensor).pressuresensor_pressure >= 100 and (#PresenceVitalSensor).presencevitalsensor_presence == false) {
  (#Valve).valve_close()
  (#Siren).siren_setsirenmode("emergency")
}
```

### Category 6 · Row 165

- Command (EN): If no motion is detected but the door is open, take a photo and output "Warning" through the speaker.
- Command (KO): 움직임이 감지되지 않는데 문이 열려 있으면, 사진을 찍고 스피커로 "경고"라고 말해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If no motion is detected but the door is open, take a photo and output "Warning" through the speaker.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#MotionSensor).motionsensor_motion == false and (#Door).door_doorstate == "open") {

    (#Camera).camera_captureimage()

    (#Speaker).speaker_speak("경고")

}

# Generated
if ((#MotionSensor).motion == false and (#Door).door_doorstate == "open") {
  (#Camera).camera_captureimage()
  (#Speaker).speaker_speak("Warning")
}
```

### Category 6 · Row 166

- Command (EN): If someone is in the living room and smoke is being detected in the kitchen, play an announcement in the living room and close the kitchen valve.
- Command (KO): 거실에 사람이 있고 주방에서 연기가 감지되고 있으면, 거실 스피커로 주방에 연기가 감지되었다고 출력하고 주방 밸브를 잠궈줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If someone is in the living room and smoke is being detected in the kitchen, play an announcement in the living room and close the kitchen valve.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#LivingRoom #PresenceSensor).presencesensor_presence == true and (#Kitchen #SmokeDetector).smokedetector_smoke == true) {

    (#LivingRoom #Speaker).speaker_speak("주방에 연기가 감지되었습니다.")

    (#Kitchen #Valve).valve_close()

}

# Generated
if ((#PresenceSensor #LivingRoom).presencesensor_presence == true and (#SmokeDetector #Kitchen).smokedetector_smoke == true) {
  (#Speaker #LivingRoom).speaker_speak("Smoke detected in the kitchen. Please evacuate immediately.")
  (#Valve #Kitchen).valve_close()
}
```

### Category 6 · Row 167

- Command (EN): If the bedroom temperature is 26 degrees or higher and the bedroom window is open, close the window and turn on the air conditioner.
- Command (KO): 안방의 온도가 26도 이상이고 창문이 열려 있으면, 창문을 닫고 에어컨을 켜줘.
- DET: `56.9817`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "service_match", "unknown_service:temperaturemeasurement_temperature"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md`
- Analysis: If the bedroom temperature is 26 degrees or higher and the bedroom window is open, close the window and turn on the air conditioner.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#Bedroom #TemperatureSensor).temperaturesensor_temperature >= 26 and (#Bedroom #Window).armrobot_currentposition > 0) {

    (#Bedroom #Window).windowcovering_downorclose()

    (#Bedroom #AirConditioner).switch_on()

}

# Generated
if ((#TemperatureSensor #bedroom).temperaturemeasurement_temperature >= 26 and (#WindowCovering #bedroom).windowcovering_currentposition > 0) {
  (#WindowCovering #bedroom).windowcovering_downorclose()
  (#AirConditioner #bedroom).airconditioner_setairconditionermode("cool")
}
```

### Category 6 · Row 168

- Command (EN): If motion is detected in the garage and the main siren is off, sound the siren in emergency and take a picture.
- Command (KO): 차고에서 움직임이 감지되고 있고 메인 사이렌이 꺼져있으면, 비상 사이렌을 울리고 차고 사진을 찍어줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "precondition", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If motion is detected in the garage and the main siren is off, sound the siren in emergency and take a picture.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#Garage #MotionSensor).motionsensor_motion == true and (#Main #Siren).switch_switch == false) {

    (#Main #Siren).siren_setsirenmode("emergency")

    (#Garage #Camera).camera_captureimage()

}

# Generated
if ((#MotionSensor).motionsensor_motion == true and (#Siren).switch_switch == false) {
  (#Siren).siren_setsirenmode("emergency")
  (#Camera).camera_captureimage()
}
```

### Category 6 · Row 169

- Command (EN): If the study carbon dioxide is 1000ppm or higher and the air purifier is in sleep mode, switch to auto mode and say "Switching the air purifier to auto mode" through the speaker.
- Command (KO): 서재 이산화탄소가 1000ppm 이상이고 공기청정기가 수면 모드이면, 자동 모드로 바꾸고 스피커로 "공기청정기를 자동모드로 변경합니다"라고 말해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the study carbon dioxide is 1000ppm or higher and the air purifier is in sleep mode, switch to auto mode and say "Switching the air purifier to auto mode" through the speaker.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#Study #AirQualitySensor).airqualitysensor_carbondioxide >= 1000 and (#Study #AirPurifier).airpurifier_airpurifiermode == "sleep") {

    (#Study #AirPurifier).airpurifier_setairpurifiermode("auto")

    (#Study #Speaker).speaker_speak("공기 청정기를 자동모드로 변경합니다")

}

# Generated
if ((#AirQualitySensor).airqualitysensor_carbondioxide >= 1000 and (#AirPurifier).airpurifier_airpurifiermode == "sleep") {
  (#AirPurifier).airpurifier_setairpurifiermode("auto")
  (#Speaker).speaker_speak("Switching the air purifier to auto mode")
}
```

### Category 6 · Row 170

- Command (EN): If the bathroom humidity is 85% or higher and the bathroom door is closed, turn on the light and open the door.
- Command (KO): 욕실 습도가 85% 이상이고 욕실 문이 닫혀 있으면, 조명을 켜고 문을 열어줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: If the bathroom humidity is 85% or higher and the bathroom door is closed, turn on the light and open the door.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#Bathroom #HumiditySensor).humiditysensor_humidity >= 85 and (#Bathroom #Door).door_doorstate == "closed") {

    (#Bathroom #Light).switch_on()

    (#Bathroom #Door).door_open()

}

# Generated
if ((#HumiditySensor #Bathroom).humiditysensor_humidity >= 85.0 and (#Door #Bathroom).door_doorstate == "closed") {
  (#Light #Bathroom).switch_on()
  (#Door #Bathroom).door_open()
}
```

### Category 6 · Row 171

- Command (EN): If the face ID 'family' is recognized at the entrance and the door lock is locked , unlock the door lock and open the door.
- Command (KO): 현관에서 인식된 얼굴 ID가 "가족"이고 도어락이 잠겨 있으면, 도어락을 풀고 문을 열어줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the face ID 'family' is recognized at the entrance and the door lock is locked , unlock the door lock and open the door.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#Entrance #FaceRecognizer).facerecognizer_recognizedresult == "family" and (#Entrance #DoorLock).doorlock_doorlockstate == "locked") {

    (#Entrance #DoorLock).doorlock_unlock()

    (#Entrance #Door).door_open()

}

# Generated
if ((#FaceRecognizer).facerecognizer_recognizedresult == "family" and (#DoorLock).doorlock_doorlockstate == "closed") {
  (#DoorLock).doorlock_unlock()
  (#Door).door_open()
}
```

### Category 6 · Row 172

- Command (EN): If the garden illuminance is below 50 and the terrace light is off, turn on the light and play an announcement in the garden.
- Command (KO): 정원 조도가 50 미만이고 테라스 조명이 꺼져 있으면, 조명을 켜고 정원 스피커로 조명을 켠다고 말해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the garden illuminance is below 50 and the terrace light is off, turn on the light and play an announcement in the garden.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#Garden #LightSensor).lightsensor_brightness < 50 and (#Terrace #Light).switch_switch == false) {

    (#Terrace #Light).switch_on()

    (#Garden #Speaker).speaker_speak("조명을 켭니다.")

}

# Generated
if ((#LightSensor).lightsensor_brightness < 50 and (#Switch).switch_switch == false) {
  (#Switch).switch_on()
  (#Speaker).speaker_speak("The garden light is now on.")
}
```

### Category 6 · Row 173

- Command (EN): If it's raining and the living room window is open, close the window and set the dehumidifier to drying mode.
- Command (KO): 비가 오고 거실 창문이 열려 있으면, 창문을 닫고 건조기를 건조 모드로 설정해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If it's raining and the living room window is open, close the window and set the dehumidifier to drying mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#RainSensor).rainsensor_rain == true and (#LivingRoom #Window).armrobot_currentposition == 0) {

    (#LivingRoom #Window).windowcovering_downorclose()

    (#Dehumidifier).dehumidifier_setdehumidifiermode("drying")

}

# Generated
if ((#RainSensor).rainsensor_rain == true and (#WindowCovering #LivingRoom).windowcovering_windowcoveringtype == "window" and (#WindowCovering #LivingRoom).windowcovering_currentposition > 0) {
  (#WindowCovering #LivingRoom).windowcovering_downorclose()
  (#Dehumidifier).dehumidifier_setdehumidifiermode("drying")
}
```

### Category 6 · Row 174

- Command (EN): If the baby room sound is 50dB or higher and the living room speaker is stopped, say the baby is awake through the speaker and play "lullaby.mp3" file.
- Command (KO): 아기방 소리가 50dB 이상이고 거실 스피커가 멈춘 상태면, 거실 스피커로 아기가 깼다고 말하고 lullaby.mp3 파일 재생을 시작해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the baby room sound is 50dB or higher and the living room speaker is stopped, say the baby is awake through the speaker and play "lullaby.mp3" file.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#BabyRoom #SoundSensor).soundsensor_sound >= 50 and (#LivingRoom #Speaker).speaker_playbackstate == "stopped") {

    (#LivingRoom #Speaker).speaker_speak("아기가 깼습니다.")

    (#LivingRoom #Speaker).speaker_play("lullaby.mp3")

}

# Generated
if ((#SoundSensor #BabyRoom).soundsensor_sound >= 50 and (#Speaker #LivingRoom).speaker_playbackstate == "stopped") {
  (#Speaker #LivingRoom).speaker_speak("The baby is awake")
  (#Speaker #LivingRoom).speaker_play("lullaby.mp3")
}
```

### Category 6 · Row 175

- Command (EN): If the server room temperature is 30 degrees or higher and the AC is off, turn it on and sound the main emergency siren.
- Command (KO): 서버실 온도가 30도 이상이고 에어컨이 꺼져 있으면, 에어컨을 냉방 모드로 켜고 메인 사이렌을 긴급 모드로 울려줘.
- DET: `56.4470`
- Failure reasons: `["dataflow", "enum_grounding", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "precondition", "semantic", "service_match", "unknown_service:temperaturemeasurement_temperature"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md`
- Analysis: If the server room temperature is 30 degrees or higher and the AC is off, turn it on and sound the main emergency siren.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
if ((#ServerRoom #TemperatureSensor).temperaturesensor_temperature >= 30 and (#ServerRoom #AirConditioner).switch_switch == false) {

    (#ServerRoom #AirConditioner).airconditioner_setairconditionermode("cool")

    (#Main #Siren).siren_setsirenmode("emergency")

}

# Generated
if ((#TemperatureSensor).temperaturemeasurement_temperature >= 30 and (#AirConditioner).switch_switch == false) {
  (#AirConditioner).switch_on()
  (#Siren).siren_setsirenmode("emergency")
}
```

### Category 6 · Row 176

- Command (EN): If the wine cellar temperature is 15 degrees or higher and humidity is 60% or higher, turn on the air conditioner and turn off the humidifier.
- Command (KO): 와인 셀러 온도가 15도 이상이고 습도가 60% 이상이면, 에어컨을 켜고 가습기를 꺼줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the wine cellar temperature is 15 degrees or higher and humidity is 60% or higher, turn on the air conditioner and turn off the humidifier.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#WineCellar #TemperatureSensor).temperaturesensor_temperature >= 15 and (#WineCellar #HumiditySensor).humiditysensor_humidity >= 60) {

    (#AirConditioner).switch_on()

    (#Humidifier).switch_off()

}

# Generated
if ((#TemperatureSensor #WineCellar).temperaturesensor_temperature >= 15 and (#HumiditySensor #WineCellar).humiditysensor_humidity >= 60) {
  (#AirConditioner #WineCellar).airconditioner_setairconditionermode("cool")
  (#Humidifier #WineCellar).switch_off()
}
```

### Category 6 · Row 177

- Command (EN): If a water leak is detected in the basement and the main valve is open, close all main valves and sound the police siren.
- Command (KO): 지하에서 누수가 감지되고 메인 밸브가 열려 있으면, 모든 메인 밸브를 잠그고 경찰 사이렌을 울려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If a water leak is detected in the basement and the main valve is open, close all main valves and sound the police siren.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#Basement #LeakSensor).leaksensor_leakage == true and (#Main #Valve).valve_valvestate == true) {

    all(#Main #Valve).valve_close()

    (#Siren).siren_setsirenmode("police")

}

# Generated
if ((#LeakSensor).leaksensor_leakage == true and (#Valve).valve_valvestate == true) {
  (#Valve).valve_close()
  (#Siren).siren_setsirenmode("police")
}
```

### Category 6 · Row 178

- Command (EN): If the warehouse fine dust level is 100 or higher and the air purifier is in auto mode, switch it to high mode and say through the warehouse speaker "Switching to high mode".
- Command (KO): 창고 미세먼지가 100 이상이고 공기청정기가 자동 모드이면, 모드를 강풍 모드로 바꾸고 창고 스피커로 "강풍 모드로 전환합니다"라고 말해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the warehouse fine dust level is 100 or higher and the air purifier is in auto mode, switch it to high mode and say through the warehouse speaker "Switching to high mode".: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#Warehouse #AirQualitySensor).airqualitysensor_finedustlevel >= 100 and (#Warehouse #AirPurifier).airpurifier_airpurifiermode == "auto") {

    (#Warehouse #AirPurifier).airpurifier_setairpurifiermode("high")

    (#Warehouse #Speaker).speaker_speak("강풍 모드로 전환합니다")

}

# Generated
if ((#AirQualitySensor #Warehouse).airqualitysensor_finedustlevel >= 100 and (#AirPurifier #Warehouse).airpurifier_airpurifiermode == "auto") {
  (#AirPurifier #Warehouse).airpurifier_setairpurifiermode("high")
  (#Speaker #Warehouse).speaker_speak("Switching to high mode")
}
```

### Category 6 · Row 179

- Command (EN): If the motion is detected in the guest room and the air conditioner is off, set the air conditioner to auto mode and set the target temperature to 24.
- Command (KO): 게스트룸에 움직임이 감지되고 있고 에어컨이 꺼져 있으면, 에어컨을 자동 모드로 설정하고 목표 온도를 24도로 설정해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "precondition"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: If the motion is detected in the guest room and the air conditioner is off, set the air conditioner to auto mode and set the target temperature to 24.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#GuestRoom #MotionSensor).motionsensor_motion == true and (#GuestRoom #AirConditioner).switch_switch == false) {

    (#GuestRoom #AirConditioner).airconditioner_setairconditionermode("auto")

    (#GuestRoom #AirConditioner).airconditioner_settargettemperature(24)

}

# Generated
if ((#MotionSensor).motionsensor_motion == true and (#AirConditioner).switch_switch == false) {
  (#AirConditioner).airconditioner_setairconditionermode("auto")
  (#AirConditioner).airconditioner_settargettemperature(24)
}
```

### Category 6 · Row 180

- Command (EN): If the living room light is on and the illuminance is 50 lux or higher, close the living room blind and set the AC to auto mode.
- Command (KO): 거실 조명이 켜져 있고 조도가 50 럭스 이상이면, 거실 블라인드를 닫고 에어컨을 자동 모드로 설정해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "precondition"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: If the living room light is on and the illuminance is 50 lux or higher, close the living room blind and set the AC to auto mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#LivingRoom #Light).switch_switch == true and (#LivingRoom #LightSensor).lightsensor_brightness >= 50) {

    (#LivingRoom #Blind).windowcovering_downorclose()

    (#LivingRoom #AirConditioner).airconditioner_setairconditionermode("auto")

}

# Generated
if ((#Light #LivingRoom).light_currentbrightness > 0 and (#LightSensor #LivingRoom).lightsensor_brightness >= 50) {
  (#WindowCovering #LivingRoom).windowcovering_downorclose()
  (#AirConditioner #LivingRoom).airconditioner_setairconditionermode("auto")
}
```

### Category 7 · Row 181

- Command (EN): Every 10 minutes, if the temperature is 30 degrees or higher, set the air conditioner to cool mode.
- Command (KO): 10분마다 확인해서 온도가 30도 이상이면 에어컨을 쿨모드로 설정해줘.
- DET: `56.4728`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic", "service_match", "unknown_service:temperaturemeasurement_temperature"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: Every 10 minutes, if the temperature is 30 degrees or higher, set the air conditioner to cool mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#TemperatureSensor).temperaturesensor_temperature >= 30) {

    (#AirConditioner).airconditioner_setairconditionermode("cool")

}

# Generated
if ((#TemperatureSensor).temperaturemeasurement_temperature >= 30.0) {
  (#AirConditioner).airconditioner_setairconditionermode("cool")
}
```

### Category 7 · Row 182

- Command (EN): Every 30 minutes, if the temperature is 20 degrees or higher and below 30 degrees, set the air conditioner to auto mode; if it is 30 degrees or higher, set it to cool mode.
- Command (KO): 30분마다 체크해서 온도가 20도 이상, 30도 미만이면 에어컨을 자동모드로 설정하고, 30도 이상이면 쿨모드로 설정해줘.
- DET: `61.8326`
- Failure reasons: `["dataflow", "enum_grounding", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic", "service_match", "unknown_service:temperaturemeasurement_temperature"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md`
- Analysis: Every 30 minutes, if the temperature is 20 degrees or higher and below 30 degrees, set the air conditioner to auto mode; if it is 30 degrees or higher, set it to cool mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
temp = (#TemperatureSensor).temperaturesensor_temperature

if (temp >= 20 and temp < 30) {

    (#AirConditioner).airconditioner_setairconditionermode("auto")

} else if (temp >= 30) {

    (#AirConditioner).airconditioner_setairconditionermode("cool")

}

# Generated
temp = (#TemperatureSensor).temperaturemeasurement_temperature
if (temp >= 20 and temp < 30) {
  (#AirConditioner).airconditioner_setairconditionermode("auto")
} else if (temp >= 30) {
  (#AirConditioner).airconditioner_setairconditionermode("cool")
}
```

### Category 7 · Row 184

- Command (EN): On weekends at 3 PM, check for leakage; if detected, set the siren to emergency mode.
- Command (KO): 주말 오후 3시에 누수를 체크해서 감지되면 긴급 사이렌을 울려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: On weekends at 3 PM, check for leakage; if detected, set the siren to emergency mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#LeakSensor).leaksensor_leakage == true) {

    (#Siren).siren_setsirenmode("emergency")
}

# Generated
if ((#LeakSensor).leaksensor_leakage == true) {
  (#Siren).siren_setsirenmode("emergency")
}
```

### Category 7 · Row 186

- Command (EN): Every 30 minutes on weekend afternoons, set the robot vacuum cleaner to auto mode.
- Command (KO): 주말 오후에 30분마다 로봇청소기를 자동모드로 작동시켜줘.
- DET: `60.4594`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Every 30 minutes on weekend afternoons, set the robot vacuum cleaner to auto mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#Clock).clock_hour == 0) {

    break

}

(#RobotVacuumCleaner).robotvacuumcleaner_setrobotvacuumcleanermodemode("auto")

# Generated
(#RobotVacuumCleaner).robotvacuumcleaner_setrobotvacuumcleanermodemode("auto")
```

### Category 7 · Row 187

- Command (EN): From 10 PM to midnight every 10 minutes, sound the emergency siren.
- Command (KO): 밤10시부터 자정까지 10분마다 긴급 사이렌을 울려줘.
- DET: `42.4734`
- Failure reasons: `["arg_type", "dataflow", "enum_grounding", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic", "service_match", "unknown_service:sirenmode_setsirenmode"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: From 10 PM to midnight every 10 minutes, sound the emergency siren.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
if ((#Clock).clock_hour == 0) {

    break

}

(#Siren).siren_setsirenmode("emergency")

# Generated
if ((#Clock).clock_hour >= 22 and (#Clock).clock_hour < 24) {
  (#Siren).sirenmode_setsirenmode("emergency")
} else {
  break
}
```

### Category 7 · Row 191

- Command (EN): At 6 AM on Mondays and Wednesdays, announce the weather information through the speaker.
- Command (KO): 월요일과 수요일 오전 6시에 날씨 정보를 스피커로 알려줘.
- DET: `62.8316`
- Failure reasons: `["arg_type", "dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md`
- Analysis: At 6 AM on Mondays and Wednesdays, announce the weather information through the speaker.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다

```joi
# GT
(#Speaker).speaker_speak("현재 날씨는 " + (#WeatherProvider).weatherprovider_weather + "입니다")

# Generated
weatherInfo = (#WeatherProvider).weatherprovider_getweatherinfo(0 | 0)
(#Speaker).speaker_speak(weatherInfo)
```

### Category 7 · Row 193

- Command (EN): Every Monday at 8 AM, if both the safe and the door lock are locked, say 'It is safe' through the speaker
- Command (KO): 월요일 아침 8시마다 금고와 도어락이 모두 잠겨있으면 스피커로 "안전합니다"라고 말해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Every Monday at 8 AM, if both the safe and the door lock are locked, say 'It is safe' through the speaker: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#Safe).safe_safestate == "locked" and (#DoorLock).doorlock_doorlockstate == "locked") {

    (#Speaker).speaker_speak("안전합니다")

}

# Generated
if ((#Safe).safe_safestate == "closed" and (#DoorLock).doorlock_doorlockstate == "closed") {
  (#Speaker).speaker_speak("It is safe")
}
```

### Category 7 · Row 194

- Command (EN): Every 30 minutes from 7 PM to 10 PM, check the robot vacuum cleaner and start it in auto mode if it is stopped.
- Command (KO): 저녁 7시부터 10시까지 30분마다 로봇청소기를 체크해서 멈춰있으면 자동 모드로 실행시켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Every 30 minutes from 7 PM to 10 PM, check the robot vacuum cleaner and start it in auto mode if it is stopped.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#RobotVacuumCleaner).robotvacuumcleaner_robotvacuumcleanermode == "stop") {

    (#RobotVacuumCleaner).robotvacuumcleaner_setrobotvacuumcleanermodemode("auto")

}

# Generated
currentHour = (#Clock).clock_hour
if ((currentHour >= 19) and (currentHour < 22)) {
  mode = (#RobotVacuumCleaner).robotvacuumcleaner_robotvacuumcleanermode
  if (mode == "stop") {
    (#RobotVacuumCleaner).robotvacuumcleaner_setrobotvacuumcleanermodemode("auto")
  }
} else {
  break
}
```

### Category 7 · Row 197

- Command (EN): At 11 PM, if safe is unlocked or the door lock is unlocked , speak 'Check the safe and door lock' through the speaker.
- Command (KO): 오후 11시에 금고가 열려있거나 도어락이 열려있으면, 스피커로 "금고와 도어락을 확인하세요"라고 말해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: At 11 PM, if safe is unlocked or the door lock is unlocked , speak 'Check the safe and door lock' through the speaker.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#Safe).safe_safestate == "unlocked" or (#DoorLock).doorlock_doorlockstate == "unlocked") {

    (#Speaker).speaker_speak("금고와 도어락의 잠금 상태를 확인해 주세요.")

}

# Generated
if ((#Safe).safe_safestate == "open" or (#DoorLock).doorlock_doorlockstate == "open") {
  (#Speaker).speaker_speak("Check the safe and door lock")
}
```

### Category 7 · Row 199

- Command (EN): Check humidity every 10 minutes; if it's 50 or higher, turn off the humidifier; if it's 20 or lower, turn on the humidifier and set it to auto mode.
- Command (KO): 10분마다 습도를 체크해서 50 이상이면 가습기를 끄고 20 이하면 가습기를 켜고 자동모드로 설정해줘.
- DET: `64.2216`
- Failure reasons: `["dataflow", "enum_grounding", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md`
- Analysis: Check humidity every 10 minutes; if it's 50 or higher, turn off the humidifier; if it's 20 or lower, turn on the humidifier and set it to auto mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
hum = (#HumiditySensor).humiditysensor_humidity

if (hum >= 50) {

    (#Humidifier).switch_off()

} else if (hum <= 20) {

    (#Humidifier).switch_on()

    (#Humidifier).humidifier_sethumidifiermode("auto")

}

# Generated
humidity = (#HumiditySensor).humiditysensor_humidity
if (humidity >= 50) {
  (#Humidifier).humidifier_sethumidifiermode("off")
} else if (humidity <= 20) {
  (#Humidifier).humidifier_sethumidifiermode("auto")
}
```

### Category 7 · Row 200

- Command (EN): Check the fine dust level every hour; if it's 200 or higher, set the air purifier to high speed; if it's 100 or lower, set it to low speed.
- Command (KO): 1시간마다 미세먼지 농도를 체크해서 200 이상이면 공기청정기를 강풍모드로 설정하고 100 이하이면 미풍모드로 설정해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "enum_grounding", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md`
- Analysis: Check the fine dust level every hour; if it's 200 or higher, set the air purifier to high speed; if it's 100 or lower, set it to low speed.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
dust = (#AirQualitySensor).airqualitysensor_finedustlevel

if (dust >= 200) {

    (#AirPurifier).airpurifier_setairpurifiermode("high")

} else if (dust <= 100) {

    (#AirPurifier).airpurifier_setairpurifiermode("low")

}

# Generated
fineDust = (#AirQualitySensor).airqualitysensor_finedustlevel
if (fineDust >= 200) {
  (#AirPurifier).airpurifier_setairpurifiermode("high")
} else if (fineDust <= 100) {
  (#AirPurifier).airpurifier_setairpurifiermode("low")
}
```

### Category 7 · Row 204

- Command (EN): Every 30 minutes from now until midnight, output the current time through the speaker.
- Command (KO): 지금부터 자정까지 30분마다 현재 시각을 스피커로 출력해줘.
- DET: `63.8070`
- Failure reasons: `["gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: Every 30 minutes from now until midnight, output the current time through the speaker.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#Clock).clock_hour == 0) {

    break

}

(#Speaker).speaker_speak("현재 시각은 " + (#Clock).clock_hour + "시" + (#Clock).clock_minute + "분 입니다")

# Generated
currentTime = (#Clock).clock_time
(#Speaker).speaker_speak(currentTime)
if ((#Clock).clock_time == "0000") {
  break
}
```

### Category 7 · Row 205

- Command (EN): Every 10 minutes from now until 3 PM, sound the emergency siren for 5 seconds and then turn it off.
- Command (KO): 지금부터 오후 3시까지 10분마다 긴급 사이렌을 5초간 울렸다 꺼줘.
- DET: `27.2736`
- Failure reasons: `["arg_type", "dataflow", "enum_grounding", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic", "service_match", "unknown_service:sirenmode_setsirenmode"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: Every 10 minutes from now until 3 PM, sound the emergency siren for 5 seconds and then turn it off.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
if ((#Clock).clock_hour == 15) {
 
    break

}

(#Siren).siren_setsirenmode("emergency")

delay(5 SEC)

(#Siren).switch_off()

# Generated
if ((#Clock).clock_time < 1500) {
  (#Siren).sirenmode_setsirenmode("emergency")
  (#Clock).clock_delay(5000)
  (#Siren).sirenmode_setsirenmode("off")
} else {
  break
}
```

### Category 7 · Row 208

- Command (EN): Every minute, if the humidity of all sensors in Group2 is 50% or higher, set all dehumidifiers to refresh mode.
- Command (KO): 그룹 2에 속한 습도 센서들을 1분마다 체크해서 모두 50% 이상이면, 모든 제습기를 리프레쉬 모드로 설정해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "numeric_grounding", "precondition", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Every minute, if the humidity of all sensors in Group2 is 50% or higher, set all dehumidifiers to refresh mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if (all(#Group2 #HumiditySensor).humiditysensor_humidity >= 50) {

    all(#Dehumidifier).dehumidifier_setdehumidifiermode("refreshing")

}

# Generated
if (all(#Group2 #HumiditySensor).humiditysensor_humidity >= 50.0) {
  all(#Group2 #Dehumidifier).dehumidifier_setdehumidifiermode("refreshing")
}
```

### Category 7 · Row 210

- Command (EN): Every morning at 7 AM, open all blinds in Zone 1.
- Command (KO): 매일 아침 7시에 구역1에 있는 모든 블라인드를 올려줘.
- DET: `69.9000`
- Failure reasons: `["gt_mismatch", "gt_receiver_coverage", "semantic"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: Every morning at 7 AM, open all blinds in Zone 1.: GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
all(#Sector1 #Blind).windowcovering_uporopen()

# Generated
all(#WindowCovering #Zone1).windowcovering_uporopen()
```

### Category 7 · Row 211

- Command (EN): Every 7 PM, if no one is detected on the 1st floor, turn off all lights; for the 2nd floor, check at 8 PM and turn off all its lights if no one is present.
- Command (KO): 밤 7시에 1층에 사람이 없으면 불을 다 꺼주고 2층은 8시에 사람이 없으면 불을 다 꺼줘.
- DET: `0.0000`
- Failure reasons: `["invalid_json"]`
- Recommended prompt files: `response_prompt_baseline_cot.md`
- Analysis: Every 7 PM, if no one is detected on the 1st floor, turn off all lights; for the 2nd floor, check at 8 PM and turn off all its lights if no one is present.: GT와 generated code의 구조 차이로 strict DET에서 감점되었습니다

```joi
# GT
if ((#Floor1 #PresenceSensor).presencesensor_presence == false) {

    all(#Floor1 #Light).switch_off()

}

delay(1 HOUR)

if ((#Floor2 #PresenceSensor).presencesensor_presence == false) {

    all(#Floor2 #Light).switch_off()

}

# Generated
<empty>
```

### Category 7 · Row 213

- Command (EN): At 6 PM on weekdays, if presence sensors in the office show no presence, turn off all air conditioners and humidifiers in the office.
- Command (KO): 평일 오후 6시에 사무실의 재실 센서가 부재 상태를 나타내면 사무실 에어컨과 가습기를 전부 꺼줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "precondition", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: At 6 PM on weekdays, if presence sensors in the office show no presence, turn off all air conditioners and humidifiers in the office.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#Office #PresenceSensor).presencesensor_presence == false) {

    all(#Office #AirConditioner).switch_off()

    all(#Office #Humidifier).switch_off()

}

# Generated
if ((#PresenceSensor #office).presencesensor_presence == false) {
  all(#AirConditioner #office).switch_off()
  all(#Humidifier #office).switch_off()
}
```

### Category 7 · Row 214

- Command (EN): Every 8 AM, open all blinds with odd tags, and at 9 AM, open all blinds with even tags.
- Command (KO): 아침 8시에 홀수 태그가 붙은 블라인드를 모두 열어주고, 9시에는 짝수 태그가 붙은 모든 블라인드를 열어줘.
- DET: `69.9000`
- Failure reasons: `["extraneous", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: Every 8 AM, open all blinds with odd tags, and at 9 AM, open all blinds with even tags.: 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
all(#Odd #Blind).windowcovering_uporopen()

delay(1 HOUR)

all(#Even #Blind).windowcovering_uporopen()

# Generated
hour = (#Clock).clock_hour
if (hour == 8) {
  all(#WindowCovering #odd).windowcovering_uporopen()
} else if (hour == 9) {
  all(#WindowCovering #even).windowcovering_uporopen()
}
```

### Category 7 · Row 216

- Command (EN): Every 10 PM, if presence is detected in the living room, turn on all lights.
- Command (KO): 밤 10시에 거실에 사람이 감지되면, 모든 불을 켜줘.
- DET: `60.2176`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Every 10 PM, if presence is detected in the living room, turn on all lights.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#LivingRoom #PresenceSensor).presencesensor_presence == true) {

    all(#Light).light_movetobrightness(100, 0)

}

# Generated
if ((#PresenceSensor #LivingRoom).presencesensor_presence == true) {
  all(#Light #LivingRoom).switch_on()
}
```

### Category 7 · Row 217

- Command (EN): At midnight, if motion is detected in the hallway, turn all hallway lights to 100% brightness.
- Command (KO): 자정에 복도에 움직임이 감지되면, 복도의 모든 조명을 100%로 켜줘.
- DET: `63.6313`
- Failure reasons: `["arg_type", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, response_prompt_baseline_cot.md, tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: At midnight, if motion is detected in the hallway, turn all hallway lights to 100% brightness.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#Hallway #MotionSensor).motionsensor_motion == true) {

    all(#Hallway #Light).light_movetobrightness(100, 0)

}

# Generated
if ((#MotionSensor #hallway).motionsensor_motion == true) {
  all(#Light #hallway).levelcontrol_movetolevel(100 | 100)
}
```

### Category 7 · Row 219

- Command (EN): If no motion is detected between 10 PM and 11 PM, lock all door locks.
- Command (KO): 밤 10시부터 11시까지 움직임이 한번도 감지되지 않았으면, 모든 도어락을 잠궈줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: If no motion is detected between 10 PM and 11 PM, lock all door locks.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#MotionSensor).motionsensor_motion == true) {

    break

}

if ((#Clock).clock_hour == 23) {

    all(#DoorLock).doorlock_lock()

    break

}

# Generated
if (((#Clock).clock_hour >= 22) and ((#Clock).clock_hour < 23)) {
  if ((#MotionSensor).motionsensor_motion == false) {
    (#DoorLock).doorlock_lock()
  }
}
```

### Category 7 · Row 222

- Command (EN): Every morning at 8 AM, make the speaker speak 'Get up'. Additionally, if the window is closed, open it.
- Command (KO): 매일 아침 8시에 스피커로 ‘일어나세요’라고 말해 줘. 그리고 창문이 닫혀있으면 열어줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Every morning at 8 AM, make the speaker speak 'Get up'. Additionally, if the window is closed, open it.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
(#Speaker).speaker_speak("일어나세요")

if ((#Window).armrobot_currentposition == 0) {

    (#Window).windowcovering_uporopen()

}

# Generated
if ((#WindowCovering).windowcovering_currentposition == 0) {
  (#WindowCovering).windowcovering_uporopen()
}
(#Speaker).speaker_speak("Get up")
```

### Category 7 · Row 223

- Command (EN): Every 30 seconds from 10 PM to 11 PM, check for rain every 30 seconds; if it rains, close the window.
- Command (KO): 오후 10시부터 11시까지 30초마다 비를 감지해서 비가 오면 창문을 닫아줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Every 30 seconds from 10 PM to 11 PM, check for rain every 30 seconds; if it rains, close the window.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#Clock).clock_hour == 23) {

    break

}

if ((#RainSensor).rainsensor_rain == true) {

    (#Window).windowcovering_downorclose()

}

# Generated
if (((#Clock).clock_hour >= 22) and ((#Clock).clock_hour < 23)) {
  if ((#RainSensor).rainsensor_rain == true) {
    (#WindowCovering).windowcovering_downorclose()
  }
} else {
  break
}
```

### Category 7 · Row 224

- Command (EN): Every 5 seconds on weekends, if the pump is off, turn it on; if it is on, turn it off.
- Command (KO): 주말에 5초마다 체크해서 펌프가 꺼져 있으면 켜고, 켜져 있으면 꺼줘.
- DET: `38.5676`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "precondition", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Every 5 seconds on weekends, if the pump is off, turn it on; if it is on, turn it off.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#Clock).clock_weekday != "saturday" and (#Clock).clock_weekday != "sunday") {

    break

}

(#Pump).switch_toggle()

# Generated
if ((#Pump).switch_switch == "off") {
  (#Pump).switch_on()
} else if ((#Pump).switch_switch == "on") {
  (#Pump).switch_off()
}
```

### Category 7 · Row 225

- Command (EN): Measure the temperature every 15 minutes; turn on the air conditioner in cool mode if it's 25 degrees or higher, and turn it off if it's below 25 degrees.
- Command (KO): 15분마다 온도를 측정해서 25도 이상이면 에어컨을 냉방 모드로 켜고, 25도 미만이면 꺼줘.
- DET: `52.0000`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic", "service_match", "unknown_service:temperaturemeasurement_temperature"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: Measure the temperature every 15 minutes; turn on the air conditioner in cool mode if it's 25 degrees or higher, and turn it off if it's below 25 degrees.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#TemperatureSensor).temperaturesensor_temperature >= 25) {

    (#AirConditioner).airconditioner_setairconditionermode("cool")

} else {

    (#AirConditioner).switch_off()
}

# Generated
temp = (#TemperatureSensor).temperaturemeasurement_temperature
if (temp >= 25.0) {
  (#AirConditioner).airconditioner_setairconditionermode("cool")
} else if (temp < 25.0) {
  (#AirConditioner).airconditioner_setairconditionermode("off")
}
```

### Category 7 · Row 226

- Command (EN): Check every 5 minutes from 10 PM to 11 PM and turn it off when charging is complete.
- Command (KO): 오후 10시부터 11시까지 5분마다 체크해서 충전이 완료되면 꺼줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "precondition", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Check every 5 minutes from 10 PM to 11 PM and turn it off when charging is complete.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
if ((#Charger).charger_chargingstate == "fullyCharged") {

    (#Charger).switch_off()

}

# Generated
if ((#Charger).charger_chargingstate == "fullyCharged") {
  (#Charger).switch_off()
} else {
  break
}
```

### Category 7 · Row 228

- Command (EN): At 6 PM, if any window is open, close all of them.
- Command (KO): 오후 6시에 창문이 하나라도 열려있으면 모두 닫아줘.
- DET: `66.8476`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: At 6 PM, if any window is open, close all of them.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if (all(#Window).armrobot_currentposition >| 0) {

    all(#Window).windowcovering_downorclose()

}

# Generated
if (any(#WindowCovering).windowcovering_currentposition > 0) {
  all(#WindowCovering).windowcovering_downorclose()
}
```

### Category 7 · Row 230

- Command (EN): Every hour from 6 PM to 8 PM, if someone is detected on the 1st floor, turn on all 1st floor lights.
- Command (KO): 오후 6시부터 8시까지 1층에 사람이 감지되면 1층 불을 다 켜줘.
- DET: `68.1239`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Every hour from 6 PM to 8 PM, if someone is detected on the 1st floor, turn on all 1st floor lights.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#Clock).clock_hour >= 20) {

    break

}

if ((#Floor1 #PresenceSensor).presencesensor_presence == true) {

    all(#Floor1 #Light).switch_on()

}

# Generated
if ((#PresenceSensor #1stFloor).presencesensor_presence == true) {
  all(#Light #1stFloor).switch_on()
}
```

### Category 8 · Row 233

- Command (EN): Every 30 minutes, toggle the living room air purifier between sleep mode and auto mode.
- Command (KO): 30분마다 거실 공기청정기를 수면모드와 자동모드 사이에서 전환해줘.
- DET: `69.9000`
- Failure reasons: `["enum_grounding", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `tempo_prompt_9.md, grammar_ver1.5.10.md, service_prompt_10.md, response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: Every 30 minutes, toggle the living room air purifier between sleep mode and auto mode.: 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
mode := 0

if (mode == 0) {

    (#LivingRoom #AirPurifier).airpurifier_setairpurifiermode("sleep")

    mode = 1

} else {

    (#LivingRoom #AirPurifier).airpurifier_setairpurifiermode("auto")

    mode = 0

}

# Generated
mode = (#AirPurifier #LivingRoom).airpurifier_airpurifiermode
if (mode == "sleep") {
  (#AirPurifier #LivingRoom).airpurifier_setairpurifiermode("auto")
} else {
  (#AirPurifier #LivingRoom).airpurifier_setairpurifiermode("sleep")
}
```

### Category 8 · Row 235

- Command (EN): Every 30 minutes, toggle the air purifier between sleep mode and high speed mode.
- Command (KO): 30분마다 공기청정기를 수면모드와 강풍모드 사이에서 전환해줘.
- DET: `69.9000`
- Failure reasons: `["enum_grounding", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `tempo_prompt_9.md, grammar_ver1.5.10.md, service_prompt_10.md, response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: Every 30 minutes, toggle the air purifier between sleep mode and high speed mode.: 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
mode := 0

if (mode == 0) {

    (#AirPurifier).airpurifier_setairpurifiermode("sleep")

    mode = 1

} else {

    (#AirPurifier).airpurifier_setairpurifiermode("high")

    mode = 0

}

# Generated
toggle := false
if (toggle == false) {
  (#AirPurifier).airpurifier_setairpurifiermode("sleep")
  toggle = true
} else {
  (#AirPurifier).airpurifier_setairpurifiermode("high")
  toggle = false
}
```

### Category 8 · Row 236

- Command (EN): Whenever the humidity level drops to 30% or below, turn on the humidifier.
- Command (KO): 습도가 30% 이하로 떨어질 때마다 가습기를 켜줘.
- DET: `65.6067`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Whenever the humidity level drops to 30% or below, turn on the humidifier.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
triggered := false
if ((#HumiditySensor).humiditysensor_humidity <= 30) {
    if (triggered == false) {
        (#Humidifier).switch_on()
        triggered = true
    }
} else {
    triggered = false
}

# Generated
triggered := false
if ((#HumiditySensor).humiditysensor_humidity <= 30.0) {
  if (triggered == false) {
    (#Humidifier).humidifier_sethumidifiermode("auto")
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 237

- Command (EN): Whenever the rain stops, open the window.
- Command (KO): 비가 그칠 때마다 창문을 열어줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Whenever the rain stops, open the window.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
triggered := false
if ((#RainSensor).rainsensor_rain == false) {
    if (triggered == false) {
        (#Window).windowcovering_uporopen()
        triggered = true
    }
} else {
    triggered = false
}

# Generated
wait until ((#RainSensor).rainsensor_rain == false)
(#WindowCovering).windowcovering_uporopen()
```

### Category 8 · Row 239

- Command (EN): Each time the humidity drops below 50%, set the dehumidifier to drying mode.
- Command (KO): 습도가 50% 밑으로 떨어질 때마다 제습기를 건조모드로 작동해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Each time the humidity drops below 50%, set the dehumidifier to drying mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
triggered := false
if ((#HumiditySensor).humiditysensor_humidity < 50) {
    if (triggered == false) {
        (#Dehumidifier).dehumidifier_setdehumidifiermode("drying")
        triggered = true
    }
} else {
    triggered = false
}

# Generated
triggered := false
if ((#HumiditySensor).humiditysensor_humidity < 50.0) {
  if (triggered == false) {
    (#Dehumidifier).dehumidifier_setdehumidifiermode("drying")
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 240

- Command (EN): Whenever the window opens, make the speaker speak 'The window is open'.
- Command (KO): 창문이 열릴 때마다 스피커로 '창문이 열렸습니다'라고 말해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Whenever the window opens, make the speaker speak 'The window is open'.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
triggered := false
if ((#Window).armrobot_currentposition > 0) {
    if (triggered == false) {
        (#Speaker).speaker_speak("창문이 열렸습니다.")
        triggered = true
    }
} else {
    triggered = false
}

# Generated
triggered := false
if ((#WindowCovering).windowcovering_windowcoveringtype == "window" and (#WindowCovering).windowcovering_currentposition > 0) {
  if (triggered == false) {
    (#Speaker).speaker_speak("The window is open")
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 244

- Command (EN): Each time the carbon dioxide level reaches 900ppm or higher, close the valve.
- Command (KO): 이산화탄소 농도가 900ppm 이상이 될때마다 벨브를 닫아줘.
- DET: `65.8402`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Each time the carbon dioxide level reaches 900ppm or higher, close the valve.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
triggered := false
if ((#AirQualitySensor).airqualitysensor_carbondioxide >= 900) {
    if (triggered == false) {
        (#Valve).valve_close()
        triggered = true
    }
} else {
    triggered = false
}

# Generated
triggered := false
if ((#CarbonDioxideSensor).carbondioxidesensor_carbondioxide >= 900.0) {
  if (triggered == false) {
    (#Valve).valve_close()
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 245

- Command (EN): Whenever the temperature becomes 30 degrees or higher, close the blind.
- Command (KO): 온도가 30도 이상이 될 때마다 블라인드를 닫아줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Whenever the temperature becomes 30 degrees or higher, close the blind.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
triggered := false
if ((#TemperatureSensor).temperaturesensor_temperature >= 30) {
    if (triggered == false) {
        (#Blind).windowcovering_downorclose()
        triggered = true
    }
} else {
    triggered = false
}

# Generated
wait until ((#TemperatureSensor).temperaturesensor_temperature >= 30.0)
(#WindowCovering).windowcovering_downorclose()
```

### Category 8 · Row 246

- Command (EN): When the door opens, make the speaker speak "Welcome" every minute thereafter.
- Command (KO): 문이 열리면 이후에 1분마다 스피커로 "어서오세요"를 출력해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When the door opens, make the speaker speak "Welcome" every minute thereafter.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#Door).door_doorstate == "open")

    active = 1

}

(#Speaker).speaker_speak("어서오세요")

# Generated
triggered := false
if (triggered == false) {
  wait until ((#Door).door_doorstate == "open")
  triggered = true
}
if (triggered == true) {
  (#Speaker).speaker_speak("Welcome")
}
```

### Category 8 · Row 247

- Command (EN): When the contact sensor is closed, sound the police siren every 10 seconds.
- Command (KO): 접촉센서가 닫히면 10초마다 경찰 사이렌을 울려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: When the contact sensor is closed, sound the police siren every 10 seconds.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#ContactSensor).contactsensor_contact == true)

    active = 1

}

(#Siren).siren_setsirenmode("police")

# Generated
triggered := false
if ((#ContactSensor).contactsensor_contact == true) {
  if (triggered == false) {
    (#Siren).siren_setsirenmode("police")
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 248

- Command (EN): Once the entrance door is opened, check the safe every 5 minutes and announce "The safe is open" through the speaker if it's not locked.
- Command (KO): 현관문이 열리면 그 후부터 5분마다 금고를 체크해서 잠겨있지 않으면 스피커로 금고가 열려있다고 출력해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Once the entrance door is opened, check the safe every 5 minutes and announce "The safe is open" through the speaker if it's not locked.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#Entrance #Door).door_doorstate == "open")

    active = 1

}

if ((#Safe).safe_safestate != "locked") {

    (#Speaker).speaker_speak("금고가 열려있습니다")

}

# Generated
triggered := false
if (triggered == false) {
  wait until ((#Door).door_doorstate == "open")
  triggered = true
}
if (triggered == true) {
  safeState = (#Safe).safe_safestate
  if (safeState != "closed") {
    (#Speaker).speaker_speak("The safe is open")
  }
}
```

### Category 8 · Row 249

- Command (EN): When a leak is detected, close the valve immediately and give a warning broadcast through the speaker every minute.
- Command (KO): 누수가 감지되면 즉시 밸브를 잠그고 1분마다 스피커로 "누수가 감지되었습니다. 대피하세요"라고 출력해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When a leak is detected, close the valve immediately and give a warning broadcast through the speaker every minute.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#LeakSensor).leaksensor_leakage == true)

    (#Valve).valve_close()

    active = 1

}

(#Speaker).speaker_speak("누수가 감지되었습니다. 대피하세요")

# Generated
triggered := false
if (triggered == false) {
  wait until ((#LeakSensor).leaksensor_leakage == true)
  (#Valve).valve_close()
  triggered = true
} else {
  (#Speaker).speaker_speak("Warning: Leak detected!")
}
```

### Category 8 · Row 250

- Command (EN): When smoke is detected, sound the emergency siren for 5 seconds every minute.
- Command (KO): 연기가 감지되면 1분마다 긴급 사이렌을 5초간 울려줘.
- DET: `62.7653`
- Failure reasons: `["arg_type", "dataflow", "enum_grounding", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: When smoke is detected, sound the emergency siren for 5 seconds every minute.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#SmokeDetector).smokedetector_smoke == true)

    active = 1

}

(#Siren).siren_setsirenmode("fire")

delay(5 SEC)

(#Siren).switch_off()

# Generated
triggered := false
if ((#SmokeDetector).smokedetector_smoke == true) {
  if (triggered == false) {
    (#Siren).siren_setsirenmode("emergency")
    (#Clock).clock_delay(5000)
    (#Siren).siren_setsirenmode("off")
    triggered = true
  }
} else {
  triggered = false
  (#Siren).siren_setsirenmode("off")
}
```

### Category 8 · Row 251

- Command (EN): At midnight, close the door and check the light every hour until 6 AM; if the brightness is greater than 30, lower it to 10.
- Command (KO): 자정이 되면 문을 닫고, 오전 6시까지 한 시간마다 조명을 체크해서 밝기가 30보다 크면 10으로 낮춰줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, response_prompt_baseline_cot.md, tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: At midnight, close the door and check the light every hour until 6 AM; if the brightness is greater than 30, lower it to 10.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    (#Door).door_close()

    active = 1

}

if ((#Clock).clock_hour == 6) {

    break

}

if ((#Light).lightsensor_brightness > 30) {

    (#Light).light_movetobrightness(10)

}

# Generated
hour = (#Clock).clock_hour
if (hour >= 0 and hour < 6) {
  (#Door).door_close()
  brightness = (#Light).light_currentbrightness
  if (brightness > 30) {
    (#Light).light_movetobrightness(10 | 100)
  }
} else {
  break
}
```

### Category 8 · Row 252

- Command (EN): When the charger voltage drops to 4V or lower, speak "The charging voltage is low" through the speaker every 30 minutes.
- Command (KO): 충전기 전압이 4V 이하로 떨어지면 30분마다 "충전 전압이 낮습니다"라고 스피커로 말해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: When the charger voltage drops to 4V or lower, speak "The charging voltage is low" through the speaker every 30 minutes.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#Charger).charger_voltage <= 4000)

    active = 1

}

(#Speaker).speaker_speak("충전 전압이 낮습니다")

# Generated
triggered := false
if ((#Charger).charger_voltage <= 4.0) {
  if (triggered == false) {
    (#Speaker).speaker_speak("The charging voltage is low")
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 253

- Command (EN): When a smoke is detected, announce it through the speaker and send an email every 5 minutes to "test@example.com" with the subject "Fire Warning" and the content "A fire has occurred. Please evacuate.".
- Command (KO): 연기가 감지되면 스피커로 화재를 알리고, 이후 5분마다 test@example.com으로 "화재 경고"라는 제목과 "화재가 발생했습니다. 대피하세요"라는 내용의 이메일을 보내줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: When a smoke is detected, announce it through the speaker and send an email every 5 minutes to "test@example.com" with the subject "Fire Warning" and the content "A fire has occurred. Please evacuate.".: 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#SmokeDetector).smokedetector_smoke == true)

    (#Speaker).speaker_speak("화재 발생! 즉시 대피하세요." )

    active = 1

}

(#EmailProvider).emailprovider_sendmail("test@example.com", "화재 경고", "화재가 발생했습니다. 대피하세요.")

# Generated
triggered := false
if ((#SmokeDetector).smokedetector_smoke == true) {
  if (triggered == false) {
    (#Speaker).speaker_speak("Smoke detected")
    (#EmailProvider).emailprovider_sendmail("test@example.com" | "Fire Warning" | "A fire has occurred. Please evacuate.")
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 254

- Command (EN): When the drying is finished, say 'Please take out the laundry' through the speaker every 10 minutes.
- Command (KO): 건조가 끝나면 10분마다 '세탁물을 꺼내세요'라고 스피커로 말해줘.
- DET: `62.1192`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: When the drying is finished, say 'Please take out the laundry' through the speaker every 10 minutes.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#LaundryDryer).laundrydryer_spinspeed == 0)

    active = 1

}

(#Speaker).speaker_speak("세탁물을 꺼내세요")

# Generated
triggered := false
if ((#LaundryDryer).laundrydryer_laundrydryermode == "finished") {
  if (triggered == false) {
    (#Speaker).speaker_speak("Please take out the laundry")
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 255

- Command (EN): If motion is detected, capture an image every 10 seconds thereafter.
- Command (KO): 움직임이 감지되면 그 뒤로 10초마다 사진을 찍어줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: If motion is detected, capture an image every 10 seconds thereafter.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#MotionSensor).motionsensor_motion == true)

    active = 1

}

(#Camera).camera_captureimage()

# Generated
triggered := false
if ((#MotionSensor).motionsensor_motion == true) {
  if (triggered == false) {
    (#Camera).camera_captureimage()
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 256

- Command (EN): Whenever the humidity reaches 50% or higher, set all dehumidifiers with the Group 1 tag to drying mode.
- Command (KO): 습도가 50% 이상이 될 때마다, 그룹1 태그가 붙은 제습기를 모두 건조모드로 작동시켜.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Whenever the humidity reaches 50% or higher, set all dehumidifiers with the Group 1 tag to drying mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
prev := (#HumiditySensor).humiditysensor_humidity

curr = (#HumiditySensor).humiditysensor_humidity

if (prev < 50 and curr >= 50) {

    all(#Group1 #Dehumidifier).dehumidifier_setdehumidifiermode("drying")

}

prev = curr

# Generated
wait until (any(#HumiditySensor).humiditysensor_humidity >= 50.0)
(#Dehumidifier #Group1).dehumidifier_setdehumidifiermode("drying")
```

### Category 8 · Row 257

- Command (EN): Whenever the brightness drops below 200 lux, turn on all lights.
- Command (KO): 조도가 200럭스보다 낮아질 때마다 모든 조명을 켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Whenever the brightness drops below 200 lux, turn on all lights.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
prev := (#LightSensor).lightsensor_brightness

curr = (#LightSensor).lightsensor_brightness

if (prev >= 200 and curr < 200) {
 
    all(#Light).switch_on()

}

prev = curr

# Generated
triggered := false
if ((#LightSensor).lightsensor_brightness < 200) {
  if (triggered == false) {
    all(#Light).switch_on()
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 258

- Command (EN): Whenever a light in the upper part is turned on, turn on a light in the lower part as well.
- Command (KO): 상단부에 있는 조명이 켜질 때마다, 하단부에 있는 조명도 켜줘.
- DET: `66.7212`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Whenever a light in the upper part is turned on, turn on a light in the lower part as well.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
prev := (#Top #Light).switch_switch

curr = (#Top #Light).switch_switch

if (prev == false and curr == true) {

    (#Bottom #Light).switch_on()

}

prev = curr

# Generated
triggered := false
if ((#Light #Upper).switch_switch == true) {
  if (triggered == false) {
    (#Light #Lower).switch_on()
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 260

- Command (EN): Every time the button with the 'Robot' tag is pressed, set all robot vacuum cleaners with 'Even' tags to auto mode.
- Command (KO): 로봇 태그가 붙은 버튼이 눌릴때마다, 짝수 태그 로봇청소기들을 모두 자동모드로 작동시켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Every time the button with the 'Robot' tag is pressed, set all robot vacuum cleaners with 'Even' tags to auto mode.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
prev := (#Robot #Button).button_button

curr = (#Robot #Button).button_button

if (prev != "pushed" and curr == "pushed") {

    all(#Even #RobotVacuumCleaner).robotvacuumcleaner_setrobotvacuumcleanermodemode("auto")

}

prev = curr

# Generated
triggered := false
if ((#Button #Robot).button_button == "pushed") {
  if (triggered == false) {
    (#RobotVacuumCleaner #Even).robotvacuumcleaner_setrobotvacuumcleanermodemode("auto")
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 261

- Command (EN): Each time the door is opened, turn on all lights in the hallway and living room.
- Command (KO): 문이 열릴 때마다, 복도와 거실의 조명을 모두 켜줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Each time the door is opened, turn on all lights in the hallway and living room.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
prev := (#Door).door_doorstate

curr = (#Door).door_doorstate

if (prev != "open" and curr == "open") {

    all(#Hallway #Light).switch_on()

    all(#LivingRoom #Light).switch_on()

}

prev = curr

# Generated
triggered := false
if ((#Door).door_doorstate == "open") {
  if (triggered == false) {
    (#Light #hallway).switch_on()
    (#Light #livingroom).switch_on()
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 262

- Command (EN): Whenever the button with the 'Stop' tag is pressed, turn off all devices with 'Even' tags.
- Command (KO): 중단 태그가 달린 버튼이 눌릴때마다 짝수 태그가 붙은 장치들을 모두 꺼줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "precondition", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Whenever the button with the 'Stop' tag is pressed, turn off all devices with 'Even' tags.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
prev := (#Stop #Button).button_button

curr = (#Stop #Button).button_button

if (prev != "pushed" and curr == "pushed") {

    all(#Even).switch_off()

}

prev = curr

# Generated
triggered := false
if ((#Button #Stop).button_button == "pushed") {
  if (triggered == false) {
    all(#Even).switch_off()
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 263

- Command (EN): Whenever it rains, close all windows and doors.
- Command (KO): 비가 올때마다, 모든 창문과 문을 닫아줘
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Whenever it rains, close all windows and doors.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
prev := (#RainSensor).rainsensor_rain

curr = (#RainSensor).rainsensor_rain

if (prev == false and curr == true) {

    all(#Window).windowcovering_downorclose()

    all(#Door).door_close()

}

prev = curr

# Generated
wait until ((#RainSensor).rainsensor_rain == true)
(#WindowCovering).windowcovering_downorclose()
(#Door).door_close()
```

### Category 8 · Row 264

- Command (EN): Whenever the door lock is locked, turn on the entrance light at maximum brightness for 10 seconds and then turn it off.
- Command (KO): 도어락이 잠길때마다 입구의 조명을 최대밝기로 10초 유지하다가 꺼줘.
- DET: `69.9000`
- Failure reasons: `["arg_type", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, response_prompt_baseline_cot.md, tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: Whenever the door lock is locked, turn on the entrance light at maximum brightness for 10 seconds and then turn it off.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
prev := (#DoorLock).doorlock_doorlockstate

curr = (#DoorLock).doorlock_doorlockstate

if (prev != "closed" and curr == "closed") {

    (#Entrance #Light).levelcontrol_movetolevel(100, 0)

    delay(10 SEC)

    (#Entrance #Light).switch_off()

}

prev = curr

# Generated
wait until ((#DoorLock).doorlock_doorlockstate == "closed")
(#Light).light_movetobrightness(100 | 100)
(#Clock).clock_delay(10000)
(#Light).switch_off()
```

### Category 8 · Row 265

- Command (EN): Whenever motion is detected at the entrance, turn on the entrance light at maximum brightness and then turn it off after 3 seconds.
- Command (KO): 입구에 움직임이 감지될 때마다 입구 조명을 최대밝기로 켰다가 3초 뒤에 꺼줘.
- DET: `57.9697`
- Failure reasons: `["arg_type", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, response_prompt_baseline_cot.md, tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: Whenever motion is detected at the entrance, turn on the entrance light at maximum brightness and then turn it off after 3 seconds.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT

prev := (#Entrance #MotionSensor).motionsensor_motion

curr = (#Entrance #MotionSensor).motionsensor_motion

if (prev == false and curr == true) {

    (#Entrance #Light).levelcontrol_movetolevel(100, 0)

    delay(3
 SEC)

    (#Entrance #Light).switch_off()

}

prev = curr

# Generated
wait until ((#PresenceSensor).presencesensor_presence == true)
(#Light #Entrance).light_movetobrightness(100 | 0)
(#Light #Entrance).switch_off()
(#Clock).clock_delay(3000)
```

### Category 8 · Row 266

- Command (EN): Whenever the brightness drops below 50 lux, open all shades in the parking lot.
- Command (KO): 조도가 50럭스 미만으로 떨어질 때마다 주차장의 모든 쉐이드를 열어줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: Whenever the brightness drops below 50 lux, open all shades in the parking lot.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
prev := (#LightSensor).lightsensor_brightness

curr = (#LightSensor).lightsensor_brightness

if (prev >= 50 and curr < 50) {

    all(#ParkingLot #Shade).windowcovering_uporopen()

}

prev = curr

# Generated
triggered := false
if ((#LightSensor).lightsensor_brightness < 50) {
  if (triggered == false) {
    all(#WindowCovering).windowcovering_uporopen()
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 267

- Command (EN): When the server rack humidity becomes higher than 70%, set the lab dehumidifier to dehumidifying mode and check the humidity every hour; turn it off if it's below 50%.
- Command (KO): 서버 랙 습도가 70%보다 높아지면 연구실 제습기를 제습모드로 설정하고 1시간마다 습도를 다시 체크해서 50% 밑이면 제습기를 꺼줘.
- DET: `64.3892`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "precondition"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: When the server rack humidity becomes higher than 70%, set the lab dehumidifier to dehumidifying mode and check the humidity every hour; turn it off if it's below 50%.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#ServerRack #HumiditySensor).humiditysensor_humidity > 70)

    (#Lab #Dehumidifier).dehumidifier_setdehumidifiermode("dehumidifying")

    active = 1

}

if ((#ServerRack #HumiditySensor).humiditysensor_humidity < 50) {

    (#Lab #Dehumidifier).switch_off()

}

# Generated
triggered := false
humidity = (#HumiditySensor).humiditysensor_humidity
if (humidity > 70.0) {
  if (triggered == false) {
    (#Dehumidifier).dehumidifier_setdehumidifiermode("dehumidifying")
    triggered = true
  }
} else if (humidity < 50.0) {
  if (triggered == true) {
    (#Dehumidifier).dehumidifier_setdehumidifiermode("finished")
    triggered = false
  }
}
```

### Category 8 · Row 268

- Command (EN): When the carbon dioxide level in the parking lot exceeds 880 ppm, speak "CO2 level danger" through the parking lot speaker every 10 seconds.
- Command (KO): 주차장 이산화탄소 농도가 880ppm보다 높아지면, 10초마다 "CO2 농도 위험"이라고 주차장 스피커로 출력해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: When the carbon dioxide level in the parking lot exceeds 880 ppm, speak "CO2 level danger" through the parking lot speaker every 10 seconds.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#ParkingLot #AirQualitySensor).airqualitysensor_carbondioxide > 880)

    active = 1

}

(#ParkingLot #Speaker).speaker_speak("CO2 농도 위험")

# Generated
triggered := false
if ((#AirQualitySensor #ParkingLot).airqualitysensor_carbondioxide > 880) {
  if (triggered == false) {
    triggered = true
  }
} else {
  triggered = false
}
if (triggered == true) {
  (#Speaker #ParkingLot).speaker_speak("CO2 level danger")
}
```

### Category 8 · Row 269

- Command (EN): When smoke is detected in the living room, sound all fire alarms. Then, speak "Please evacuate" through the speaker every 10 seconds.
- Command (KO): 거실에서 연기가 감지되면 모든 화재 경보를 울리고, 10초마다 스피커로 "대피하세요"라고 출력해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "extraneous", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: When smoke is detected in the living room, sound all fire alarms. Then, speak "Please evacuate" through the speaker every 10 seconds.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#LivingRoom #SmokeDetector).smokedetector_smoke == true)

    all(#Siren).siren_setsirenmode("fire")

    active = 1

}

(#Speaker).speaker_speak("대피하세요")

# Generated
triggered := false
if (triggered == false) {
  wait until ((#SmokeDetector #LivingRoom).smokedetector_smoke == true)
  (#Siren).siren_setsirenmode("fire")
  triggered = true
} else {
  (#Speaker).speaker_speak("Please evacuate")
}
```

### Category 8 · Row 270

- Command (EN): When any presence sensor on the 1st floor detects presence, sound all emergency sirens for 3 seconds every minute and then turn them off.
- Command (KO): 1층에서 재실센서가 하나라도 감지되면, 1분마다 모든 긴급 사이렌을 3초간 울렸다 꺼줘.
- DET: `61.4168`
- Failure reasons: `["arg_type", "dataflow", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "precondition", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: When any presence sensor on the 1st floor detects presence, sound all emergency sirens for 3 seconds every minute and then turn them off.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until (all(#Floor1 #PresenceSensor).presencesensor_presence ==| true)

    active = 1

}

all(#Siren).siren_setsirenmode("emergency")

delay(3 SEC)

all(#Siren).switch_off()

# Generated
triggered := false
if (any(#PresenceSensor #1stFloor).presencesensor_presence == true) {
  if (triggered == false) {
    (#Siren).siren_setsirenmode("emergency")
    (#Clock).clock_delay(3000)
    (#Siren).siren_setsirenmode("off")
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 271

- Command (EN): When motion is detected in the lobby, capture an image of the lobby every 30 seconds.
- Command (KO): 로비에서 움직임이 감지되면 30초마다 로비 사진을 찍어줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: When motion is detected in the lobby, capture an image of the lobby every 30 seconds.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#Lobby #MotionSensor).motionsensor_motion == true)

    active = 1

}

(#Lobby #Camera).camera_captureimage()

# Generated
triggered := false
if ((#MotionSensor #lobby).motionsensor_motion == true) {
  if (triggered == false) {
    (#Camera #lobby).camera_captureimage()
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 272

- Command (EN): When smoke is detected by the kitchen smoke detector, speak "Fire outbreak" every 10 seconds through the living room speaker.
- Command (KO): 주방의 연기 감지기로 연기가 감지가 되면 거실 스피커로 10초마다 "화재 발생"이라고 말해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "numeric_grounding", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, tempo_prompt_9.md`
- Analysis: When smoke is detected by the kitchen smoke detector, speak "Fire outbreak" every 10 seconds through the living room speaker.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
active := 0

if (active == 0) {

    wait until ((#Kitchen #SmokeDetector).smokedetector_smoke == true)

    active = 1

}

(#LivingRoom #Speaker).speaker_speak("화재 발생")

# Generated
triggered := false
if ((#SmokeDetector #kitchen).smokedetector_smoke == true) {
  if (triggered == false) {
    triggered = true
  }
  if (triggered == true) {
    (#Speaker #livingroom).speaker_speak("Fire outbreak")
  }
} else {
  triggered = false
}
```

### Category 8 · Row 273

- Command (EN): Whenever the kitchen leak sensor detects a leak, start streaming with the kitchen camera.
- Command (KO): 주방의 누수 센서가 감지될 때마다 주방 카메라로 스트리밍을 시작해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Whenever the kitchen leak sensor detects a leak, start streaming with the kitchen camera.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
prev := (#Kitchen #LeakSensor).leaksensor_leakage

curr = (#Kitchen #LeakSensor).leaksensor_leakage

if (prev == false and curr == true) {

    (#Kitchen #Camera).camera_startstream()
}

prev = curr

# Generated
triggered := false
if ((#LeakSensor #kitchen).leaksensor_leakage == true) {
  if (triggered == false) {
    (#Camera #kitchen).camera_startstream()
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 274

- Command (EN): Whenever the motion sensor in the yard detects anything, sound the police siren.
- Command (KO): 마당에 있는 움직임 센서가 감지될 때마다 경찰 사이렌을 울려줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Whenever the motion sensor in the yard detects anything, sound the police siren.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
prev := (#Yard #MotionSensor).motionsensor_motion

curr = (#Yard #MotionSensor).motionsensor_motion

if (prev == false and curr == true) {

    (#Yard #Siren).siren_setsirenmode("police")

}

prev = curr

# Generated
triggered := false
if ((#MotionSensor).motionsensor_motion == true) {
  if (triggered == false) {
    (#Siren).siren_setsirenmode("police")
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 275

- Command (EN): Whenever button 2 of the multi-button is pressed, open all windows in the living room.
- Command (KO): 멀티버튼의 버튼2가 눌릴 때마다 거실의 창문을 모두 열어줘.
- DET: `60.0539`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "service_match", "unknown_service:multibutton_button2"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md, service_prompt_10.md, tempo_prompt_9.md`
- Analysis: Whenever button 2 of the multi-button is pressed, open all windows in the living room.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
prev := (#MultiButton).dimmerswitch_button2

curr = (#MultiButton).dimmerswitch_button2

if (prev != "pushed" and curr == "pushed") {

    all(#LivingRoom #Window).windowcovering_uporopen()

}

prev = curr

# Generated
triggered := false
if ((#MultiButton).multibutton_button2 == "pressed") {
  if (triggered == false) {
    (#WindowCovering #LivingRoom).windowcovering_uporopen()
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 278

- Command (EN): Every hour, alternate the air conditioner's target temperature between 25 and 20 degrees.
- Command (KO): 회의실 에어컨의 목표 온도를 1시간마다 25와 20으로 번갈아 설정해줘.
- DET: `69.9000`
- Failure reasons: `["gt_mismatch", "numeric_grounding"]`
- Recommended prompt files: `tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: Every hour, alternate the air conditioner's target temperature between 25 and 20 degrees.: 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
state := 0

if (state == 0) {

    (#MeetingRoom #AirConditioner).airconditioner_settargettemperature(25)

    state = 1

} else {

    (#MeetingRoom #AirConditioner).airconditioner_settargettemperature(20)

    state = 0

}

# Generated
temp := 25
if (temp == 25) {
  (#AirConditioner).airconditioner_settargettemperature(25)
  temp = 20
} else {
  (#AirConditioner).airconditioner_settargettemperature(20)
  temp = 25
}
```

### Category 8 · Row 279

- Command (EN): Whenever the car charger in the parking lot is fully charged, speak "Charging is complete" through the speaker.
- Command (KO): 주차장의 차량 충전기가 완충될때마다, 스피커로 "충전이 완료되었습니다"라고 말해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "gt_receiver_coverage"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Whenever the car charger in the parking lot is fully charged, speak "Charging is complete" through the speaker.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
prev := (#ParkingLot #Charger).charger_chargingstate

curr = (#ParkingLot #Charger).charger_chargingstate

if (prev != "fullyCharged" and curr == "fullyCharged") {

    (#ParkingLot #Speaker).speaker_speak("충전이 완료되었습니다.")

}

prev = curr

# Generated
triggered := false
if ((#Charger #parking_lot).charger_chargingstate == "fullyCharged") {
  if (triggered == false) {
    (#Speaker).speaker_speak("Charging is complete")
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 8 · Row 280

- Command (EN): Whenever the meeting room door is opened, turn on the light at maximum brightness and then turn it off after 10 seconds.
- Command (KO): 회의실 문이 열릴 때마다, 조명의 밝기를 최대밝기로 켰다가 10초뒤에 꺼줘.
- DET: `57.1637`
- Failure reasons: `["arg_type", "extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding", "semantic"]`
- Recommended prompt files: `service_prompt_10.md, caution_prompt_8.md, response_prompt_baseline_cot.md, tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: Whenever the meeting room door is opened, turn on the light at maximum brightness and then turn it off after 10 seconds.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
prev := (#MeetingRoom #Door).door_doorstate
 
curr = (#MeetingRoom #Door).door_doorstate

if (prev != "open" and curr == "open") {

    (#Light).levelcontrol_movetolevel(100, 0)

    delay(10 SEC)

    (#Light).switch_off()

}

prev = curr

# Generated
wait until ((#Door).door_doorstate == "open")
(#Light).light_movetobrightness(100 | 0)
(#Light).light_movetobrightness(0 | 0)
(#Clock).clock_delay(10000)
```
