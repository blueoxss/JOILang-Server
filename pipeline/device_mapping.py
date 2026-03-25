import ollama
import json
import time
import re
import os
import argparse
import time
import requests

'''
from mqtt.mqtt_handler import mqtt_handler
from utility.thing_extract import extract_thing_list, extract_thing_from_thing_list
from utility.servicelist_modify import file_parse 
'''
from .SERVICE_DESCRIPTION_FINAL import description
from .device_verifier import *


THINGS_LIST = """(#AirConditioner)\n(#AirPurifier)\n(#AirQualityDetector)\n(#Blind)\n(#Button)\n(#Calculator)\n(#Camera)\n(#Charger)\n(#Clock)\n(#ContactSensor)\n(#Curtain)\n(#Dehumidifier)\n(#Dishwasher)\n(#DoorLock)\n(#EmailProvider)\n(#Fan)\n(#Feeder)\n(#GasMeter)\n(#GasValve)\n(#Humidifier)\n(#HumiditySensor)\n(#Irrigator)\n(#LeakSensor)\n(#Light)\n(#LightSensor)\n(#MenuProvider)\n(#MotionSensor)\n(#PresenceSensor)\n(#Pump)\n(#Refrigerator)\n(#RobotCleaner)\n(#Shade)\n(#Siren)\n(#SmartPlug)\n(#SmokeDetector)\n(#SoundSensor)\n(#Speaker)\n(#Switch)\n(#Television)\n(#TemperatureSensor)\n(#Valve)\n(#WeatherProvider)\n(#Window)"""
MAPPING_INSTRUCTION_DEVICES =  f"""Please read the CODE OF CONDUCT between [INST] and [/INST] very carefully. Go through the following instructions step by step and complete the task.
You are an module of an AIOT System called "SoPIoT". The Big Picture of SoPIoT is understand the user's natural language request and convert it into a SoP-Lang which is a language that AIoT system can understand.

Your role is to get a user input and figure out what devices are needed for them.  Come up with devices  as many as  possible that can be used for the command.
YOU ARE RESPONSIBLE FOR ANALYZING WHICH DEVICES TO USE PRINT EVERY ONE OF THEM TO EXECUTE THE COMMAND

    THE FINAL GENERATION FORMAT MUST BE IN A SINGLE 3 LINE RESULT :

    [OUTPUT]
        [Device] : (Needed device list) 
    [/OUTPUT]

    THESE ARE JUST EXAMPLES 

    [EXAMPLES]

        1. Input: If the temperature sensor is detected below 18 degrees, set the air conditioner to heat mode. value check: check the temperature action: turn on the air conditioner, set the airconditioner mode to heat
        [OUTPUT]
            [Device] : (#TemperatureSensor), (#AirConditioner)
        [/OUTPUT]
        
        2. Input : Every hour, when it is 50 minute, open the blinds of the room and play soft music on the speakers. valuecheck:check the time action : open the blind, play soft music on speaker
        [OUTPUT]
            [Device] : (#Clock), (#TemperatureSensor), (#AirConditioner),  (#Blind), (#Speaker)
        [/OUTPUT]

        3. Input : If the humidity is over 50, turn on the dehumidifier and the airpurifier and fan. set fan into the high mode if temperature is over 20 valuecheck: check the humidity check the temperature aciton : turn on the dehumifier, turn on the fan, turn on the airpurifier, set the fan into high mode
        [OUTPUT]
            [Device] : (#HumiditySensor), (#TemperatureSensor), (#Dehumidifier), (#AirPurifier), (#Fan)
        [/OUTPUT]

        4. Input: turn on the air conditioner  valuecheck : None action: turn on the airconditioner
        [OUTPUT]
            [Device] : (#AirConditioner)
        [/OUTPUT]

        
        5. Input: turn on the coffeemaker valuecheck : None action: turn on the coffeemaker
        [OUTPUT]
            [Device] : None
        [/OUTPUT]
    
        6. Input: If the temperature is below 23 degrees Celsius, turn on the air conditioner and if it's above 25 degrees Celsius, turn it off value check: check the temperature action: turn on the airconditioner, turn off the airconditioner
        [OUTPUT]
            [Device] : (#TemperatureSensor), (#AirConditioner)
        [/OUTPUT]

        7. Input:Play the music between 12:30 and 1:00, and open the blinds to 50% to let the natural light in. value check: check the time action: turn on the speaker, play the music using speaker, set the blind open percentn to 50.
        [OUTPUT]
            [Device] : (#Clock), (#Speaker), (#Blind)
        [/OUTPUT]
        
        8. Input: When you start reading, set the light to natural light mode and adjust the brightness to 60%.  value check: None action: turn on the light, set the light level to 60
        [OUTPUT]
            [Device] : (#Light)
        [/OUTPUT]
    OTHERS ARE NOT ALLOWED!!!!

    Here are the list of devices.
    {THINGS_LIST}
    You must find appropriate values or functions in the list. ALWAYS MAKE DEVICES FROM THIS LIST!!!!

    You should check each sentence and see whether there is anything you don't find in the list.
    FIGURE OUT FROM  COMMAND AND FIND MANY DEVICES AS POSSIBLE!!!!!

    Let's think step by step.  
    DO NOT PRINT ANY DESCRIPTIONS. ONLY THE RESULT
    ==========
    STEP 1. Device Mapping

    Using the original command (input) given, Figure out What exact device is need a to execute the command. You should only use Devices in the given device string. 
    Return the corresponding Devices for all parts of the command. Find all the devices for the command YOU SHOULD NOT MISS ANY FIND MANY AS POSSIBLE. FIND EVERY SINGLE ONE OF THEM FROM THE INPUT COMMAND

 """

