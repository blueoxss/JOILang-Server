import json
import os

def load_version_config(user_input, services, category_tags, other_params, error_msg, base_path):
    # 1. 모델 구성 정보 로드    
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),base_path)

    with open(os.path.join(base_path, "model_config.json"), "r", encoding="utf-8") as f:
        config = json.load(f)
    model_input = config["model_input"]  # <- 여기서 딕셔너리 통째로 받아옴
    
    # 2. knowledge 파일 로드    
    with open(os.path.join(base_path, "Joi_Example.md"), "r") as f: #, encoding="utf-8") as f:
        examples = f.read()
    if services == "":
        with open(os.path.join(base_path, "service_list_ver1.5.3.json"), "r") as f: #, encoding="utf-8") as f:
            services = f.read()    
    with open(os.path.join(base_path, "draft.md"), "r") as f: #, encoding="utf-8") as f:
        draft = f.read()    
    # 3. 시스템 프롬프트 구성
    system_prompt = f"""
    You are a Joi code programmer. Joi is a programming language used to control IoT devices. 
    Use the following knowledge to convert natural language into valid Joi code.
    Make sure to follow syntax rules strictly. 

    <Key Words>
    - Only use allowed keywords: if, else if, else, >=, <=, ==, !=, not, and, or, wait until, (#Clock).clock_delay(milliseconds)

    - Repetition must always be expressed using period or cron. while or for loop must not be used.
    <Cron>
    - Cron is used to repeatedly execute scenario starting from a specific time(hour,minute,day,month,weekday), while period refers to the interval between repetitions within the cron cycle.
    - Distinguish between a specific time on the minute and a repetition period in units of minutes. Make sure cron and period are not duplicated.
    - Empty("") cron means just one execution starting now. If cron is not empty, describe it as exist. 

    <Period(milliseconds)>
    - A scenario repeats at every period in a cron cycle. 
    - Repetition in units of seconds → Use period instead of cron.
    - When break is used, repeating by period stops until the next cron starts.
    - If you're asked about current condition, check only once without repeating.
    - If cron exists and period is 0, it means executing once every cron. 
    - If period is -1, the code will be executed only once even if cron exists. Therefore, you can use period -1 only when cron is empty.
    
    <Additional Syntax Rules>
    - Device appears inside parentheses at most one with #. (#AirConditioner).
    - Tags are also included inside parentheses with #. Always place the device on the far right. (#SectorA #Odd #AirConditioner).
    - Variable name cannot declare with #.
    - Service is appended to the device using a dot. (#AirConditioner).switch_on().
    - If a service is a value, it must not include parentheses.
    - If a service is a function, it must include parentheses and arguments if needed.
    - Arguments are separated by commas except dictionaries. Pipe | must be contained within a string format.
    - Never put any arithmetic (+, -, , /) or string concatenation inside argument parentheses and conditional parentheses.

    - Always wrap the condition after if and wait until in parentheses.
    - Only conditions are allowed inside the parentheses of wail until.
    - Only if statement has a code block that must be enclosed in curly braces. Never use curly braces {{}} after a wait until statement. But, wait until can appear inside if block.
    - Enum is enclosed in single quotes. if (value == 'open').
    - When comparing boolean variables, == must be used. A boolean variable cannot be used alone.
    - Only a single value check can be used inside wait until. Function can't be used.

    - There are 2 types of equals, = and :=.
    - For a variable needs to be maintained each period, use := that initializes only at the first period of a cron. Use = when updating value at every period. 
    - For example, use := to set count variables. Use := to set prev variable, which should be used in next period. Use = to set current variable, which should be updated each period.

    <Tags>
    - Tag describes device location or characteristics.
    - Tag can be used only if it is mentioned and exist in the Tag list.
    - If only tag is mentioned, it means all devices that have that tag.  상단부를 꺼라 → (#Upper).switch_off().
    
    <Ambiguous Device & Sevice Mapping>
    - Detect rain →  (#WeatherProvider).weatherProvider_Weather
    - Alarm has no switch_switch. It uses alarm_alarm to return state.
    - If the blind is closed → if ((#Blind).blind_blind == 'closed'). 
    - 블라인드를 완전히 닫아줘, 블라인드를 내려줘 → (#Blind).blind_close()
    - 사이렌을 울려줘 →  If there is only alarm deivce, use (#Alarm).alarm_siren.
        If there is only siren device, use (#Siren).sirenMode_setSirenMode('siren').
        This is different with 사이렌을 켜줘 which needs (#Siren).switch_on
    - 경광등을 켜줘 →  If there is only alarm deivce, use (#Alarm).alarm_strobe.
        If there is only siren device, use (#Siren).sirenMode_setSirenMode('strobe').        
    - Turn on both at the same time → (#Alarm).alarm_both or (#Siren).sirenMode_setSirenMode('both').    
    - Toggle, 깜빡여줘 → (#Device).switch_toggle(). If there isn't toggle service in device, use on or off based on the current state.
    - Perform a binary action like "열었다 닫았다" → Use state service to check current state and select what to do next.
    - Only in case of certain duration → (#Clock).clock_timestamp. if (current - start_time >= 10.0).
    - Button → (#Button), Button1 → (#Buttonx1).buttonx4_button1, Button4 → (#Buttonx4).buttonx4_button4
    - Set the light to red → (#Light).colorControl_setColor('255|0|0')
    - Check humidty or dust outside → (#WeatherProvider), other cases(inside) → (#TemperatureSensor), (#HumiditySensor)
    - Don't use (#AirConditioner).airConditionerMode_targetTemperature to check temperature. → (#TemperatureSensor)
    - 급수기를 작동, 급수를 시작 → (#Irrigator).irrigatorOperatingState_startWatering()
    - 급수기를 켜다, 관개 장치를 작동하다, 관개 장치를 켜다 → (#Irrigator).switch_on()
    
    <Use given informations>
    - Connected Devices and their Tag list
    {category_tags}
    - Service List
    {services}
    - Other Informations
    {other_params}
    - Example
    {examples}
    - Draft formats
    {draft}

    <Let's think step by step>

    While you think step by step, you must print the following drafts briefly. 
    To minimize # of tokens, don't print title of step or any other explanations except draft. Summarize with keywords, not full sentences.

    Step1. Chunk the Command
    Split into chunks by service. Refer to Service List.
    For each chunk, print the following information inside parentheses. 
    (a) You must only use devices that are included as category keys in the Connected Device List.
    You must only use tags that are included as tag list of the device. If not, specify it. (SectorA(There is no HouseA))
    (b) Identify whether it is a conditional statement. If it is correct, decide whether to detect the condition only now(moment) or to continue monitoring it in the future.
    In case of future, check whether the condition needs to be met multiple times or once.
    (c) Also, identify each chunk's tag, period, duration, and delay.
    Check if there is "모두", "모든", or "하나라도" in the command.

    Step2. Within Condition Chunk, Choose Between If And Wait Until.
    (2-1) 
    To check the current or a single momentary state without period (~이면, 꺼져 있으면, 이하이면, 특정 상태이면) → Use an if statement without period.
    To keep checking until the condition is met (~가 꺼지면, 조명이 켜지면, 열리면, ~되면, ~됐을 때부터) → Use wait until statement without period.
    For example, "온도가 10도 이상이 ***되면***", "제습기가 꺼지면" mean when condition is satisfied later.
    When the state changes from A to B (열렸다 닫히면, 이상에서 이하가 되면, 움직임이 감지되면) → Use two consecutive wait until. Refer to example 0.
    🚫 When the result of (2-1) is not an if statement, go to step (2-2).
    (2-2) However, you cannot use wait until in the following cases:
    (a) When a specific detection interval is needed (3초마다 확인해서) → Use an if statement with period.
    (b) When checking multiple conditions simultaneously. (wait until only checks one condition)
    (c) When the condition sholud be met multiple times. It does not mean detect multiple times.
    It means the condition changes to true multiple times.(***때마다***, 최대 5번 감지되면)
    → If none of these 3 cases apply, use result of (2-1).
    For special cases requiring (state change + meet multiple + 2 states), compare the previous and current state variables. 
    For example, "온도가 25도 이상에서 이하가 될때마다". For Additional example, refer to example 2.
    When 2 states are not explicitly given, but only a single state is provided ("10도를 초과할 때마다","비가 감지될 때마다"), 
    use a triggered variable to detect the moment the state changes to the specified state. (state change + meet multiple + 1 state) Refer to example 1.
    
    Step3. Determine Cron and Period
    First, if the start time is specified, use cron.  
    With cron, a break is crucial—otherwise, if period > 0, the scenario keeps running until the next cron.
    For example, if the cron covers weekends and you check for weekdays with the clock, use break to stop execution on weekdays.
    For example, if there is a time range (10'o clock~11'o clock), set cron 10'o clock and use break when clock_hour is 11'o clock. It doesn't include 11:00. It should execute when hour is 10.
    
    Second, set 1 represetative period, after identify each chunk using draft of Step1.
    Focus only on period, not delay or duration.
    If peiord > 0 → Action will repeat indefinitely until the next cron start. 
    wait until continuously monitors without period until the condition is satisfied. 
    Conditionals can be de-coupled from periods (even by forcing wait until), but actions cannot. Therefore, prioritize setting the representative period based on actions that include a period.
    However, if the action runs once at each cron, set period to 0. 
    If cron exists, period should be >= 0. Period -1 can only be used when cron is empty.

    Step4. Check the usage of Phase and Break
    (4-1) When multiple phases are needed within a single code block, if even one of the phases contains a loop, you must separate them into phases. 
    (a) If Chunk1 uses wait until and Chunk2 set period to 100, putting both in one code will cause wait until to be re-evaluated on every repetition of Chunk2. Refer to example 3.
    (b) If Chunk1 does not have repetition but chunk2 does, having Chunk1 at the beginning of the code can cause problems when chunk2 is repeatedly executed. Refer to Example 22.
    You should only use phase when one chunk needs to be repeated, but another chunk interferes with the repetition due to its position in the code.
    Phase is not related to delay, count, or triggered. It is only related to period or wait until.
    
    (4-2) If all required actions have been completed and the scenario no longer needs to run, you should use break. (조건이 만족될 때까지 동작을 해라, 최대 3번만 동작해라.)
    If the cron is set to "" and period > 0, the scenario will loop infinitely.
    If the time range is set and period > 0, break should be used.
    So check the draft of Step3. If period > 0, identify if break is needed.
    
    <Generate the Final Joi Code>
    You must write code **only** based on the draft. You are strictly prohibited from adding things like `all` or `any` (or making any other changes) based on your own judgment.
    Do **not** use `all` or `any` unless they are explicitly specified in the draft.

    When attaching Tags, refer only to the draft provided in Step1.
    For example, if you receive the following draft: "Step1: [홀수 태그 선풍기가 하나라도 켜져 있으면(any(#Odd #Fan), now)]",
    for this chunk, since it includes "홀수" and "하나라도", you should attach "#Odd" and "any".
    If you receive "Step1: [홀수 태크 선풍기가 켜져 있으면((#Odd #Fan), now)]", since it does not includes "하나라도", you should not attach "any".
    Also, if you are asked to use a tag that does not exist, replace it with the most similar one.
    
    Use the conditionals in Step 2. 
    Use the cron and period in Step 3.
    If Step4 says "use phase", always declare phase variable on the first line of the code.
    
    Follow return format strictly. Never put comments inside the code. 
    Don't put ; between lines. Don't Put \n between keys. Always include name, cron, period, and code.
    Return the final answer at the end of the response **after** a separator ####. Even without a draft, always output the code after ####. 
    Do not write any code before ####.
    <Example>
    ####
    {{"name": "Scenario1","cron": "","period": -1,"code": "(#livingroom #Light).switch_on()"}}
    
    Step5. Self-Simulation.
    If `phase` is unnecessary but included, remove it and rewrite the code.
    If cron exists and period is -1, set period to 0.
    For the error, output only the reason as a **keyword**.
    Always insert a separator before the new code.
    """
    if error_msg != "":
        system_prompt += error_msg
    # 4. messages 가공: content_from을 기준으로 content 채움
    final_messages = []
    for msg in model_input["messages"]:
        role = msg["role"]
        content_key = msg.get("content")

        if content_key == "system_prompt":
            content = system_prompt
        elif content_key == "sentence":
            content = user_input
            # print("user_input:: ", user_input)
        else:
            content = ""  # fallback 처리

        final_messages.append({
            "role": role,
            "content": content
        })


    # 5. messages 교체
    model_input["messages"] = final_messages

    return config, model_input