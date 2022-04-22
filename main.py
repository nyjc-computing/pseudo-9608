import sys
from pprint import PrettyPrinter

from builtin import ParseError, RuntimeError, LogicError
import scanner
import parser
import resolver
import interpreter



src = '''
DECLARE Five : INTEGER
FUNCTION AddOne(Num : INTEGER) RETURNS INTEGER
    RETURN Num + 1
ENDFUNCTION
Five <- 5
OUTPUT "5 + 1 is ", AddOne(Five)
'''



def main():
    pp = PrettyPrinter(indent=2, compact=True)
    try:
        tokens = scanner.scan(src)
        statements = parser.parse(tokens)
        statements, frame = resolver.inspect(statements)
    except (ParseError, LogicError) as err:
        print(err)
        sys.exit(65)
    try:
        frame = interpreter.interpret(statements, frame)
        pp.pprint(frame)
    except RuntimeError as err:
        print(err)
        sys.exit(70)



if __name__ == "__main__":
    main()
