# compare_soplang_ir.py

from joi_parser_full import parser, lexer
from z3 import *
import json
import difflib
import re, yaml, os

#Soplang 코드를 PLY 기반 파서로 파싱하여 AST return
def parse_soplang(code: str):
    return parser.parse(code, lexer=lexer)

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

def compare_codes(gold: dict, pred: dict):
    # 1. cron, period 정확히 일치 여부 확인
    cron_equal = gold["cron"] == pred["cron"]
    period_equal = gold["period"] == pred["period"]

    # 2. script 파싱 후 AST 비교
    gold_ast = {"type": "Scenario", "body": parse_script_only(gold["code"])}
    pred_ast = {"type": "Scenario", "body": parse_script_only(pred["code"])}
  
    logic1 = extract_logic_expressions(gold_ast)
    logic2 = extract_logic_expressions(pred_ast)

    logic_equiv = are_equivalent(logic1, logic2)
    script_sim = compute_similarity(gold["code"], pred["code"])
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
    script_code = json_data["code"].replace("\\n", "\n")

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
        "code": json_data["code"],
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

def normalize_action(node):
    if isinstance(node, dict) and node.get("type") == "Action":
        tag = node.get("target", [])
        method = node.get("service")
        args = node.get("args", [])

        # Alarm 관련 매핑
        if method == "alarm_siren":
            return {"type": "Action", "target": tag, "service": "siren_sirenset", "args": ["siren"]}
        elif method == "alarm_both":
            return {"type": "Action", "target": tag, "service": "siren_sirenset", "args": ["both"]}
        elif method == "alarm_off":
            return {"type": "Action", "target": tag, "service": "siren_sirenset", "args": ["off"]}

        # AudioMute 관련 매핑
        elif method == "audioMute_mute":
            return {"type": "Action", "target": tag, "service": "audioMute_setMute", "args": ["muted"]}
        elif method == "audioMute_unmute":
            return {"type": "Action", "target": tag, "service": "audioMute_setMute", "args": ["unmuted"]}

        # MediaPlayback 관련 매핑
        elif method == "mediaPlayback_fastForward":
            return {"type": "Action", "target": tag, "service": "mediaPlayback_setPlaybackStatus", "args": ["fastForward"]}
        elif method == "mediaPlayback_pause":
            return {"type": "Action", "target": tag, "service": "mediaPlayback_setPlaybackStatus", "args": ["paused"]}
        elif method == "mediaPlayback_stop":
            return {"type": "Action", "target": tag, "service": "mediaPlayback_setPlaybackStatus", "args": ["stopped"]}

        normalized_tag = []
        for t in tag:
            t_lower = t.lower()
            if any(name in t.lower() for name in ["curtain", "shade", "blind", "windowshade"]):
                normalized_tag.append("#Blind")  # 모든 블라인드류를 #Blind로 통일
            elif "occupancy" in t_lower or "presence" in t_lower:
                normalized_tag.append("#OccupancySensor")
            else:
                normalized_tag.append(t)
        node["target"] = normalized_tag

    return node

def normalize_ast(ast):
    def dfs(node):
        if isinstance(node, dict):
            node = normalize_action(node)
            return {k: dfs(v) for k, v in node.items()}
        elif isinstance(node, list):
            return [dfs(item) for item in node]
        else:
            return node
    return dfs

