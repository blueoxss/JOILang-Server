import sys
import json
from .soplang_parser_full import parser, lexer
from .soplang_ir_simulator import (
    flatten_actions,
    extract_logic_expressions,
    generate_context_from_conditions
)
from compare_soplang_ir import compare_codes

def parse(code):
    return parser.parse(code, lexer=lexer)

def format_trace(trace, context, label):
    formatted = []
    for step in trace:
        if step[0] == "Action":
            time = step[4]
            variables = ', '.join([f"{k}={v}" for k, v in context.items()])
            action = f"{step[1]}.{step[2]}{step[3]}"
            formatted.append(f"[{label}] 시간: {time}, {variables} → {action}")
    return formatted

# ✅ 1. 파일명은 터미널에서 받기
if len(sys.argv) != 3:
    print("Usage: python simulate_compare.py <gold.txt> <pred.txt>")
    sys.exit(1)

gold_file = sys.argv[1]
pred_file = sys.argv[2]

# ✅ 2. 코드 읽기
with open(gold_file, encoding='utf-8') as f:
    gold_code = f.read()
with open(pred_file, encoding='utf-8') as f:
    pred_code = f.read()

# ✅ 3. 논리 동등성 및 유사도 비교 (compare_soplang_ir)
compare_result = compare_codes(gold_code, pred_code)
print("\n✅compare_soplang_ir 결과:")
print(f"equivalent: {compare_result['equivalent']}")
print(f"similarity: {compare_result['similarity']}")

# ✅ 4. 시뮬레이션을 위한 파싱
ir_gold = parse(gold_code)
ir_pred = parse(pred_code)

# ✅ 5. 정답 코드에서 조건 추출
logic = extract_logic_expressions(ir_gold)
contexts = generate_context_from_conditions(logic)
print("\n✅ 실행 context:")
print(json.dumps(contexts, indent=2, ensure_ascii=False))



print("\nTrace 비교:")

for i, context in enumerate(contexts):
    print(f"\n[Context #{i}] {context}")

    try:
        trace_gold = flatten_actions(ir_gold, context.copy())
        trace_pred = flatten_actions(ir_pred, context.copy())

        actions_gold = [step for step in trace_gold if step[0] == "Action"]
        actions_pred = [step for step in trace_pred if step[0] == "Action"]

        print(f" 정답 Action 수: {len(actions_gold)}, 생성 Action 수: {len(actions_pred)}")

        max_len = max(len(actions_gold), len(actions_pred))
        for j in range(max_len):
            g = actions_gold[j] if j < len(actions_gold) else "❌ 없음"
            p = actions_pred[j] if j < len(actions_pred) else "❌ 없음"
            print(f"  Step {j}")
            print("   정답:", g)
            print("   생성:", p)
            print("   ✅ 동일" if g == p else "   ❌ 다름")

    except Exception as e:
        print("❌ 예외 발생:", e)


