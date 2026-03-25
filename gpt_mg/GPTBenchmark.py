import os
import time
import json
#import openai
import tiktoken

#from gpt_mg.version0_1.config_loader import load_version_config
#from gpt_mg.version0_2.config_loader import load_version_config_for_cs_review

from gpt_mg.version0_2.config_loader import load_version_config
import re

from dotenv import load_dotenv

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY_PROJ_BENCH")  # .env 파일에서 키 가져오기

from openai import OpenAI

client = OpenAI()

# 전역 변수로 max_tokens 설정
MAX_TOKENS = 3000 #4000 #FOR ChatGPT-4o
MAX_TOKENS_MARGIN = 0.1
MAX_TOKENS_SAFE = int(MAX_TOKENS * (1 - MAX_TOKENS_MARGIN))  # 여유를 두고 설정

#[TODO] review papers code fix
"""
base_path = "./version0_2/"  # base_path를 사용자의 경로에 맞게 설정

# 2-1. professor_feedback_examples.md 파일 로드
with open(os.path.join(base_path, "professor_feedback_examples.md"), "r", encoding="utf-8") as f:
    feedback_examples = f.read()

# 2-2. reference_papers.md 파일에 나열된 파일들을 읽어서 합치기
reference_papers = ""
with open(os.path.join(base_path, "reference_papers.md"), "r", encoding="utf-8") as f:
    # reference_papers.md 파일 안의 각 라인이 파일 경로일 경우 그 파일을 읽어와 합침
    paper_files = f.readlines()
    for paper_file in paper_files:
        paper_file_path = paper_file.strip()  # 각 파일 경로의 공백 제거
        if os.path.exists(paper_file_path):
            with open(paper_file_path, "r", encoding="utf-8") as paper_f:
                reference_papers += paper_f.read() + "\n"  # 각 논문의 내용을 추가
"""

# 토큰 수 계산 함수
def get_token_count(text):
    encoder = tiktoken.get_encoding("cl100k_base")  # GPT-3.5와 호환되는 인코딩
    return len(encoder.encode(text))

# 텍스트를 토큰 수에 맞게 분할하는 함수
def split_text_by_tokens(text, max_tokens=MAX_TOKENS_SAFE):
    parts = []
    current_part = ""
    for sentence in text.split("\n"):  # 문장 단위로 분할
        if get_token_count(current_part + "\n" + sentence) <= max_tokens:
            current_part += "\n" + sentence
        else:
            parts.append(current_part)
            current_part = sentence
    if current_part:
        parts.append(current_part)
    return parts

