from builtin import TYPES, NULL
from builtin import ParseError
from builtin import lte, add
from scanner import makeToken
from lang import Literal, Name, Unary, Binary, Get, Call
from lang import ExprStmt, Output, Input, Declare, Assign
from lang import Conditional, Loop, ProcFunc, Return, FileAction



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

def makeExpr(
    *,
    type=None, value=None,
    frame=None, name=None, expr=None,
    left=None, oper=None, right=None,
    callable=None, args=None,
    token=None,
):
    if name is not None:
        if frame is not None:
            return Get(frame, name, token=token)
        elif expr is not None:
            return Assign(name, expr, token=token)
        else:
            return Name(name, token=token)
    if type is not None and value is not None:
        return Literal(type, value, token=token)
    if oper is not None and right is not None:
        if left is not None:
            return Binary(left, oper, right, token=token)
        else:
            return Unary(oper, right, token=token)
    if callable is not None and args is not None:
        return Call(callable, args, token=token)
    raise ValueError("Could not find valid keyword argument combination")

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
    token = consume(tokens)
    if token['type'] == 'name':
        return makeExpr(name=token['word'], token=token)
    else:
        raise ParseError(f"Expected variable name", token)

def value(tokens):
    token = check(tokens)
    # A single value
    if token['type'] in ['INTEGER', 'STRING']:
        expr = makeExpr(
            type=token['type'],
            value=token['value'],
            token=token,
        )
        consume(tokens)
        return expr
    #  A grouping
    elif match(tokens, '('):
        expr = expression(tokens)
        expectElseError(tokens, ')', "after '('")
        return expr        
    elif token['type'] == 'name':
        name = identifier(tokens)
        expr = makeExpr(
            frame=NULL,
            name=name.name,
            token=name,
        )
        # Function call
        args = []
        if match(tokens, '('):
            arg = expression(tokens)
            args += [arg]
            while match(tokens, ','):
                arg = expression(tokens)
                args += [arg]
            expectElseError(tokens, ')', "after '('")
            expr = makeExpr(
                callable=expr,
                args=args,
                token=name,
            )
        return expr
    else:
        raise ParseError("Unexpected token", token)

def muldiv(tokens):
    # *, /
    expr = value(tokens)
    while not atEnd(tokens) and check(tokens)['word'] in ('*', '/'):
        oper = consume(tokens)
        right = value(tokens)
        expr = makeExpr(
            left=expr,
            oper=oper['value'],
            right=right,
            token=token,
        )
    return expr

def addsub(tokens):
    expr = muldiv(tokens)
    while not atEnd(tokens) and check(tokens)['word'] in ('+', '-'):
        oper = consume(tokens)
        right = muldiv(tokens)
        expr = makeExpr(
            left=expr,
            oper=oper['value'],
            right=right,
            token=token,
        )
    return expr

def comparison(tokens):
    # <, <=, >, >=
    expr = addsub(tokens)
    while not atEnd(tokens) and check(tokens)['word'] in ('<', '<=', '>', '>='):
        oper = consume(tokens)
        right = addsub(tokens)
        expr = makeExpr(
            left=expr,
            oper=oper['value'],
            right=right,
            token=token,
        )
    return expr

def equality(tokens):
    # <>, =
    expr = comparison(tokens)
    while not atEnd(tokens) and check(tokens)['word'] in ('<>', '='):
        oper = consume(tokens)
        right = comparison(tokens)
        expr = makeExpr(
            left=expr,
            oper=oper['value'],
            right=right,
            token=token,
        )
    return expr

def expression(tokens):
    expr = equality(tokens)
    return expr

def assignment(tokens):
    name = identifier(tokens)
    expectElseError(tokens, '<-', "after name")
    expr = expression(tokens)
    return makeExpr(name=name.name, expr=expr, token=name)

# Statement parsers

def outputStmt(tokens):
    exprs = [expression(tokens)]
    while match(tokens, ','):
        exprs += [expression(tokens)]
    expectElseError(tokens, '\n', "after statement")
    return Output('output', exprs)

def inputStmt(tokens):
    name = identifier(tokens)
    expectElseError(tokens, '\n', "after statement")
    return Input('input', name)

def declare(tokens):
    name = identifier(tokens).name
    expectElseError(tokens, ':', "after name")
    typetoken = consume(tokens)
    if typetoken['word'] not in TYPES:
        raise ParseError("Invalid type", typetoken)
    return Declare(name, typetoken['word'])
    
def declareStmt(tokens):
    expr = declare(tokens)
    expectElseError(tokens, '\n', "after statement")
    return ExprStmt('declare', expr)

