from builtin import ParseError
from scanner import makeToken



# Helper functions

def atEnd(tokens):
    if check(tokens)['type'] == 'EOF':
        return True
    return False

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

def identifier(tokens):
    token = check(tokens)
    if token['type'] == 'name':
        return consume(tokens)
    else:
        raise ParseError(f"Expected variable name, got {repr(token['word'])}")

def value(tokens):
    token = check(tokens)
    # A single value
    if token['type'] in ['integer', 'string']:
        return consume(tokens)
    #  A grouping
    elif token['word'] == '(':
        consume(tokens)  # (
        expr = expression()
        if not check(tokens)['word'] == ')':
            raise ParseError(f"')' expected at end of expression")
        consume(tokens)  # )
        return expr        
    elif token['type'] == 'name':
        return consume(tokens)
    else:
        raise ParseError(f"Unexpected token {repr(token['word'])}")

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
    expr = equality(tokens)
    return expr

# Statement parsing helpers

def expectElseError(tokens, word):
    if check(tokens)['word'] == word:
        consume(tokens)
        return True
    raise ParseError(f"Expected {word}")

def match(tokens, *words):
    if check(tokens)['word'] in words:
        consume(tokens)
        return True
    return False

# Statement parsers

def outputStmt(tokens):
    exprs = [expression(tokens)]
    while match(tokens, ','):
        exprs += [expression(tokens)]
    expectElseError(tokens, '\n')
    stmt = {
        'rule': 'output',
        'exprs': exprs,
    }
    return stmt

def declareStmt(tokens):
    name = value(tokens)
    expectElseError(tokens, ':')
    typetoken = consume(tokens)
    expectElseError(tokens, '\n')
    stmt = {
        'rule': 'declare',
        'name': name,
        'type': typetoken,
    }
    return stmt

def assignStmt(tokens):
    name = value(tokens)
    expectElseError(tokens, '<-')
    expr = expression(tokens)
    stmt = {
        'rule': 'assign',
        'name': name,
        'expr': expr,
    }
    return stmt

def statement(tokens):
    if match(tokens, 'OUTPUT'):
        return outputStmt(tokens)
    if match(tokens, 'DECLARE'):
        return declareStmt(tokens)
    elif check(tokens)['type'] == 'name':
        return assignStmt(tokens)
    else:
        raise ParseError(f"Unrecognised token {check(tokens)}")

# Main parsing loop

def parse(tokens):
    tokens.append(makeToken('EOF', "", None))
    statements = []
    while not atEnd(tokens):
        while match(tokens, '\n'):
            pass
        statements += [statement(tokens)]
        while match(tokens, '\n'):
            pass
    return statements