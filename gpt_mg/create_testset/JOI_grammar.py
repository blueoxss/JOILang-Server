grammar="""Let me teach you SoPLang.
This is the lex and yacc syntax of SoPLang.
lex is below:

[+-]?[0-9]+  {return INTEGER;}
[-+]?([0-9]*\\.[0-9]+|[0-9]+) {return DOUBLE;}
[ \t];[\n]    { return ENTER; }
"\r\n" {return WINDOW_ENTER; }
"wait until" { return WAIT_UNTIL; }
"loop" { return LOOP; }
"if" { return IF; }
"else" { return ELSE; }
"," { return COMMA; }
":" { return COLON; }
">=" { return GE; }
"<=" { return LE; }
"==" { return EQ; }
"!=" { return NE; }
"[" { return '['; }
"]" { return ']'; }
"." { return DOT; }
"not" { return NOT; }
"all" { return ALL; }
"or" { return OR; }
"and" { return AND; }
"MSEC" { return MSEC;}
"SEC" { return SEC;}
"MIN" { return MIN;}
"HOUR" { return HOUR;}
"DAY" { return DAY;}
";" { return ';'; }
"#" { return '#'; }
"=" { return ASSIGN; }
"//"[^\n]*[\n]   { /* comment */ }
\"([^\\\"]|\\.)*\" {return STRING_LITERAL;}
[a-zA-Z][_a-zA-Z0-9]* /* identifier */ { return IDENTIFIER;}

now, yacc syntax in below:

scenario: statement_list;
statement_list:
    statement
  | statement statement_list;
statement:
    action_behavior
  | if_statement
  | loop_statement
  | wait_statement
  | compound_statement;
compound_statement: '{' blank statement_list '}';
action_behavior:
    (output ASSIGN) range_type '(' tag_list ')' DOT IDENTIFIER '(' action_input ')'
  | range_type '(' tag_list ')' DOT IDENTIFIER '(' action_input ')'
  | (output ASSIGN) '(' tag_list ')' DOT IDENTIFIER '(' action_input ')'
  | '(' tag_list ')' DOT IDENTIFIER '(' action_input ')';
output: identifier_list;
identifier_list:
    IDENTIFIER
  | IDENTIFIER COMMA blank identifier_list;
range_type: ALL | OR;
tag_list: hashtag_list;
hashtag_list:
    '#' IDENTIFIER
  | '#' IDENTIFIER hashtag_list
  | '#' IDENTIFIER blank hashtag_list;
action_input: %empty | input;
input:
    primary_expression
    | input blank COMMA blank primary_expression;
primary_expression:
    IDENTIFIER
    | INTEGER
    | DOUBLE
    | STRING_LITERAL
    | '(' tag_list ')' DOT IDENTIFIER
    | range_type '(' tag_list ')' DOT IDENTIFIER;
if_statement: IF '(' condition_list ')' blank statement blank else_statement;
condition_list:
    condition
  | '(' condition_list ')'
  | condition_list blank OR blank condition_list
  | condition_list blank AND blank condition_list
  | NOT condition blank;
else_statement: %empty | ELSE blank statement;
loop_statement: LOOP '(' loop_condition ')' blank statement;
loop_condition:
    %empty
  | period_time COMMA condition_list
  | period_time
  | condition_list;
period_time: INTEGER time_unit;
time_unit: MSEC | SEC | MIN | HOUR | DAY;
wait_statement:
    WAIT_UNTIL '(' condition_list ')'
  | WAIT_UNTIL '(' period_time ')';
"""
samples="""Here is the templates of SoPLang script.
loop (1 SEC)
{
        wait until ( (#VTTT).VVV >= 1 )
        (#STTT).SSS()
},

loop (1 SEC)
{
        if ( (#clock).hour >= 13 and (#clock).hour <= 14 )
        {
                (#STTT #STTT).SSS()
        }
},

loop (2 MIN)
{
        if ( (#VTTT #VTTT).VVV >= 120 and (#VTTT).VVV <= 130 )
        {
                (#STTT #STTT).SSS()
        }
},

loop (3 SEC)
{
        x = (#STTT).SSS(arg1, arg2, arg3)
        (#STTT).SSS("XX", x)
        wait until ((#VTTT).VVV == 100 );
},

loop (1 HOUR)
{
        if ( (#VTTT).VVV >= 0 and (#VTTT).VVV <= 3 )
        {
                (#STTT #STTT).SSS()
        }

        x = (#STTT #STTT #STTT).SSS(arg1)
        (#STTT).SSS("test", x)
        wait until ((#VTTT).VVV == 100 );
},

loop (1 SEC)
{
        if ( (#VTTT #VTTT).VVV == 1 and (#TTT).VVV < 50 )
        {
                x = (#STTT #STTT #STTT).SSS()
                (#STTT).SSS("ikess@gmail.com", "움직임 감지", "test file", x)
        }
}

VVV should be replaced with a value service in the service list
SSS should be replaced with a function service in the service list.
VTTT should be replaced with a tag of VVV in the value service list.
STTT should be replaced with a tag of SSS in the function service list.
"""

samples2="""Here is the samples of SoPLang script.
My email address is "ikess@gmail.com"

- Let me know the weather every 1 hour
loop (1 HOUR)
{
        x = (#util).get_weather()
        (#speaker).tts(x)
}
- If it rains, notify me “비 와요” when i am at door
loop (1 SEC)
{
        if ( (#door #movement).detected == 1 )
        {
                x = (#util).get_weather()
                if (x == "rainy")
                {
                        (#door #speaker).tts("비 와요")
                }
        }
}
- If the somewhere is dark and you detect movement, turn on the lights, take a picture, and email it to me.
loop (1 SEC)
{
        if ( (#somewhere #movement).detected == 1 and (#XXX).brightness < 50 )
        {
                (#tag1 #somewhere #light).turn_on()
                (#util).send_with_file("ikess@gmail.com", "움직임 감지", "test file", x)
        }
}
- Turn off the air conditioning when the room is below 23 degrees, turn it on when it's above 25 degrees.
loop (30 SEC)
{
        if ( (#tag1 #room).temperature <= 23 )
        {
                (#tag2 #meeting_room #air_conditioner).turn_off()
        }
        else if ( (#tag3 #meeting_room).temperature > 25 )
        {
                (#air_conditioner).turn_on()
        }
}
- If my room is too dusty, return the robot vacuum.
    loop (10 SEC)
    {
        if ( (#euiseok).dust > 100 )
        {
                (#euiseok #vacuum).start_cleaning()
        }
    }
- 1시에서 2시 사이에 움직임이 감지되면, 불을 켜줘.
    loop (10 SEC)
    {
        if ( (#clock).hour >= 13 and (#clock).hour <= 14 )
        {
                (#euiseok #light).turn_on()
        }
    }
"""