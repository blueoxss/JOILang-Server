import unittest
import json
from .soplang_parser_full import parser, lexer
from .compare_soplang_ir import parse_script_json, compare_codes, extract_logic_expressions
from .soplang_ir_simulator import generate_context_from_conditions, flatten_actions

"""
class TestSoplangParserFull(unittest.TestCase):

    def test_basic(self):
        json_data = {
            "name": "",
            "cron": "* * * * *",
            "period": 1000,
            "script": "if(temperature > 30) {\\n  (#fan).on()\\n}"
        }
        tree = parse_script_json(json_data)
        print("\n[basic AST]:\n", json.dumps(tree, indent=2, ensure_ascii=False))
        self.assertIsInstance(tree, dict)

    def test_cron(self):
        json_data = {
            "name": "사무실 움직임 시 불 켜고 사진 전송",
            "cron": "* * * * *",
            "period": 1000,
            "script": "if ((#office #movement).detected == 1 && (#office).brightness < 50) {\\n  (#office #light).turn_on()\\n  x = (#office).take_picture()\\n  (#util).send_mail(\"움직임 감지\", x)\\n}"
        }
        tree = parse_script_json(json_data)
        print("\n[cron AST]:\n", json.dumps(tree, indent=2, ensure_ascii=False))
        self.assertIsNotNone(tree, dict)
    
    def test_functioncall(self):
        json_data = {
            "name": "",
            "cron": "* * * * *",
            "period": 1000,
            "script": "photo = (#Camera).take()"
        }
        tree = parse_script_json(json_data)
        print("\n[function_call AST]:\n", json.dumps(tree, indent=2, ensure_ascii=False))
        self.assertIsNotNone(tree, dict)
    
    def test_all(self):
        json_data = {
            "name": "",
            "cron": "* * * * *",
            "period": 1000,
            "script": "all(#Light).off()"
        }
        tree = parse_script_json(json_data)
        print("\n[all AST]:\n", json.dumps(tree, indent=2, ensure_ascii=False))
        self.assertIsNotNone(tree, dict)
        
    def test_arithmetic_expression(self):
        json_data = {
            "name": "산술 연산 테스트",
            "cron": "* * * * *",
            "period": 1000,
            "script": "x := 4 / 3\\ny = x + 2\\n(#target).set_temp(y)"
        }
        tree = parse_script_json(json_data)
        print("\n[산술 연산 AST]:\n", json.dumps(tree, indent=2, ensure_ascii=False))
        self.assertIsNotNone(tree)
        self.assertIsInstance(tree, dict)
    def test_delay_statement(self):
        json_data = {
            "name": "지연 테스트",
            "cron": "* * * * *",
            "period": 1000,
            "script": "delay(1000)\\n(#speaker).say(\"1초 경과\")"
        }
        tree = parse_script_json(json_data)
        print("\n[Delay AST]:\n", json.dumps(tree, indent=2, ensure_ascii=False))
        self.assertIsNotNone(tree)
        self.assertIsInstance(tree, dict)

class TestCompareSoplangIR(unittest.TestCase):

    def test_compare_equivalent_scripts(self):
        gold = {
            "name": "기준 스크립트",
            "cron": "* * * * *",
            "period": 1000,
            "script": "x := 4 / 3\\ny = x + 2\\n(#target).set_temp(y)"
        }
        pred = {
            "name": "유사 스크립트",
            "cron": "* * * * *",
            "period": 1000,
            "script": "x := 4 / 3\\ny = x + 2\\n(#target).set_temp(y)"
        }

        result = compare_codes(gold, pred)
        print("\n✅ [compare_equivalent_scripts result]:\n", json.dumps(result, indent=2))
        self.assertTrue(result["cron_equal"])
        self.assertTrue(result["period_equal"])
        self.assertTrue(result["logic_equivalent"])
        self.assertEqual(result["script_similarity"], 1.0)

    def test_compare_different_logic(self):
        gold = {
            "name": "문턱값 높음",
            "cron": "* * * * *",
            "period": 1000,
            "script": "if (temperature > 30) {\\n  (#fan).on()\\n}"
        }
        pred = {
            "name": "문턱값 낮음",
            "cron": "* * * * *",
            "period": 1000,
            "script": "if (temperature > 10) {\\n  (#fan).on()\\n}"
        }

        result = compare_codes(gold, pred)
        print("\n❗ [compare_different_logic result]:\n", json.dumps(result, indent=2))
        self.assertTrue(result["cron_equal"])
        self.assertTrue(result["period_equal"])
        self.assertFalse(result["logic_equivalent"])
        self.assertLess(result["script_similarity"], 1.0)

def parse_script_only(script_code: str):
    wrapped_code = f"{{\n{script_code}\n}}"
    return parser.parse(wrapped_code, lexer=lexer)


class TestSoplangIrSimulator(unittest.TestCase):
    def test_condition_contexts_and_actions(self):
        script = '''
        if ((#sensor).temp > 30 or (#sensor).humidity < 50) {
            (#fan).on()
        }
        '''

        ast = parse_script_only(script)
        logic = extract_logic_expressions(ast)

        print("\n[Extracted Logic Conditions]:")
        for l in logic:
            print(json.dumps(l, indent=2))

        contexts = generate_context_from_conditions(logic)

        print(f"\n[Generated Contexts] ({len(contexts)} variants):")
        for ctx in contexts:
            print(ctx)

        print("\n[Actions for each context]:")
        for i, ctx in enumerate(contexts):
            actions = flatten_actions(ast, context=ctx.copy())
            print(f"\nContext #{i+1}: {ctx}")

            action_only = [a for a in actions if a[0] == "Action"]
            if not action_only:
                print("  ⚠️ No actions executed")
            else:
                for act in action_only:
                    target = act[1]
                    service = act[2]
                    args = ", ".join(map(str, act[3])) if act[3] else ""
                    print(f"  → Action: {target}.{service}({args})")

"""              
# class TestAll(unittest.TestCase):