class GPTBenchmark:
    def __init__(self, version_path="./version0_2", testset_name=None):
        self.version_path = version_path
        self.testset_name = testset_name
        self.config_path = os.path.join(self.version_path, "model_config.json")
        self._load_config()
        self.baseline_latency = self._measure_baseline_latency()
        print("Baseline Server Latency", self.baseline_latency)

    def _load_config(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.results = []

    def _measure_baseline_latency(self, trials=10):
        latencies = []
        for _ in range(trials):
            start = time.perf_counter()
            _ = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": " "}, \
                          {"role": "user", "content": " "}]
            )
            end = time.perf_counter()
            latencies.append(end - start)
        return sum(latencies) / len(latencies)
    
    def finalize_results(self):
        test_metadata = {
            "total_sentences": len(self.results),
            "short_token_count": 0,
            "mid_token_count": 0,
            "long_token_count": 0,
            "avg_response_time_short": 0.0,
            "avg_response_time_mid": 0.0,
            "avg_response_time_long": 0.0
        }

        short_times, mid_times, long_times = [], [], []

        for r in self.results:
            tokens = r.get("tokens", 0)
            rt = r.get("response_time", 0)
            if tokens < 50:
                short_times.append(rt)
            elif 50 <= tokens < 100:
                mid_times.append(rt)
            elif tokens >= 200:
                long_times.append(rt)

        test_metadata["short_token_count"] = len(short_times)
        test_metadata["mid_token_count"] = len(mid_times)
        test_metadata["long_token_count"] = len(long_times)

        test_metadata["avg_response_time_short"] = round(sum(short_times) / (len(short_times) or 1), 3)
        test_metadata["avg_response_time_mid"] = round(sum(mid_times) / (len(mid_times) or 1), 3)
        test_metadata["avg_response_time_long"] = round(sum(long_times) / (len(long_times) or 1), 3)

        self.config["test_result"] = {
            "testset": self.testset_name,
            "last_tested": time.strftime("%Y-%m-%d"),
            "best_code_output_path": os.path.join(self.version_path, "results_best_code.txt"),
            "test_metadata": test_metadata,
            "results": self.results
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        print(f"✅ Finalized and saved benchmark results to {self.config_path}")

    def run(self, sentence):
        #config, model_input = load_version_config(sentence, self.version_path)
        config, model_input = load_version_config_for_cs_review(sentence, self.version_path)
        """
        [Reference Papers]
        {reference_papers}
        ---
        [Professor Feedback Examples]
        {feedback_examples}
        """
        logs = {"sentence": sentence}

        # Read the LaTeX file content
        with open("version0_2/paper.txt", "r", encoding="utf-8") as file:
            paper_content = file.read()

        # Function to remove LaTeX commands
        def remove_latex_commands(text):
            # Remove LaTeX commands (anything that starts with \)
            text = re.sub(r"\\[a-zA-Z]+\*?(\[.*?\])?(\{.*?\})?", "", text)
            # Remove comments (anything between % and end of line)
            text = re.sub(r"%.*$", "", text, flags=re.MULTILINE)
            # Remove multiple spaces and line breaks for cleaner output
            text = re.sub(r"\s+", " ", text).strip()
            return text

        # Process the LaTeX content
        processed_text = remove_latex_commands(paper_content)

        # 공통 context
        #You are a helpful assistant for academic paper review.

        #[Reference Papers]
        #{reference_papers}
        #[Professor Feedback Examples]
        #{feedback_examples}

        static_prompt_prefix = f"""
[Target Paper Content]
{processed_text}
""".strip()

        static_token_count = get_token_count(static_prompt_prefix)
        #allowed_tokens_for_target = MAX_TOKENS_SAFE - static_token_count
        allowed_tokens_for_target = MAX_TOKENS_SAFE
        # sentence를 고정 context를 고려한 나머지 토큰 수 기준으로 분할
        text_parts = split_text_by_tokens(static_prompt_prefix, max_tokens=allowed_tokens_for_target)
        # text_parts = split_text_by_tokens(sentence, max_tokens=allowed_tokens_for_target)

        # 전체 응답 시간 측정
        total_start = time.perf_counter()
        responses = []
        print("Length of text_parts >> ", len(text_parts))
        # 각 분할된 텍스트에 대해 순차적으로 요청
        for part in text_parts:
            print("<< part >> ", part[:30]+part[-30:])
            #model_input['messages'] = [{"role": "user", "content": part}]
            for message in model_input['messages']:
                if message['role'] == 'user':
                    message['content'] = part #+ "~~"
            response = client.chat.completions.create(
                **model_input
            )
            print(response.choices[0].message.content)
            # 응답을 리스트에 저장
            responses.append(response.choices[0].message.content)
        
        # 전체 응답을 합침
        final_response = "\n".join(responses)
        # final_response = " ".join(raesponses)
        best_code = final_response

        #best_code = response.choices[0].message.content.strip() #content
        total_end = time.perf_counter()

        #best_code = chunk.choices[0].delta.content if chunk.choices[0].delta else ""

        #logs["best_code"] = best_code
        logs["response_time"] = round(total_end - total_start, 4)
        logs["baseline_latency"] = round(self.baseline_latency, 4)
        logs["baseline_adjusted_time"] = round(total_end - total_start - self.baseline_latency, 4)

        #print("Benchmark Result:", json.dumps(logs, indent=2, ensure_ascii=False))
        with open(os.path.join(self.version_path, "results_best_code.txt"), "a", encoding="utf-8") as f:
            f.write(f"{best_code}\n\n")
        # 결과를 model_config.json에 기록
        self.results.append(logs)
        return logs


    def run_stream(self, sentence):
        config, model_input = load_version_config(sentence, self.version_path)
        logs = next((r for r in self.results if r["sentence"] == sentence), {"sentence": sentence})

        first_token_time = None
        tokens = 0
        stream_response = client.chat.completions.create(
            **model_input,
            stream=True
        )

        best_code_parts = []
        for chunk in stream_response:
            if not first_token_time:
                first_token_time = time.perf_counter()
            # 전체 응답을 누적하여 best_code 만들기 위함
            delta = chunk.choices[0].delta
            if delta and delta.content:
                 # 실시간 출력하기 위함
                print(delta.content, end="", flush=True) 
                best_code_parts.append(delta.content)
            tokens += 1
        #best_code = "".join(best_code_parts).strip()    
        stream_end = time.perf_counter()
        print()

        #logs["best_code"] = best_code
        #logs["response_time"] = round(total_end - total_start, 4)
        logs["inference_time"] = round(stream_end - first_token_time, 4)
        logs["tokens"] = tokens
        logs["tokens_per_sec"] = round(tokens / (stream_end - first_token_time + 1e-5), 2)
        #logs["baseline_latency"] = round(self.baseline_latency, 4)
        #logs["baseline_adjusted_time"] = round(total_end - total_start - self.baseline_latency, 4)

        #print("Benchmark Result:", json.dumps(logs, indent=2, ensure_ascii=False))
        self.results[-1].update(logs)

        # 결과를 model_config.json에 기록
        #self._update_model_config()
        return logs

    def _update_model_config(self, result):
        result_obj = {
            "last_tested": time.strftime("%Y-%m-%d"),
            "best_code_output_path": "./results/best_code_ver0.1.txt",
            "test_metadata": self._calculate_test_metadata(),
            "results": self.results
        }

        self.config["test_result"] = result_obj
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        print(f"Updated result to {self.config_path}")

    def _calculate_test_metadata(self):
        short = [r for r in self.results if r.get("tokens", 0) < 50]
        mid = [r for r in self.results if 50 <= r.get("tokens", 0) <= 100]
        long = [r for r in self.results if r.get("tokens", 0) >= 200]

        def avg_rt(group):
            if not group:
                return 0.0
            return round(sum(r["response_time"] for r in group if "response_time" in r) / len(group), 3)

        return {
            "total_sentences": len(self.results),
            "short_token_count": len(short),
            "mid_token_count": len(mid),
            "long_token_count": len(long),
            "avg_response_time_short": avg_rt(short),
            "avg_response_time_mid": avg_rt(mid),
            "avg_response_time_long": avg_rt(long)
        }

# 함수 호환 유지용
benchmark_cache = {}
def get_script_gpt(sentence, version_path="./version0_2"):
    if version_path not in benchmark_cache:
        benchmark_cache[version_path] = GPTBenchmark(version_path)
    return benchmark_cache[version_path].run(sentence)

if __name__ == "__main__":
    # Instantiate the benchmark class for version 0.2
    benchmark = GPTBenchmark(version_path="./version0_1")
    
    # Provide a sentence for benchmarking
    sentence = "This is a sample sentence for the academic paper."
    
    # Run the benchmark for the provided sentence
    logs = benchmark.run(sentence)
    
    # The results (e.g., response time, token counts) will be stored in `logs`
    print(logs)
