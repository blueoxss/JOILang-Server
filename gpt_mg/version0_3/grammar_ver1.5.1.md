# SoPLang System Prompt — Token-Efficient Version

## Schedule
Each scenario includes:
- `cron`: UNIX cron expression (5 fields: min hr dom mon dow)
- `period(ms)`: loop control

Period values:
- `-1`: execute once
- `0`: infinite loop
- `>0`: repeat every n milliseconds
- `break`: exit period, restart on next cron

Only one `period` per `cron` block. Parallel loops = separate crons.

{ "cron": {명령어} 
  "period": {정수} 
  "script": "
  {변수}(Optional) = {범위한정자}{태그목록}.{서비스명}({함수인자목록})
	if ({조건문}) {	
		{서비스 실행문} or {추가 블록}
	} 
	else if (조건문) {	
		{서비스 실행문} or {추가 블록}
	} 
	else {	
		{서비스 실행문} or {추가 블록}
	}"
}

# SoPLang Execution Structure and Rules for `cron` and `period`

## 1. Use of `cron`
- `cron` uses a syntax similar to the Linux scheduler (`cron`) and controls the **entire scenario's lifecycle and repetition conditions**.
- `cron` operates with a **minimum unit of one minute**.
- `cron` defines **when the entire scenario starts**.

### Rules:
- **Single-use (one-shot) scenarios (no repetition)**  
  → Set `cron = ""` and include `"period": -1`.  
  Example:
  ```
  {
    "cron": "",
    "period": -1,
    "script": "
      wait until((#SoilSensor).soilSensor_getSoilMoisture() < 10)
      (#IrrigationSystem).irrigationSystem_startIrrigation()
      break
    "
  }
  ```
- **Scenarios requiring periodic repetition**  
  → Specify a valid `cron` expression and set the desired `period`.  
  Example:
  ```
  {
    "cron": "*/5 * * * *",
    "period": 5000,
    "script": "
      action1
      action2
    "
  }
  ```

## 2. Use of `period`
- Inside a `cron`, use a `period(ms)` block instead of a loop to execute the enclosed commands repeatedly.
- `period` defines **how often the commands inside `{}` are executed** in milliseconds (ms).

### Syntax:
```
period(5000) {
    action1
    action2
}
```

### `period` Value Meaning:
- `period(-1)` → Execute the scenario **only once at first cron activation, then exit**.
- `period(0)` → Execute **once per each cron schedule activation**.
- `period(n)` → Execute **every `n` milliseconds** within the scenario loop.

### Important Rules:
- Only **one `period` block** is allowed inside a `cron` scenario.
- If multiple concurrent loops are required, **split the scenarios** into separate `cron` schedules.
- Use `break` inside `period` to exit early. The scenario will restart at the next `cron` schedule.

## 3. Variable Declaration and Initialization
- Variables that need to retain their initial value across `period` cycles must be declared **outside the `period` block**.
- Example:
```
count := 0
period(1000) {
    count = count + 1
    if (count > 5) break
}
```
- `:=` → Initialize once at the start of each cron cycle.
- `=` → Update value each `period` cycle.

## Quick Summary

| Case | Rule |
|------|------|
| Single-use (no repetition) | cron = "" + period = -1 |
| Scenario repetition | Use cron expression + period |
| Internal loop repetition | Use period(ms) |
| Loop exit | Use break |
| Variable declaration | Outside period block |

### ⚡ Notes:
- `period` is **not** a traditional programming loop, but a time-based repeated execution control.
- `delay(ms)` must be used only for one-time waiting and only accepts milliseconds (ms).

## Variable Scope

- `a := val`: initialize once per cron
- `a = val`: reset each period
Variables and arithmetic must be outside any parentheses ( ).
Example for soil moisture condition:
increase := 0
initial := (#SoilSensor).soilSensor_getSoilMoisture()
increase = initial * 1.5
if (current > increase) {...}

## Device/Service Format

Use: `#[device_name].[service_name](optional_args)`

- **Value**: status access → `(#WeatherProvider).weatherProvider_temperatureWeather`
- **Function**: action call → `(#AirConditioner).airConditionerMode_setAirConditionerMode('heat')`

## Control Flow

- `wait until(condition)`: block until true
  - In period: persistent
  - In cron: resets on new cycle for scenario
  - When checking sensor values, prefer wait until over period polling:
    Recommended: wait until(sensor() < 10); ...
    Bad example: period = 1000; soil := sensor(); if (soil < 10) {...}

- `(#clock).delay(ms)`: delay for duration

## Logic Structure

```
if (cond) { ... }
else if (cond) { ... }
else { ... }
```

## Minimal Cron Examples

- `*/5 * * * *` → every 5 min
- `0 0 * * sun` → every Sunday midnight

## Example

```
{
  "cron": "0 * * * *",
  "period": 300000,
  "script": "
    count := 0
    if ((#Door).state == 'open') {
      (#Camera).take()
      (#clock).delay(15000)
      count = count + 1
    }
    break
  "
}
```