#     def test_code_vs_label(self):
#         code = [
#             {
#                 "name": "Label1",
#                 "cron": "*/1 * * * *",
#                 "period": 180000,
#                 "code": "\nbutton_state = (#Button).button_button\nif (button_state != 'pushed') {\n    (#Button).switch_toggle()\n}\n"
#             },
#             {
#                 "name": "Label2",
#                 "cron": "*/1 * * * *",
#                 "period": 300000,
#                 "code": "\nac_state = (#AirConditioner).switch_switch\nif (ac_state == 'off') {\n    (#AirConditioner).switch_on()\n} else if (ac_state == 'on') {\n    (#AirConditioner).switch_off()\n}\n"
#             },
#             {
#                 "name": "문턱값 높음",
#                 "cron": "* * * * *",
#                 "period": 1000,
#                 "code": "if (temperature > 30) {\n  (#fan).on()\n}"
#             }
#         ]

#         label = [
#             {
#                 "name": "Label1",
#                 "cron": "*/1 * * * *",
#                 "period": 180000,
#                 "code": "\nbutton_state = (#Button).button_button\nif (button_state != 'pushed') {\n    (#Button).switch_toggle()\n}\n"
#             },
#             {
#                 "name": "Label2",
#                 "cron": "*/1 * * * *",
#                 "period": 300000,
#                 "code": "\nac_state = (#AirConditioner).switch_switch\nif (ac_state == 'off') {\n    (#AirConditioner).switch_on()\n} else if (ac_state == 'on') {\n    (#AirConditioner).switch_off()\n}\n"
#             },
#             {
#                 "name": "문턱값 높음",
#                 "cron": "* * * * *",
#                 "period": 1000,
#                 "code": "if (temperature >= 30) {\n  (#fan).on()\n}"
#             }
#         ]
#         def parse_code_to_ast(script: str):
#             wrapped = f"{{\n{script}\n}}"
#             return parser.parse(wrapped, lexer=lexer)
#         for i, (gen, gold) in enumerate(zip(code, label), start=1):
#             print(f"\n[Test{i}]")

#             gold_wrapped = {
#                 "name": gold["name"],
#                 "cron": gold["cron"],
#                 "period": gold["period"],
#                 "script": gold["code"]
#             }

#             gen_wrapped = {
#                 "name": gen["name"],
#                 "cron": gen["cron"],
#                 "period": gen["period"],
#                 "script": gen["code"]
#             }

#             result = compare_codes(gold_wrapped, gen_wrapped)

#             print(f"- cron : {result['cron_equal']}")
#             print(f"- period : {result['period_equal']}")
#             print(f"- ast_similarity: {result['ast_similarity']:.3f}")
#             print(f"- script similarity: {result['script_similarity']:.3f}")
#             print("\n→ Simulated Action Traces:")
#         try:
#             gold_ast = parse_code_to_ast(gold["code"])
#             gen_ast = parse_code_to_ast(gen["code"])

#             logic = extract_logic_expressions(gold_ast)
#             contexts = generate_context_from_conditions(logic)

#             for ctx_idx, ctx in enumerate(contexts):
#                 gold_trace = flatten_actions(gold_ast, ctx.copy())
#                 gen_trace = flatten_actions(gen_ast, ctx.copy())

#                 gold_actions = [a for a in gold_trace if a[0] == "Action"]
#                 gen_actions = [a for a in gen_trace if a[0] == "Action"]

#                 max_len = max(len(gold_actions), len(gen_actions))
#                 for j in range(max_len):
#                     g = gold_actions[j] if j < len(gold_actions) else "❌ Missing"
#                     p = gen_actions[j] if j < len(gen_actions) else "❌ Missing"

#                     if g != p:
#                         print(f"\n❌ MISMATCH @ Context #{ctx_idx+1}, Step {j}")
#                         print(f"→ Variables: {ctx}")
#                         print(f"→ Gold Action: {g}")
#                         print(f"→ Pred Action: {p}")

#         except Exception as e:
#             print(f"❌ Simulation failed: {e}")    

class ParserTestCase(unittest.TestCase):
    def test_basic_if(self):
        code = '''
        {
          count := 0
          if (count >= 3) {
            (#A).run()
          }
        }
        '''
        result = parser.parse(code, lexer=lexer)
        self.assertIsNotNone(result)

if __name__ == '__main__':
    result = parser.parse("count := 0\nif (count >= 3) { (#A).run() }", lexer=lexer)
    print(result)
    unittest.main()
