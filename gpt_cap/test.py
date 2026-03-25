import ast
import pandas as pd
from run import generate_joi_code  

test_idx = [387,391,393,394,395,396,397,398,399,400,
    401,402,403,404,405,408,410,411,412,413,418,430,431,432,433,434,435,436,437,438,439,440,441,442,443,444,
    445,446,447,448,449,450,451,452,453,454,455,456,457,458,459
]
'''
    1,2,3,4,5,8,9,10,12,
    13,18,38,44,47,54,59,63,64,69,82,85,86,87,108,
    127,148,149,154,157,    
    161,166,167,168,173,215,229,236,258,262,264,269,272,273,278,284,285,286,287,288,289,290,291,292,
    294,295,296,297,298,299,301,302,303,305,306,307,308,309,310,311,313,314,315,316,317,318,319,320,
    321,322,323,324,325,326,327,328,329,330,331,332,333,334,335,336,337,338,339,340,341,342,343,344,345,348,
    351,354,357,359,363,364,366,368,369,370,371,373,374,376,377,386,387,391,393,394,395,396,397,398,399,400,
    401,402,403,404,405,408,410,411,412,413,418,430,431,432,433,434,435,436,437,438,439,440,441,442,443,444,
    445,446,447,448,449,450,451,452,453,454,455,456,457,458,459
]
'''
csv_file_path = 'result_0715.csv'
print("Length ", len(test_idx))
error_idx = []
try:
    df = pd.read_csv(csv_file_path, encoding='utf-8-sig')

    # if 'generated_code_gpt-4.1-mini_cap' not in df.columns:
    #     df['generated_code_gpt-4.1-mini_cap'] = None

    for idx in test_idx:
        print("🛑 Index:", idx)
        row = df.iloc[idx-1]
        command_val = row['command']
        devices_val = row['connected_devices']
        options_val = row['options']        
        print(">> Command : ", command_val)

        if pd.isna(devices_val):
            devices_val = None
        else:            
            if isinstance(devices_val, str):
                devices_val = ast.literal_eval(devices_val)
        
        try:
            result = generate_joi_code(command_val, "", devices_val, "", options_val)
            print(result["code"][0])
            df.at[idx-1, 'generated_code_gpt-4.1-mini_cap'] = result["code"][0]  # 해당 인덱스만 갱신
            df.at[idx-1, 'response_time_generated_code_gpt-4.1-mini_cap'] = result["log"]["response_time"]
            df.to_csv(csv_file_path, index=False, encoding='utf-8-sig')  # 매번 저장
        except Exception as e:
            print(f"Index {idx}에서 에러 발생: {e}")
            error_idx.append(idx)

except FileNotFoundError:
    print(f"에러: 파일을 찾을 수 없습니다 - {csv_file_path}")
print(error_idx)