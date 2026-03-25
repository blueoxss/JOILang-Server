import re
from difflib import SequenceMatcher
import requests
import json
from sentence_transformers import SentenceTransformer, util
from .SERVICE_DESCRIPTION_FINAL import description
#from .mqtt import syntax_verify
import os

import traceback
def google_translate(command, api_key = os.environ['GOOGLE_TRANSLATE_KEY']):
    print("translate")
    url = "https://translation.googleapis.com/language/translate/v2"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "q": command,
        "target": "ko",
        "format": "text"
    }
    params = {
        "key": api_key
    }
    print(data)
    response = requests.post(url, headers=headers, params=params, data=json.dumps(data))
    print("response")
    if response.status_code == 200:
        print(response)

        translation = response.json()["data"]["translations"][0]["translatedText"]
        print(translation)
        return translation
    else:
        print("Exception")
        raise Exception(f"Error: {response.status_code}, {response.text}")
def add_quote(param):
    if param[0] != '"':
        param = '"' + param
    if param[-1] != '"':
        param = param + '"'
    return param

model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
EMAIL_ADDRESS = "ethan0913@snu.ac.kr"
MUSIC_PATH = 'music/quiet.mp3'
def transformer_similarity(word1, word2):
    embeddings = model.encode([word1, word2])
    similarity = util.pytorch_cos_sim(embeddings[0], embeddings[1])
    return similarity.item()
def similar(a,b):
    return SequenceMatcher(None,a,b).ratio()
def get_most_similar(word:str,candidates:list[str]):
    result = ""
    best = -1
    for candidate in candidates:
        sim = transformer_similarity(word,candidate)
        if sim > best:
            result = candidate
            best = sim
    return result
def get_functions_of_device(device):
    s =  description[device]
    pattern = r'\b(\w+)\s*\('
    matches = re.findall(pattern, s)
    if s == "MenuProvider": return ['menu','todayMenu']
    return matches
def get_values_of_device(device):
    s =  description[device]
    s = s[s.find('Values'):]
    values = []
    for line in s.split('\n'):
        e = line.find(':')
        value = line[:e].strip()
        if value != "Values" and value != "":
            values.append(line[:e].strip())
    return values
def fix_syntax(code):
    code = code.replace("&&"," and ")
    code = code.replace("||"," or ")
    code = code.replace("LOOP","loop")
    code = code.replace("IF","if")
    code = code.replace("ELSE","else")
    code = code.replace("THEN","")
    code = code.replace("then","")
    code = code.replace("hours","HOUR")
    code = code.replace("HOURS","HOUR")
    code = code.replace(" hour"," HOUR") # clock.hour이 아닌 wait until hour만 바꿔야 하므로 space가 있다
    

    i = 0 
    while i < len(code): #if statement parantheses fix
        j = i - 1
        q_count = 0
        while j >= 0: # if "if" keyword inside quotations, skip
            if code[j] == '"':
                q_count += 1
            j -= 1
        if q_count % 2 == 1:
            i += 1
            continue
        if code[i] == 'f' and code[i-1] == 'i' and not code[i-2].isalpha():
            count = 0
            j = i
            while code[j] != '\n' and code[j] != '{':
                if code[j] == '(':count += 1
                if code[j] == ')': count -= 1
                j += 1
            code = code[:i-1] + "if" + "((" + code[i+1:]
            while  code[i] != '\n' and code[i] != '{':
                i+=1
            count += 2
            if count > 0:
                code = code[:i] + ')'*count + code[i:]
            i += 1
        i += 1
    code = code.replace("{","\n{")
    code = code.replace("}","\n}\n")
   
    i = 0
    while i < len(code) - 1: # remove comments
        if code[i] == '/' and code[i+1] == '/':
            j = i
            while j < len(code):
                if code[j] == '\n':break
                j += 1
            if j == len(code):
                code = code[:i]
            else:
                code = code[:i] + code[j:]
        i += 1
    i = 0
    while i < len(code): # fix empty blocks
        j = i - 1
        q_count = 0
        while j >= 0:
            if code[j] == '"':
                q_count += 1
            j -= 1
        if q_count % 2 == 1:
            i += 1
            continue
        if code[i] =='{':
            j = i+1
            need_add = False
            while j < len(code):
                if code[j] == ' ' or code [j] == '\n' or code[j] == '\t':
                    j += 1
                elif code[j] == '}':
                    need_add = True
                    break
                else:
                    break
            if need_add:
                code = code[:i+1] + "(#Calculator).add(1.0,1.0)" + code[i+1:]
        i += 1

    i = 0
    while i < len(code) - 10:
        j = i - 1
        q_count = 0
        while j >= 0: # if "wait until" keyword inside quotations, skip
            if code[j] == '"':
                q_count += 1
            j -= 1
        if q_count % 2 == 1:
            i += 1
            continue
        if code[i:i+10] == "wait until":
            line_break = i + 10
            while line_break < len(code):
                if code[line_break] == '\n':break
                line_break += 1
            if "MIN" in code[i:line_break] or "HOUR" in code[i:line_break] or "SEC" in code[i:line_break]:
                i += 1
                continue
            count = 0
            for j in range(i + 10,line_break):
                if code[j] == '(':count+=1
                elif code[j] == ')':count -= 1
            count += 2
            code = code[:i+10] + '((' + code[i+10:line_break] + ')' * count + code[line_break:]
        i += 1
            

    return code


    
