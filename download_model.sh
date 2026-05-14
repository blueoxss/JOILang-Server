#!/bin/bash

# 모델이 저장될 최상위 디렉토리 설정
BASE_DIR="./local_models"
mkdir -p "$BASE_DIR"

# 모델 다운로드 함수 정의
download_model() {
    local repo_id=$1
    local local_name=$2
    
    echo "================================================="
    echo "🚀 다운로드 시작: $local_name"
    echo "📦 저장소: $repo_id"
    echo "================================================="
    
    # hf 명령어를 사용하여 로컬 디렉토리로 다운로드
    hf download "$repo_id" --local-dir "$BASE_DIR/$local_name"
    
    echo "✅ 다운로드 완료: $local_name"
    echo ""
}

# ---------------------------------------------------------
# 모델 다운로드 실행 (주석 처리된 모델도 원하면 주석 해제 후 사용)
# ---------------------------------------------------------

download_model "microsoft/Phi-3.5-mini-instruct" "phi35_mini"
download_model "google/gemma-2-9b-it" "gemma2_9b_it"
download_model "Qwen/Qwen2.5-Coder-7B-Instruct" "qwen25_coder_7b"
download_model "meta-llama/Meta-Llama-3.1-8B-Instruct" "llama31_8b"
download_model "Qwen/Qwen2.5-Coder-14B-Instruct" "qwen25_coder_14b"

echo "🎉 모든 모델 다운로드가 완료되었습니다!"
echo "이제 인터넷 연결을 끊고 $BASE_DIR 경로를 참조하여 오프라인으로 사용할 수 있습니다."