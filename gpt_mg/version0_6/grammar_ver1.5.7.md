# Timing Control
## cron
- `cron` (String): UNIX cron syntax for trigger. 
  - cron = '': Start immediately. No further cron triggers.
  - Resets scenario regardless of blocking.
  - Use "cron": "* * * * *", and specify other fields (hour, day, etc.) as needed in standard UNIX cron order: minute, hour, day, month, weekday.
## period
- `period` (Integer): Controls execution loop after cron trigger
  - `-1`: Execute once, then stop.
  - `0`: Execute once per cron trigger. (no further execution within the same cron cycle)
  - `>= 100`: Repeat every period milliseconds (continuous monitoring).
## When to Use `period` over `cron`
- If the user command includes "매초마다", "매 5분마다", "15초마다" 등 반복 주기 표현이 포함된 경우,  
- You must always control repeated intervals **using period first**, not cron.
  **반드시 `cron`이 아닌 `period`로 주기 반복을 제어해야 합니다.**
- **Never use `while` in code**

## Periodic Execution within Time Range in cron scenario
To run a scenario repeatedly **only within a specific hour range** (e.g., between 18:00 and 19:00), use `(#Clock).clock_hour` to conditionally check current time.
### [Example]
```
{name} = "Scenario1"
cron = "<start hour cron>"
period = <period ms>
code =
  <flag> := <initial_bool>
  if (((#Clock).clock_hour >= <startHour>) and ((#Clock).clock_hour < <endHour>)) {
    if (<flag> == true) {
      (#Device).<action1>()
      <flag> = false
    } else {
      (#Device).<action2>()
      <flag> = true
    }
  } else {
    break
  }
```



## [Example]
### Cron and period use case1: Run once now
```
{
"cron": ""
"period": -1
"code: "action1, ..."
}
```
### Cron and period use case2: Run at 9 AM once
```
{
"cron": "0 9 * * *"
"period": -1
"code": "action1, ..."
}
```
###  Daily 9 AM execution
```
{
"cron": "0 9 * * *"
"period": 0
"code": "action1, ..."
}
```
###  Continuous 10-second monitoring
```
{
"cron": ""
"period": 10000
"code": "action1, ..."
}
```

# Variable Management
- all variables Declared with := after "name", "cron", and "period".
- all variables Must be declared only inside the "code" block, do not place them inside or next to "period".

## Global variables
- Global variables must be declared **strictly at the very beginning** of the "code" block, before any logic, if, or service calls.
- All variables must be declared once at the very beginning of the "code" block using :=, and must be updated later using = during execution.
- Do not declare variables like curtainOpen := true in the middle of the "code" logic.
- This ensures proper initialization and consistent scoping across executions.
Declared using :=, and persist across period executions within the same cron cycle.
- Automatically reset on new cron trigger.
- Reassigned with `=`.
- Variable values are preserved and updated across all executions within the same period loop.
- Used for tracking global state across periods, such as counts, toggles, durations, triggers, and flags.

### [Example]
```
{
"cron": ""
"period": 100
"code":
  triggered := false
  if ((#Device).attribute == value) {
    if (triggered == false) {
      // ... Execute code only at the moment the condition turns true
      triggered = true
    }
  } else {
    // Reset the flag when the condition is no longer true
    triggered = false 
  }
}
```

## Local Variables
- Declared within code blocks using `=`
- Scoped to current period execution only

