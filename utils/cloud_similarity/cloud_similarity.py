import os
import time
from argparse import ArgumentParser
import json

import pandas as pd
from openai import OpenAI
from pandas import DataFrame

from dotenv import load_dotenv

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY_PROJ_BENCH")  # .env 파일에서 키 가져오기

from openai import OpenAI

client = OpenAI()


def _call(model_input: dict) -> dict:
    start = time.perf_counter()
    response = client.chat.completions.create(**model_input)
    end = time.perf_counter()

    output = dict()
    output["response_time"] = end - start
    result = response.choices[0].message.content.strip()
    output["message"] = result

    print(f"Response Time: {output['response_time']:.4f} seconds")
    print(f"Response Message: \n{result}")
    return output


def generate(model_input: dict) -> dict:
    # Call the OpenAI API with retries
    retry = 3
    while retry > 0:
        try:
            logs = _call(model_input)
            break
        except Exception as e:
            print(f"Error: {e}")
            retry -= 1
            if retry > 0:
                wait_seconds = 60
                print(f"Retrying in {wait_seconds:.2f} seconds... ({retry} retries left)")
                time.sleep(wait_seconds)
            else:
                print("Failed after multiple retries.")
                logs = {"error": str(e)}
                exit(1)
    
    # Fill others key for compatibility
    logs["translated_sentence"] = ""
    logs["mapped_devices"] = ""
    return logs


def parse_result(result: str) -> list:
    try:
        results = eval(result[7:-3]) # Remove the leading "```json" and trailing "```"
    except Exception as e:
        print(e)
        print("Failed to parse result.")
    return results

def merge_results_with_df(results, df, gt_col, gen_col):
    merged = []
    for idx, res in enumerate(results):
        df_row = df.iloc[idx]
        
        # 비교 (둘 다 str로)
        gt_df = str(df_row[gt_col])
        gt_res = str(res.get(gt_col, ''))
        gen_df = str(df_row[gen_col])
        gen_res = str(res.get(gen_col, ''))
        
        # 다르면 경고 단순 두 코드 일치 검사 \n ' 등의 여부 미고려.
        if gt_df != gt_res:
            print(f"[{idx}] GT 불일치!\ndf: {gt_df}\nresults: {gt_res}")
        if gen_df != gen_res:
            print(f"[{idx}] generated_code 불일치!\ndf: {gen_df}\nresults: {gen_res}")
        
        # 병합 dict 생성
        merged_dict = {
            "category_analysis": df_row['category_analysis'],
            "command": df_row['command'],
            "GT": gt_df,  # df 값 우선
            "generated_code": gen_df,  # df 값 우선
            "cloud_similarity_gpt4o": res.get("cloud_similarity_gpt4o"),
            "explanation": res.get("explanation", "")
        }
        merged.append(merged_dict)
    return merged

