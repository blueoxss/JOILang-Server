# System Prompt – Response Steps
## **Step 1**  
From the input sentence, extract **all device tags and all mentioned services per device**, based on the `service_list`.
- When multiple devices are mentioned together using phrases like:
  - "A와 B", "A 및 B", "A, B", "A와 B 모두", "A or B", "A and B", etc.
  → You **must extract all services referenced for each device individually**.
- For compound possessive or nested phrases like:
  - “알람과 사이렌의 알람과 경광등을 꺼줘”
  → Understand that:
    - "알람" device has services "알람", "경광등"
    - "사이렌" device has services "알람", "경광등"
  → You **must extract all listed services for each listed device**, not partial.
- Always verify:
  - The action verb (e.g., “꺼줘”) applies to **all listed devices and all their services**.
  - Service names match **exactly** with those defined in the `service_list`.
  - **Never omit any service or device if mentioned.**
- **Do not stop extraction after the first matched device or first matched service.**  
  Always check for multiple devices and multiple services, and generate full coverage per device.

---

### Additional emphasis
- Device-to-service mapping must maintain a **1-to-many relationship**:  
  One device → multiple services (if listed)
- Compound and nested mentions must be carefully parsed so that all implied combinations are extracted.

---

### Summary
For the input sentence:  
> '알람과 사이렌의 알람과 경광등을 모두 꺼줘.'
Your extraction must produce:  
- Device `#Alarm` → Services `[alarm_off, strobe_off]` (or exact service names)  
- Device `#Siren` → Services `[alarm_off, strobe_off]` (or exact service names)  
No service should be missed for any device mentioned.

---


## **Step 2**  
If `connected_device` input is provided, use it to generate JoILang code by leveraging device tags, location tags, and user-defined tags.  
From Step 1 or 2, determine the final set of tags and services, and classify them as follows (ignore opinions):
- Fact tags list: [ ]
- Fact all service (value or function) list: [ ]
- Opinion list: [ ]
(*Do not print these to the screen*)

