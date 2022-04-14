from builtin import ParseError



# Helper functions

def atEnd(tokens):
    return (len(tokens) == 0)

def check(tokens):
    return tokens[0]

def consume(tokens):
    token = tokens.pop(0)
    return token

def makeExpr(left, oper, right):
    return {
        'left': left,
        'oper': oper,
        'right': right,
    }

# Precedence parsers

# Expr: {'left': ..., 'oper': ..., 'right': ...}

def value(tokens):
    # A single value
    if check(tokens)['type'] in ['integer', 'string']:
        return consume(tokens)
    #  A grouping
    elif check(tokens)['word'] == '(':
        consume(tokens)  # (
        expr = expression()
        if not check(tokens)['word'] == ')':
            raise ParseError(f"')' expected at end of expression")
        consume(tokens)  # )
        return expr        

def muldiv(tokens):
    # *, /
    expr = value(tokens)
    while check(tokens)['word'] in ['*', '/']:
        oper = consume(tokens)
        right = value(tokens)
        expr = makeExpr(expr, oper, right)
    return expr

def addsub(tokens):
    expr = muldiv(tokens)
    while check(tokens)['word'] in ['+', '-']:
        oper = consume(tokens)
        right = muldiv(tokens)
        expr = makeExpr(expr, oper, right)
    return expr

def comparison(tokens):
    # <, <=, >, >=
    expr = addsub(tokens)
    while check(tokens)['word'] in ['<', '<=', '>', '>=']:
        oper = consume(tokens)
        right = addsub(tokens)
        expr = makeExpr(expr, oper, right)
    return expr

def equality(tokens):
    # <>, =
    expr = comparison(tokens)
    while check(tokens)['word'] in ['<>', '=']:
        oper = consume(tokens)
        right = comparison(tokens)
        expr = makeExpr(expr, oper, right)
    return expr

def expression(tokens):
    # An entire expression
    expr = equality(tokens)
    return expr

# Statement parsers

def outputStmt(tokens):
    return stmt

def statement(tokens):
    if check(tokens)['word'] == 'OUTPUT':
        consume(tokens)
        stmt = outputStmt(tokens)
    else:
        raise ParseError(f"Unrecognised token {check(tokens)}")
    return stmt