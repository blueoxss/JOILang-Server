import requests

response = requests.post("http://127.0.0.1:11434/api/chat", json={
    "model": "llama3",
    "messages": [
        {"role": "user", "content": "Device_Limitations :" + " " + "\n=======\nUser input: " + " "}
    ],
    "options": {"temperature": 0}
})

print(response.json())  # 응답 확인 