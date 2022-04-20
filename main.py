import sys

from builtin import ParseError, RuntimeError, LogicError
import scanner
import parser
import resolver
import interpreter



src = '''
DECLARE i : INTEGER
i <- 1
WHILE i < 10 DO
    OUTPUT i
    i <- i + 1
ENDWHILE
'''
# src = '''
# DECLARE i : INTEGER
# i <- 1
# REPEAT
#     OUTPUT i
#     i <- i + 1
# UNTIL i >= 10
# '''
# src = '''
# DECLARE i : INTEGER
# FOR i <- 1 TO 10
#     OUTPUT i
# ENDFOR
# '''



def main():
    try:
        tokens = scanner.scan(src)
        statements = parser.parse(tokens)
        statements, frame = resolver.inspect(statements)
    except (ParseError, LogicError) as err:
        print(err)
        sys.exit(65)
    try:
        frame = interpreter.interpret(statements, frame)
        print(frame)
    except RuntimeError as err:
        print(err)
        sys.exit(70)



if __name__ == "__main__":
    main()
