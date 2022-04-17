import sys

from builtin import ParseError, RuntimeError, LogicError
import scanner
import parser
import resolver
import interpreter



src = '''
DECLARE Index : INTEGER
Index <- 5
CASE OF Index
    5: OUTPUT "Five"
    4: OUTPUT "Four"
    3: OUTPUT "Three"
    2: OUTPUT "Two"
    1: OUTPUT "One"
    0: OUTPUT "I don't know!"
    OTHERWISE OUTPUT "I can't count beyond five"
ENDCASE
'''



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
