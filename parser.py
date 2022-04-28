from builtin import TYPES
from builtin import ParseError
from builtin import get, lte, add, call
from scanner import makeToken
from lang import Literal, Name, Unary, Binary, Get, Call



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

def makeLiteralExpr(type, value):
    return Literal(type, value)

def makeNameExpr(name):
    return Name(name)

def makeUnaryExpr(oper, right):
    return Unary(oper, right)

def makeBinaryExpr(left, oper, right):
    return Binary(left, oper, right)

def makeGetExpr(frame, name):
    return Get(frame, name)

def makeCallExpr(callable, args):
    return Call(callable, args)

def expectElseError(tokens, word, addmsg=None):
    if check(tokens)['word'] == word:
        consume(tokens)
        return True
    msg = f"Expected {addmsg}" if addmsg else "Expected"
    raise ParseError(msg, check(tokens))

def match(tokens, *words):
    if check(tokens)['word'] in words:
        consume(tokens)
        return True
    return False

# Precedence parsers

def identifier(tokens):
    token = check(tokens)
    if token['type'] == 'name':
        return Name(token['word'])
    else:
        raise ParseError(f"Expected variable name", token)

def value(tokens):
    token = check(tokens)
    # A single value
    if token['type'] in ['integer', 'string']:
        expr = makeLiteralExpr(token['type'], token['value'])
        return expr
    #  A grouping
    elif match(tokens, '('):
        expr = expression(tokens)
        expectElseError(tokens, ')', "after '('")
        return expr        
    elif token['type'] == 'name':
        frame = None
        name = identifier(tokens)
        args = []
        expr = makeGetExpr(frame, name)
        # Function call
        if match(tokens, '('):
            arg = expression(tokens)
            args += [arg]
            while match(tokens, ','):
                arg = expression(tokens)
                args += [arg]
            expectElseError(tokens, ')', "after '('")
            expr = makeCallExpr(expr, args)
        return expr
    else:
        raise ParseError("Unexpected token", token)

def muldiv(tokens):
    # *, /
    expr = value(tokens)
    while not atEnd(tokens) and check(tokens)['word'] in ('*', '/'):
        oper = consume(tokens)
        right = value(tokens)
        expr = makeBinaryExpr(expr, oper['value'], right)
    return expr

def addsub(tokens):
    expr = muldiv(tokens)
    while not atEnd(tokens) and check(tokens)['word'] in ('+', '-'):
        oper = consume(tokens)
        right = muldiv(tokens)
        expr = makeBinaryExpr(expr, oper['value'], right)
    return expr

def comparison(tokens):
    # <, <=, >, >=
    expr = addsub(tokens)
    while not atEnd(tokens) and check(tokens)['word'] in ('<', '<=', '>', '>='):
        oper = consume(tokens)
        right = addsub(tokens)
        expr = makeBinaryExpr(expr, oper['value'], right)
    return expr

def equality(tokens):
    # <>, =
    expr = comparison(tokens)
    while not atEnd(tokens) and check(tokens)['word'] in ('<>', '='):
        oper = consume(tokens)
        right = comparison(tokens)
        expr = makeBinaryExpr(expr, oper['value'], right)
    return expr

def expression(tokens):
    expr = equality(tokens)
    return expr

# Statement parsers

def outputStmt(tokens):
    exprs = [expression(tokens)]
    while match(tokens, ','):
        exprs += [expression(tokens)]
    expectElseError(tokens, '\n', "after statement")
    stmt = {
        'rule': 'output',
        'exprs': exprs,
    }
    return stmt

def inputStmt(tokens):
    name = identifier(tokens)
    expectElseError(tokens, '\n', "after statement")
    stmt = {
        'rule': 'input',
        'name': name,
    }
    return stmt

def declare(tokens):
    name = identifier(tokens)
    expectElseError(tokens, ':', "after name")
    typetoken = consume(tokens)
    if typetoken['word'] not in TYPES:
        raise ParseError("Invalid type", typetoken)
    var = {
        'name': name,
        'type': typetoken,
    }
    return var
    
def declareStmt(tokens):
    var = declare(tokens)
    expectElseError(tokens, '\n', "after statement")
    stmt = {
        'rule': 'declare',
        'name': var['name'],
        'type': var['type'],
    }
    return stmt

def assignStmt(tokens):
    name = identifier(tokens)
    expectElseError(tokens, '<-', "after name")
    expr = expression(tokens)
    expectElseError(tokens, '\n', "after statement")
    stmt = {
        'rule': 'assign',
        'name': name,
        'expr': expr,
    }
    return stmt

