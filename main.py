import sys

from builtin import ParseError, RuntimeError
import scanner
import parser
import interpreter



src = 'OUTPUT "Hello", ", ", "everyone", "!"'



def main():
    try:
        tokens = scanner.scan(src)
        statements = parser.parse(tokens)
    except ParseError as err:
        print(err)
        sys.exit(65)
    try:
        interpreter.interpret(statements)
    except RuntimeError as err:
        print(err)
        sys.exit(70)



if __name__ == "__main__":
    main()