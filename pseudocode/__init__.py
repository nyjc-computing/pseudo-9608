from typing import Optional
from typing import Iterable, List, MutableMapping
from typing import TypedDict, Callable as function
import os, sys, traceback

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



__version__ = '0.4.0'
VERSION = f"Pseudo {__version__}"
HELP = """
usage: pseudo [option] ... file
Options and arguments:
-h     : print this help message and exit (also --help)
file   : program read from script file
""".strip()



# https://stackoverflow.com/a/66416364/318186
def printException() -> None:
    etype, value, tb = sys.exc_info()
    info, error = traceback.format_exception(etype, value, tb)[-2:]
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



# Error codes
# https://gist.github.com/bojanrajkovic/831993

def main():
    # Argument handling
    if len(sys.argv) == 1:
        print("No argument provided.")  # Unhandled error
        print("Try `pseudo -h' for more information.")
        sys.exit(64)  # command line usage error
    if len(sys.argv) > 1:
        if sys.argv[1] == '-h':
            print(HELP)
            sys.exit(0)
        elif sys.argv[1].startswith('-'):
            print(f"Unknown option: {sys.argv[1]}")
            print("Try `pseudo -h' for more information.")    
            sys.exit(64)  # command line usage error

    # File checks
    srcfile = sys.argv[1]
    if not os.path.isfile(srcfile):
        print(f"pseudo: can't open file {srcfile!r}")
        sys.exit(65)  # data format error
    try:
        with open(srcfile, 'r') as f:
            f.readline()
    except Exception as error:
        print(f"pseudo: can't open file {srcfile!r}:")
        print(error)
        sys.exit(65)  # data format error

    pseudo = Pseudo()
    result = pseudo.runFile(srcfile)
    lines = result['lines']
    err = result['error']
    if err:
        if type(err) in (builtin.ParseError, builtin.LogicError):
            error(lines, err)
            sys.exit(65)  # data format error
        elif type(err) in (RuntimeError,):
            error(lines, err)
            sys.exit(70)  # internal software error
