from openai import OpenAI
import os
from collections import defaultdict
import time
import importlib
import json
import re
#from static_analyzer import StaticAnalyzer, parse_script_json
from gpt_cap.static_analyzer import StaticAnalyzer, parse_script_json
from gpt_cap.cron_period_analyzer import check_cron_period_overlap
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 한 단계 위

from dotenv import load_dotenv

load_dotenv()
# 하드코딩 대신 환경 변수에서 가져옵니다.
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY_SVC")

client = OpenAI()

def extract_services(answer_str):
    # 정규식을 사용하여 "#Device_Service" 형식을 모두 추출
    matches = re.findall(r"#([A-Za-z0-9]+)_([A-Za-z0-9]+_[A-Za-z0-9]+)", answer_str)
    return matches  # 리스트 형태로 반환: [(Device, Service), ...]

def find_service_info(service_list_path, service_refs):
    with open(service_list_path, 'r', encoding='utf-8') as f:
        service_data = json.load(f)

    filtered_info = {}

    for device, service in service_refs:
        if device in service_data and service in service_data[device]:
            if device not in filtered_info:
                filtered_info[device] = {}
            filtered_info[device][service] = service_data[device][service]

    return filtered_info

def find_device_info(service_list_path, device_names):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    print("BASE_DIR:", BASE_DIR)
    SERVICE_LIST_PATH = os.path.join(BASE_DIR, "stage_2", "service_list_ver1.5.3.json")

    with open(SERVICE_LIST_PATH, 'r', encoding='utf-8') as f:
        service_data = json.load(f)

    filtered_info = {}

    for device in device_names:
        if device in service_data:
            filtered_info[device] = service_data[device]
    
    return filtered_info

def extract_code_block(output):
    start = output.rfind('####')       
    if start == -1:
        return output
    return output[start+5:]

def generate_joi_code(sentence: str, model: str, connected_devices: dict, current_time: str, other_params: dict = None) -> dict:
    """
    Parameters:
    - sentence (str): 자연어 명령어
    - model (str): 모델 이름 (사용되지 않음)
    - connected_devices (dict): 디바이스 정보
    - current_time (str): 현재 시각 (YYYY-MM-DD HH:MM:SS)
    - other_params (dict, optional): 기타 옵션

    Returns:
    - dict: JOI 시나리오 및 로그 정보
    """
    logs = {}
    path_tmp = '.'
    ### Stage1 ###
    start = time.perf_counter()
    
    Print_draft = 1
    Print_debugging = 1
    
    if connected_devices is not None:                          
        devices = list({device['category'] for device in connected_devices.values()})        
        category_tags = defaultdict(set)
        for info in connected_devices.values():
            cat = info['category']
            for tag in info['tags']:
                if tag != cat:
                    category_tags[cat].add(tag)
        category_tags = {k: sorted(list(v)) for k,v in category_tags.items()}  
        print(category_tags)
        services = find_device_info("stage_2/service_list_ver1.5.3.json",devices)        
    else: 
        services, category_tags = "", "You can use anyting."
    ### Stage2 ###
    cnt = 0    
    error_msg = ""
    while cnt < 2:        
        if Print_debugging: print("✅ Code Generation")
        config_loader_module = importlib.import_module(f"gpt_cap.stage_2.config_loader")
        load_version_config = getattr(config_loader_module, 'load_version_config')    
        config, model_input = load_version_config(sentence, services, category_tags, other_params, error_msg, path_tmp)    
        response = client.chat.completions.create(**model_input)
        best_code = response.choices[0].message.content.strip()
        # 출력 여부
        if Print_draft: 
            print(best_code)
        best_code = extract_code_block(best_code)
        # if Print_debugging: print(best_code)
        
        # #### Static Analyzer ####
        if Print_debugging: print("✅ Static Analyzer")        
        best_code = json.loads(best_code)        
        tree = parse_script_json(best_code)
        # 1. Check Parsing Error
        if "error" in tree:            
            error_msg = f"""
            Error code: '{best_code}',
            Error Message: '{tree["error"]}
            """
            if Print_debugging: print("❌ Parsing error:", tree["error"])
        # 2. Check Error in AST
        else:
            analyzer = StaticAnalyzer()
            warnings = analyzer.run(tree["ast"])
            overlap_warning = check_cron_period_overlap(tree["cron"], tree["period"]) 
            if overlap_warning is not None: 
                warnings.append(overlap_warning)            
            if warnings:
                if Print_debugging: print(f"❌Error❌ {warnings}")
                error_msg = f"Error code: '{best_code}', Error Message: '{warnings}'"                                        
            else: # 에러 없으면 종료
                break   
        cnt += 1                            
            
        
    logs["best_code"] = best_code    
    end = time.perf_counter()
    logs["response_time"] = f"{end - start:.4f} seconds"
    print(logs["response_time"])
    return {
        "code": [
            best_code
        ],
        "log": logs
    }

   
