# soplang_parser_full.py - Fixed TAG parsing logic and simplified AST rules

import ply.lex as lex
import ply.yacc as yacc

# --------- TOKENS ---------
tokens = (
    'INTEGER', 'DOUBLE', 'IDENTIFIER', 'STRING_LITERAL',
    'GE', 'LE', 'EQ', 'NE', 'ASSIGN', 'DECLARE',
    'COMMA', 'DOT', 'HASH', 'LPAREN', 'RPAREN',
    'MILLISECOND', 'SECOND', 'MINUTE', 'HOUR', 'DAY',
    'WAIT_UNTIL', 'IF', 'ELSE', 'NOT', 'OR', 'AND',
    'GT', 'LT', 'LBRACE', 'RBRACE', 'ANY', 'ALL',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'DELAY',
    'TAG', 'PERCENT'
)

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('left', 'EQ', 'NE'),
    ('left', 'GT', 'GE', 'LT', 'LE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
)

t_COMMA = r','
t_DOT = r'\.'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_HASH = r'\#'
t_ASSIGN = r'='
t_GE = r'>='
t_LE = r'<='
t_EQ = r'=='
t_NE = r'!='
t_ignore = ' \t'
t_GT = r'>'
t_LT = r'<'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_DECLARE = r':='
t_PLUS = r'\+'
t_MINUS = r'-'
t_TIMES = r'\*'
t_DIVIDE = r'/'
t_TAG = r'\#[A-Za-z0-9_]+'
t_PERCENT = r'%'

def t_WAIT_UNTIL(t): r'wait\suntil'; return t
def t_IF(t): r'if'; return t
def t_ELSE(t): r'else'; return t
def t_NOT(t): r'not'; return t
def t_OR(t): r'or|\|\|'; return t
def t_AND(t): r'and|\&\&'; return t
def t_MILLISECOND(t): r'MSEC'; return t
def t_SECOND(t): r'SEC'; return t
def t_MINUTE(t): r'MIN'; return t
def t_HOUR(t): r'HOUR'; return t
def t_DAY(t): r'DAY'; return t
def t_ANY(t): r'any'; return t
def t_ALL(t): r'all'; return t
def t_DELAY(t): r'delay'; return t

def t_DOUBLE(t):
    r'[-+]?[0-9]*\.[0-9]+'
    t.value = float(t.value)
    return t

def t_INTEGER(t):
    r'[+-]?[0-9]+'
    t.value = int(t.value)
    return t

def t_STRING_LITERAL(t):
    r'(\"([^\\\"]|\\.)*\"|\'([^\\\']|\\.)*\')'
    t.value = t.value[1:-1]
    return t

