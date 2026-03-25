import json
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

import json
import torch
import faiss
from transformers import AutoTokenizer, AutoModel

# 1. JSON 로드
# with open('./service_list_ver1.5.4.json', 'r', encoding='utf-8') as f:
#     raw_data = json.load(f)

# # 2. 텍스트 추출
# texts = [item["text"] for item in raw_data]
# metadata = [item["key"] for item in raw_data]

# # 3. 모델 로드 (GTE-Qwen2)
# model_name = "Alibaba-NLP/gte-Qwen2-1.5B-instruct"
# tokenizer = AutoTokenizer.from_pretrained(model_name)
# model = AutoModel.from_pretrained(model_name).eval().cuda()

# def get_embeddings(texts, batch_size=16):
#     all_embeddings = []
#     for i in range(0, len(texts), batch_size):
#         batch = texts[i:i+batch_size]
#         encoded = tokenizer(batch, padding=True, truncation=True, return_tensors="pt").to(model.device)
#         with torch.no_grad():
#             output = model(**encoded)
#             embeddings = output.last_hidden_state[:, 0]  # CLS token
#             all_embeddings.append(embeddings.cpu())
#     return torch.cat(all_embeddings).numpy()

# # 4. 임베딩 생성
# embeddings = get_embeddings(texts)

# # 5. FAISS 인덱스 생성 및 저장
# dimension = embeddings.shape[1]
# index = faiss.IndexFlatL2(dimension)
# index.add(embeddings)

# faiss.write_index(index, 'faiss_index_qwen2.index')
# with open('metadata_qwen2.json', 'w', encoding='utf-8') as f:
#     json.dump(metadata, f, ensure_ascii=False, indent=2)

# print("✅ Alibaba-NLP/gte-Qwen2-1.5B-instruct 기반 인덱스 저장 완료!")


# # 1. 데이터 로딩
with open('./service_list_ver1.5.4.json', 'r', encoding='utf-8') as f:
    raw_data = json.load(f)
with open('metadata_qwen2.json', 'r', encoding='utf-8') as f:
    metadata = json.load(f)

# 2. FAISS 인덱스 로딩
index = faiss.read_index('faiss_index_qwen2.index')

# 3. GTE-Qwen2 모델 로딩
model_name = "Alibaba-NLP/gte-Qwen2-1.5B-instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name).eval().cuda()

# 4. 임베딩 함수
def get_qwen_embedding(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True).to(model.device)
    with torch.no_grad():
        output = model(**inputs)
        return output.last_hidden_state[:, 0].cpu().numpy()

# 5. 쿼리 입력 및 검색
query = input("Input: ")
query_vector = get_qwen_embedding(query)
_, indices = index.search(query_vector, k=5)

# 6. 결과 출력
print(f"\n🔍 Top matches for: '{query}'\n")
for i in indices[0]:
    if i >= len(metadata):
        continue
    key = metadata[i]
    match = next((item for item in raw_data if item["key"] == key), None)
    if match:
        print(f"{match['key']} → {match['text']}")

