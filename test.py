import ollama
import os
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:44267"  # 또는 "http://localhost:11434"
print(os.environ.get("OLLAMA_HOST"))  # 정상적으로 설정되었는지 확인

response = ollama.chat(
    model="soplang", #"llama3",#soplang",

    messages=[{"role": "user", "content": "Hello, how are you?"}],
    options={"temperature": 0}  # host 매개변수 없이 실행
)

print(response)

