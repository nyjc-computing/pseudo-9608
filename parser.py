from builtin import ParseError, get, lte, add
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
        frame = None
        name = identifier(tokens)
        oper = {'type': 'symbol', 'word': '', 'value': get}
        return makeExpr(frame, oper, name)
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

def inputStmt(tokens):
    return stmt

def declareStmt(tokens):
    name = identifier(tokens)
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
    name = identifier(tokens)
    expectElseError(tokens, '<-')
    expr = expression(tokens)
    expectElseError(tokens, '\n')
    stmt = {
        'rule': 'assign',
        'name': name,
        'expr': expr,
    }
    return stmt

def caseStmt(tokens):
    expectElseError(tokens, 'OF')
    cond = value(tokens)
    expectElseError(tokens, '\n')
    stmts = {}
    while not atEnd(tokens) and check(tokens)['word'] in ('OTHERWISE', 'ENDCASE'):
        val = value(tokens)['value']
        expectElseError(tokens, ':')
        stmt = statement(tokens)
        stmts[val] = stmt
    fallback = None
    if match(tokens, 'OTHERWISE'):
        fallback = statement(tokens)
    expectElseError(tokens, 'ENDCASE')
    expectElseError(tokens, '\n')
    stmt = {
        'rule': 'case',
        'cond': cond,
        'stmts': stmts,
        'fallback': fallback,
    }
    return stmt

def ifStmt(tokens):
    cond = expression(tokens)
    if match(tokens, '\n'):
        pass  # optional line break
    expectElseError(tokens, 'THEN')
    expectElseError(tokens, '\n')
    stmts = {}
    true = []
    while not atEnd(tokens) and check(tokens)['word'] in ('ELSE', 'ENDIF'):
        true += [statement(tokens)]
    stmts[True] = true
    fallback = None
    if match(tokens, 'ELSE'):
        expectElseError(tokens, '\n')
        false = []
        while not atEnd(tokens) and check(tokens)['word'] in ('ENDIF',):
            false += [statement(tokens)]
        fallback = false
    expectElseError(tokens, 'ENDIF')
    expectElseError(tokens, '\n')
    stmt = {
        'rule': 'if',
        'cond': cond,
        'stmts': stmts,
        'fallback': fallback,
    }
    return stmt

def whileStmt(tokens):
    cond = expression(tokens)
    expectElseError(tokens, 'DO')
    expectElseError(tokens, '\n')
    stmts = []
    while not atEnd(tokens) and check(tokens)['word'] not in ('ENDWHILE',):
        stmts += [statement(tokens)]
    expectElseError(tokens, 'ENDWHILE')
    expectElseError(tokens, '\n')
    stmt = {
        'rule': 'while',
        'init': None,
        'cond': cond,
        'stmts': stmts,
    }
    return stmt

def repeatStmt(tokens):
    expectElseError(tokens, '\n')
    stmts = []
    while not atEnd(tokens) and check(tokens)['word'] not in ('UNTIL',):
        stmts += [statement(tokens)]
    expectElseError(tokens, 'UNTIL')
    cond = expression(tokens)
    expectElseError(tokens, '\n')
    stmt = {
        'rule': 'repeat',
        'init': None,
        'cond': cond,
        'stmts': stmts
    }
    return stmt

def forStmt(tokens):
    name = identifier(tokens)
    expectElseError(tokens, '<-')
    start = value(tokens)
    expectElseError(tokens, 'TO')
    end = value(tokens)
    step = {
        'type': 'integer',
        'word': '1',
        'value': 1,
    }
    if match(tokens, 'STEP'):
        step = value(tokens)
    expectElseError(tokens, '\n')
    stmts = []
    while not atEnd(tokens) and check(tokens)['word'] not in ('ENDFOR',):
        stmts += [statement(tokens)]
    expectElseError(tokens, 'ENDFOR')
    expectElseError(tokens, '\n')
    # Initialise name to start
    init = assignStmt([
        name,
        {'type': 'keyword', 'word': '<-', 'value': None},
        start,
        {'type': 'keyword', 'word': '\n', 'value': None},
    ])
    # Generate loop cond
    cond = expression([
        name,
        {'type': 'symbol', 'word': '<=', 'value': lte},
        end,
        {'type': 'keyword', 'word': '\n', 'value': None},
    ])
    # Add increment statement
    incr = assignStmt([
        name,
        {'type': 'keyword', 'word': '<-', 'value': None},
        name,
        {'type': 'keyword', 'word': '+', 'value': add},
        step,
        {'type': 'keyword', 'word': '\n', 'value': None},
    ])
    stmt = {
        'rule': 'while',
        'init': init,
        'cond': cond,
        'stmts': stmts + [incr],
    }
    return stmt

def statement(tokens):
    if match(tokens, 'OUTPUT'):
        return outputStmt(tokens)
    if match(tokens, 'INPUT'):
        return inputStmt(tokens)
    if match(tokens, 'DECLARE'):
        return declareStmt(tokens)
    if match(tokens, 'CASE'):
        return caseStmt(tokens)
    if match(tokens, 'IF'):
        return ifStmt(tokens)
    if match(tokens, 'WHILE'):
        return whileStmt(tokens)
    if match(tokens, 'REPEAT'):
        return repeatStmt(tokens)
    if match(tokens, 'FOR'):
        return forStmt(tokens)
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