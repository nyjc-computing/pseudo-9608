import sys

from pseudocode.builtin import ParseError, RuntimeError, LogicError
from pseudocode import scanner
from pseudocode import parser
from pseudocode import resolver
from pseudocode import interpreter



__version__ = '0.2.1'



def error(lines, err):
    errType = type(err).__name__ + ':'
    if err.line:
        lineinfo = f"[Line {err.line}]"
        print(lineinfo, lines[err.line - 1])
    if err.col:
        leftmargin = len(lineinfo) + 1 + err.col
        print((' ' * leftmargin) + '^')
    print(errType, err.report())
    
def run(srcfile):
    with open(srcfile, 'r') as f:
        src = f.read()
    try:
        tokens, lines = scanner.scan(src)
        statements = parser.parse(tokens)
        statements, frame = resolver.inspect(statements)
    except (ParseError, LogicError) as err:
        error(lines, err)
        sys.exit(65)
    try:
        frame = interpreter.interpret(statements, frame)
    except RuntimeError as err:
        error(lines, err)
        sys.exit(70)