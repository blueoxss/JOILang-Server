import sys
import json
from itertools import product
import re
from soplang_parser_full import parser, lexer
from compare_soplang_ir import extract_logic_expressions

# Soplang 표현식을 현재 context 로 평가
def evaluate_expression(expr, context):
    if isinstance(expr, dict):
        if expr.get("type") == "AttrAccess":
            key = f"{expr['tags'][0]}.{expr['attr']}"
            return context.get(key, 0)
        elif expr.get("type") == "MethodCall":
            # return dummy value
            return f"result_of_{expr['method']}"
    elif isinstance(expr, str):
        val = context.get(expr, expr)
        try:
            if isinstance(val, str) and val.isdigit():
                return int(val)
            elif isinstance(val, str) and '.' in val:
                return float(val)
            else:
                return val
        except:
            return val
    return expr

def convert_type(left, right):
    try:
        if isinstance(right, (int, float)):
            return type(right)(left)
        if isinstance(right, str):
            return str(left)
    except:
        pass
    return left

def evaluate_condition(cond, context):
    if cond is None:
        return True
    if isinstance(cond, dict):
        op = cond.get("op")
        if op in ("and", "or"):
            left = evaluate_condition(cond["left"], context)
            right = evaluate_condition(cond["right"], context)
            return (left and right) if op == "and" else (left or right)
        elif op == "not":
            return not evaluate_condition(cond["expr"], context)
        else:
            left = evaluate_expression(cond["left"], context)
            right = evaluate_expression(cond["right"], context)
            left = convert_type(left, right)
            if op == '>=': return left >= right
            if op == '<=': return left <= right
            if op == '==': return left == right
            if op == '!=': return left != right
            if op == '>': return left > right
            if op == '<': return left < right
    return False

# 블록 내부의 statement 를 순회하여 조건 평가 및 action 실행
def flatten_actions(ir, context, depth=0):
    actions = []

    def visit(node):
        if not isinstance(node, dict):
            actions.append((f"⚠️ Skipping non-dict node", repr(node), depth))
            return
        t = node.get("type")
        if t == "Assign":
            val = evaluate_expression(node["value"], context)
            context[node["target"]] = val
            actions.append(("Assign", node["target"], val, depth))

        elif t == "Action":
            args = [evaluate_expression(arg, context) for arg in node["args"]]
            actions.append(("Action", ','.join(node["target"]), node["service"], tuple(args), depth))

        elif t == "If":
            cond_result = evaluate_condition(node["condition"], context)
            if cond_result:
                visit(node["then"])
            elif node.get("else"):
                visit(node["else"])

        elif t == "Block":
            for s in node.get("body", []):
                visit(s)

        elif t == "WaitUntil":
            ok = evaluate_condition(node["condition"], context)
            actions.append((f"WaitUntil[{'OK' if ok else 'BLOCKED'}]", str(node["condition"]), depth))
    top_level = ir.get("body", [])

    if len(top_level) == 1 and top_level[0].get("type") == "Block":
        top_level = top_level[0].get("body", [])
    for stmt in top_level:
        visit(stmt)

    return actions


def extract_candidates_from_condition(cond):
    candidates = {}

    if cond is None or not isinstance(cond, dict):
        return candidates

    op = cond.get("op")
    if op in ("and", "or"):
        left = cond.get("left")
        right = cond.get("right")
        for sub in [left, right]:
            subc = extract_candidates_from_condition(sub)
            for var, vals in subc.items():
                candidates.setdefault(var, set()).update(vals)
    elif op == "not":
        expr = cond.get("expr")
        subc = extract_candidates_from_condition(expr)
        for var, vals in subc.items():
            candidates.setdefault(var, set()).update(vals)
    else:
        left = cond["left"]
        if isinstance(left, dict) and left.get("type") == "AttrAccess":
            var = f"{left['tags'][0]}.{left['attr']}"
        else:
            var = left
        val = cond["right"]

        # 숫자 기반 조건 처리
        if isinstance(val, (int, float)):
            # 조건 연산자에 따라 주변 값 포함
            if op == '<':
                vals = [val - 1, val]
            elif op == '<=':
                vals = [val, val + 1]
            elif op == '>':
                vals = [val + 1, val]
            elif op == '>=':
                vals = [val, val - 1]
            elif op in ('==', '!='):
                vals = [val, val + 1]  # == 3 이면 3, 4로 비교
            else:
                vals = [val]
            candidates.setdefault(var, set()).update(vals)

    return candidates



def generate_context_from_conditions(logic):
    candidates = {}

    for cond in logic:
        sub_candidates = extract_candidates_from_condition(cond)
        for var, vals in sub_candidates.items():
            candidates.setdefault(var, set()).update(vals)

    keys = sorted(candidates.keys())
    value_sets = [sorted(candidates[k]) for k in keys]

    context_variants = []
    for combo in product(*value_sets):
        ctx = {k: v for k, v in zip(keys, combo)}
        context_variants.append(ctx)

    return context_variants

