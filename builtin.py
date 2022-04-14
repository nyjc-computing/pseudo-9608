# Errors

class ParseError(Exception): pass



# Token types

KEYWORDS = [
    'DECLARE', 'OUTPUT',
    'WHILE', 'DO', 'ENDWHILE',
    'CASE', 'OF', 'OTHERWISE', 'ENDCASE',
]

TYPES = ['INTEGER', 'STRING']

OPERATORS = [
    '+', '-', '/', '*', '=',
    '<', '<-', '<=', '>', '>=', '<>',
]

SYMBOLS = [':']



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



# Classifier

operators = {
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
