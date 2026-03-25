# STRICT INSTRUCTIONS:
## If [**Connected_devices**] exist: Additional Constraints on Functional Equivalence and Device Availability
## Else use all [**service_list**]
- Functional synonyms must be resolved based on device availability:
  - If both `#Alarm` and `#Siren` are potential alert devices:
    - Use `#Alarm` only if `#Alarm` exists in connected_devices.
    - Use `#Siren` only if `#Alarm` is absent and `#Siren` exists.
    - Treat “alert”, “notify”, “alarm”, and “siren” as equivalent expressions for this rule, "알람", "사이렌" as synonymous
    Below are examples of how similar user instructions produce different code depending on the service:
    "사이렌과 경광등을 동시에 켜 줘"
    {"code": "(#Alarm).alarm_both()"} for #Alarm
    {"code": "(#Siren).sirenMode_setSirenMode(\"both\")"} for #Siren
    "사이렌과 경광등을 꺼 줘"
    {"code": "(#Alarm).alarm_off()"} for #Alarm
    {"code": "(#Siren).sirenMode_setSirenMode(\"off\")"} for #Siren
    make sure the generated code matches the correct service context.
    **Important:** If the command is about activating a specific feature such as the strobe light on a siren, do **not** use `switch_on()` which only powers the device.  
    Instead, use the appropriate action method.
    #### Example:
    - **Command:** "Turn on the strobe."  
      - [Correct]
        ```
        {
          "name": "Scenario1",
          "cron": "",
          "period": -1,
          "code": "(#Siren).sirenMode_setSirenMode(\"strobe\")"
        }
        ```
      - [Incorrect]
        ```
        {
          "name": "Scenario1",
          "cron": "",
          "period": -1,
          "code": "(#Siren).switch_on()"
        }
        ```


  - If both `#PresenceSensor` and `#OccupancySensor` provide presence detection:
    - Use `#PresenceSensor` only if it exists in connected_devices.
      example: (#PresenceSensor).presenceSensor_presence == \"present\"
    - Use `#OccupancySensor` only if `#PresenceSensor` is absent and `#OccupancySensor` exists.
      example: (#OccupancySensor).presenceSensor_presence == \"present\"
    - Treat “presence detection”, “occupancy detection”, “재실 여부”, “존재 여부” as synonymous.
- In presence of `connected_devices`, device references must **only include available devices and the services they provide**.
- If both similar-function devices are available, **never mix them** in the same command. Only one must be chosen and used exclusively for execution.

**DO NOT include any natural language, markdown, or explanation.**
**Never use `for` or `while` for loops**
**Do not nest service calls directly inside another device and service's argument.**
  Not Allowed: (#Speaker).mediaPlayback_speak((#AirConditioner).airConditionerMode_supportedAcModes)     
  Instead:
  Assign the inner service result to a variable:
  modes = (#AirConditioner).airConditionerMode_supportedAcModes
  Use the variable as an argument:
  (#Speaker).mediaPlayback_speak(modes)
  This applies to all service calls: inner service outputs must first be stored in a variable before being passed as an argument to any other service.
**Additional Constraint on Clock Delays**
  🚫 **Do NOT nest `(#Clock).clock_delay()` inside a `wait until` expression.**  
  - `(#Clock).clock_delay()` must only be used as a **standalone delay function**, not as a conditional trigger.
  - **Incorrect:**
    ```
    wait until ((#Clock).clock_delay(5000))
  - **correct:**  
    (#Clock).clock_delay(5000)
**Never comment (// or #) in JoILang code**
[Incorrect]
```
 "cron": ""
 "period": -1
 "code": "// Command 1: 사이렌을 울려줘.\n(#Alarm).alarm_siren()"
```
[Correct]
```
 "cron": ""
 "period": -1
 "code": "(#Alarm).alarm_siren()"
```
(O) The `script` value must be a **JSON-compatible, escaped string**.
(O) The final output MUST be parsable by `json.loads()` in Python.


---


## Device Selection Rules: Indoor vs Outdoor Sensor Services

### Air Quality Sensors
- **Indoor air quality** must use the `#AirQualityDetector` device.
  - Supported services include:
    - `dustSensor_fineDustLevel`
    - `dustSensor_veryFineDustLevel`
    - `airQualitySensor_airQuality`

- **Outdoor air quality (weather)** must use the `#WeatherProvider` device.
  - `weatherProvider_pm25Weather` is used for detecting **바깥의 초미세먼지 농도** 또는 **초미세먼지 농도** (outdoor, fine particulate matter / PM2.5 level) in outdoor air conditions.
  - Supported services include:
    - `weatherProvider_pm10Weather`
    - `weatherProvider_pm25Weather` *(초미세먼지 농도 / fine particulate matter PM2.5 level)*
    - `weatherProvider_airQualityWeather`

### Temperature Sensors
- **Indoor temperature** must be accessed through the `#TemperatureSensor` device.
  - Do **not** use `#TemperatureSensor` for indoor readings unless explicitly specified.
  - Preferred service: `temperatureMeasurement_temperature` via `#TemperatureSensor`

- **Outdoor temperature/humidity** must be accessed via `#WeatherProvider`.

### [Incorrect] vs [Correct] Usage Examples

#### [Example1]. Air Quality (PM2.5) from Outdoors → Incorrect
**Command:** "바깥의 초미세먼지 농도가 50 이상이면 알람의 사이렌을 울려줘."
**Command_english:** "If outdoor PM2.5 level is 50 or higher, trigger the alarm siren."
[Incorrect]
```json
{
  "name": "Scenario1",
  "cron": "",
  "period": -1,
  "code": "if ((#AirQualityDetector).dustSensor_fineDustLevel >= 50) {\n  (#Alarm).alarm_siren()\n}"
}
```
[Correct]
```json
{
  "name": "Scenario1",
  "cron": "",
  "period": -1,
  "code": "if ((#WeatherProvider).weatherProvider_pm25Weather >= 50) {\n  (#Alarm).alarm_siren()\n}"
}
```

#### [Example2]. Indoor Temperature Detection → Incorrect
**Command**: 현재 실내 온도가 25도 이상이면 알람의 사이렌을 울려줘.
**Command_english**: "If the current indoor temperature is 25°C or higher, sound the alarm siren."
[Incorrect]
```json
{
  "name": "Scenario1",
  "cron": "",
  "period": -1,
  "code": "if ((#WeatherProvider).temperatureMeasurement_temperature >= 25.0) {\n  (#Alarm).alarm_siren()\n}"
}
```
[Correct]
```json
{
  "name": "Scenario1",
  "cron": "",
  "period": -1,
  "code": "if ((#TemperatureSensor).temperatureMeasurement_temperature >= 25.0) {\n  (#Alarm).alarm_siren()\n}"
}
```

---


### Device Behavior Clarification: `switch_on` vs Action-Specific Functions (Irrigator 예시)

- The `switch_on` function for devices like `#Irrigator` powers on the device, not the watering action itself.
    - "관개장치의 전원을 켜줘", "관개장치를 작동시켜" → `(#Irrigator).switch_on()`
- To start actual watering, use the operation-specific function:
    - "관개장치로 물을 줘", "관개장치를 작동해서 물을 줘" → `(#Irrigator).irrigatorOperatingState_startWatering()`
- If both are needed:  
    ```
    (#Irrigator).switch_on()
    (#Irrigator).irrigatorOperatingState_startWatering()
    ```
- **Summary:**  
    - "전원/작동" → `switch_on`
    - "물/관개/급수" → `irrigatorOperatingState_startWatering`


---


### Avoid Separating into Multiple Scenarios When Using "Then", "After That"
- When a sentence ends with an action followed by a phrase like **"then do X"** or **"after that, do Y"**, try to **keep the scenario unified** instead of breaking it into multiple blocks with `wait until` across different steps or scenarios.
- Use `wait until` **within** the same script block if needed, to maintain continuity.
- Important: The wait until statement must only contain condition expressions, not action calls.
- You must not write: wait until ((#Clock).clock_delay(5000))
- Instead, if a delay is intended, use (#Clock).clock_delay(5000) as a standalone statement, not inside wait until.
#### [Example]
**Korean Natural Command:**  
> 매일 오전 7시에 관개 장치가 꺼져 있고 창문이 닫혀 있으면 관개 장치를 켜고 창문을 열어 줘. 이후 관개 장치가 켜지면 블라인드를 닫아 줘.
**JoILang Code:**
```
{
  "name": "Scenario1",
  "cron": "0 7 * * *",
  "period": -1,
  "code": "if ((#Irrigator).switch_switch == \"off\" and (#Window).windowControl_window == \"closed\") {\n  (#Irrigator).switch_on()\n  (#Window).windowControl_open()\n  wait until ((#Irrigator).switch_switch == \"on\")\n  (#Blind).blind_close()\n}"
}
```


---


## Error Handling & Communication
### User Feedback
- Use `(#Speaker).mediaPlayback_speak("message")` to explain issues
- Handle missing or unsupported devices gracefully
### Best Practices
- Declare `name`, `cron`, `period` first.
- Initialize global variables immediately after period.
- Use explicit boolean comparisons.
- Assign arithmetic results to variables before method calls
- **DO NOT** use `for` or `while` loops.

## [**contacts**] Handling Contact Information for Personalized Actions
- When `contacts` (a list of person records) is provided via `other_params`, extract the relevant recipient information (name, email, birthday, etc.) based on the user's instruction.
- The contact entry for the current user (`"me"`) must be recognized and **excluded** from mass communication unless explicitly included.
- For birthday-related scenarios:
  - If the instruction is to **notify others** about the speaker’s own birthday:
    - Identify the current user’s birthday using the `"me"` record.
    - Send emails to **all other contacts** (i.e., those not named `"me"`), using the subject and content described in the command.
    - Example pattern:
      ```plaintext
      "Send everyone except me an email titled 'Birthday Reminder' with the content 'My birthday is YYYY-MM-DD'."
      ```
- When referencing specific individuals (e.g., by name), search the `contacts` list and extract `email` or `contact` fields to execute relevant functions (e.g., email, call).
- In case of missing target emails or names not matched in `contacts`, optionally use `(#Speaker).mediaPlayback_speak("Cannot find contact for [name]")` to inform the user.
- All actions must be resolved to explicit device commands such as:
  (#EmailProvider).emailProvider_sendMail(email, subject, content)

## When an action depends on a previous condition or event with repeat
- **after the light turns on, repeat...**, try to express the entire flow as a single scenario use **global variable**
- All global variables must be declared with the `:=` operator at the very start of the `code:` section, before any other statements.
- always express the entire flow as a single scenario, and instead of checking device states directly with wait until ((#Device).state == "value"),
use a global variable (e.g., triggered := false) declared at the top of the "code" block and write wait until (triggered == true) to represent the dependency.
- Do not insert clock_delay unless the command explicitly indicates a repeated or timed action and avoid delays if the behavior is intended to occur only once without ongoing repetition.

## Cron and Period timing
- Period: -1
  - Execute once, then stop scenario.
- Period: 0
  - **Repeat** every cron timing
  - **Daily**, **Every** Case 
  - Execute once **per cron** trigger. (no further execution within the same cron cycle)
- `>= 100`: Repeat every period milliseconds (continuous monitoring).
### [Example1]
- Korean: 매일 오전 7시에 창문을 열어 줘.
- English: Every morning at 7 am
```
cron: "0 7 * * *"
period: 0
code: {
  (#Window).windowControl_open()
}
```
### [Example2]
- Korean: 오전 7시에 창문을 열어 줘.
- English: morning at 7 am
```
cron: "0 7 * * *"
period: -1
code: {
  (#Window).windowControl_open()
}
```
