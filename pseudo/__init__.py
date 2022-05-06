import sys
from pprint import PrettyPrinter

from pseudo.builtin import ParseError, RuntimeError, LogicError
from pseudo import scanner
from pseudo import parser
from pseudo import resolver
from pseudo import interpreter



__version__ = '0.1.0'



def run(srcfile='main.pseudo'):
    if len(sys.argv) != 1:
        srcfile = sys.argv[1]
    with open(srcfile, 'r') as f:
        src = f.read()
    pp = PrettyPrinter(indent=2, compact=True)
    try:
        tokens, lines = scanner.scan(src)
        statements = parser.parse(tokens)
        statements, frame = resolver.inspect(statements)
    except (ParseError, LogicError) as err:
        errType = type(err).__name__ + ':'
        if err.line:
            lineinfo = f"[Line {err.line}]"
            print(lineinfo, lines[err.line - 1])
        if err.col:
            leftmargin = len(lineinfo) + 1 + err.col
            print((' ' * leftmargin) + '^')
        print(errType, err.report())
        sys.exit(65)
    try:
        frame = interpreter.interpret(statements, frame)
        pp.pprint(frame)
    except RuntimeError as err:
        print(err)
        sys.exit(70)