# TODO: Read system prompt from a file or define it in a more structured way
system_prompt = f"""
# JOI Lang Semantic Similarity Evaluator (Batch Mode)

You are an advanced AI model specialized in evaluating the semantic similarity between pairs of "JOI lang" code snippets: a "Generated Code" and a "Ground Truth Code". Your evaluation must focus on the *intended execution meaning, core logic, and overall behavior*, not just superficial syntactic similarity. You will analyze a batch of up to 50 code pairs provided in a single input string.

## Context and Knowledge:
You should leverage your understanding of Domain Specific Languages (DSLs) for IoT/automation. The previously provided detailed descriptions of "SoP-lang" (including its syntax, grammar, keywords like `action_behavior`, `if_statement`, `wait_statement`, `condition_list`, `tag_list`, `action_input`, `period_time`, etc.) should be considered highly analogous to JOI lang. Assume JOI lang shares similar structural and semantic constructs unless the code itself clearly indicates otherwise.

## Core Evaluation Aspects (Inspired by compare_soplang_ir.py logic):

Your similarity assessment for each pair should be a holistic judgment based on the following, weighted conceptually:

1.  **Overall Program Structure & Core Logic (Weight: approx. 40%):**
    *   **Sequence & Type of Statements:** Similarity in the order and types of main statements used (e.g., actions, conditionals, loops, wait constructs).
    *   **Control Flow Equivalence:** How well the structure of control flow constructs matches.
        *   Are `if-else` blocks logically equivalent?
        *   Are loop structures (if any) performing similar iterations or targeting similar conditions?
    *   **Nesting & Ordering:** Correctness of logical block nesting and overall statement order if critical for the script's logic.
    *   Significant structural deviations (e.g., a missing `if` block in the generated code that exists in ground truth, or a fundamentally different sequence of critical actions) should heavily penalize the score for this aspect.

2.  **Action Equivalence (e.g., `action_behavior` in SoP-lang) (Weight: approx. 30%):**
    *   **Target Specification:** Similarity of the targeted services/devices (e.g., based on tags, identifiers).
    *   **Action/Method Name:** The core function/method being called on the target.
    *   **Action Inputs/Parameters:** Similarity of values and types passed as arguments to the action.

3.  **Conditional Logic & Expressions (e.g., `condition_list` in SoP-lang) (Weight: approx. 20%):**
    *   Applicable for `if` statements and conditional `wait until` constructs.
    *   **Semantic Equivalence:** Do the conditions, when evaluated, lead to the same logical outcomes? Consider:
        *   Operands involved in comparisons.
        *   Comparison operators (`==`, `!=`, `>=`, `<=`, `>`, `<`).
        *   Logical connectives (`AND`, `OR`, `NOT`) and grouping.
    *   Conceptually, think if these conditions would be deemed equivalent by a solver like Z3 (as in `are_equivalent` from the Python example).

4.  **Time-based Logic & `wait until` Constructs (Weight: approx. 10%, with special rule):**
    *   **Direct `wait until <period_time>` matches:** Similarity of delay durations and units (e.g., `wait until 10 SEC`).
    *   **Conditional `wait until <condition>` matches:** Assessed under "Conditional Logic".
    *   **SPECIAL RULE for `wait until` vs. `if` for delays:**
        *   If the Ground Truth Code uses a `wait until <period_time>` construct (e.g., `wait until 5 MINUTE`) specifically for creating a delay.
        *   AND the Generated Code implements a *semantically equivalent delay logic* using an `if` statement (or a loop with an `if` checking elapsed time) that achieves the *same delay duration and triggering outcome*.
        *   THEN, for this specific aspect of implementing the delay, the similarity contribution should be considered **80% (0.8)**. The overall score will then be influenced by this 0.8 factored with this aspect's weight and other aspects.
        *   If the `if` construct in the generated code is for a different logical purpose, or doesn't achieve the same delay effect, this special rule does not apply, and it should be evaluated normally under "Conditional Logic" or "Program Structure."

## Scoring Guidelines:
*   For each code pair, derive a single `similarity_score` float between 0.0 and 1.0.
    *   **1.0:** Semantically identical. Minor, non-functional differences like comments or whitespace are acceptable for 1.0.
    *   **0.8 - 0.99:** Highly similar. Minor semantic differences that don't fundamentally change the core outcome or intent. The "wait until vs. if for delay" special rule (if applicable and positive) might lead to scores in this range if other parts are perfect.
    *   **0.5 - 0.79:** Moderately similar. Some key semantic aspects match, but others differ significantly, or a major component is missing/incorrect.
    *   **0.0 - 0.49:** Low similarity. Fundamental differences in logic, core actions, targets, or overall intent.
    *   **0.0** If the Generated Code is completely empty or missing.
*   Provide a `brief_explanation` string if the `similarity_score` is less than 1.0. This explanation should concisely highlight the *most significant semantic differences* that led to the score. If the score is 1.0, the explanation should be an empty string.
*   The explanation should be clear and focused on the core logic, actions, or conditions that differ, without going into excessive detail.Do not penalize the code for using single quotes instead of double quotes for string literals, as this is a stylistic and non-functional difference.

## Special Tolerance Rules:
- **Numeric Representation Tolerance**:
  - Minor differences in numeric formatting (e.g., `30` vs `30.0`) **must be ignored** as long as they are semantically equivalent in the execution context (e.g., temperature thresholds, timer durations).
  - Do **not deduct points** for this difference.

- **Language Consistency in Action Inputs**:
  - If the **action argument text** (e.g., timer name or speech content) is written in a language that **does not match** the language of the user’s command, deduct **0.1** from the final score.
    - For Korean commands, Korean arguments are expected.
    - For English commands, English arguments are expected.
    - Mismatches like `"테스트 타이머"` in an English command or `"Test Timer"` in a Korean command incur a 0.1 penalty.


## Input Format:
You will receive a single string `user_content`. This string contains up to 50 JOI lang code pairs.
Each pair is formatted as:
`Generated Code {{generated_code_snippet}}`
`Ground Truth Code {{ground_truth_code_snippet}}`
These pairs are separated by the delimiter "---".

Example snippet of `user_content` with two pairs:
```
Generated Code IF (#TempSensor.get() > 25) {{ ALL (#Fan).on(); }}
Ground Truth Code IF (#TempSensor.get() > 25) {{ ALL (#Fan).on(); }}
---
Generated Code ALL (#Light).set("OFF"); WAIT_UNTIL(5 SEC); ALL (#Light).set("ON");
Ground Truth Code ALL (#Light).set("OFF"); // Implement 5 sec delay using if
IF (Time.elapsedSinceLastAction() >= 5 SEC) {{ ALL (#Light).set("ON"); }}
```

## Output Format:
You **MUST** return a single, valid JSON string that can be directly parsed by `json.loads()` in Python. This string must represent a LIST of JSON objects. Each object in the list corresponds to one input code pair and must have the following exact structure and keys:

```json
[
  {{
    "generated_code": "The exact generated code string from the input pair",
    "ground_truth_code": "The exact ground truth code string from the input pair",
    "cloud_similarity_gpt4o": <float_between_0.0_and_1.0>,
    "explanation": "<string_explanation_if_score_is_less_than_1.0_else_empty_string>"
  }}
  // ... more objects for other pairs
]
```

"""


