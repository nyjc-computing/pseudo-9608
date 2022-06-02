from typing import Optional
from typing import Iterable, List, MutableMapping
from typing import TypedDict, Callable as function
from sys import exc_info
from traceback import format_exception

from . import builtin
from .lang import Frame
from .system import system as sysFrame

from . import scanner, parser
from .resolver import Resolver
from .interpreter import Interpreter

class Result(TypedDict):
    """The metadata dict passed to an Array declaration"""
    lines: List[str]
    frame: Frame
    error: Optional[builtin.PseudoError]



__version__ = '0.3.2'



# https://stackoverflow.com/a/66416364/318186
def printException() -> None:
    etype, value, tb = exc_info()
    info, error = format_exception(etype, value, tb)[-2:]
    print(f'Exception in:\n{info}\n{error}')

def error(lines: Iterable[str], err: builtin.PseudoError) -> None:
    errType = type(err).__name__ + ':'
    if err.line:
        lineinfo = f"[Line {err.line}]"
        print(lineinfo, lines[err.line - 1])  # type: ignore
    if err.col:
        leftmargin = len(lineinfo) + 1 + err.col
        print((' ' * leftmargin) + '^')
    print(errType, err.report())



class Pseudo:
    """A 9608 pseudocode interpreter"""
    def __init__(self) -> None:
        self.handlers: MutableMapping[str, function] = {
            'output': print,
            'input': input,
        }

    def registerHandlers(self, **kwargs: function) -> None:
        for key, handler in kwargs.items():
            if key not in self.handlers:
                raise KeyError(f"Invalid handler key {repr(key)}")
            self.handlers[key] = handler

    def runFile(self, srcfile: str) -> Result:
        with open(srcfile, 'r') as f:
            src = f.read()
        return self.run(src)
    
    def run(self, src: str) -> Result:
        globalFrame = Frame(typesys=sysFrame.types, outer=sysFrame)
        result: Result = {
            'lines': [],
            'frame': globalFrame,
            'error': None,
        }

        # Parsing
        try:
            tokens, lines = scanner.scan(src)
            result['lines'] += lines
            statements = parser.parse(tokens)
        except builtin.ParseError as err:
            result['error'] = err
            return result
        except Exception:
            printException()
            return result

        # Resolving
        resolver = Resolver(globalFrame, statements)
        try:
            resolver.inspect()
        except builtin.LogicError as err:
            result['error'] = err
            return result
        except Exception:
            printException()
            return result

        # Interpreting
        interpreter = Interpreter(globalFrame, statements)
        interpreter.registerOutputHandler(self.handlers['output'])
        try:
            interpreter.interpret()
        except builtin.RuntimeError as err:
            result['error'] = err
        except Exception:
            printException()
        finally:
            return result
