import csv
import json
import re
#################### Level 2 #######################
def extract_script(script_field):
    # ""script"": "" ~ ""내부의 내용만 가져오기 위해 정규식 사용
    match = re.search(r'code\":\s\"(.*?)\"', script_field, re.DOTALL)
    if match:
        content = match.group(1)
        return content.strip()
    else:
        return ""

input_csv = 'level_2.csv'
output_json = 'level_2.json'

result = []
with open(input_csv, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        korean_command = row['Korean']
        script_field = row['Script']
        script_code = extract_script(script_field)

        item = {
            "command": korean_command,
            "code": [
                {
                    "name": "Scenario1",
                    "cron": "",
                    "period": -1,
                    "code": script_code
                }
            ]
        }
        result.append(item)

with open(output_json, 'w', encoding='utf-8') as jsonfile:
    json.dump(result, jsonfile, ensure_ascii=False, indent=2)

#################### Level 1 #######################
# def extract_script(script_field):
#     # ""script"": "" ~ ""내부의 내용만 가져오기 위해 정규식 사용
#     match = re.search(r'script\":\s\"(.*?)\"', script_field, re.DOTALL)
#     if match:
#         content = match.group(1)
#         return content.strip()
#     else:
#         return ""

# input_csv = 'level_1.csv'
# output_json = 'level_1.json'

# result = []
# with open(input_csv, newline='', encoding='utf-8') as csvfile:
#     reader = csv.DictReader(csvfile)
#     for row in reader:
#         korean_command = row['Korean']
#         script_field = row['Script']
#         script_code = extract_script(script_field)

#         item = {
#             "command": korean_command,
#             "code": [
#                 {
#                     "name": "Scenario1",
#                     "cron": "",
#                     "period": -1,
#                     "code": script_code
#                 }
#             ]
#         }
#         result.append(item)

# with open(output_json, 'w', encoding='utf-8') as jsonfile:
#     json.dump(result, jsonfile, ensure_ascii=False, indent=2)