## JoILang Temporal Condition Interpretation Guide
### 1. Static condition (state check): ~였으면, ~인 상태면, ~라면 (If)
   - Korean command: “문이 닫혀 있으면”
   - English translated command: "if the door is closed"
   - → if ((#Door).doorControl_door == "closed")
   - 현재 상태가 닫힘일 때 즉시 실행
   - Applies when the state is already true at evaluation time.

### 2. Dynamic transition (state change detection): ~하면, ~하게 되면 (When)
   - Korean command: “문이 닫히면”
   - English translated command: "when the door closes"
   - → wait until ((#Door).doorControl_door == "closed"), 
   - Korean command: "제습기가 꺼지면"
   - → wait until((#Dehumidifier).switch_switch == "off")
   - 열린 상태에서 닫힐 때만 실행 (이미 닫힘이면 미실행)
   - Triggers only when the condition becomes true from the opposite state.

### 3-1. Combined condition: ~였다가 ~하면, ~였거나 ~하면, ~이거나 ~하면 (If + when, If + And then)
   - Korean command: "비어있다가 누군가 감지되면"
   - "**비어있다가**" is **state check(과거 상태 검사)** + "누군가 감지되면" **state change(미래 변화 감지)**를 모두 수용
   - Korean command: “문이 닫혀있거나 닫히면”
   - English translated command: "if or when the door is closed"
   - → if ((#Door).doorControl_door == "closed") { ... } else { wait until ((#Door).doorControl_door == "closed") }
   - 현재 상태가 이미 참인지 확인하고, 아니라면 그 상태가 미래에 될 때까지 기다리는 방식
   - 즉, **state check(현재 상태 검사)**와 **state change(미래 변화 감지)**를 모두 수용
   - 이 두 조건은 시간상 연속되지 않아도 되며, 서로 독립적으로 만족될 수 있음
   #### [Example]: “토양 습도가 20% 이상인데 알람이 켜지게 되면 물을 줘” → 토양 상태와 알람 이벤트는 독립적이며, 둘 다 충족되었을 때 실행
   - Use: if (토양 습도 state check) { wait until (알람 state change) }
   - Reacts to either current satisfaction or future transition—whichever happens—ensuring coverage of both temporal paths.

### 3-2. Combined condition: = ~하고 ~하면, (When + When)   
   - Separately,When a condition involves **two consecutive state changes**, like “A happened, and then B happens” 
   - Korean command: "**비었다가** 누군가 감지되면"
   - "**비었다가**" is **state check(현재 변화 감지)** + "누군가 감지되면" **state change(미래 변화 감지)**를 모두 수용

   - Korean example: “문이 닫혔다 열리면”, “비가 오는데 창문이 열려 있으면”  
   - → Use **two `wait until` statements** to capture both transitions when events must occur in sequence.  
   - If the condition requires simultaneous truth (e.g., “if it's raining and the window is open”), use a single `if (...) and (...)` block instead.
   #### [Example] "문이 열렸다 닫히면 알림을 울려줘."
   ```
   {"name": "DoorClosedAlert", "cron": "", "period": -1, "code": 
   "wait until((#DoorLock).doorControl_door == \"open\")\n
   wait until((#DoorLock).doorControl_door == \"closed\")\n(#Alarm).alarm_siren()"}
   ```

### 4. One-Time Trigger + Subsequent Repeating Action
   - When the natural language includes phrases like “after ~, repeat every N seconds”,  
it should be interpreted as a **one-time condition trigger**, followed by a **periodic loop** of actions.
#### Key Principles
- Detect the **triggering event** only once using **Dynamic transition (state change detection)** `wait until (...)` or **Static condition (state check)** `if`.
- Control repeated actions using `period > 0` and a Boolean flag variable.
- Use flags like `triggered := false` or `action := false` to maintain state inside the loop.
#### [Correct Example: One-time trigger, then loop]  
**Command**:  
> "When the front door closes, immediately turn off the light, and then flash the strobe every 3 seconds."
**Interpretation**:
- `"when the door closes"` → single detection via `wait until (...)`
- `"every 3 seconds"` → continuous action with `period: 3000`
```
{
  "name": "Scenario1",
  "cron": "",
  "period": 3000,
  "code": "action := false\nif (action == false) {\n  wait until ((#Door).doorControl_door == \"closed\")\n  (#Light).switch_off()\n  action = true\n}\nif (action == true) {\n  (#Alarm).alarm_strobe()\n}"
}
```

### 5. loop는 period를 의미하며, Combined condition + Repeating condition (dynamic + periodic): ~할 때마다, ~하게 될 때마다 + 주기적으로 ~해줘.
   - Korean command: “문이 열릴 때마다”
   - English translated command: "whenever the door opens"
   - → use with period > 0 loop:
     if ((#Door).doorControl_door == "closed") { wait until ((#Door).doorControl_door == "open") }
   - Korean command: “문이 열릴 때마다”, “문이 닫혔다 열릴 때마다 사진을 5초 단위로 찍어줘”
   - English translated command: "whenever the door opens", "after the door closes and opens, take a photo every 5 seconds"
   - → Use with "period": 100 to continuously monitor state transitions and respond in real time.
   - → Combine state change detection with loop { ... clock_delay(...) } to express repeated actions after the triggering condition.
   [example]
   ```
   "cron": "",
   "period": 100,
   "code": "
      wait until ((#DoorLock).doorControl_door == \"closed\") {
         wait until ((#DoorLock).doorControl_door == \"open\")
         (#Camera).camera_take()
         (#Clock).clock_delay(5000)
      }
   "
   ```
   - Use this pattern when a condition leads to continuous behavior (e.g., taking photos every N seconds) rather than a one-time reaction.
   - When a command includes both a **"state-based trigger" (~할 때마다)** and a **"fixed time loop" (e.g., every 2 seconds)**, you **must use `period` with a state flag variable** to prevent repeated triggering within the same state.  
   - This ensures actions occur **only once per transition** while still checking repeatedly.  
   - You must initialize a **boolean variable** using `:=` and reset it appropriately to track state transitions accurately.
   #### [Example]
   **Korean:** `2초마다 상태를 확인해서 TV가 켜질 때마다 스피커도 켜 줘.`  
   **JoILang:**
   ```
      "name": "Scenario1",
      "cron": "",
      "period": 2000,
      "code": "
      triggered := false
      if ((#Television).switch_switch == "on") {
         if (triggered == false) {
         (#Speaker).switch_on()
         triggered = true
         }
         } else {
         triggered = false
      }
   ```

### 6. 주기적 감시/반복 실행 기반: 계속 ~하면 ~해줘, ~동안 ~하면 ~해줘
   - Requires periodic check or loop (period) to react to each occurrence.
   - Use "period": 100 (or another value > 0) to repeatedly check the condition at regular intervals.
   - When using variables to count time or duration inside "code", such as lightOnTime = lightOnTime + 100, the period value directly determines the unit of increment.
   - Therefore, if no specific interval is given, you must set "period": 100" as the default to ensure accurate time tracking (e.g., 1800000ms = 30 minutes).
   - Important distinction: If the command describes a one-time event followed by a delay, 
   - The `(#Clock).clock_delay(ms)` command suspends execution for the specified duration in milliseconds without needing to be used with `wait until`. It can be used as a standalone blocking statement.
   - If a command includes a numeric time condition (e.g., "5초 내에, within 5 seconds"), you must ensure the logic enforces that constraint explicitly in code.
   - → This is not a repeating condition. It should be handled using "period": -1 and an explicit delay call like:
   - [Example]
      Korean: “불이 켜져있으면 30분 후에 알림을 울려줘”
      English: "If the light is on, trigger an alarm 30 minutes later."
      ```
      "cron": ""
      "period": -1
      "code": "if ((#Light).switch_switch == \"on\") { (#clock).delay(1800000); (#Alarm).alarm_siren() }"
      ```

### General Mapping Principles:
- Use `if (...)` for **instantaneous execution based on current state**.
- Use `wait until (...)` for **monitoring future state transitions**.
- Combine `if (...)` and `wait until (...)` using `if-else` to **cover both present and future satisfaction**.
- Use `"period": > 0` to **enable repeated detection** for expressions like "every time", "whenever", or “~할 때마다”.

