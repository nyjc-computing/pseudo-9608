# Errors

class ParseError(Exception):
    def __init__(self, msg, token):
        super().__init__(msg)
        self.token = token
        self.line = token['line']

class RuntimeError(Exception):
    def __init__(self, msg, token):
        super().__init__(msg)
        self.token = token
        self.line = token['line']

class LogicError(Exception):
    def __init__(self, msg, token):
        super().__init__(msg)
        self.token = token
        self.line = token['line']



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