def find_services_in_code(code):
    result = []
    tag_start = -1
    tag_end = -1
    i = 0
    while i < len(code)-2:
        if code[i] == '(' and code[i+1] == '#':
            tag_start = i + 2
            tag_end = code.find(')',tag_start) - 1
            service_start = tag_end + 3
            j = service_start
            while j < len(code):  
                if not code[j].isalpha():
                    service_end = j
                    break
                j += 1
            service_end -= 1
            service_name = code[service_start:service_end+1]
            tag_name = code[tag_start:tag_end+1]
            is_function = False
            parameters = []
            if code[service_end+1] == '(':
                is_function = True
                parameter_end = code.find(')',service_end+1)
                if service_name == 'speak':
                    parameters = [code[service_end+2:parameter_end]]
                elif'Mail' in  service_name:
                    parameters = re.findall(r'"(.*?)"', code[service_end+2:parameter_end])
    
    # Check if there is any non-quoted part left
                    remaining_part = re.sub(r'"(.*?)"', '', code[service_end+2:parameter_end]).strip(', ')
    
    # Combine the results
                    if remaining_part:
                        parameters.append(remaining_part)



                else:
                    parameters = code[service_end+2:parameter_end].split(',')
                if len(parameters) == 1 and parameters[0] == '':
                    parameters = []
                service_end = parameter_end
            tag_name = tag_name.split(' ')
            for j in range(len(tag_name)):
                if tag_name[j][0] == '#':
                    tag_name[j] = tag_name[j][1:]
            result.append({"tag":tag_name,"service":service_name,"is_function":is_function,"start_index":tag_start-2,"end_index":service_end,"parameters":parameters})
            
        i += 1
    print(result)
    return result


def fix_function_parameters(tag,function,parameters:list[str]):
    for tag_name in tag:
        if tag_name in description.keys():
            device_tag = tag_name
    service = description[device_tag][:description[device_tag].find('Values')].split('\n')
    for line in service:
        if function in line:
            if '{' in line:
                enum = line[line.find('{')+1:line.find('}')].split("|")
                if function == 'setWaterPortion':return [parameters[0],get_most_similar(parameters[1],enum)]
                if function == 'setFeedPortion':return [str(float(parameters[0])),get_most_similar(parameters[1],enum)]
                if function == 'setColor': return parameters
                # above: enum param + something else
                # below: enum param only
                return [get_most_similar(parameters[0],enum)]
            elif function == 'sendMail':
                return ['"' + EMAIL_ADDRESS + '"',add_quote(google_translate(parameters[1])),add_quote(google_translate(parameters[2]))]
            elif function == 'sendMailWithFile':
                return ['"' + EMAIL_ADDRESS + '"',add_quote(google_translate(parameters[1])),add_quote(google_translate(parameters[2])),parameters[3]]
            elif function == 'play':
                return ['"' + MUSIC_PATH + '"']    
            elif function == 'speak':
                print("function: speak")
                print(parameters[0])
                print(google_translate(parameters[0]))
                return [add_quote(google_translate(parameters[0]))]            
            else:
                return parameters
    return parameters