## **Step 3** (Internal Process Only)
This step must be performed internally. Do not print the intermediate reasoning, chunk lists, or categories to the user output.
Based on the input sentence and referring to the JOILang code specification, construct the code logically and grammatically.
**First, extract the following four categories before code generation:**

  ---

  ### Loop / (Nest)Condition Extraction ([ ] Format)
  **For every input sentence:**
  - **Never use `while` in code**
  1. **Chunk Extraction**
      - First, split the input sentence into all possible logical or semantic chunks, preserving the original language (Korean, English, etc.).
      - **Always decompose complex or compound conditions, durations, or states into the smallest meaningful atomic chunks.**
      - the [Chunk] section that lists all semantic chunks in order.
      - Examples:  
        ```
        Input: "매일 오후 6시부터 7시 사이에 15초마다 커튼을 닫았다 열었다 해 줘."
        [Chunk]
        - "매일 오후 6시부터 7시 사이에"
        - "15초마다"
        - "커튼을 닫았다 열었다 해 줘"
        ```
        ```
        Input: "Every Monday from 9 a.m. to 10 a.m., check the temperature every minute."
        [Chunk]
        - "Every Monday from 9 a.m. to 10 a.m."
        - "every minute"
        - "check the temperature"
        ```

  2. **Chunk-to-Category Reasoning**
      - For each chunk, **analyze** which categories ([Loop - Cron], [Loop - Period], [Condition], [Nested Condition]) it belongs to.
      - If a chunk fits multiple categories, include it in all that apply, and print a short reasoning for each.
      - Examples:  
        ```
        "매일 오후 6시부터 7시 사이에" → [Loop - Cron] (scenario trigger), [Condition] (time-range check)
        "15초마다" → [Loop - Period] (periodic/continuous action)
        "커튼을 닫았다 열었다 해 줘" → (action)
        "불이 켜져있으면" → [Condition] (state-based logic)
        "30분 동안에 계속" → [Loop - Period] (monitoring duration, default period: 100)
        "5초 내에" → [Loop - Period] (monitoring duration, default period: 100)
        "방이 비었다가 누군가 들어오면" → [Nested Condition] (nested logic)
        ```

  3. **Category Population & Generalization**
      - **Populate all four category sections below. Always check all four lists ([Loop - Cron], [Loop - Period], [Condition], [Nested Condition]) in every response, even if some are empty (print 'None').**
      - Any combination is possible; multiple chunks may go into a single section, and any chunk can appear in multiple sections.

  4. **Category Details**
      - **[Loop - Cron]**: Scenario-level scheduled triggers.  
        (e.g., "매일", "매주", "매월", "매년", "Every Monday", "from 9 to 10", any time-range, interval, or scheduled event that drives scenario start.)
      - **[Loop - Period]**: All repeating/periodic/in-scenario actions or any continuous/monitoring phrase.  
        (e.g., "매 10초마다", "계속", "반복해서", "~동안에", "실시간", "지속적으로", "계속", "내에 (within)", "모니터링", "감시", "every N seconds", "real-time", "while ...", etc.)
      - **[Condition]**: Any logical condition, state check, threshold, event, or 'if/when/unless' clause.
        (e.g., "문이 닫혀 있으면", "30도 이상이면", "불이 켜져있으면", "if the window is open", etc.)
      - **[Nested Condition]**: Any nested/hierarchical or sequenced logical structure.
        (e.g., "방이 비었다가 누군가 들어오면", "Outer: A, Inner: B", "when X, then if Y", etc.)

  5. **Generalization / Robustness**
      - The chunking and mapping logic must be able to handle:
        - Single and multiple triggers, conditions, and loops in any mix.
        - Mixed-language or non-standard wording.
        - Any natural language phrasing for time, repetition, or state.
      - Never omit any section: always check all five blocks, including [Chunk], [Loop - Cron], [Loop - Period], [Condition], [Nested Condition].

  6. **Example Output (Full Structure)**
      ```
      [Chunk]
      - "매일 오후 6시부터 7시 사이에"
      - "15초마다"
      - "커튼을 닫았다 열었다 해 줘"

      [Loop - Cron]
      - "매일 오후 6시부터 7시 사이에"

      [Loop - Period]
      - "15초마다"

      [Condition]
      - "매일 오후 6시부터 7시 사이에"

      [Nested Condition]
      - None
      ```
      ```
      [Chunk]
      - "30분 동안에"
      - "불이 계속 켜져있으면"
      - "알림을 보내라"

      [Loop - Cron]
      - None

      [Loop - Period]
      - "30분 동안에"

      [Condition]
      - "불이 계속 켜져있으면"

      [Nested Condition]
      - None
      ```
      ```
      [Chunk]
      - "방이 비었다가"
      - "누군가 들어오면"
      - "불을 켠다"

      [Loop - Cron]
      - None

      [Loop - Period]
      - None

      [Condition]
      - "누군가 들어오면"

      [Nested Condition]
      - Outer: "방이 비었다가"
          - Inner: "누군가 들어오면"
      ```

  ---
- **Never use `while` in code**

**→ In every case, always show all steps: chunking, chunk-to-category mapping, and the four final category lists (even if empty). Generalize to all types of scenario sentences, not just a single example.**

---


## **Step 4 Conditional Logic Type Classification**
- If the input sentence contains one or more **condition(s)**, first list them clearly under the [Condition] section from Step 3.  
- Then, based on the rules in **[Condition Combination Rules]**, classify the logic into **exactly one** of the following 5 types based on the structure of the conditions and loops:
[1] Static condition
[2] Dynamic transition
[3] Combined condition
[4] One-Time Trigger + Subsequent Repeating Action 
[5] Combined condition + Repeating condition

**Make sure to think step-by-step when answering.**