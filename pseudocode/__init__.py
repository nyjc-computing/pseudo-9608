from typing import Iterable, Mapping, Callable as function

from . import builtin
from .lang import Frame
from .system import system

from . import scanner, parser
from .resolver import Resolver
from .interpreter import Interpreter



__version__ = '0.2.1'



def error(lines: Iterable, err: builtin.PseudoError) -> None:
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
    def __init__(self) -> None:
        self.handlers = {
            'output': print,
            'input': input,
        }

    def registerHandlers(self, **kwargs: Mapping[str, function]) -> None:
        for key, handler in kwargs.items():
            if key not in self.handlers:
                raise KeyError(f"Invalid handler key {repr(key)}")
            self.handlers[key] = handler

    def runFile(self, srcfile: str) -> "Frame":
        with open(srcfile, 'r') as f:
            src = f.read()
        return self.run(src)
    
    def run(self, src: str) -> "Frame":
        globalFrame = Frame(typesys=system.types, outer=system)
        result = {
            'lines': None,
            'frame': globalFrame,
            'error': None,
        }

        # Parsing
        try:
            tokens, lines = scanner.scan(src)
            result['lines'] = lines
            statements = parser.parse(tokens)
        except builtin.ParseError as err:
            result['error'] = err
            return result
        except Exception as err:
            breakpoint()

        # Resolving
        resolver = Resolver(globalFrame, statements)
        try:
            resolver.inspect()
        except builtin.LogicError as err:
            result['error'] = err
            return result
        except Exception as err:
            breakpoint()

        # Interpreting
        interpreter = Interpreter(globalFrame, statements)
        interpreter.registerOutputHandler(self.handlers['output'])
        try:
            interpreter.interpret()
        except builtin.RuntimeError as err:
            result['error'] = err
        except Exception as err:
            breakpoint()
        finally:
            return result