def caseStmt(tokens):
    expectElseError(tokens, 'OF', "after CASE")
    cond = value(tokens)
    expectElseError(tokens, '\n', "after CASE OF")
    stmts = {}
    while not atEnd(tokens) and check(tokens)['word'] in ('OTHERWISE', 'ENDCASE'):
        val = value(tokens).evaluate()
        expectElseError(tokens, ':', "after CASE value")
        stmt = statement(tokens)
        stmts[val] = stmt
    fallback = None
    if match(tokens, 'OTHERWISE'):
        fallback = statement(tokens)
    expectElseError(tokens, 'ENDCASE', "at end of CASE")
    expectElseError(tokens, '\n', "after ENDCASE")
    stmt = {
        'rule': 'case',
        'cond': cond,
        'stmts': stmts,
        'fallback': fallback,
    }
    return stmt

def ifStmt(tokens):
    cond = expression(tokens)
    match(tokens, '\n')  # optional line break
    expectElseError(tokens, 'THEN', "after IF")
    expectElseError(tokens, '\n', "after THEN")
    stmts = {}
    true = []
    while not atEnd(tokens) and check(tokens)['word'] in ('ELSE', 'ENDIF'):
        true += [statement(tokens)]
    stmts[True] = true
    fallback = None
    if match(tokens, 'ELSE'):
        expectElseError(tokens, '\n', "after ELSE")
        false = []
        while not atEnd(tokens) and check(tokens)['word'] in ('ENDIF',):
            false += [statement(tokens)]
        fallback = false
    expectElseError(tokens, 'ENDIF', "at end of IF")
    expectElseError(tokens, '\n', "after statement")
    stmt = {
        'rule': 'if',
        'cond': cond,
        'stmts': stmts,
        'fallback': fallback,
    }
    return stmt

def whileStmt(tokens):
    cond = expression(tokens)
    expectElseError(tokens, 'DO', "after WHILE condition")
    expectElseError(tokens, '\n', "after DO")
    stmts = []
    while not atEnd(tokens) and not match(tokens, 'ENDWHILE'):
        stmts += [statement(tokens)]
    expectElseError(tokens, '\n', "after ENDWHILE")
    stmt = {
        'rule': 'while',
        'init': None,
        'cond': cond,
        'stmts': stmts,
    }
    return stmt

def repeatStmt(tokens):
    expectElseError(tokens, '\n', "after REPEAT")
    stmts = []
    while not atEnd(tokens) and not match(tokens, 'UNTIL'):
        stmts += [statement(tokens)]
    cond = expression(tokens)
    expectElseError(tokens, '\n', "at end of UNTIL")
    stmt = {
        'rule': 'repeat',
        'init': None,
        'cond': cond,
        'stmts': stmts
    }
    return stmt

def forStmt(tokens):
    name = identifier(tokens)
    expectElseError(tokens, '<-', "after name")
    start = value(tokens)
    expectElseError(tokens, 'TO', "after start value")
    end = value(tokens)
    step = makeLiteralExpr('INTEGER', 1)
    if match(tokens, 'STEP'):
        step = value(tokens)
    expectElseError(tokens, '\n', "at end of FOR")
    stmts = []
    while not atEnd(tokens) and not match(tokens, 'ENDFOR'):
        stmts += [statement(tokens)]
    expectElseError(tokens, 'ENDFOR', "at end of FOR")
    expectElseError(tokens, '\n', "after ENDFOR")
    # Initialise name to start
    init = assignStmt([
        name,
        makeToken(name['line'], name['col'], 'keyword', '<-', None),
        start,
        makeToken(end['line'], end['col'], 'keyword', '\n', None),
    ])
    # Generate loop cond
    cond = expression([
        name,
        makeToken(name['line'], name['col'], 'symbol', '<=', lte),
        end,
        makeToken(start['line'], start['col'], 'keyword', '\n', None),
    ])
    # Add increment statement
    incr = assignStmt([
        name,
        makeToken(name['line'], name['col'], 'keyword', '<-', None),
        name,
        makeToken(name['line'], name['col'], 'keyword', '+', add),
        step,
        makeToken(end['line'], name['col'], 'keyword', '\n', None),
    ])
    stmt = {
        'rule': 'while',
        'init': init,
        'cond': cond,
        'stmts': stmts + [incr],
    }
    return stmt

