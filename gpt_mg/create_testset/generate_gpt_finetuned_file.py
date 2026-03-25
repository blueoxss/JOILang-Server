import json

def convert_txt_to_jsonl(input_txt_path, output_jsonl_path, system_prompt="You are a SoPLang programmer..."):
    with open(input_txt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    data = []
    prompt = ""
    code = ""
    reading_code = False

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            if prompt and code:
                data.append({
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": code.strip()}
                    ]
                })
                code = ""
            prompt = line[1:].strip()
            reading_code = True
        elif reading_code:
            code += line + "\n"

    # 마지막 예제 추가
    if prompt and code:
        data.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": code.strip()}
            ]
        })

    # 저장
    with open(output_jsonl_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"✅ 변환 완료: {output_jsonl_path} ({len(data)} 개 샘플)")

    if __name__ == "__main__":
    convert_txt_to_jsonl(
        input_txt_path="generated_soplang_scripts.txt",
        output_jsonl_path="finetune_data.jsonl",
        system_prompt="You are a SoPLang programmer. SoPLang is a programming language used to control IoT devices..."
    )