# Device Control
## Device Selection
- **All tag name is english**
- The tags can be combined from command.
- Each device has pre-defined Tags (**device**, **location**, **group**...).
- (#Tag1 #Tag2 ...) selects devices with ALL specified tags (AND logic, separated by spaces).
- Access: `(#Tags).attribute` (read-only) or `(#Tags).method(args)` (control)
- Tags must be accurately **extracted from the command**, typically consisting of one device tag and a combination of user-defined tags like location, group, or multiple user-defined tags only.
- A valid device selection typically consists of one device tag (e.g., #Light) and one or more user-defined tags such as #location, #group, etc.
### [Example]
Command: "Turn on the lights in the odd group"
→ #Light is the device tag for "lights"
→ #Odd is a user-defined group tag
→ Combined expression: (#Light #Odd).switch_on()

## Additional Rule: When Tag is Not a Device Type
[Step1] If the **tag** in the command is not found in the **device list** as a device tag:
[Step2] Look up the tag in the [connected_devices] list.
- Identify which devices contain the tag and extract their category (e.g., Light, Alarm).
[Step3] - For each discovered category:
- Check available control **function list** OR the **service list** for conditional checks and control actions  
  (e.g., `switch_off()`, `alarm_off()`, `relativeHumidityMeasurement_humidity`, etc.)
[Step4] Generate all control commands per device type using the tag as a shared filter.
### [Example1]
- Command: "Turn off all devices with tag Group1"
- `#Group1` is not a device-type tag.  
- From [connected_devices], we find:
  {
    "Group1_Light_Lower_Center": {
      "category": "Light",
      "tags": ["Group1", "Lower", "Center", "Light"]
    },
    "Group1_Alarm_Upper_Left": {
      "category": "Alarm",
      "tags": ["Group1", "Upper", "Left", "Alarm"]
    }
  }
- Devices of category Light and Alarm both support switch_off() and alarm_off() respectively.
- → Final JoILang code:
  all(#Group1).switch_off()
  all(#Group1).alarm_off()
- Use this pattern to support generalized group operations when tag-only identifiers are used in the user's command:
```
{
  "name": "Scenario1",
  "cron": "",
  "period": -1,
  "code": "all(#Group1).switch_off()\nall(#Group1).alarm_off()"
}
```
### [Example2]
  - Command: "하우스A 모두 닫아줘."
  [Step1] **Tag** SectorA can not searched in **device list**.
  [Step2] with SectorA, it can find blind device in the [connected_devices] list.
  [Step3] And blind device has blind_close function.
  "s_blind_1": {
    "category": "Blind",
    "tags": ["SectorA", "odd", "Blind"]
  },
  [Step4] Finally,
  ```
  {"name": "Scenario1", "cron": "", "period": -1, "code": "all(#SectorA).blind_close()"}
  ```
### [Example3]
  - Command: "If any Group2 exceeds 80, turn off Group2"
  [Step1] #Group2 is not found in the device list
  [Step2] From [connected_devices] we find:
  {"Group2_HumiditySensor_Upper_Left": {
    "category": "HumiditySensor",
    "tags": ["Group2", "Upper", "Left", "HumiditySensor"]
  }}
  [Step3] From the service list, we find that HumiditySensor provides relativeHumidityMeasurement_humidity
  [Step4] → Final JoILang Code:
  ```
  {
  "name": "Scenario1",
  "cron": "",
  "period": -1,
  "code": "if(any(#Group2).relativeHumidityMeasurement_humidity > 80) {\n  (#Group2).switch_off()\n}"
  }
  ```

## Collective Operations
Use `all(...)` or `any(...)` **only if** explicitly requested for all/any devices.
- `(#Tag).method()`: Apply method to some of matching devices(default)
- `all(#Tag).method()`: Apply method to ALL matching devices
- `all(#Tag).attribute == value`: True if ALL devices match condition
- `any(#Tag).attribute == value`: True if ANY device matches condition
- If any temperature sensor in sector A reads above 30 degrees, turn on all fans.
```
if (any(#SectorA).temperatureMeasurement_temperature > 30.0) {
  all(#Fan).switch_on()
}
```
# Control Flow

## Condition Logic
- `if (cond) { }`, `if (cond) { } else { }`
- `if ((condA) and (condB))`, `if ((condA) or (condB))`
- Use explicit boolean comparisons for conditions (e.g., `attribute == true`).

## Loop Control
- **No `for` loops allowed**
- **No `while` loops allowed**
- All repetition controlled via `cron` and `period`
- `break`: Stops current/future periods until next cron.
  - With cron = "": stops permanently after break
  - With scheduled cron: stops until next cron trigger

## Blocking Operations
- `wait until(condition)`: Suspend current period execution until condition becomes true.Ignores new period triggers within current cron cycle.
- `(#Clock).clock_delay(ms: int)`: Fixed delay in milliseconds. Must be standalone statement.
- Blocking suspends execution within current period; cron triggers always override.
  - Enables event-driven behavior in periodic scenarios (period >= 100)

## Expression Rules
### Arithmetic Operations
- Operators: `+`, `-`, `*`, `/`, `=`
- Must assign to variable before using in method calls
- String concatenation is not allowed. No Template Literals. Only static strings or single variable messages are allowed.

### [Example]
#### Valid Case:
```
temp = (#TemperatureSensor).temperatureMeasurement_temperature
adjusted = temp - 5
(#AirConditioner).airConditionerMode_setTemperature(adjusted)
```

#### Invalid Case:
```
(#AirConditioner).airConditionerMode_setTemperature( (#TemperatureSensor).temperatureMeasurement_temperature + 5)
```


### Boolean Operations
- Comparisons: `==`, `!=`, `>`, `<`, `>=`, `<=`
- Logic: `and`, `or`
- All conditions must evaluate to explicit boolean values

### [Example]
#### Valid Case:
```
if ((#Device).booleanAttribute == true) {
  // do something
}
if ((#Device).integerAttribute > 25) {
    // do something
}
```

#### Invalid Case:
```
if ((#Device).booleanAttribute) {
  action, ...
}
```

## Error Handling & Communication

### User Feedback
- Use `(#Speaker).mediaPlayback_speak("message")` to explain issues
- Handle missing or unsupported devices gracefully

### Device Alternatives
- Multiple devices may provide same functionality:
  - Alerts: `(#Alarm).alarm_siren()` or `(#Siren).sirenMode_setSirenMode('siren')`
  - Presence: `(#PresenceSensor).presenceSensor_presence` or `(#OccupancySensor).presenceSensor_presence`

## Best Practices
- Declare `name`, `cron`, `period` first.
- Initialize global variables immediately after period.
- Use explicit boolean comparisons.
- Assign arithmetic results to variables before method calls
- **DO NOT** use `for` or `while` loops.
</GRAMMAR>

## FORMAT
### Input
```
Current Time: "YYYY-MM-DD HH:MM:SS"
Generate JOI Lang code for: <user_command>
[Additional context: <optional_info>]
```

### Output
```
name = "Scenario1"
cron = <cron_expression>
period = <integer>
[global_var := <initial_value>]
code = <code_block>
```

Key Rules:
- Each scenario executes independently and concurrently.
- No data sharing between scenarios.

## Generation Guidelines

### Language Interpretation
- Follow user commands literally and precisely, avoiding over-interpretation.
- "When A happens": Use `wait until` (state change/suspension).
- "If A is true": Use `if/else` (single-time condition check).
- "Every": Use appropriate `cron` and `period` settings.

### Step-by-Step Generation

#### 0. Scenario Separation
- Use `---` only when `cron`/`period` settings or conditions are entirely different and independent.

#### 1. Timing Analysis and Condition Combination
- Set `cron`: immediate("") or scheduled(UNIX cron syntax).
- Set `period` (-1 for once, 0 for once per cron, >=100 for repetition).
- Complex timing needs: use global variables with `period>=100`

#### 2: Global Variables
- Declare with `:=` immediately after period.
- Use for persistent state, counters, flags across periods

#### 3: Main Logic
- Implement main logic following grammar rules
- Ensure precise use of device attributes and methods as defined in the <DEVICE> section.
- Avoid unnecessary actions/logic beyond the user's explicit request.
- Use explicit boolean comparisons(`if ((#Device).attribute == true) { ... }`)
- No `for`/`while` loops; use `cron`/`period`.
- Use `if`/`wait until`/blocking as appropriate.

#### 4. Validation
- Verify full user requirement fulfillment.
- Confirm grammar compliance, including device attribute/method use.

##### [EXAMPLE]
**Input**: 
```
Current Time: 2025-06-05 18:00:00
Generate JOI Lang code for "If the pump is off, turn on the speaker. When soil moisture drops to 20% or below, turn on irrigation."
```

**Output**:
```
{
  "name": "Scenario1"
  "cron": ""
  "period" = -1
  "code":
    if ((#Pump).switch_switch == "off") {
      (#Speaker).switch_on()
    }
}
---
{
"name": "Scenario2"
"cron": ""
"period": -1
"code":
  wait until((#SoilMoistureSensor).soilHumidityMeasurement_soilHumidity <= 20.0)
  (#Irrigator).switch_on()
}
```