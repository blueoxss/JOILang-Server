# import json
# import tiktoken
# import sys

# def count_tokens_in_json(file_path, model="gpt-3.5-turbo"):
#     # JSON 파일 읽기
#     with open(file_path, 'r', encoding='utf-8') as f:
#         data = json.load(f)

#     # JSON 데이터를 문자열로 변환
#     json_string = json.dumps(data, ensure_ascii=False)

#     # 모델에 맞는 인코더 불러오기
#     encoding = tiktoken.encoding_for_model(model)

#     # 토큰화 및 토큰 수 세기
#     tokens = encoding.encode(json_string)
#     token_count = len(tokens)

#     print(f"총 토큰 수: {token_count}")

# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("사용법: python count_tokens.py <json 파일 경로>")
#     else:
#         count_tokens_in_json(sys.argv[1])
import tiktoken
import sys

def count_tokens_in_md(file_path, model="gpt-3.5-turbo"):
    # 마크다운 파일 읽기
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # 모델에 맞는 인코더 불러오기
    encoding = tiktoken.encoding_for_model(model)

    # 텍스트를 토큰으로 인코딩
    tokens = encoding.encode(text)
    token_count = len(tokens)

    print(f"총 토큰 수: {token_count}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python count_tokens_md.py <md 파일 경로>")
    else:
        count_tokens_in_md(sys.argv[1])
