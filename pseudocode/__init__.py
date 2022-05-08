from .builtin import ParseError, RuntimeError, LogicError
from .lang import Frame
from .function import system

from . import scanner, parser, resolver
from .interpreter import Interpreter



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



class Pseudo:
    """A 9608 pseudocode interpreter"""
    def __init__(self):
        self.handlers = {
            'output': print,
            'input': input,
        }

    def registerHandlers(self, **kwargs):
        for key, handler in kwargs.items():
            if key not in self.handlers:
                raise KeyError(f"Invalid handler key {repr(key)}")
            self.handlers[key] = handler

    def runFile(self, srcfile):
        with open(srcfile, 'r') as f:
            src = f.read()
        return self.run(src)
    
    def run(self, src):
        result = {
            'lines': None,
            'frame': None,
            'error': None,
        }
        globalFrame = Frame(outer=system)
        try:
            tokens, lines = scanner.scan(src)
            result['lines'] = lines
            statements = parser.parse(tokens)
            statements, frame = resolver.inspect(statements)
            result['frame'] = frame
        except (ParseError, LogicError) as err:
            result['error'] = err
            return result

        interpreter = Interpreter(frame, statements)
        interpreter.registerOutputHandler(self.handlers['output'])
        try:
            frame = interpreter.interpret()
            result['frame'] = frame
        except RuntimeError as err:
            result['error'] = err
        finally:
            return result
