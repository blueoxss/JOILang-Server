## Step-by-Step Guide for Separating `value` and `function` in Natural Language Commands (Prompt Guide)

---

## Purpose
Your task is to:
1. Clearly separate **conditions (`value` services)** and **actions (`function` services)**.
2. Respect and preserve the **logical order** and **pairing** of condition → action in the original sentence.
3. Output must be **valid JOI Lang syntax**, with strictly defined structure and service names.

---

## Step 1: Distinguish Conditional vs. Action Phrases
### Conditions: Characteristics of `value` Phrases
Purpose: Used for state evaluation or comparison conditions
- Used for evaluating the state of sensors or devices.
- Includes expressions like: "if", "when", "greater than", "in case", "is on", "equals", "during", etc.
- You must only use `value` services defined in [service_list_value]
- Both device tags and service names must exactly match the entries
- Do NOT create or assume any service name that is not explicitly listed
- If a device does not exist in the full list, use a device only if it exists in [connected_devices]
- Do not use undefined value services (e.g., windowControl_window) in condition expressions
#### [Correct Examples]
- if ((#Window).windowControl_door == "closed")
#### [Incorrect Examples]
- (#Light).switch_switch == "on"      
- This is a value, not a function


### Actions: Characteristics of `function` Phrases
Purpose: Used for device control or command execution
- Used for executing control commands on devices.
- Includes verbs like: "turn on", "turn off", "open", "close", "send", "activate", etc.
- You must only use `function` services defined in [service_list_function]
- Both device tags and function names must exactly match the entries
- If a device is not available in the full list, use only those available in [connected_devices]
- Do not use value-type services as functions
#### [Correct Examples]
- (#Light).switch_on()
- (#Curtain).curtain_close()
#### [Incorrect Examples]
- (#Window).windowControl_window()    
- This function does not exist



---


## Step 2: Prepare extracted `value`/`function` for JOI Lang processing
### Split compound natural language commands into:
- `value` expressions (conditions) → Convert into sensor evaluation expression:  
  `if ((#Sensor).attribute >= value)`
- `function` expressions (actions) → Convert into device command expression:  
  `(#Tag).function_on()`
#### [Example]  
Command: “If it’s raining and the window is open, close the window.”
- `value`:
  - “It’s raining”
  - “The window is open”
- `function`:
  - “Close the window”


---


## Step 3: Extract `value` and `function` + Preserve Temporal **Execution Order**
### General Patterns of Execution Flow
- Your job is not just to separate them, but also to **preserve the execution order as implied by the natural sentence**, not just by grammar structure.
- Natural language commands can appear in different logical forms.  
- The model must handle the correct **temporal relationship** between condition and action.

#### ✅ Pattern 1: Condition → Action (Most common)
- Evaluate condition first, then execute one or more actions.
[Example]:  
> “If it’s raining and the window is open, close the window.”
```
if ((#RainSensor).rainStatus == "on" and (#Window).windowControl_door == "open") {
    (#Window).windowControl_close()
}
```
#### ✅ Pattern 2: Action → Condition → Termination or Follow-up
- The command begins with an action, and later introduces a condition for stopping, switching, or repeating.
[Example]:  
> “Turn on the irrigator. When the light exceeds 500 lux, turn it off and stop.“
```
(#Irrigator).switch_on()
wait until ((#LightSensor).lightLevel_light >= 500)
(#Irrigator).switch_off()
break
```
#### ✅ Pattern 3: Multiple Independent Condition → Action Pairs
- Each condition controls its own action. They are not necessarily sequential or nested.
- Always **evaluate the condition before executing any related action**.
- Never reverse the order from the original command unless explicitly indicated.
[Example]:  
> “If soil is dry, start irrigation. If temperature is high, turn on the fan.”
```
if ((#SoilSensor).moisture < 30) {
    (#Irrigator).switch_on()
}
if ((#Thermometer).temperatureMeasurement_temperature >= 30) {
    (#Fan).switch_on()
}
```
#### ✅ Pattern 4: Mixed or Nested Execution Flow
- Commands can involve a **combination of patterns**, such as:
  - A condition triggering multiple actions,
  - Then a follow-up condition for termination,
  - Or nested conditions within an action block.
[Example]:  
> “If it's morning and no one is home, open the curtains. Then, when the light exceeds 800 lux, turn them off.”
```
if ((#Clock).clock_time >= 600 and (#Presence).presence == "not_present") {
    (#Curtain).curtain_open()
    wait until ((#LightSensor).lightLevel_light >= 800)
    (#Curtain).curtain_close()
}
```


---


## Additional Syntax Rules for Mapping
### For **value services**:
Use the **return_descriptor** to determine comparison format and semantics.

#### [Example]
- If "device": "Clock", "service": "clock_time" has return_descriptor = {"format": "hhmm"},
then use:
"code": if ((#Clock).clock_time == 1515)

### For **function services**:
Use **argument_type** or **argument_format** to determine the correct format.
Use **argument_bounds** or **argument_descriptor** to determine the correct format.

#### [Example1]
- If "device": "Light", "service": "colorControl_setColor" has argument type DICT
with bounds key/value pairs: "RED|GREEN|BLUE" and example "255|255|255",
then use:
(#Light).colorControl_setColor("255|0|0")

#### [Example2]
If "device": "Calculator", "service": "calculator_mod" function service has
  "argument_type": "DOUBLE | DOUBLE",
  "argument_format": " | ",
then use:
- "code": {"name": "Scenario1", "cron": "", "period": -1, "code": "(#Calculator).calculator_mod(10 | 3)"}


---


## Summary Table of Examples

| Natural Language Command                               | value                          | function       |
|--------------------------------------------------------|--------------------------------|----------------|
| If the door is open, trigger the alarm                 | Check door status              | Trigger alarm  |
| If the window is closed and temperature exceeds 30°C   | Window status, temp condition  | Turn on fan    |
| When the button is pressed, turn off the lights        | Button press                   | Turn off light |
| If any humidity sensor in Group 1 reads below 30       | Group 1 humidity condition     | Water the area |

---

## Proceeding to the Next Step

1. Use `value` → map automatically from [`service_list_value`] (`service_list_ver1.5.4_value.json`)
2. Use `function` → map from [`service_list_function`] (`service_list_ver1.5.4_function.json`)
3. Assemble both into a complete SoP-Lang code block  