def t_IDENTIFIER(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    return t

def t_newline(t):
    r'[\n\r]+'
    t.lexer.lineno += t.value.count('\n')

def t_error(t):
    print(f"Illegal character '{t.value[0]}'")
    t.lexer.skip(1)

lexer = lex.lex()

# --------- PARSER ---------

def p_scenario(p):
    'scenario : statement_list'
    p[0] = {"type": "Scenario", "body": p[1]}

def p_statement_list(p):
    '''statement_list : statement
                      | statement statement_list'''
    p[0] = [p[1]] if len(p) == 2 else [p[1]] + p[2]

def p_statement(p):
    '''statement : action
                 | all_action
                 | assignment
                 | if_statement
                 | wait_statement
                 | compound_statement'''
    p[0] = p[1]

def p_tag_list(p):
    '''tag_list : TAG
                | tag_list TAG'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_tag_expression(p):
    'tag_expression : LPAREN tag_list RPAREN'
    p[0] = {"type": "TagAccess", "tags": p[2]}

def p_attr_access(p):
    'expression : tag_expression DOT IDENTIFIER'
    p[0] = {"type": "AttrAccess", "tags": p[1]["tags"], "attr": p[3]}

def p_method_call(p):
    '''expression : tag_expression DOT IDENTIFIER LPAREN input RPAREN
                  | tag_expression DOT IDENTIFIER LPAREN RPAREN'''
    p[0] = {
        "type": "MethodCall",
        "tags": p[1]["tags"],
        "method": p[3],
        "args": p[5] if len(p) == 7 else []
    }

def p_action(p):
    '''action : LPAREN tag_list RPAREN DOT IDENTIFIER LPAREN RPAREN
              | LPAREN tag_list RPAREN DOT IDENTIFIER LPAREN input RPAREN'''
    p[0] = {
        "type": "Action",
        "target": p[2],
        "service": p[5],
        "args": [] if len(p) == 8 else p[7]
    }

def p_all_action(p):
    '''all_action : ALL LPAREN tag_list RPAREN DOT IDENTIFIER LPAREN RPAREN
                  | ALL LPAREN tag_list RPAREN DOT IDENTIFIER LPAREN input RPAREN'''
    p[0] = {
        "type": "AllAction",
        "target": p[3],
        "service": p[6],
        "args": [] if len(p) == 9 else p[8]
    }
def p_expression_boolean(p):
    '''expression : expression AND expression
                  | expression OR expression'''
    p[0] = {"type": "BoolOp", "op": p[2].lower(), "left": p[1], "right": p[3]}
def p_expression_all_attr_access(p):
    'expression : ALL LPAREN tag_list RPAREN DOT IDENTIFIER'
    p[0] = {
        "type": "AllAttrAccess",
        "target": p[3],
        "attr": p[6]
    }
    
def p_expression_percent(p):
    'expression : expression PERCENT'
    p[0] = {"type": "Percent", "value": p[1]}  
      
def p_assignment(p):
    '''assignment : IDENTIFIER ASSIGN expression
                  | IDENTIFIER DECLARE expression'''
    assign_type = "Declare" if p[2] == ':=' else "Assign"
    p[0] = {"type": assign_type, "target": p[1], "value": p[3]}

def p_expression_literals(p):
    '''expression : IDENTIFIER
                  | INTEGER
                  | DOUBLE
                  | STRING_LITERAL'''
    p[0] = p[1]

def p_expression_binary(p):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression'''
    p[0] = {"type": "BinaryOp", "op": p[2], "left": p[1], "right": p[3]}
    

    
def p_input(p):
    '''input : expression
             | input COMMA expression'''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

def p_compound_statement(p):
    'compound_statement : LBRACE statement_list RBRACE'
    p[0] = {"type": "Block", "body": p[2]}

def p_if_statement(p):
    'if_statement : IF LPAREN condition_list RPAREN compound_statement else_clause'
    p[0] = {"type": "If", "condition": p[3], "then": p[5], "else": p[6]}

def p_else_clause(p):
    '''else_clause : ELSE statement
                   | empty'''
    p[0] = p[2] if len(p) == 3 else None

def p_delay_statement(p):
    'statement : DELAY LPAREN expression RPAREN'
    p[0] = {"type": "Delay", "value": p[3]}

def p_condition_list(p):
    '''condition_list : condition
                      | LPAREN condition_list RPAREN
                      | condition_list AND condition_list
                      | condition_list OR condition_list
                      | NOT condition'''
    if len(p) == 2:
        p[0] = p[1]
    elif p[1] == '(':
        p[0] = p[2]
    elif p[1] in ('not', 'NOT'):
        p[0] = {"op": "not", "expr": p[2]}
    else:
        p[0] = {"op": p[2], "left": p[1], "right": p[3]}
        
    
def p_condition(p):
    '''condition : expression GE expression
                 | expression LE expression
                 | expression EQ expression
                 | expression NE expression
                 | expression GT expression
                 | expression LT expression'''
    p[0] = {"left": p[1], "op": p[2], "right": p[3]}

def p_wait_statement(p):
    '''wait_statement : WAIT_UNTIL LPAREN condition_list RPAREN
                      | WAIT_UNTIL LPAREN period_time RPAREN'''
    if isinstance(p[3], str):
        p[0] = {"type": "WaitUntil", "time": p[3]}
    else:
        p[0] = {"type": "WaitUntil", "condition": p[3]}

def p_period_time(p):
    'period_time : INTEGER time_unit'
    p[0] = f"{p[1]} {p[2]}"

def p_time_unit(p):
    '''time_unit : MILLISECOND
                 | SECOND
                 | MINUTE
                 | HOUR
                 | DAY'''
    p[0] = p[1]

def p_empty(p):
    'empty :'
    p[0] = []

def p_error(p):
    if p:
        print(f"Syntax error at token {p.type} ({p.value}) line {p.lineno} col {p.lexpos}")
    else:
        print("Syntax error at EOF")

parser = yacc.yacc()
