import sys

from builtin import ParseError, RuntimeError, LogicError
import scanner
import parser
import resolver
import interpreter



src = '''
DECLARE Result : STRING
OUTPUT "Enter some text: "
INPUT Result
OUTPUT "You entered: ", Result
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
