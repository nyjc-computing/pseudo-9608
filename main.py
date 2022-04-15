import sys

from builtin import ParseError, RuntimeError, LogicError
import scanner
import parser
import resolver
import interpreter



src = '''
DECLARE Index : INTEGER
Index <- 1
OUTPUT Index
'''



def main():
    try:
        tokens = scanner.scan(src)
        statements = parser.parse(tokens)
        statements, frame = resolver.resolve(statements)
    except (ParseError, LogicError) as err:
        print(err)
        sys.exit(65)
    try:
        frame = interpreter.interpret(statements)
        print(frame)
    except RuntimeError as err:
        print(err)
        sys.exit(70)



if __name__ == "__main__":
    main()
