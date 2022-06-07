"""Keywords, operators, and errors supported in pseudo-9608.
"""

# Errors

class PseudoError(Exception):
    """Base exception class for all Pseudo errors."""
    
    def __init__(self, msg, token, line=None) -> None:
        super().__init__(msg)
        self.token = token
        self.line = line
        self.column = None
        if token:
            self.line = token.line
            self.column = token.column
        else:
            self.line = None

    def msg(self) -> str:
        return self.args[0]

    def report(self) -> str:
        """Returns the contained token and message as a formatted string"""
        return f"{repr(self.token)}: {self.msg()}"

class ParseError(PseudoError):
    """Custom error raised by scanner and parser."""

class RuntimeError(PseudoError):
    """Custom error raised by interpreter."""

class LogicError(PseudoError):
    """Custom error raised by resolver."""



# Operators
# These operators are used internally by the interpreter.
def add(x, y):
    return x + y

def sub(x, y=None):
    """Sub is overloaded to function as sub() and neg()"""
    if y is None:
        return -x
    return x - y

def mul(x, y):
    return x * y

def div(x, y):
    return x / y

def lt(x, y):
    return x < y

def lte(x, y):
    return x <= y

def gt(x, y):
    return x > y

def gte(x, y):
    return x >= y

def ne(x, y):
    return x != y

def eq(x, y):
    return x == y

def AND(x, y):
    return x and y

def OR(x, y):
    return x or y

def NOT(x):
    return not x



# Token types

KEYWORDS = [
    'DECLARE', '<-',
    'OUTPUT', 'INPUT',
    'CASE', 'OF', 'OTHERWISE', 'ENDCASE',
    'IF', 'THEN', 'ELSE', 'ENDIF',
    'WHILE', 'DO', 'ENDWHILE',
    'REPEAT', 'UNTIL',
    'FOR', 'TO', 'STEP', 'ENDFOR',
    'PROCEDURE', 'ENDPROCEDURE', 'CALL',
    'FUNCTION', 'RETURNS', 'ENDFUNCTION', 'RETURN',
    'TYPE', 'ENDTYPE',
    'BYREF', 'BYVALUE',
    'OPENFILE', 'READ', 'WRITE', 'APPEND',
    'READFILE', 'WRITEFILE', 'CLOSEFILE',
]

VALUES = ['NULL', 'TRUE', 'FALSE']

NUMERIC = ('INTEGER', 'REAL')

EQUATABLE = ('BOOLEAN',) + NUMERIC

LITERAL = EQUATABLE + ('STRING',)

TYPES = LITERAL + ('FILE', 'ARRAY', 'NULL')

NULL = object()

OPERATORS = {
    '+': add,
    '-': sub,
    '*': mul,
    '/': div,
    '<': lt,
    '<=': lte,
    '>': gt,
    '>=': gte,
    '<>': ne,
    '=': eq,
    'AND': AND,
    'OR': OR,
    'NOT': NOT,
}

SYM_SINGLE = '()[]:,.'

SYM_MULTI = '+-/*=<>'

SYMBOLS = SYM_SINGLE + SYM_MULTI