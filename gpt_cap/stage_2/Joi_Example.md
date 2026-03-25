### Examples
0. 온도가 20도 이하였다가 이상이되면 블라인드를 닫아.
Step1: [온도가 20도 이하였다가 이상이되면(meet once)] → [블라인드를 닫아(once)]
Step2: cond1: 2 consecutive wait untils (state change + meet once)
Step3: cron: "", period:-1
Step4: phase x, break x
Step5: X
code:
    wait until ((#Window).windowControl_window == 'open')
    wait until ((#Window).windowControl_window == 'closed')
    (#Blind).blind_close()

1. 창문이 열릴 때마다 블라인드를 닫아 줘.
Step1: [창문이 열릴 때마다(meet multiple)] → [블라인드를 닫아(once)]
Step2: cond1: if+triggered (state change + meet multiple + single state)
Step3: cron: "", period: 100
Step4: phase x, break x (p>0 but no range)
Step5: X
code:
    triggered := false
    if ((#Window).windowControl_window == 'open') {
        if (triggered == false) {
            (#Blind).blind_close()
            triggered = true
        }
    } else {
        triggered = false
}

2. 창문이 열렸다 닫힌 횟수가 3번이 되면 블라인드를 닫아.
Step1: [창문이 열렸다 닫힌 횟수가 3번이 되면(meet multiple, count)] → [블라인드를 닫아(once)]
Step2: cond1: if + prev var (state change + meet multiple + 2 states)
Step3: cron: "", period: 100
Step4: phase x, break x (p>0 but no range)
Step5: X
code:    
    window_count := 0
    prev_window_state := (#Window).windowControl_window    
    window_state = (#Window).windowControl_window
    if ((prev_window_state == 'open') and (window_state == 'closed')) {
        window_count = window_count + 1
    }
    prev_window_state = window_state
    if (window_open_to_close_count >= 3) {
        (#Blind).blind_close()
        break
    }

3. 일조량이 200룩스 이하가 되면 2초마다 조명을 켜고, 1초 후에 꺼.
Step1: [일조량이 200룩스 이하가 되면(meet once)] → [2초마다 조명을 켜고(period)] → [1초 후에(delay)] → [꺼(once)]
Step2: cond1: wait until
Step3: cron: "", period: 2000
Step4: use phase (wait until and action with period 2000 co-exist), break X (p>0 but no range)
Step5: X
code:
    phase := false
    if (phase == false) {
        wait until((#LightSensor).lightLevel_light <= 200)
        phase = true
    } else {
        (#Light).switch_on()
        (#Clock).clock_delay(1000)
        (#Light).switch_off()
    }

4. 10초마다 알람과 사이렌을 껐다 켰다 반복해 줘.
Step1: [10초마다 알람과 사이렌을 껐다 켰다 반복해 줘(period, select between 2 states)]
Step2: X 
Step3: cron: "", period: 10000
Step4: phase X, break X (p>0 but no range)
Step5: X
code:
    alarm_state := true
    if (alarm_state == true) {
        (#Alarm).alarm_off()
        (#Siren).switch_off()
        alarm_state = false
    } else {
        (#Alarm).alarm_siren()
        (#Siren).switch_on()
        alarm_state = true
    }
### Delay Example
4. 1초 후에 알람을 꺼줘.
Step1: [1초 후에(delay)] → [알람을 꺼줘(once)]
Step2: X
Step3: cron: "", period: -1
Step4: phase X, break X
Step5: X
code: 
    (#Clock).clock_delay(1000)
    (#Alarm).switch_off()

5. 10초마다 알람을 1초간 울렸다 꺼지게 하고, 울릴 때마다 에어컨을 켜.
Step1: [10초마다 알람을 1초간 울렸다 꺼지게 하고(period, delay)] → [울릴 때마다(always occurs, after 울렸다)] → [에어컨을 켜(once)]
Step2: X
Step3: cron: "", period: 10000
Step4: phase X, break X (p>0 but no range)
Step5: X
code:
    (#Alarm).alarm_siren()
    (#AirConditioner).switch_on()
    (#Clock).clock_delay(1000)
    (#Alarm).switch_off()
## Time Example
6. 지금이 오후 3시 15분이면.
omitted Step 1,2,4.
Step3: cron: "", period: -1
Step5: X
code: 
    if ((#Clock).clock_time(1515))

7. 주말에 온도가 30도 이상이 되면 에어컨을 켜줘.
Step1: [주말에 온도가 30도 이상이 되면(meet once)] → [에어컨을 켜줘(once)]
Step2: cond1: wait until
Step3: cron: "0 0 * * 0,6", period: 0 (cron exists)
Step4: phase X, break X 
Step5: X
code:
    wait until((#TemperatureSensor).temperatureMeasurement_temperature >= 30) 
    (#AirConditioner).switch_on()

8. 더 이상 움직임이 감지가 안되면.
Omitted draft.
code: 
    wait until((#PresenceSensor).presenceSensor_presence == 'not present')

9. 평일 자정에 선풍기가 켜져 있으면 선풍기를 켜줘.
Step1: [평일 자정에 선풍기가 켜져 있으면(cron, moment)] → [선풍기를 켜줘(once)] 
Step2: cond1: if(moment=now)
Step3: cron: "0 0 * * 1-5", period: 0 (cron exists)
Step4: phase X, break X 
Step5: X
code:
    if ((#Fan).switch_switch == 'on') {
        (#Fan),switch_on()
    }

10. 오후 10시부터 11까지 3초마다 알람의 사이렌을 울려.
omitted Step 1,2.
Step3: cron: "0 22 * * *", period: 3000
Step4: phase X, break when hour is 23.
Step5: X
code: 
    If ((#Clock).clock_hour == 23) {
        break     
    }  
    (#Alarm).alarm_siren()

11. 오전 8시부터 10시 사이에 1시간마다 A를 해.
Step1: [오전 8시부터 10시 사이에 1시간마다 A를 해(period)]
Step2: X
Step3: cron: "0 8-9 * * *" (8-9 means every hour.), period: 0 (You should not set period 3600000.)
Step4: phase X, break X 
Step5: X
omitted code.

12. 주말에 실시간으로 확인해서 창문이 열리면 블라인드를 완전히 닫아줘.
Step1: [주말에 실시간으로 확인해서 창문이 열리면(period, meet once)] → [닫아줘(once)]
Step2: cond1: if with period 100ms
Step3: cron: "0 0 * * 0,6", period: 100
Step4: phase X, break when it isn't weekends
Step5: X
code: 
    weekday = (#Clock).clock_weekday
    if ((weekday != 'saturday') and (weekday != 'sunday')) {
        break
    }
    if ((#Window).windowControl_window == 'open') {
        (#Blind).blind_close()
    }

13. 가장 최근에 찍은 사진을 내 주변사람들에게 제목 "b"와 내용 "c"로 보내줘.
omitted drafts.
code:
    latest_photo = (#Camera).camera_image
    (#EmailProvider).emailProvider_sendMailWithFile('010-1111-1111','b','c', latest_photo)
    (#EmailProvider).emailProvider_sendMailWithFile('010-2222-2222','b','c', latest_photo)
### Tag Example
14. 하우스A에 있는 선풍기가 모두 켜져 있으면 블라인드를 닫아.
Device list: {'Fan': ['SectorA','Left']}
Step1: [하우스 A에 있는 선풍기가 모두 켜져 있으면(all(#SectorA #Fan)(there is no HouseA), now)] → [블라인드를 닫아 (#Blind, once)]
omitted Step 2,3,4,5.
code:
    if (all(#SectorA #Fan).switch_switch == 'on') {
        (#Blind).blind_close()
    }

15. 그룹A 태그를 모두 꺼줘.
Device list: {'Alarm': ['GroupA'], 'Light': ['GroupA']}
omitted drafts.
code:
    all(#GroupA).alarm_off()
    all(#GroupA).switch_off()

16. 그룹2번의 습도가 모두 80을 초과하면 관개장치를 꺼 줘.
Device list: {'HumiditySensor': ['Sector2'], 'Irrigator': ['Sector2']}
Step1: [그룹2번의 습도가 모두 80을 초과하면(all(#Sector2 #HumiditySensor)(there is no Group2), meet once)] → [조명을 꺼(#Light, now)]
Step2: cond1: wait until
Step3: cron: "", period: -1
Step4: phase X, break X
Step5: X
code:
    wait until(all(#Sector2 #HumiditySensor).relativeHumidityMeasurement_humidity > 80)
    (#Irrigator).switch_off()
### Others
17. 1월 1일에 실시간으로 확인하여 움직임이 감지되면 5초 후 조명을 키고 10초 후 커튼을 열어.
Step1: [1월 1일에 실시간으로 확인하여 움직임이 감지되면(period, meet once)] → [5초 후(delay)] → [조명을 키고(once)] → [10초 후(delay)] → [커튼을 열어(once)]
Step2: cond1: if (100ms period)
Step3: cron: "" period: 100
Step4: phase X (no wait until), break when it's not january 1st
Step5: X
code:
    if (((#Clock).clock_month != 1) or ((#Clock).clock_day != 1)) {
        break
    } 
    if ((#MotionSensor).motionSensor_motion == 'active') {
        (#Clock).clock_delay(5000)
        (#Light).switch_on()
        (#Clock).clock_delay(10000)
        (#Curtain).curtain_open()
    }

18. 5초마다 알람을 켜고 2.5초 뒤에 꺼. 켜고 끌 때 확인해서 블라인드가 닫혀있으면 열어.
Step1: [5초마다 알람을 켜고(period)] → [2.5초 뒤에(delay)] → [꺼(once)] → [켜고 끌 때 확인해서 블라인드가 닫혀있으면(when)] → [열어(once)]
Step2: cond1: if(when==now)
Step3: cron: "", period: 5000
Step4: phase X, break X (p>0 but no range)
Step5: X
code:
    (#Alarm).switch_on()
    if ((#Blind).blind_blind == 'closed') {
        (#Blind).blind_open()
    }
    (#Clock).clock_delay(2500)
    (#Alarm).switch_off()
    if ((#Blind).blind_blind == 'closed') {
        (#Blind).blind_open()
    }

19. 주말에 온도가 연속으로 3회 20 이상을 기록하고 그 중 두번째 값이 가장 높았다면 알람의 사이렌을 울려줘.
Step1: [주말에 온도가 연속으로 3회 20 이상을 기록하고(period, meet multiple, continuous)] → [그 중 두번째 값이 가장 높았다면(now)] → [알람의 사이렌을 울려줘(once)]
Step2: cond1: if (it's not state change, count), cond2: if(now)
Step3: cron: "0 0 * * 0,6", period: 100
Step4: phase X, break when it's not weekends
Step5: X
code:
    t1 := 0
    t2 := 0
    t3 := 0
    weekday = (#Clock).clock_weekday
    if ((weekday != 'saturday') and (weekday != 'sunday')) {
        break
    }
    t1 = t2
    t2 = t3
    t3 = (#TemperatureSensor).temperatureMeasurement_temperature
    if ((t1 >= 20) and (t2 >= 20) and (t3 >= 20) and (t2 > t1) and (t2 > t3)) {
        (#Alarm).alarm_siren()
    }

20. 문이 닫혔다 열리면 5초마다 알람의 사이렌을 울려.
Step1: [문이 닫혔다 열리면 (meet once, state change)] → [5초마다 알람의 사이렌을 울려(period)]
Step2: cond1: 2 consecutive wait untils
Step3: cron: "", period: 5000
Step4: use phase(wait until and action with period 5000 co-exist), break X (p>0 but no range)
Step5: X
code:
    phase := false
    if (phase == false) {
        wait until((#DoorLock).doorControl_door == 'closed')
        wait until((#DoorLock).doorControl_door == 'open')
        phase = true
    } else {
        (#Alarm).alarm_siren()
    }

21. 창문이 열린 후 5초 내에 알람이 꺼지면 알람의 사이렌을 울려.
Step1: [창문이 열린 후(meet once)] → [5초 내에 알람이 꺼지면(meet once)] → [알람의 사이렌을 울려(once)]
Step2: cond1: wait until, cond2: if
Step3: cron: "", period: 100(default)
Step4: use phase(wait until and if with period 100 co-exist), break when 5 sec later.
Step5: X
code:
    phase := false
    if (phase == false) {
        wait until((#Window).windowControl_window == 'open')
        init_time := 0
        phase = true
    } else {
        init_time = init_time + 100
        if (init_time <= 5000) {
            if ((#Alarm).alarm_alarm == 'off') {
                (#Alarm).alarm_siren()
                break
            }
        } else {
            break
        }
    }

22. 오후 1시에 짝수 태그 창문이 하나라도 열려 있고 조명이 켜져 있으면 사이렌을 울려줘. 사이렌을 울렸는지 상관없이 1초 후부터는 실시간으로 확인해서 홀수 태그 문이 두 번 열렸다 닫히면 커튼을 닫아줘.
Step1: [오후 1시에 짝수 태그 창문이 하나라도 열려 있고(cron, now, 짝수, 하나라도)] → [조명이 켜져있으면(now)] → [사이렌을 울려줘(once)] → [사이렌을 울렸는지 상관없이 1초 후부터는 실시간으로 확인해서 홀수 태그 문이 두 번 열렸다 닫히면(홀수, delay, meet multiple, state change, 2states)] → [커튼을 닫아줘(once)]
Step2: cond1+cond2: if, cond3: if + prev var (state change + multiple + 2 states)
Step3: cron: "0 13 * * *", period: 100(default)
Step4: use phase(first phase causes problem when second phase repeats), break X (p>0 but no range)
Step5: X
code:
    phase := false
    if (phase == false) {
        if ((any(#Even #Window).windowControl_window == 'open') and ((#Light).switch_switch == 'on')) {
            (#Alarm).alarm_siren()
            (#Clock).clock_delay(1000)
        } 
    } else {
        door_count := 0
        prev_door_state := (#Odd #DoorLock).doorControl_door
        door_state := (#Odd #DoorLock).doorControl_door
        if ((prev_door_state == 'open') and (door_state == 'closed')) {
            door_count = door_count + 1
        }
        prev_door_state = door_state
        if (door_count >= 2) {
            (#Curtain).curtain_close()
            break
        }
    }

23. 알람이 켜져있는데 10초가 지나도 알람이 켜져있으면 알람을 꺼줘.
Step1: [알람이 켜져있는데(now)] → [10초가 지나도(delay)] → [알람이 켜져있으면(moment)] → [알람을 꺼줘(once)]
omitted other Steps.
code:
    if ((#Alarm).switch_switch == 'on') {
        (#Clock).clock_delay(10000)
        if ((#Alarm).swtich_switch == 'on') {
            (#Alarm).alarm_off()
        }
    }

24. 평일 자정에 창문이 열려있고 기온이 20도면 창문을 닫아. 그 후, 실시간으로 확인하여 30초 연속으로 기온이 20도 미만이면 선풍기를 꺼. 그때 알람이 꺼져있으면 3초 뒤에 사이렌을 울려줘.
Step1: [평일 자정에 창문이 열려있고(cron, now)] → [기온이 20도면(now)] → [창문을 닫아(once)] → [그 후, 실시간으로 확인하여 30초 연속으로 기온이 20도 미만이면(period, meet multiple, continuous)] → [선풍기를 꺼(once)] → [그때 알람이 꺼져있으면(moment)] → [3초 뒤에(delay)] → [사이렌을 울려줘(once)]
Step2: cond1+cond2: if, cond3: if with period 100ms, cond4: if
Step3: cron: "0 0 * * 1-5", period: 100
Step4: use phase(first phase causes problem when second phase repeats), break when it's saturday.
Step5: X
code:
    phase := 0
    continuous_time := 0 
    if ((#Clock).clock_weekday == 'saturday') or ((#Clock).clock_weekday == 'sunday') {
        break
    }
    if (phase == 0) {
        if ((#Window).windowControl_window == 'closed') and ((#AirQualityDetector). temperatureMeasurement_temperature == 30) {
            (#Window).windowControl_close()
        }
        phase = 1
    } else {
        if ((#AirQualityDetector). temperatureMeasurement_temperature < 20) {
            continuous_time = continuous_time + 100
        } else {
            continuous_time = 0
        }
        if (continuous_time >= 30000) {
            (#Fan).switch_off()
            if ((#Alarm).alarm_alarm == 'off') {
                (#Clock).clock_delay(3000)
                (#Alarm).alarm_siren()
            }
            break
        }
    }