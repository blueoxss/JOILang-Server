import json
from gpt_cap.joi_parser_full import parser, lexer
from gpt_cap.cron_period_analyzer import check_cron_period_overlap

service_list_path = "./gpt_cap/stage_2/service_list_ver1.5.3.json"
def load_device_spec(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def parse_script_json(json_data):
    script_code = json_data["code"].replace("\\n", "\n")
    wrapped_code = f"{{\n{script_code}\n}}"

    # 파싱 시도
    try:
        tree = parser.parse(wrapped_code, lexer=lexer)
    except SyntaxError as e:
        return {"error": str(e)}
    if tree is None:
        raise ValueError(f"파싱 실패: {json_data.get('name', '<unnamed>')}")

    # AST 추출
    body = tree.get("body", [])
    block = body[0] if body and body[0]["type"] == "Block" else None
    ast = block["body"] if block else []

    return {
        "name": json_data.get("name", ""),
        "cron": json_data["cron"],
        "period": json_data["period"],
        "code": json_data["code"],
        "ast": ast
    }
    
class StaticAnalyzer:
    def __init__(self):
        self.defined = set()
        self.used = set()
        self.warnings = []
        self.var_types = {}
        self.service_file = load_device_spec(service_list_path)
        self.is_wait_until = False
        
    def analyze_block(self, block):
        for stmt in block.get("body", []):            
            self.analyze_stmt(stmt)
    
    def analyze_stmt(self, stmt):
        t = stmt.get("type")
        if t in ("Assign", "Declare"):            
            var = stmt["target"]
            if var in self.var_types:
                self.used.add(var)
            value = stmt["value"]       
            self.defined.add(var)     
            if isinstance(value, dict):          
                if value.get("type") == "MethodCall":   
                    tags = value.get("tags", [])             
                    device = tags[-1][1:] if tags else None
                    method = value.get("method")
                    if device and method:
                        return_type = self.get_device_attr_type(device, method)
                        self.var_types[var] = return_type
                    else:
                        self.warnings.append(
                            f"Invalid assignment: device '{device}' method call '{method}()' not allowed in assignment"
                        )
                elif value.get("type") == "AttrAccess":
                    tags = value.get("tags", [])
                    device = tags[-1] if tags else None                
                    if not device or device[0] != '#' or not device[1:].isalpha():
                        self.warnings.append("Assignment RHS: device name not found or invalid")                       
                    self.var_types[var] = self.get_device_attr_type(device[1:], value.get("attr"))                                                                                                     
                elif value.get("type") == "String":                                 
                    self.var_types[var] = "STRING"
                elif value.get("type") == "Bool":                                 
                    self.var_types[var] = "BOOL"
                elif value.get("type") == "Identifier":                 
                    self.used.add(value.get("name"))                       
                    self.var_types[var] = self.var_types[value.get("name")]    
                elif value.get("type") == "BinaryOp":                    
                    if isinstance(value["left"], dict):
                        self.var_types[var] = self.var_types[value["left"]["name"]]
                        self.used.add(value["left"]["name"])                        
                    else:
                        self.var_types[var] = self.infer_type(value["left"])    
                    if isinstance(value["right"], dict):
                        self.var_types[var] = self.var_types[value["right"]["name"]]
                        self.used.add(value["right"]["name"])                        
            else: 
                self.var_types[var] = self.infer_type(value)            
                            
        elif t == "Action":                    
            tags = stmt.get("target") 
            device = tags[-1][1:] if tags else None               
            service = stmt.get("service")
            # device, service 있는지 체크         
            return_type = self.get_device_attr_type(device, service)
            
            if return_type is not None:
                # Argument 체크             
                info = self.service_file.get(device, {})
                service_info = info.get(service)            
                arg_type = service_info.get("argument_type")
                args = stmt.get("args", [])
                # argument_type이 없는데 argument가 들어가면 에러
                if arg_type is None and args:
                    self.warnings.append(f"{device}.{service} does not take any arguments, but arguments were provided.")
                # argument_type이 있는데 args가 비거나 공백이면 에러
                if arg_type is not None and (not args or args == [""] or args[0] in ("", None)):
                    self.warnings.append(f"{device}.{service} requires an argument of type '{arg_type}', but none was given.")
                # ENUM and Type 체크
                if arg_type is not None:
                    expected_types = [s.strip() for s in arg_type.split("|")]
                    if len(args) != len(expected_types):
                        self.warnings.append(
                            f"{device}.{service} expects {len(expected_types)} arguments, but got {len(args)}."
                        )
                    else:
                        for i, (arg, expected) in enumerate(zip(args, expected_types)):
                            # ENUM 처리
                            if expected == "ENUM":
                                enums = self.get_enum_values(device)
                                arg_val = arg.get("value") if isinstance(arg, dict) and arg.get("type") == "String" else arg
                                if arg_val not in enums:
                                    self.warnings.append(
                                        f"ENUM argument '{arg_val}' not allowed for {device}.{service}. Allowed: {enums}"
                                    )
                            else:
                                # 타입 추론                            
                                arg_type_name = arg
                                if not isinstance(arg, dict):
                                    arg_type_name = self.infer_type(arg)
                                else:
                                    arg_type_name = self.get_type(arg)                                
                                # DOUBLE/INTEGER 호환 허용
                                if expected != arg_type_name:
                                    if not (
                                        (expected == "DOUBLE" and arg_type_name == "INTEGER") or
                                        (expected == "INTEGER" and arg_type_name == "DOUBLE")
                                    ):
                                        self.warnings.append(f"{service} argument {i+1} type is {expected}, not {arg_type_name}")
                                        if arg_type_name == "unknown": self.warnings.append("Arithmetic isn't allowed within arguments. Calculate them beforehand.")
                                        
        elif t == "If":            
            cond = stmt["condition"]                        
            always = self.analyze_condition(cond)
            if always == "always_true": self.warnings.append("Condition always true")
            elif always == "always_false": self.warnings.append("Condition always false")
                
            if stmt.get("then"):                
                self.analyze_block(stmt["then"])
            if stmt.get("else"):                
                self.analyze_stmt(stmt["else"])
                
        elif t == "WaitUntil":
            self.is_waituntil = True
            cond = stmt["condition"]
            always = self.analyze_condition(cond)
            if always == "always_true": self.warnings.append("Condition always true")
            elif always == "always_false": self.warnings.append("Condition always false")
        
        elif t == "Block":
            if self.is_wait_until:
                self.warnings.append("WaitUntil statement must not have a block")
                self.is_wait_until = False
            else:
                self.analyze_block(stmt)
                            
    #service_list에서 service의 return_type 가져오기 + device, service 있는지
    def get_device_attr_type(self, device, attr):
        device_list = list(self.service_file.keys())
        if device not in device_list:
            self.warnings.append(f"There is no '{device}' in device list. Replace it with the most similar one.")
            return None
        info = self.service_file[device]        
        if attr in info and "return_type" in info[attr]:
            type = info[attr]["return_type"]
            if type == "ENUM": return "STRING"
            else: return type.upper()
        else:
            self.warnings.append(f"There is no '{attr}' in '{device}'. Replace it with the most similar one.")
        return None

    #service_list에서 enum 리스트 가져오기 (return_type이 "ENUM"인 service들 다 긁어옴)
    def get_enum_values(self, device):
        info = self.service_file.get(device, {})
        all_enums = []
        for attr, attr_info in info.items():
            if isinstance(attr_info, dict) and attr_info.get("return_type") == "ENUM":
                enums_desc = attr_info.get("enums_descriptor", [])
                for desc in enums_desc:
                    # '• enum - 설명' 에서 enum만 추출
                    dot_idx = desc.find('-')
                    if dot_idx != -1:
                        enum = desc[1:dot_idx].strip()
                    else:
                        enum = desc[1:].strip()
                    all_enums.append(enum)
        return all_enums


    
    def analyze_condition(self, cond):
        if isinstance(cond, dict):
            op = cond.get("op")
            if op in ('==', '!=', '>=', '<=', '>', '<'):
                l = cond["left"]
                r = cond["right"]                
                # 1. 할당되지 않은 변수 사용
                for side in [l, r]:
                    if isinstance(side, dict) and side.get("type") == "Identifier":
                        varname = side["name"]
                        if self.var_types.get(varname) is None:
                            self.warnings.append(f"'{varname}' is not assigned")
                        else:
                            self.used.add(varname)
                # 2. l,r끼리 type 일치
                l_type = self.get_type(l)
                r_type = self.get_type(r)
                type_pair = {l_type, r_type}
                if not (type_pair <= {"INTEGER", "DOUBLE"}) and l_type != r_type:
                    self.warnings.append(f"Cannot compare '{l_type}' with '{r_type}'")                    
                
                # 3. 항상 참/거짓 체크 (상수 비교)
                if isinstance(l, (int, float, bool)) and isinstance(r, (int, float, bool)):
                    result = eval(f"{l} {op} {repr(r)}")
                    if result is True:
                        return "always_true"
                    elif result is False:                        
                        return "always_false"
            elif op in ('and', 'or'):
                lval = self.analyze_condition(cond["left"])
                rval = self.analyze_condition(cond["right"])
                if lval == "always_false" or rval == "always_false":
                    return "always_false"
                elif lval == "always_true" and rval == "always_true":
                  return "always_true"
            elif op == "not":
                val = self.analyze_condition(cond["expr"])
                if val == "always_true":
                    return "always_false"
                elif val == "always_false":
                    return "always_true"
        return None
                
    # for Assign
    def infer_type(self, value):          
        if isinstance(value, bool):            
            return "BOOL"
        elif isinstance(value, int):
            return "INTEGER"
        elif isinstance(value, float):
            return "DOUBLE"
        elif isinstance(value, str):
            try:
                float(value)
                return "DOUBLE"
            except ValueError:
                return "STRING"
        return "unknown"
    
    # for Condition
    def get_type(self, expr):                
        if isinstance(expr, dict):            
            t = expr.get("type")            
            if t == "MethodCall":
                device = expr["tags"][-1][1:]   
                method = expr.get("method")
                return self.get_device_attr_type(device, method)
            elif t == "AttrAccess":               
                try:  
                    device = expr["tags"][-1][1:]   
                except:
                    device = expr["target"][-1][1:]   
                try:             
                    type = self.service_file[device][expr["attr"]]["return_type"]
                except KeyError:
                    self.warnings.append(f"Device '{device}' or '{expr['attr']}' not found in service_list file")
                    return "unknown"
                if type == "ENUM": return "STRING"
                else: return type
            elif t == "Identifier":                
                self.used.add(expr["name"])
                return self.var_types.get(expr["name"])
            elif t == "Float" or t == "Double":                 
                return "DOUBLE"
            elif t == "Integer":                 
                return "INTEGER"
            elif t == "String": 
                return "STRING"  
            elif t == "Bool":
                return "BOOL"      
                      
        elif isinstance(expr, int):            
            return "INTEGER"
        elif isinstance(expr, float):
            return "DOUBLE"
        elif isinstance(expr, str):
            return "STRING"
        elif isinstance(expr, bool):
            return "BOOL"  
        return "unknown"
    
    def check_unused(self):
        unused = self.defined - self.used
        for var in unused:
            self.warnings.append(f"Unused identifier: {var}")
    
    def run(self, ast_body):
        for stmt in ast_body:
            # print(json.dumps(stmt, indent=2, ensure_ascii=False))
            self.analyze_stmt(stmt)
        self.check_unused()
        return self.warnings

# json_data = {
#             "name": "Scenario1",
#             "cron": "",
#             "period": 5000,
#             "code": "blind_level = (#Blind).blindLevel_blindLevel\nif (blind_level > 0) {\n    new_level = blind_level - 10\n    if (new_level < 0) {\n        new_level = 0\n    }\n    (#Blind).blindLevel_setBlindLevel(new_level)\n} else {\n    break\n}"
#             }        
# json_data2 = {"name": "Scenario","cron": "0 9 * * 1-5","period": 100,"code": "phase := false\nweekday = (#Clock).clock_weekday\nif ((weekday != 'monday') and (weekday != 'tuesday') and (weekday != 'wednesday') and (weekday != 'thursday') and (weekday != 'friday')) {\n    break\n}\nif (phase == false) {\n    if (((#Window).windowControl_window == 'closed') and ((#AirQualityDetector).carbonDioxideMeasurement_carbonDioxide >= 1000) and ((#TemperatureSensor).temperatureMeasurement_temperature >= 30)) {\n        (#Clock).clock_delay(5000)\n        (#Window).windowControl_open()\n        if ((#Fan).switch_switch == 'off') {\n            (#Fan).switch_on()\n        }\n        phase = true\n        dust_duration := 0\n    }\n} else {\n    if ((#AirQualityDetector).dustSensor_dustLevel >= 50) {\n        dust_duration = dust_duration + 100\n        if (dust_duration >= 60000) {\n            (#Window).windowControl_close()\n            (#Fan).switch_off()\n            if ((#HumiditySensor).relativeHumidityMeasurement_humidity <= 40) {\n                (#Humidifier).switch_on()\n            }\n            if (((#SoilMoistureSensor).soilHumidityMeasurement_soilHumidity <= 25) and ((#Irrigator).switch_switch == 'off')) {\n                (#Irrigator).switch_on()\n            }\n            break\n        }\n    } else {\n        dust_duration = 0\n    }\n}"}
# json_data3 = {"name": "Scenario1",
#               "cron": "",
#               "period": 100,
#               "code": "presence_triggered := false\ncurrent_light_level := 0\nif ((#PresenceSensor).presenceSensor_presence == 'present') {\n    if (presence_triggered == false) {\n        presence_triggered = true\n        (#Clock).clock_delay(10000)\n        current_light_level = (#Light).switchLevel_level\n        (#Light).switchLevel_setLevel(1,0)\n    }\n} else {\n    presence_triggered = false\n}"}
# json_data4 = {
#             "name": "",
#             "cron": "",
#             "period": -1,
#             "code": "latest_photo := (#Camera).camera_image\n(#EmailProvider).emailProvider_sendMailWithFile('홍길동','사진','사진입니다', latest_photo)"
#         }
# tree = parse_script_json(json_data2)
# # print("\n[basic AST]:\n", json.dumps(tree, indent=2, ensure_ascii=False))
# analyzer = StaticAnalyzer()
# if "error" in tree:
#     print(tree["error"])
# else:
#     warnings = analyzer.run(tree["ast"])

#     overlap_warning = check_cron_period_overlap(tree["cron"], tree["period"]) 
#     if overlap_warning is not None: warnings.append(overlap_warning)

#     print(warnings)


