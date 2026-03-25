# import pandas as pd

# # 1. 원본 CSV 파일 읽기 (인코딩 지정, 예: cp949)
# df = pd.read_csv('final_output_ing.csv', encoding='cp949')

# # 2. 새 파일로 저장 (엑셀/메모장/리눅스 모두 한글 잘 보이는 utf-8-sig 권장)
# df.to_csv('final_output_ing2.csv', encoding='utf-8-sig', index=False)
import pandas as pd
import os

# def convert_xlsx_to_csv(xlsx_path, csv_path, sheet_name=0):
#     """
#     XLSX 파일의 특정 시트를 CSV 파일로 변환합니다.

#     :param xlsx_path: 입력할 XLSX 파일의 경로
#     :param csv_path: 출력할 CSV 파일의 경로
#     :param sheet_name: 변환할 시트의 이름 또는 인덱스 (0은 첫 번째 시트)
#     """
#     try:
#         # 엑셀 파일의 특정 시트를 DataFrame으로 읽기
#         # sheet_name=None으로 하면 모든 시트를 딕셔너리 형태로 읽어올 수 있습니다.
#         df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
        
#         # DataFrame을 CSV 파일로 저장
#         # index=False 옵션은 DataFrame의 인덱스를 CSV 파일에 포함하지 않도록 합니다.
#         df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
#         print(f"성공: '{xlsx_path}'의 시트 '{sheet_name}'이(가) '{csv_path}'(으)로 변환되었습니다.")

#     except FileNotFoundError:
#         print(f"에러: 파일을 찾을 수 없습니다 - '{xlsx_path}'")
#     except Exception as e:
#         print(f"에러 발생: {e}")

# # --- 사용 예시 ---
# if __name__ == "__main__":
#     # 1. 첫 번째 시트를 변환하는 경우
#     input_xlsx = 'final_output_250616.xlsx'
#     output_csv = 'final_output_250616.csv'
#     convert_xlsx_to_csv(input_xlsx, output_csv)

#     # 2. 시트 이름을 지정하여 변환하는 경우
#     # input_xlsx = 'data.xlsx'
#     # output_csv = 'data_sales.csv'
#     # convert_xlsx_to_csv(input_xlsx, output_csv, sheet_name='SalesData')import pandas as pd

# # 파일 읽기
# a = pd.read_csv('final_output_250616_cap.csv')
# b = pd.read_csv('output.csv')

# # 원하는 열만 뽑아서 A에 추가 (index 기준)
# a['cloud_similarity_cloud_english'] = b['cloud_similarity_gpt4o']

# # 저장
# a.to_csv('final_output_250616_cap.csv', index=False)
import pandas as pd
import re
df = pd.read_csv('test3.csv', encoding='utf-8')

# 예: code 열의 실제 줄바꿈을 \n 문자열로 변환
# df['joi_pred_cloud_korean'] = df['joi_pred_cloud_korean'].str.replace('\r\n', '\\n', regex=False)  # CRLF 먼저
# df['joi_pred_cloud_korean'] = df['joi_pred_cloud_korean'].str.replace('\n', '\\n', regex=False)
# df['joi_pred_cloud_korean'] = df['joi_pred_cloud_korean'].str.replace('\r', '\\n', regex=False)
# df['joi_pred_cloud_english'] = df['joi_pred_cloud_english'].str.replace('\r\n', '\\n', regex=False)  # CRLF 먼저
# df['joi_pred_cloud_english'] = df['joi_pred_cloud_english'].str.replace('\n', '\\n', regex=False)
# df['joi_pred_cloud_english'] = df['joi_pred_cloud_english'].str.replace('\r', '\\n', regex=False)

# for col in ['joi_pred_cloud_english', 'joi_pred_cloud_korean']:  # 필요한 컬럼명을 리스트로!
#     if col in df.columns:
#         df[col] = df[col].astype(str).str.replace("'", '"')
import pandas as pd

# 파일 읽기

# def single_to_double_escaped(s):
#     if pd.isna(s):
#         return s
#     return re.sub(r"'([^']*)'", r'\\"\1\\"', s)

# for col in ['joi_pred_cloud_korean', 'joi_pred_cloud_english']:
#     if col in df.columns:
#         df[col] = df[col].apply(single_to_double_escaped)

# def fix_json_newlines(s):
#     if pd.isna(s):
#         return s
#     # 모든 종류의 줄바꿈을 \n 문자열로 escape
#     return s.replace('\r\n', '\\n').replace('\n', '\\n').replace('\r', '\\n')

# for col in ['joi_pred_cloud_korean', 'joi_pred_cloud_english']:
#     if col in df.columns:
#         df[col] = df[col].apply(fix_json_newlines)

# def escape_newlines(s):
#     if pd.isna(s):
#         return s
#     # 실제 엔터(\r, \n, \r\n) → '\\n'으로 통일
#     return s.replace('\r\n', '\\n').replace('\n', '\\n').replace('\r', '\\n')

# for col in ['joi_pred_cloud_korean', 'joi_pred_cloud_english']:
#     if col in df.columns:
#         df[col] = df[col].apply(escape_newlines)
import pandas as pd

# 파일 읽기
df = pd.read_csv('test4_with_local_similarity.csv', encoding='utf-8-sig')

score_cols = [
    'cloud_similarity_cloud_korean',
    'cloud_similarity_cloud_english',
    'local_similarity',
]

df = df[~pd.isna(df['local_similarity']) & (df['local_similarity'] != '')]

means = df[score_cols].mean()

print(means)
