import sys

from builtin import ParseError, RuntimeError
import scanner
import parser
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
    except ParseError as err:
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
