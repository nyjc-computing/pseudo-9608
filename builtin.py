# Errors

class PseudoError(Exception):
    """Base exception class for all Psuedo errors."""
    def __init__(self, msg, token, line=None):
        super().__init__(msg)
        self.token = token
        if line is not None:
            self.line = line
        else:
            self.line = token['line']

class ParseError(PseudoError):
    """Custom error raised by scanner and parser."""

class RuntimeError(Exception):
    """Custom error raised by interpreter."""

class LogicError(Exception):
    """Custom error raised by resolver."""



# Operators

def add(x, y):
    return x + y

def sub(x, y):
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

def get(frame, name):
    return frame[name]['value']

def call(func, args):
    return func, args



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
    'BYREF', 'BYVALUE',
]

TYPES = ['INTEGER', 'STRING']

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
}

SYMBOLS = [',', ':']
