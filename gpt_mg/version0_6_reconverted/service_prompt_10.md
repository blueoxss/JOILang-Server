## Step-by-Step Guide for Separating `value` and `function` in Natural Language Commands (Prompt Guide)

---

## Purpose

Before converting a natural language command into SoP-Lang, clearly distinguish between **condition evaluation (`value`)** and **action execution (`function`)** within the sentence.

---

## Step 1: Distinguish Conditional vs. Command Phrases
### Characteristics of `value` Phrases
Purpose: Used for state evaluation or comparison conditions
Typically includes expressions such as: if, when, in case, greater than, during, etc.
- You must only use services defined in [service_list_value]
- Both device tags and service names must exactly match the entries
- Do NOT create or assume any service name that is not explicitly listed
- If a device does not exist in the full list, use a device only if it exists in [connected_devices]
- Do not use undefined value services (e.g., windowControl_window) in condition expressions
#### [Correct Examples]
- if ((#Window).windowControl_door == "closed")
#### [Incorrect Examples]
- (#Light).switch_switch == "on"      
- This is a value, not a function


### Characteristics of `function` Phrases
Purpose: Used for device control or command execution
Typically includes imperative verbs like: turn on, turn off, close, open, send, activate, etc.
- You must only use services defined in [service_list_function]
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

## Step 2: Extract both `value` and `function` from compound sentences
For composite commands, split the sentence into separate `value` and `function` components.

**Example:**  
> “If it’s raining and the window is open, close the window.”

- `value`:
  - “It’s raining”
  - “The window is open”

- `function`:
  - “Close the window”

---

## Step 3: Prepare extracted `value`/`function` for SoP-Lang processing
- `value` → Convert into sensor evaluation expression:  
  **Example:**  
  `if ((#Sensor).attribute() >= value)`

- `function` → Convert into device command expression:  
  **Example:**  
  `(#Device).function_on()`


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