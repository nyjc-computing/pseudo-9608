import sys

from pseudocode.builtin import ParseError, RuntimeError, LogicError
from pseudocode import scanner
from pseudocode import parser
from pseudocode import resolver
from pseudocode.interpreter import Interpreter



__version__ = '0.2.1'



class Pseudo:
    """A 9608 pseudocode interpreter"""
    def __init__(self):
        self.handlers = {
            'output': None,
        }

    def registerHandlers(self, output):
        self.handlers['output'] = output

    @staticmethod
    def error(lines, err):
        errType = type(err).__name__ + ':'
        if err.line:
            lineinfo = f"[Line {err.line}]"
            print(lineinfo, lines[err.line - 1])
        if err.col:
            leftmargin = len(lineinfo) + 1 + err.col
            print((' ' * leftmargin) + '^')
            print(errType, err.report())

    def runFile(self, srcfile):
        with open(srcfile, 'r') as f:
            src = f.read()
        self.run(src)
    
    def run(self, src):
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
            self.error(lines, err)
            sys.exit(65)
        else:
            result['frame'] = frame
        interpreter = Interpreter(frame, statements)
        try:
            frame = interpreter.interpret()
        except RuntimeError as err:
            result['error'] = err
            self.error(lines, err)
            sys.exit(70)
        else:
            result['frame'] = frame
        return result