MAPPING_INSTRUCTION_DEVICES_YG= """
Please read the CODE OF CONDUCT between [INST] and [/INST] very carefully. Go through the following instructions step by step and complete the task.
You are the second module of the AIoT system called "SoPIoT" which stands for Service Oriented Platform for Internet of Things.
The Big Picture of SoPIoT is to understand the user's natural language request and convert it into a SoP-Lang which is a language that the AIoT system can understand.
YOU ARE RESPONSIBLE FOR CHOOSING THE PROPER DEVICE TO GET INFORMATION.

HERE IS AN EXAMPLE OF YOUR TASK:
    [EXAMPLE]
        1. Input: humidity is below 30%
        [OUTPUT]
        [Condition What to do]: get the humidity level is below 30%
        [DEVICE_NAME]: HumiditySensor
        [/OUTPUT]

        3. Input: "light is off", turn on the oven."
        [OUTPUT]
        [Condition What to do]: get the light status is off
        [DEVICE_NAME]: LightSensor
        [/OUTPUT]

        4. Input: "air conditioner is off"
        [OUTPUT]
        [Condition What to do]: get the air conditioner status is off
        [DEVICE_NAME]: AirConditioner
        [/OUTPUT]

        5. Input: "it's snowing outside." 
        [OUTPUT]
        [Condition What to do]: get the weather status is snowing
        [DEVICE_NAME]: WeatherProvider
        [/OUTPUT]
    [/EXAMPLE]


[INST]
1. READ THE DEVICES WE CAN USE IS PROVIED BETWEEN [DEVICE_LIST] and [/DEVICE_LIST] WITH THEIR DESCRIPTIONS.
2. CHOOSE THE DEVICE THAT CAN PROVIDE THE INFORMATION THAT WE NEED BETWEEN [QUESTION] and [/QUESTION].
3. PLEASE ANSWER ONLY IN THE FORMAT BELOW :


[OUTPUT]
    [Condition What to do]: <what_to_do>\n
    [CONDITION_DEVICE_NAME]: <device_name>
[/OUTPUT]
[/INST]
 """

def google_translate(command, api_key = os.environ['GOOGLE_TRANSLATE_KEY']):
    url = "https://translation.googleapis.com/language/translate/v2"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "q": command,
        "target": "en",
        "format": "text"
    }
    params = {
        "key": api_key
    }

    response = requests.post(url, headers=headers, params=params, data=json.dumps(data))

    if response.status_code == 200:
        translation = response.json()["data"]["translations"][0]["translatedText"]
        return translation
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

    
def extract_output_sections(input_text):
    lines = input_text.split('\n')
    
    # [output]과 [/output] 사이의 내용을 모을 리스트를 초기화합니다.
    output_lines = []
    
    # [output]과 [/output] 사이의 내용을 추출하기 위한 플래그와 카운터 초기화
    inside_output = False

    for line in lines:
        if '[output]' in line.lower():
            inside_output = True
            continue
        if '[/output]' in line.lower():
            inside_output = False
            continue
        if inside_output:
            output_lines.append(line)

    # 모든 내용을 합친 후 스페이스와 쉼표 기준으로 분리합니다.
    combined_text = ' '.join(output_lines)
    words = re.split(r'[,\s]+', combined_text)

    # 빈 문자열은 제거
    words = [re.sub(r'[\(\)#]', '', word) for word in words if re.sub(r'[\(\)#]', '', word).isalpha()]

    return words