def fix_function_name(tag,function):
    for tag_name in tag:
        if tag_name in description.keys():
            device_tag = tag_name

    functions = get_functions_of_device(device_tag)
    if function in functions:
        return function
    return get_most_similar(function,functions)
def fix_location_tag(tag:list[str]):
    for name in tag:
        if name in description.keys():
            device = name
    print(description[device])
    a = description[device].find('Tags')
    tags = description[device][a:].split('\n')
    tags = tags[1:-1]
    for i in range(len(tags)):
        tags[i] = tags[i].strip()
        if tags[i][-1]==',':
            tags[i]=tags[i][:-1]
    for i in range(len(tag)):
        if device == tag[i]:
            continue
        tag[i] = get_most_similar(tag[i],tags)
    return tag

def fix_function(tag,function,parameters:list[str]):
    tag = fix_location_tag(tag)
    function = fix_function_name(tag,function)
    parameters = fix_function_parameters(tag,function,parameters)
    print(parameters)
    tags_string = '('
    for tag_name in tag:
        tags_string += '#' + tag_name 
    tags_string += ')'
    result = tags_string + '.' + function + "(" + ",".join(parameters) + ")"
    return result
def fix_value_name(tag,value):
    if 'SoundSensor' in tag:
        return 'sound'
    for tag_name in tag:
        if tag_name in description.keys():
            device_tag = tag_name
    values = get_values_of_device(device_tag)
    if value in values:
        return value
    return get_most_similar(value,values)
def fix_value(tag,value):
    tag = fix_location_tag(tag)
    value = fix_value_name(tag,value)
    tags_string = '('
    for tag_name in tag:
        tags_string += '#' + tag_name 
    tags_string += ')'

    return tags_string + '.' + value
def find_variables(code)->list[str]:
    variable_list = []
    for i in range(1,len(code)-1):
        if code[i] == '=' and code[i-1] != '=' and code[i-1] != '!' and code[i+1] != '=':
            j = i-1
            while j >= 0:
                if code[j].isalnum() or code[j].isalnum(): #assume var name is alphanumeric
                    var_end = j
                    j -= 1
                    while j >= 0:
                        if not code[j].isalnum():
                            var_start = j+1
                            break
                        j -= 1
                    if j<0:var_start = 0
                    variable_list.append(code[var_start:var_end+1])
                    break
                j-=1
    return variable_list
def find_left_operand(code,operator_index):
    j = operator_index-1
    while j > 0:
        if code[j] == '"':
            left_end = j
            j -= 1
            while j > 0:
                if code[j] == '"':
                    left_start = j
                    break
                j -= 1
            break
        if code[j].isalnum() or code[j] == "_":
            left_end = j
            j -= 1
            closing = False
            while j > 0:
                if code[j] == ')':closing = True
                if code[j] == ' '  or code[j] == '\n':
                    left_start = j
                    break
                if code[j] == '(':
                    if closing:left_start = j
                    else:left_start = j+1
                    break
                j -= 1
            break
        j -= 1
    return (left_start,left_end)
