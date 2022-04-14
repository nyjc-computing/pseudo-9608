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



# Precedence parsers

# Expr: {'left': ..., 'oper': ..., 'right': ...}

def value(tokens):
    # A single value or grouping
    pass

def muldiv(tokens):
    # *, /
    pass

def addsub(tokens):
    # +, -
    pass

def comparison(tokens):
    # <, <=, >, >=
    pass

def equality(tokens):
    # <>, =
    pass

def expression(tokens):
    # An entire expression
    pass