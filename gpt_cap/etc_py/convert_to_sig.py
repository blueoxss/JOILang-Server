# 기존 파일을 읽어서 utf-8-sig로 새로 저장
input_path = 'output_cap_0704.csv'
output_path = 'output_cap_0704_sig.csv'

with open(input_path, 'r', encoding='utf-8') as f_in:
    data = f_in.read()

with open(output_path, 'w', encoding='utf-8-sig') as f_out:
    f_out.write(data)
