### 1. Basic service specification

[ALL|OR|Space](#Tag1 ... #TagN).ServiceName

### 1-1. Service Qualifiers *Tag*

Qualifies service mapping candidates through a list of tags.

- Syntax: (#TAGNAME #TAGNAME2 ...)

### 1-2. Range qualifier *Range*

Limits the range of the final mapping if there are multiple mapping candidates.

1. service run
Default (blank): Pick one service and map it.
**ALL**: Map all satisfied services
2. check if conditions are met
Default (blank): True if all candidates satisfy the condition
**OR: True if at least one candidate satisfies the condition

Example service specification
```
(#camera #living_room).capture()
ALL(#camera).capture_with_timeout(10)
```


### 1-3. Assignment

Saves the result of the Function Service to a variable.

If you use the ALL Range qualifier, you cannot substitute.

```
img = (#camera).capture()
```

### 2. Conditional statements

- IF
- ELSE
```cpp
IF (x == 1) {
	...
} ELSE {
	...
}
```

### 3. Event trigger
- WAIT UNTIL
- Wait for an event to occur.

```
WAIT UNTIL (x == 1);
...
```

### Sample scenario

1. TV 볼륨을 10으로 설정해줘
'''
Incorrect Code:
 '''json
 {
  "cron": "* * * * *",
  "period": 0,
  "script": "
    (#Television).audioVolume_setVolume(10)
  "
}
'''
Reason: For one-time tasks, configure the cron as an empty string " " and period as -1.
Correct Code:
 '''json
 {
  "cron": " ",
  "period": -1,
  "script": "
    (#Television).audioVolume_setVolume(10)
  "
}
'''

2. 1시간마다 TV 볼륨을 10으로 설정해줘
'''
Incorrect Code:
 '''json
 {
  "cron": "0 * * * *",
  "period": -1,
  "script": "
    (#Television).audioVolume_setVolume(10)
  "
}
'''
Reason: Since it should run once per cron cycle, the period must be set to 0.
'''
Incorrect Code:
 '''json
 {
  "cron": "0 * * * *",
  "period": 0,
  "script": "
    (#Television).audioVolume_setVolume(10)
  "
}
'''

3. 비가오면 창문을 닫아줘
'''
Incorrect Code:
 '''json
{
  "cron": "*/5 * * * *",
  "period": -1,
  "script": "
    if ((#WeatherProvider).weatherProvider_weather == 'rain') {
      (#Window).windowControl_close()
    }
  "
}
'''
Reason: Continuous measurement tasks are executed every 100 milliseconds. Since there is no specific time condition, the cron is set to " ".
Correct Code:
 '''json
{
  "cron": " ",
  "period": 100,
  "script": "
    if ((#WeatherProvider).weatherProvider_weather == 'rain') {
      (#Window).windowControl_close()
    }
  "
}
'''

4. 날씨가 맑으면 블라인드를 올려줘
'''
Incorrect Code:
 '''json
{
  "cron": "*/5 * * * *",
  "period": 100,
  "script": "
    if ((#WeatherProvider).weatherProvider_weather == 'clear') {
      (#Blind).blind_open()
    }
  "
}
'''
Reason: If there is no specific time condition, you should set cron empty(" ").
Correct Code:
 '''json
{
  "cron": " ",
  "period": 100,
  "script": "
    if ((#WeatherProvider).weatherProvider_weather == 'clear') {
      (#Blind).blind_open()
    }
  "
}
'''

5. 오전 9시 20분부터 11시 50분까지 30분 간격으로 10분동안 청소해줘
'''
Incorrect Code:
 '''json
{
  "cron": "20 9 * * *",
  "period": 1800000,
  "script": "
    (#RobotCleaner).robotCleanerCleaningMode_setRobotCleanerCleaningMode('auto')
    (#clock).delay(600000)
    (#RobotCleaner).robotCleanerCleaningMode_setRobotCleanerCleaningMode('stop')
    break
  "
}
'''
Reason: 'break' is inappropriate. Even if there is no 'break', this code make robot clean all day, not until 11:50.
Correct Code:
 '''json
{
  "cron": "20 9 * * *",
  "period": 1800000,
  "script": "
    if ((#Clock).clock_hour == 11 and (#Clock).clock_minute == 50) {
      break
    }
    (#RobotCleaner).robotCleanerCleaningMode_setRobotCleanerCleaningMode('auto')
    (#clock).delay(600000)
    (#RobotCleaner).robotCleanerCleaningMode_setRobotCleanerCleaningMode('stop')
} 