def procedureStmt(tokens):
    name = identifier(tokens)
    params = []
    if match(tokens, '('):
        passby = makeToken(name['line'], name['col'], 'keyword', 'BYVALUE', None)
        if check(tokens)['word'] in ('BYVALUE', 'BYREF'):
            passby = consume(tokens)
        var = declare(tokens)
        params += [var]
        while match(tokens, ','):
            var = declare(tokens)
            params += [var]
        expectElseError(tokens, ')', "at end of parameters")
    expectElseError(tokens, '\n', "after parameters")
    stmts = []
    while not atEnd(tokens) and not match(tokens, 'ENDPROCEDURE'):
        stmts += [statement(tokens)]
    expectElseError(tokens, 'ENDPROCEDURE', "at end of PROCEDURE")
    expectElseError(tokens, '\n', "after ENDPROCEDURE")
    stmt = {
        'rule': 'procedure',
        'name': name,
        'passby': passby,
        'params': params,
        'stmts': stmts,
    }
    return stmt

def callStmt(tokens):
    name = value(tokens)
    args = []
    if match(tokens, '('):
        arg = expression(tokens)
        args += [arg]
        while match(tokens, ','):
            arg = expression(tokens)
            args += [arg]
        expectElseError(tokens, ')', "after arguments")
    expectElseError(tokens, '\n', "at end of CALL")
    stmt = {
        'rule': 'call',
        'name': name,
        'args': args,
    }
    return stmt

def functionStmt(tokens):
    name = identifier(tokens)
    params = []
    if match(tokens, '('):
        passby = makeToken(name['line'], name['col'], 'keyword', 'BYVALUE', None)
        var = declare(tokens)
        params += [var]
        while match(tokens, ','):
            var = declare(tokens)
            params += [var]
        expectElseError(tokens, ')', "at end of parameters")
    expectElseError(tokens, 'RETURNS', "after parameters")
    typetoken = consume(tokens)
    if typetoken['word'] not in TYPES:
        raise ParseError("Invalid type", typetoken)
    expectElseError(tokens, '\n', "at end of FUNCTION")
    stmts = []
    while not atEnd(tokens) and not match(tokens, 'ENDFUNCTION'):
        stmts += [statement(tokens)]
    expectElseError(tokens, '\n', "after ENDFUNCTION")
    stmt = {
        'rule': 'function',
        'name': name,
        'passby': passby,
        'params': params,
        'stmts': stmts,
        'returns': typetoken,
    }
    return stmt

def returnStmt(tokens):
    expr = expression(tokens)
    expectElseError(tokens, '\n', "at end of RETURN")
    stmt = {
        'rule': 'return',
        'expr': expr,
    }
    return stmt

def openfileStmt(tokens):
    name = value(tokens)
    expectElseError(tokens, 'FOR', "after file identifier")
    if check(tokens)['word'] not in ('READ', 'WRITE', 'APPEND'):
        raise ParseError("Invalid file mode", check(tokens))
    mode = consume(tokens)
    expectElseError(tokens, '\n')
    stmt = {
        'rule': 'file',
        'action': 'open',
        'name': name,
        'mode': mode,
        'data': None,
    }
    return stmt

def readfileStmt(tokens):
    name = value(tokens)
    expectElseError(tokens, ',', "after file identifier")
    data = identifier(tokens)
    expectElseError(tokens, '\n')
    stmt = {
        'rule': 'file',
        'action': 'read',
        'name': name,
        'mode': None,
        'data': data,
    }
    return stmt

def writefileStmt(tokens):
    name = value(tokens)
    expectElseError(tokens, ',', "after file identifier")
    data = expression(tokens)
    expectElseError(tokens, '\n')
    stmt = {
        'rule': 'file',
        'action': 'write',
        'name': name,
        'mode': None,
        'data': data,
    }
    return stmt

def closefileStmt(tokens):
    name = value(tokens)
    expectElseError(tokens, '\n')
    stmt = {
        'rule': 'file',
        'action': 'close',
        'name': name,
        'mode': None,
        'data': None,
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
    if match(tokens, 'PROCEDURE'):
        return procedureStmt(tokens)
    if match(tokens, 'CALL'):
        return callStmt(tokens)
    if match(tokens, 'FUNCTION'):
        return functionStmt(tokens)
    if match(tokens, 'RETURN'):
        return returnStmt(tokens)
    if match(tokens, 'OPENFILE'):
        return openfileStmt(tokens)
    if match(tokens, 'READFILE'):
        return readfileStmt(tokens)
    if match(tokens, 'WRITEFILE'):
        return writefileStmt(tokens)
    if match(tokens, 'CLOSEFILE'):
        return closefileStmt(tokens)
    elif check(tokens)['type'] == 'name':
        return assignStmt(tokens)
    else:
        raise ParseError("Unrecognised token", check(tokens))

# Main parsing loop

def parse(tokens):
    lastline = tokens[-1]['line']
    tokens += [makeToken(lastline, 0, 'EOF', "", None)]
    statements = []
    while not atEnd(tokens):
        while match(tokens, '\n'):
            pass
        statements += [statement(tokens)]
        while match(tokens, '\n'):
            pass
    return statements
