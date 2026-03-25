# compare_soplang_ir.py

from .soplang_parser_full import parser, lexer
from z3 import *
import json
import difflib

#Soplang 코드를 PLY 기반 파서로 파싱하여 AST return
def parse_soplang(code: str):
    return parser.parse(code, lexer=lexer)
def extract_json_fields(s, keys=("cron", "period", "code")):
    """
    GT, pred 문자열에서 cron, period, code, script 값을 추출
    """
    # 큰따옴표, 작은따옴표, \n, \ 등 escape 문자 제거
    s = s.replace('\n', ' ').replace('\r', ' ')
    s = s.replace('\\"', '"').replace("\\'", "'")
    s = s.replace("\\\\", "\\")
    # 중괄호 안에 있을 때만 추출
    try:
        # 중괄호로 감싸진 부분만 추출
        m = re.search(r'\{.*\}', s)
        if m:
            s = m.group(0)
    except Exception:
        pass

    result = {}
    for k in keys:
        # "key": "value" 또는 'key': 'value' 또는 "key": value (숫자)
        v = None
        m = re.search(rf'["\']?{k}["\']?\s*:\s*["\']?([^,"\'}}\n]*)', s)
        if m:
            v = m.group(1).strip()
        result[k] = v
    return result

#조건 관련 모든 노드 추출
def extract_logic_expressions(ast):
    logic = []

    def dfs(node):
        if isinstance(node, dict):
            node_type = node.get("type")
            if node_type == "Scenario":
                dfs(node.get("body"))
            elif node_type == "If":
                logic.append(node["condition"])
                dfs(node.get("then"))
                if node.get("else"):
                    dfs(node["else"])
            elif node_type == "WaitUntil":
                if node.get("condition"):
                    logic.append(node["condition"])
            elif node_type == "Block":
                for stmt in node.get("body", []):
                    dfs(stmt)
        elif isinstance(node, list):
            for item in node:
                dfs(item)

    dfs(ast)
    return logic





#Z3(논리식 비교 라이브러리) 를 사용하기 위한 전처리 과정
def condition_to_z3(cond):
    if cond is None or not isinstance(cond, dict):
        return BoolVal(True)

    op_map = {
        ">=": lambda l, r: l >= r,
        "<=": lambda l, r: l <= r,
        "==": lambda l, r: l == r,
        "!=": lambda l, r: l != r,
        ">": lambda l, r: l > r,
        "<": lambda l, r: l < r
    }

    left = cond["left"]
    right = cond["right"]
    op = cond["op"]

    try:
        # 실수형 판단
        if isinstance(right, float):
            l = Real(left) if isinstance(left, str) else left
            r = RealVal(right)
        else:
            l = Int(left) if isinstance(left, str) else left
            r = IntVal(right)

        return op_map[op](l, r)

    except Exception as e:
        #print(f"[Z3 WARN] Failed to convert condition: {cond} → {e}")
        return BoolVal(True)


def are_equivalent(logic1, logic2):
    s = Solver()
    expr1 = And([condition_to_z3(cond) for cond in logic1 if cond])
    expr2 = And([condition_to_z3(cond) for cond in logic2 if cond])
    s.add(expr1 != expr2)
    return s.check() == unsat

def compute_similarity(code1, code2):
    seq = difflib.SequenceMatcher(None, code1, code2)
    return seq.ratio()