def ast_similarity_score(ast1, ast2):
    norm1 = normalize_ast(ast1)
    norm2 = normalize_ast(ast2)
    flat1 = flatten_ast(ast1)
    flat2 = flatten_ast(ast2)
    
    matcher = difflib.SequenceMatcher(None, flat1, flat2)
    return matcher.ratio()

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def compare_all(model_name: str):
    gold_path = f"./Testset/TestsetWithDevices_translated"
    pred_path = f"./Testset/Eval_{model_name}"
    
    results_summary = []
    all_scores = []
    
    def extract_number(filename):
        match = re.search(r'(\d+)', filename)
        return int(match.group(1)) if match else float('inf')
    files = sorted(
        [f for f in os.listdir(gold_path) if f.endswith(".yaml")],
        key=extract_number
    )
    # files = sorted(
    #     [f for f in os.listdir(gold_path) if f == "category_5.yaml"]
    # )
    
    for file_idx, file in enumerate(files):
        file_results = []
        file_scores = []
        
        with open(os.path.join(gold_path, file), 'r', encoding='utf-8') as f1:
            gold_data = yaml.safe_load(f1)
        
        with open(os.path.join(pred_path, f"evaluation_{file}"), 'r', encoding='utf-8') as f2:
            pred_data = yaml.safe_load(f2)
        
        for ex_idx, (gold_item, pred_item) in enumerate(zip(gold_data, pred_data)):
            ex_id = f"ex{file_idx}-{ex_idx + 1}"
            default_scenario = {"name": "Scenario1", "cron": "", "period": -1, "code": "", "score": 100}

            pred_list = pred_item.get("generated_code", [])
            if isinstance(pred_list, dict):
                pred_list = [pred_list]
            elif not isinstance(pred_list, list):
                pred_list = []
            pred = pred_list[0] if pred_list else default_scenario

            model = {
                "name": pred.get("name", "Scenario1"),
                "cron": pred.get("cron", ""),
                "period": pred.get("period", -1),
                "code": pred.get("code", "")
            }

            gold_candidates = gold_item.get("code", []) or [default_scenario]

            best_code_score = -1
            best_result = None
            best_score_detail = {}
            best_status = ""
            best_diff = {}
            best_weight = 100

            for gold_idx, gold in enumerate(gold_candidates):
                label = {
                    "name": gold.get("name", "Scenario1"),
                    "cron": gold.get("cron", ""),
                    "period": gold.get("period", -1),
                    "code": gold.get("code", "")
                }

                weight = gold.get("score", 100)
                result = compare_codes(label, model)

                code_score = round(result["ast_similarity"], 3)
                cron_score = 100 if result["cron_equal"] else 0
                period_score = 100 if result["period_equal"] else 0
                logic_score = int(code_score * 100 * (weight / 100))  
                # print(f"[Debug] {ex_id} → selected scenario {gold_idx + 1} (code_score: {code_score})")
                # print(gold)
                if code_score > best_code_score:
                    best_code_score = code_score
                    best_result = result
                    best_weight = weight
                    best_score_detail = {
                        "cron": cron_score,
                        "period": period_score,
                        "code": logic_score
                    }
                    best_label = label
                    best_diff = {}
                    if not result["cron_equal"]:
                        best_diff["cron"] = f"model = {model['cron']}, label = {label['cron']}"
                    if not result["period_equal"]:
                        best_diff["period"] = f"model = {model['period']}, label = {label['period']}"
                    if code_score < 1.0:
                        best_diff["code"] = f"ast_similarity = {code_score}"
            file_scores.append(best_score_detail)
            file_results.append({
                "id": ex_id,
                "score": best_score_detail,
                "diff": best_diff
            })   
        
        def avg_by_key(score_list, key):
            return sum(s[key] for s in score_list) / len(score_list)
        
        if file_scores:
            avg_file_score = {
                "cron": avg_by_key(file_scores, "cron"),
                "period": avg_by_key(file_scores, "period"),
                "code": avg_by_key(file_scores, "code")
            }

            results_summary.extend(file_results)
            results_summary.append({
                "id": f"{file.replace('.yaml', '')}-avg",
                "score": {k: round(v, 1) for k, v in avg_file_score.items()}
            })
            all_scores.extend(file_scores)
        
    def avg_all(key):
        return sum(s[key] for s in all_scores) / len(all_scores)

    if all_scores:
        overall_avg = {
            "cron": avg_all("cron"),
            "period": avg_all("period"),
            "code": avg_all("code")
        }

        results_summary.append({
            "id": "overall-avg",
            "score": {k: round(v, 1) for k, v in overall_avg.items()}
        })
    
    with open(f"./Testset/Eval_{model_name}/comparison_summary.yaml", "w", encoding="utf-8") as out_f:
        yaml.dump(results_summary, out_f, allow_unicode=True, sort_keys=False)
        
        
if __name__ == "__main__":
    compare_all("codegemma")