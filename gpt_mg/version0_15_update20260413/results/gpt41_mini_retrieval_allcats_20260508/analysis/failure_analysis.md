# GPT-4.1-mini Category Failure Analysis

- Condition: `retrieval`
- Model: `gpt41_mini`
- Category runs: `8`
- Total failed rows: `7`

## Category Summary

| Category | Rows | Failures | Avg DET | Pass Rate | Exact Rate | Avg Prompt Tokens | Avg LLM Latency (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 30 | 0 | 99.6520 | 1.0000 | 0.8333 | 26844.13 | 2.4103 |
| 2 | 30 | 0 | 98.5588 | 1.0000 | 0.7667 | 23754.63 | 2.0799 |
| 3 | 30 | 2 | 97.3675 | 0.9333 | 0.7667 | 25244.43 | 2.2150 |
| 4 | 30 | 3 | 95.3780 | 0.9000 | 0.6000 | 25184.30 | 2.2673 |
| 5 | 30 | 1 | 96.7384 | 0.9667 | 0.6333 | 25433.77 | 2.3513 |
| 6 | 30 | 1 | 97.3721 | 0.9667 | 0.6667 | 25584.97 | 2.4624 |
| 7 | 50 | 0 | 95.0990 | 1.0000 | 0.3600 | 25771.56 | 2.5738 |
| 8 | 50 | 0 | 95.8522 | 1.0000 | 0.4000 | 25593.34 | 2.5570 |

## Failure Reason Distribution

- `gt_mismatch`: 7
- `gt_receiver_coverage`: 6
- `gt_service_coverage`: 6
- `semantic`: 4
- `extraneous`: 3
- `numeric_grounding`: 1
- `enum_grounding`: 1
- `dataflow`: 1

## Failure Case Analysis

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

### Category 3 · Row 90

- Command (EN): If the lab humidity is 50 or higher, turn on the dehumidifier, and if it's below 50, turn on the humidifier.
- Command (KO): 연구실 습도가 50 이상이면 제습기를 켜고 50 미만이면 가습기를 켜줘.
- DET: `69.9000`
- Failure reasons: `["gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "numeric_grounding"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md, tempo_prompt_9.md, grammar_ver1.5.10.md`
- Analysis: If the lab humidity is 50 or higher, turn on the dehumidifier, and if it's below 50, turn on the humidifier.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; 명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다

```joi
# GT
if ((#Lab #HumiditySensor).humiditysensor_humidity >= 50) {

    (#Lab #Dehumidifier).switch_on()

} else {

    (#Lab #Humidifier).switch_on()

}

# Generated
prev := (#HumiditySensor).humiditysensor_humidity

curr = (#HumiditySensor).humiditysensor_humidity

if (prev < 50 and curr >= 50) {

    all(#Group1 #Dehumidifier).dehumidifier_setdehumidifiermode("drying")

}

prev = curr
```

### Category 4 · Row 106

- Command (EN): When the entrance door lock is unlocked, turn on the living room light.
- Command (KO): 현관 도어락이 잠금해제되면 거실 조명을 켜줘.
- DET: `69.9000`
- Failure reasons: `["extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: When the entrance door lock is unlocked, turn on the living room light.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
wait until ((#Entrance #DoorLock).doorlock_doorlockstate == "unlocked")

(#LivingRoom #Light).switch_on()

# Generated
prev := (#DoorLock).doorlock_doorlockstate

curr = (#DoorLock).doorlock_doorlockstate

if (prev != "closed" and curr == "closed") {

    (#Entrance #Light).levelcontrol_movetolevel(100, 0)

    delay(10 SEC)

    (#Entrance #Light).switch_off()

}

prev = curr
```

### Category 4 · Row 107

- Command (EN): When motion is detected in the bedroom, turn on the bedroom air conditioner.
- Command (KO): 침실에 움직임이 감지되면 침실 에어컨을 켜줘.
- DET: `69.7752`
- Failure reasons: `["enum_grounding", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md, service_prompt_10.md`
- Analysis: When motion is detected in the bedroom, turn on the bedroom air conditioner.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다; mode/enum 값이 GT와 다르게 선택됐습니다

```joi
# GT
wait until ((#Bedroom #MotionSensor).motionsensor_motion == true)

(#Bedroom #AirConditioner).airconditioner_setairconditionermode("auto")

# Generated
triggered := false
if ((#Bedroom #MotionSensor).motionsensor_motion == true) {
  if (triggered == false) {
    (#Bedroom #AirConditioner).switch_on()
    triggered = true
  }
} else {
  triggered = false
}
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
triggered := false
if (all(#Hallway #PresenceSensor).presencesensor_presence ==| true) {
  if (triggered == false) {
    all(#Hallway #Light).light_movetorgb(128, 0, 128)
    triggered = true
  }
} else {
  triggered = false
}
```

### Category 5 · Row 150

- Command (EN): Check the wine cellar temperature now and again in 10 minutes. If it has changed by 1 degree or higher, announce through the speaker that the wine cellar temperature has changed rapidly.
- Command (KO): 지금 와인 셀러 온도를 체크하고 10분뒤에 다시 체크해서 1도 이상 차이가 나면, 스피커로 온도가 급변했다고 안내해줘.
- DET: `69.9000`
- Failure reasons: `["dataflow", "gt_mismatch", "semantic"]`
- Recommended prompt files: `caution_prompt_8.md, grammar_ver1.5.10.md, response_prompt_baseline_cot.md`
- Analysis: Check the wine cellar temperature now and again in 10 minutes. If it has changed by 1 degree or higher, announce through the speaker that the wine cellar temperature has changed rapidly.: 읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다

```joi
# GT
original_temp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature

delay(10 MIN)

temp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature

if (temp >= original_temp + 1 or temp <= original_temp - 1) {

    (#Speaker).speaker_speak("와인셀러의 온도가 급변했습니다")
}

# Generated
originalTemp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature
  delay(10 MIN)
  newTemp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature
  diff = newTemp - originalTemp
  if (diff >= 1 or diff <= -1) {
    (#Speaker).speaker_speak("와인셀러의 온도가 급변했습니다")
  }
```

### Category 6 · Row 171

- Command (EN): If the face ID 'family' is recognized at the entrance and the door lock is locked , unlock the door lock and open the door.
- Command (KO): 현관에서 인식된 얼굴 ID가 "가족"이고 도어락이 잠겨 있으면, 도어락을 풀고 문을 열어줘.
- DET: `64.2780`
- Failure reasons: `["extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic"]`
- Recommended prompt files: `response_prompt_baseline_cot.md, caution_prompt_8.md`
- Analysis: If the face ID 'family' is recognized at the entrance and the door lock is locked , unlock the door lock and open the door.: GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다; GT가 요구한 receiver scope를 충분히 덮지 못했습니다

```joi
# GT
if ((#Entrance #FaceRecognizer).facerecognizer_recognizedresult == "family" and (#Entrance #DoorLock).doorlock_doorlockstate == "locked") {

    (#Entrance #DoorLock).doorlock_unlock()

    (#Entrance #Door).door_open()

}

# Generated
prev := (#DoorLock).doorlock_doorlockstate

curr = (#DoorLock).doorlock_doorlockstate

if (prev != "closed" and curr == "closed") {

    (#Entrance #Light).levelcontrol_movetolevel(100, 0)

    delay(10 SEC)

    (#Entrance #Light).switch_off()

}

prev = curr
```