def compare_codes_string(gt_str, pred_str):
    """
    GT, pred가 문자열(JSON 또는 유사 JSON)일 때, cron/period/code/script 값만 추출해서 비교
    compare_codes와 동일한 return 구조를 가짐
    """
    # dict가 들어오면 string으로 변환
    if isinstance(gt_str, dict):
        gt_str = json.dumps(gt_str, ensure_ascii=False)
    if isinstance(pred_str, dict):
        pred_str = json.dumps(pred_str, ensure_ascii=False)

    gt = extract_json_fields(gt_str)
    pred = extract_json_fields(pred_str)

    # code/script 필드명 통일
    gt_code = gt.get("code") or gt.get("script") or ""
    pred_code = pred.get("code") or pred.get("script") or ""

    # 값 비교 (공백, \n, " 등 제거)
    def clean(s):
        if s is None:
            return ""
        return re.sub(r'[\s"\'\\]', '', s)

    cron_equal = clean(gt.get("cron")) == clean(pred.get("cron"))
    period_equal = clean(gt.get("period")) == clean(pred.get("period"))

    # script/code 유사도
    script_sim = compute_similarity(clean(gt_code), clean(pred_code))

    # ast 유사도 (문자열이므로 파싱 없이 0.0 반환)
    ast_sim = 0.0

    # 논리 동치 (문자열 비교만 하므로 False)
    logic_equiv = False

    return {
        "cron_equal": cron_equal,
        "period_equal": period_equal,
        "cron": {"gold": gt.get("cron"), "pred": pred.get("cron")},
        "period": {"gold": gt.get("period"), "pred": pred.get("period")},
        "logic_equivalent": logic_equiv,
        "script_similarity": round(script_sim, 3),
        "ast_similarity": round(ast_sim, 3)
    }


def compare_codes(gold: dict, pred: dict):
    # 1. cron, period 정확히 일치 여부 확인
    cron_equal = gold["cron"] == pred["cron"]
    period_equal = gold["period"] == pred["period"]

    # 2. script 파싱 후 AST 비교
    gold_ast = {"type": "Scenario", "body": parse_script_only(gold["script"].replace("\\n", "\n"))}
    pred_ast = {"type": "Scenario", "body": parse_script_only(pred["script"].replace("\\n", "\n"))}
  
    logic1 = extract_logic_expressions(gold_ast)
    logic2 = extract_logic_expressions(pred_ast)

    logic_equiv = are_equivalent(logic1, logic2)
    script_sim = compute_similarity(gold["script"], pred["script"])
    ast_sim = ast_similarity_score(gold_ast, pred_ast)

    return {
        "cron_equal": cron_equal,
        "period_equal": period_equal,
        "cron": {"gold": gold["cron"], "pred": pred["cron"]},
        "period": {"gold": gold["period"], "pred": pred["period"]},
        "logic_equivalent": logic_equiv,
        "script_similarity": round(script_sim, 3),
        "ast_similarity": round(ast_sim, 3)
    }


def parse_script_only(script_code: str):
    return parser.parse(script_code, lexer=lexer)

def parse_script_json(json_data):
    script_code = json_data["script"].replace("\\n", "\n")

    # {}로 감싸서 valid한 statement_list 구성
    wrapped_code = f"{{\n{script_code}\n}}"

    # 파싱 시도
    tree = parser.parse(wrapped_code, lexer=lexer)
    if tree is None:
        raise ValueError(f"파싱 실패: {json_data.get('name', '<unnamed>')}")

    # AST 추출
    body = tree.get("body", [])
    block = body[0] if body and body[0]["type"] == "Block" else None
    ast = block["body"] if block else []

    # 전체 반환
    return {
        "name": json_data.get("name", ""),
        "cron": json_data["cron"],
        "period": json_data["period"],
        "script": json_data["script"],
        "ast": ast
    }

def flatten_ast(node):
    flat = []

    def dfs(n):
        if isinstance(n, dict):
            flat.append(f"DICT:{sorted(n.keys())}")
            for k, v in n.items():
                dfs(v)
        elif isinstance(n, list):
            flat.append("LIST")
            for v in n:
                dfs(v)
        else:
            if isinstance(n, str):
                flat.append(f"VALUE:str={n}")
            elif isinstance(n, (int, float)):
                flat.append(f"VALUE:{type(n).__name__}={n}")
            else:
                flat.append(f"VALUE:{type(n).__name__}")

    dfs(node)
    return flat


def ast_similarity_score(ast1, ast2):
    flat1 = flatten_ast(ast1)
    flat2 = flatten_ast(ast2)
    
    matcher = difflib.SequenceMatcher(None, flat1, flat2)
    return matcher.ratio()

