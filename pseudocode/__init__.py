from typing import Optional
from typing import Iterable, List, MutableMapping
from typing import TypedDict, Callable as function
import os, sys

import logging
logging.basicConfig(
    filename='pseudo.log',
    filemode='w',
    format='%(name)s - %(levelname)s - %(message)s',
)

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



__version__ = '0.4.1'
VERSION = f"Pseudo {__version__}"
HELP = """
usage: pseudo [option] ... file
Options and arguments:
-h     : print this help message and exit (also --help)
file   : program read from script file
""".strip()



def logException(msg="Unexpected error has occurred") -> None:
    # https://docs.python.org/3.8/library/logging.html#logging.Logger.exception
    logging.exception(msg)
    print("Pseudo ERROR: " + msg)
    print("""
The details of this error have been logged in pseudo.log.

Please help us detect and fix bugs in pseudo by reporting this error at
https://github.com/nyjc-computing/pseudo-9608/issues/new/choose.
""".strip())

def report(lines: Iterable[str], err: builtin.PseudoError) -> None:
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
        self.frame: Frame = Frame(
            typesys=sysFrame.types,
            outer=sysFrame
        )
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
        result: Result = {
            'lines': [],
            'frame': self.frame,
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
            logException()
            return result

        # Resolving
        resolver = Resolver(self.frame, statements)
        try:
            resolver.inspect()
        except builtin.LogicError as err:
            result['error'] = err
            return result
        except Exception:
            logException()
            return result

        # Interpreting
        interpreter = Interpreter(self.frame, statements)
        interpreter.registerOutputHandler(self.handlers['output'])
        try:
            interpreter.interpret()
        except builtin.RuntimeError as err:
            result['error'] = err
        except Exception:
            logException()
        finally:
            return result



# Error codes
# https://gist.github.com/bojanrajkovic/831993

def main():
    # REPL mode
    if len(sys.argv) == 1:
        pseudo = Pseudo()
        print(VERSION)
        while True:
            line = input('### ')
            result = pseudo.run(line)
            if not result['error']:
                continue
            report(result['lines'], result['error'])

    # Argument handling
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

    # Script mode
    pseudo = Pseudo()
    result = pseudo.runFile(srcfile)
    if not result['error']:
        sys.exit(0)

    # Error handling
    report(result['lines'], result['error'])
    if type(result['error']) in (builtin.ParseError, builtin.LogicError):
        sys.exit(65)  # data format error
    elif type(result['error']) in (RuntimeError,):
        sys.exit(70)  # internal software error