if __name__ == "__main__":
    parser = ArgumentParser(description="Generate cloud similarity using OpenAI API")
    parser.add_argument("input_file", type=str, help="Input CSV file containing data")
    parser.add_argument("output_file", type=str, nargs="?", default="output.csv", help="Output CSV file to save results")
    parser.add_argument("-gen", "--generated_code", dest="generated_code", type=str, default="generated_code", help="Column name for generated code")
    parser.add_argument("-gt", "--ground_truth", dest="ground_truth", type=str, default="GT", help="Column name for ground truth code")
    args = parser.parse_args()

    # Load input data
    df: DataFrame = pd.read_csv(args.input_file, encoding="utf-8-sig")
    gen_col = args.generated_code
    gt_col = args.ground_truth
    # Prepare model input
    model_input = {
        "model": "gpt-4o",
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": ""
            },
        ],
    }

    total_results = []

    if "selected" in df.columns:
        selected_df = df[df["selected"] == 1]
    else:
        selected_df = df
    # Iterate through each row in the DataFrame
    for i in range(0, len(selected_df), 50):
        print(f"Processing batch {i // 50 + 1}...")
        batch = selected_df.iloc[i:i+50]
        
        pairs = [
            f"Generated Code {row[gen_col][0] if isinstance(row[gen_col], list) and row[gen_col] else row[gen_col]}\
            \nGround Truth Code {row[gt_col]}\n"
            for _, row in batch.iterrows()
        ]
        user_content = "---\n".join(pairs)
        model_input["messages"][1]["content"] = user_content
        
        result = generate(model_input)
        results = parse_result(result['message'])
        results = merge_results_with_df(results, batch, gt_col, gen_col)
        total_results.extend(results)

    # Save results to output file
    output_df = pd.DataFrame(total_results)
    output_df.to_csv(args.output_file, index=False, encoding="utf-8-sig")
    print(f"Results saved to {args.output_file}")
