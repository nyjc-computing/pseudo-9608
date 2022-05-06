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

def runFile(srcfile):
    with open(srcfile, 'r') as f:
        src = f.read()
    run(src)
    
def run(src):
    result = {
        'frame': None,
        'error': None,
        'output': [],
    }
    try:
        tokens, lines = scanner.scan(src)
        statements = parser.parse(tokens)
        statements, frame = resolver.inspect(statements)
    except (ParseError, LogicError) as err:
        result['error'] = err
        error(lines, err)
        sys.exit(65)
    else:
        result['frame'] = frame
    try:
        frame = interpreter.interpret(statements, frame)
    except RuntimeError as err:
        result['error'] = err
        error(lines, err)
        sys.exit(70)
    else:
        result['frame'] = frame
    return result