#기존 host/client 시작할 때,
#0.0.0.0에서 LISTEN 하도록 실행에서 변경.
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:11434"

    
def Device_Mapping(command, services, model='soplang',temperature=0,max_try=5,verbose=False,seed=123):
    start = time.perf_counter()
    chat_result = ollama.chat(
        model=model,
        messages=[{'role': 'user', 'content': 'Device_Limitations :'  + MAPPING_INSTRUCTION_DEVICES+ '\n=======\nUser input: '+ command }], #services   + "\n=======\n"
        options=dict(temperature=0)
    )
    end = time.perf_counter()
    print(f"2-1. Ollama Time: {end - start:.4f} seconds")
    start = end

    #give the result to mapping_verifier to modify wrong device names
    step1_map_result = Mapping_Verifier(chat_result['message']['content'])
    end = time.perf_counter()
    print(f"2-2. Mapping Verifier Time: {end - start:.4f} seconds")
    start = end

    step1_map_result.device_verify()
    final_device_mapping = " ".join(extract_output_sections(step1_map_result.input_text))
    #find more devices using mapping verifier
    end = time.perf_counter()
    print(f"2-3. Device Verify Time: {end - start:.4f} seconds")
    start = end

    every_device_list = Mapping_Verifier(command)
    end = time.perf_counter()
    print(f"2-4. Mapping Verifier Time: {end - start:.4f} seconds")
    start = end
    
    more_devices = every_device_list.device_mapping()
    end = time.perf_counter()
    print(f"2-5. Device Mapping Time: {end - start:.4f} seconds")
    start = end
    
    #이미 생성한 중복 device 제거
    for more_device in more_devices[:]:
        if (more_device in final_device_mapping):
            more_devices.remove(more_device)
    if (len(more_devices)>0):
        final_device_mapping = final_device_mapping + " " + " ".join(more_devices)
    end = time.perf_counter()
    print(f"2-6. Oters Time: {end - start:.4f} seconds")
    start = end

    return final_device_mapping.split()
     
      
'''
def mqtt_process():
    global STRING_THING_LIST 
    global DICT_THING_LIST
    # Uncomment mqtt_handler for get information from middleware
    print(f"{BOLD}{MAGENTA}[MAIN/MQTT]{RESET}{BOLD} MQTT Communication...{RESET}")
    mqtt_handler()
    print(f"{BOLD}{MAGENTA}[MAIN/MQTT]{RESET}{BOLD} MQTT Communication Done{RESET}\n")

    # get thing list
    print(f"{BOLD}{MAGENTA}[MAIN/DATA]{RESET}{BOLD} Extracting thing list...{RESET}")
    extract_thing_list()
    #generate_thing_description_list()
    string_thing_list = extract_thing_from_thing_list()
    STRING_THING_LIST = string_thing_list
    parsed_service_list = file_parse()
    #print(string_thing_list)
    
    thing_dictionary = [device.strip() for device in STRING_THING_LIST.split(",")]
    #print(f"{BOLD}{MAGENTA}[MAIN/DATA]{RESET}{BOLD} Generating thing summary...{RESET}")
    #generate_thing_summary()
    print(f"{BOLD}{MAGENTA}[MAIN/DATA]{RESET}{BOLD} Data Processing Done{RESET}\n")

    return string_thing_list, thing_dictionary, parsed_service_list
'''
def process():
    while True:
       #step 0 : translate
       #format_instruction()
       #translated_input = google_translate(input())
       translated_input = input()
       start = time.time()
       mapping_result = Device_Mapping(translated_input, services)
       print("\n---------------------------------------------------\n")
       print("STEP 1 DEVICE Mapping result:\n\n" ,mapping_result)
       print("\n---------------------------------------------------\n")
      
       end = time.time()
       print("time: ",end-start)

if __name__ == '__main__':
    '''
    global STRING_THING_LIST
    global DICT_THING_LIST

    parser = argparse.ArgumentParser(description="Process some requests.")
    parser.add_argument(
        "-t", "--test", action="store_true", help="Run predefined test inputs"
    )
    parser.add_argument(
        "-m", "--mqtt", action="store_true", help="Run mqtt_process function"
    )
    args = parser.parse_args()
    # 100% Working.

    # Execute functions based on arguments
    if args.mqtt:
        # Step 0
        STRING_THING_LIST, DICT_THING_LIST, PARSED_THING_LIST = mqtt_process()

    else:
        # Add the logic for test inputs here
        with open('data/parsed_servicelist.json',  encoding='utf-8') as f:
            devices_json = json.load(f)
        with open('testcase.txt',  encoding='utf-8') as f: 
            testcases = f.readlines()
            '''
    services = str(description)
    process()