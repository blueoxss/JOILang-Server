# https://www.notion.so/endermaru/1c4a0b445987803c8886d3d7eb978f84 
from openai import OpenAI
import os

# OpenAI API 키 설정 (환경 변수 또는 직접 삽입)

from dotenv import load_dotenv

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY_PROJ_BENCH")  # .env 파일에서 키 가져오기

from openai import OpenAI

client = OpenAI()

# grammar/samples은 gpt.py에서 그대로 복사
from JOI_grammar import grammar, samples2

# 테스트 문장 파일 경로
input_path = "soplang_test_sentences.txt"
output_path = "generated_soplang_scripts.txt"

# 문장 불러오기
with open(input_path, "r", encoding="utf-8") as f:
    test_sentences = [line.strip() for line in f if line.strip()]

results = []


for sentence in test_sentences:
    prompt = f"""
You are a SoPLang script generator. Given a user instruction, generate valid SoPLang code. only print generated code

### Instruction
{sentence}

### Grammar
{grammar}

### Examples
{samples2}

### Output
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful SoPLang code generator."},
            {"role": "user", "content": prompt}
        ]
    )

    result = response.choices[0].message.content
    results.append(f"# {sentence}\n{result}\n")

# 결과 저장
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print(f"✅ 변환 완료! 파일 저장됨 → {output_path}")