def assignStmt(tokens):
    name = identifier(tokens).name
    expectElseError(tokens, '<-', "after name")
    expr = expression(tokens)
    expectElseError(tokens, '\n', "after statement")
    return Assign('assign', name, expr)

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
    return Conditional('case', cond, stmts, fallback)

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
    return Conditional('if', cond, stmts, fallback)

def whileStmt(tokens):
    cond = expression(tokens)
    expectElseError(tokens, 'DO', "after WHILE condition")
    expectElseError(tokens, '\n', "after DO")
    stmts = []
    while not atEnd(tokens) and not match(tokens, 'ENDWHILE'):
        stmts += [statement(tokens)]
    expectElseError(tokens, '\n', "after ENDWHILE")
    return Loop('while', None, cond, stmts)

def repeatStmt(tokens):
    expectElseError(tokens, '\n', "after REPEAT")
    stmts = []
    while not atEnd(tokens) and not match(tokens, 'UNTIL'):
        stmts += [statement(tokens)]
    cond = expression(tokens)
    expectElseError(tokens, '\n', "at end of UNTIL")
    return Loop('repeat', None, cond, stmts)

def forStmt(tokens):
    name = identifier(tokens)
    expectElseError(tokens, '<-', "after name")
    start = value(tokens)
    expectElseError(tokens, 'TO', "after start value")
    end = value(tokens)
    step = makeExpr(type='INTEGER', value=1, token=end.token())
    if match(tokens, 'STEP'):
        step = value(tokens)
    expectElseError(tokens, '\n', "at end of FOR")
    stmts = []
    while not atEnd(tokens) and not match(tokens, 'ENDFOR'):
        stmts += [statement(tokens)]
    expectElseError(tokens, '\n', "after ENDFOR")
    # Initialise name to start
    init = Assign('assign', name.name, start)
    # Generate loop cond
    cond = Binary(
        makeExpr(frame=NULL, name=name.name, token=name),
        lte,
        end,
        token=name,
    )
    # Add increment statement
    incr = Assign(
        'assign',
        name,
        Binary(
            makeExpr(frame=NULL, name=name.name, token=name),
            add,
            step,
            token=name,
        ),
    )
    return Loop('while', init, cond, stmts + [incr])

def procedureStmt(tokens):
    name = identifier(tokens).name
    params = []
    if match(tokens, '('):
        passby = 'BYVALUE'
        if check(tokens)['word'] in ('BYVALUE', 'BYREF'):
            passby = consume(tokens)['word']
        expr = declare(tokens)
        params += [expr]
        while match(tokens, ','):
            expr = declare(tokens)
            params += [expr]
        expectElseError(tokens, ')', "at end of parameters")
    expectElseError(tokens, '\n', "after parameters")
    stmts = []
    while not atEnd(tokens) and not match(tokens, 'ENDPROCEDURE'):
        stmts += [statement(tokens)]
    expectElseError(tokens, '\n', "after ENDPROCEDURE")
    return ProcFunc('procedure', name, passby, params, stmts, None)

def callStmt(tokens):
    callable = value(tokens)
    expectElseError(tokens, '\n', "at end of CALL")
    return ExprStmt('call', callable)

def functionStmt(tokens):
    name = identifier(tokens).name
    params = []
    if match(tokens, '('):
        passby = 'BYVALUE'
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
    return ProcFunc('function', name, passby, params, stmts, typetoken['word'])

def returnStmt(tokens):
    expr = expression(tokens)
    expectElseError(tokens, '\n', "at end of RETURN")
    return ExprStmt('return', expr)

def openfileStmt(tokens):
    name = value(tokens)
    expectElseError(tokens, 'FOR', "after file identifier")
    if check(tokens)['word'] not in ('READ', 'WRITE', 'APPEND'):
        raise ParseError("Invalid file mode", check(tokens))
    mode = consume(tokens)['word']
    expectElseError(tokens, '\n')
    return FileAction('file', 'open', name, mode, None)

def readfileStmt(tokens):
    name = value(tokens)
    expectElseError(tokens, ',', "after file identifier")
    data = identifier(tokens).name
    expectElseError(tokens, '\n')
    return FileAction('file', 'read', name, None, data)

def writefileStmt(tokens):
    name = value(tokens)
    expectElseError(tokens, ',', "after file identifier")
    data = expression(tokens)
    expectElseError(tokens, '\n')
    return FileAction('file', 'write', name, None, data)

def closefileStmt(tokens):
    name = value(tokens)
    expectElseError(tokens, '\n')
    return FileAction('file', 'close', name, None, None)

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