def find_right_operand(code,operator_index):
    j = operator_index+2
    while j < len(code):
        if  code[j] == '"':
            right_start = j
            j += 1
            while j < len(code):
                if  code[j]=='"':
                    right_end = j 
                    break
                j += 1
            if j == len(code): right_end = len(code) - 1
            break
        elif code[j] == '(': #value
            j += 1
            while j < len(code):
                if code[j] == ')':
                    j += 1
                    break
                j += 1
            while j < len(code):
                if not code[j].isalnum() and code[j] != "_" and code[j] != '#' and code[j] != ')' and code[j] != '"':
                    right_end = j - 1
                    break
                j += 1
        elif code[j].isalnum(): #variable, number
            right_start = j
            j += 1
            while j < len(code):
                if not code[j].isalnum()and code[j] != "_" and not code[j] == '.':
                    right_end = j - 1
                    break
                j += 1
            if j == len(code): right_end = len(code) - 1
            break
        j += 1
    return (right_start,right_end)
def find_comparison(code):
    result = []
    for i in range(len(code)-1):
        if (code[i] == '=' or code[i] == '!') and code[i+1] == '=':
            left_start,left_end = find_left_operand(code,i)
            right_start,right_end = find_right_operand(code,i)
            result.append({'index':i,'left_start':left_start,'left_end':left_end,'right_start':right_start,'right_end':right_end})
    return result




def fix_services(code):
    used_services = find_services_in_code(code)
    new_services = []

    for service in used_services:
        if service['is_function']:
            print(service)
            new_function = fix_function(service['tag'],service['service'],service['parameters'])
            new_services.append(new_function)
        else:
            new_value = fix_value(service['tag'],service['service'])
            new_services.append(new_value)

    new_code = ''
    start = 0
    for i in range(len(used_services)):
        end = used_services[i]['start_index'] - 1
        new_code += code[start:end+1]
        new_code += new_services[i]
        start = used_services[i]['end_index'] + 1
    new_code += code[used_services[len(used_services)-1]['end_index']+1:]
    return new_code
def fix_comparison(left,operator,right,variables)->str:
    print(left)
    print(right)
    if left[0] == '(' and right[0] == '(': return left + ' ' + operator + ' ' + right
    if left[0] != '(' and right[0] != '(': return left + ' ' + operator + ' ' + right
    if left in variables: return left + ' ' + operator + ' ' + right
    if right in variables: return left + ' ' + operator + ' ' + right
    if left[0] != '(':
        temp = right
        right = left
        left = temp
    # from this point, left is value service and right is a literal
    if right[0] == '"': right = right[1:len(right)-1]
    tags = left[2:left.find(')')].split('#')
    for tag in tags:
        if tag in description.keys():
            device = tag
    value_name = left[left.find('.')+1:]
    values = description[device][description[device].find('Values'):].split('\n')

    for value in values:
        if value_name in value:
            if '{' in value:
                enum_values = value[value.find('{')+1:value.find('}')].split('|')
                return left + ' ' + operator + ' ' + get_most_similar(right,enum_values)

            else:
                return left + ' ' + operator + ' ' + right
def fix_comparisons(code):
    variables = find_variables(code)
    comparisons = find_comparison(code)
    new_code = ''
    start = 0
    for i in range(len(comparisons)):
        left = code[comparisons[i]['left_start']:comparisons[i]['left_end']+1]
        operand = code[comparisons[i]['index']:comparisons[i]['index']+2]
        right = code[comparisons[i]['right_start']:comparisons[i]['right_end']+1]
        end = comparisons[i]['left_start'] - 1
        new_code += code[start:end+1]
        new_code += fix_comparison(left,operand,right,variables)
        start = comparisons[i]['right_end'] + 1
    new_code += code[comparisons[len(comparisons)-1]['right_end']+1:]
    return new_code


def fix_code2(code):
    try:
       code = fix_syntax(code)
       print('syntax')
       code = fix_services(code)
       print('services')
       code = fix_comparisons(code)
       return code
    except Exception as e:
        traceback.print_exc()
        return code
if __name__ == '__main__':
    code = """
wait until (2 MIN)
if(( ((#Feeder #livingroom).switch == "off") ))
{
(#Feeder #livingroom).on()

}

(#Feeder #livingroom).setFeedPortion(50, "grams")
(#Feeder #livingroom).startFeeding()

"""

    code = fix_code(code)
    print(code)
    print(syntax_verify(code,"jh"))

        
        
