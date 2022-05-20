from .builtin import TYPES, NULL
from .builtin import ParseError
from .builtin import lte, add
from .lang import Token
from .lang import Literal, Name, Unary, Binary, Get, Call, Assign
from .lang import ExprStmt, Output, Input, Declare
from .lang import Conditional, Loop, ProcFunc, TypeStmt, FileAction



# Helper functions

def atEnd(tokens):
    if matchType(tokens, 'EOF'):
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
    frame=None, name=None, assignee=None, expr=None,
    left=None, oper=None, right=None,
    callable=None, args=None,
    token=None,
):
    if name is not None:
        if frame is not None:
            return Get(frame, name, token=token)
        elif expr is not None:
            if assignee is None:
                assignee = name
            return Assign(name, assignee, expr, token=token)
        elif type is not None:
            return Declare(name, type, token=token)
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
    raise ValueError(
        "Could not find valid keyword argument combination"
    )

def expectElseError(tokens, word, addmsg=None):
    if check(tokens).word == word:
        consume(tokens)
        return True
    msg = f"Expected {word}"
    if addmsg: msg += f" {addmsg}"
    raise ParseError(msg, check(tokens))

def match(tokens, *words, advance=True):
    if check(tokens).word not in words:
        return False
    if advance:
        consume(tokens)
    return True

def matchType(tokens, *types, advance=False):
    if check(tokens).type not in types:
        return False
    if advance:
        consume(tokens)
    return True

# Precedence parsers
# Expressions are parsed with this precedence (highest to lowest):
# 1. <name> | <literal> | <unary> | calls
# 2. *, /
# 3. +, -
# 4. < | <= | > | >=
# 5. <> | =
# 6. AND | OR

def identifier(tokens):
    if matchType(tokens, 'name'):
        token = consume(tokens)
        return makeExpr(name=token.word, token=token)
    else:
        raise ParseError(f"Expected variable name", consume(tokens))

def literal(tokens):
    token = consume(tokens)
    return makeExpr(
        type=token.type,
        value=token.value,
        token=token,
    )

def unary(tokens):
    oper = consume(tokens)
    right = value(tokens)
    return makeExpr(
        oper=oper.value,
        right=right,
        token=oper,
    )

def name(tokens):
    iden = identifier(tokens)
    return makeExpr(
        frame=NULL,
        name=iden.name,
        token=iden.token(),
    )

def callExpr(tokens, expr):
    args = []
    while not atEnd(tokens) and match(tokens, ')', advance=False):
        match(tokens, ',')  # ,
        arg = expression(tokens)
        args += [arg]
    expectElseError(tokens, ')', "after '('")
    return makeExpr(
        callable=expr,
        args=args,
        token=name.token(),
    )

def attrExpr(tokens, expr):
    name = identifier(tokens)
    return makeExpr(
        frame=expr,
        name=name.name,
        token=name.token(),
    )

def value(tokens):
    token = check(tokens)
    # Unary expressions
    if match(tokens, '-', 'NOT', advance=False):
        return unary(tokens)
    # A single value
    if matchType(tokens, *TYPES):
        return literal(tokens)
    #  A grouping
    elif match(tokens, '('):
        expr = expression(tokens)
        expectElseError(tokens, ')', "after '('")
        return expr
    # A name or call or attribute
    elif matchType(tokens, 'name'):
        expr = name(tokens)
        while not atEnd(tokens) and match(tokens, '(', '.', advance=False):
            # Function call
            if match(tokens, '('):
                expr = callExpr(tokens, expr)
            # Attribute get
            if match(tokens, '.'):
                expr = attrExpr(tokens, expr)
        return expr
    else:
        raise ParseError("Unexpected token", token)

def muldiv(tokens):
    # *, /
    expr = value(tokens)
    while not atEnd(tokens) and match(tokens, '*', '/', advance=False):
        oper = consume(tokens)
        right = value(tokens)
        expr = makeExpr(
            left=expr,
            oper=oper.value,
            right=right,
            token=oper,
        )
    return expr

def addsub(tokens):
    expr = muldiv(tokens)
    while not atEnd(tokens) and match(tokens, '+', '-', advance=False):
        oper = consume(tokens)
        right = muldiv(tokens)
        expr = makeExpr(
            left=expr,
            oper=oper.value,
            right=right,
            token=oper,
        )
    return expr

def comparison(tokens):
    # <, <=, >, >=
    expr = addsub(tokens)
    while not atEnd(tokens) and match(tokens, '<', '<=', '>', '>=', advance=False):
        oper = consume(tokens)
        right = addsub(tokens)
        expr = makeExpr(
            left=expr,
            oper=oper.value,
            right=right,
            token=oper,
        )
    return expr

def equality(tokens):
    # <>, =
    expr = comparison(tokens)
    while not atEnd(tokens) and match(tokens, '<>', '=', advance=False):
        oper = consume(tokens)
        right = comparison(tokens)
        expr = makeExpr(
            left=expr,
            oper=oper.value,
            right=right,
            token=oper,
        )
    return expr

def logical(tokens):
    # AND, OR
    expr = equality(tokens)
    while not atEnd(tokens) and match(tokens, 'AND', 'OR', advance=False):
        oper = consume(tokens)
        right = equality(tokens)
        expr = makeExpr(
            left=expr,
            oper=oper.value,
            right=right,
            token=oper,
        )
    return expr

def expression(tokens):
    expr = logical(tokens)
    return expr

def assignment(tokens):
    assignee = name(tokens)  # Get Expr
    while not atEnd(tokens) and match(tokens, '.'):
        # Attribute get
        assignee = attrExpr(tokens, assignee)
    expectElseError(tokens, '<-', "after name")
    expr = expression(tokens)
    return makeExpr(
        name=assignee.name,
        assignee=assignee,
        expr=expr,
        token=assignee.token(),
    )

# Statement parsers

def outputStmt(tokens):
    exprs = [expression(tokens)]
    while not atEnd(tokens) and match(tokens, ','):
        exprs += [expression(tokens)]
    expectElseError(tokens, '\n', "after statement")
    return Output('output', exprs)

def inputStmt(tokens):
    name = identifier(tokens)
    expectElseError(tokens, '\n', "after statement")
    return Input('input', name)

def declare(tokens):
    name = identifier(tokens)
    expectElseError(tokens, ':', "after name")
    typetoken = consume(tokens)
    if typetoken.word not in TYPES and typetoken.type != 'name':
        raise ParseError("Invalid type", typetoken)
    return makeExpr(
        name=name.name,
        type=typetoken.word,
        token=name.token(),
    )
    
def declareStmt(tokens):
    expr = declare(tokens)
    expectElseError(tokens, '\n', "after statement")
    return ExprStmt('declare', expr)

def typeStmt(tokens):
    name = identifier(tokens).name
    expectElseError(tokens, '\n')
    exprs = []
    while not atEnd(tokens) and not match(tokens, 'ENDTYPE', advance=False):
        expectElseError(tokens, 'DECLARE')
        exprs += [declare(tokens)]
        expectElseError(tokens, '\n')
    expectElseError(tokens, 'ENDTYPE')
    expectElseError(tokens, '\n')
    return TypeStmt('declaretype', name, exprs)

def assignStmt(tokens):
    expr = assignment(tokens)
    expectElseError(tokens, '\n', "after statement")
    return ExprStmt('assign', expr)

def caseStmt(tokens):
    expectElseError(tokens, 'OF', "after CASE")
    cond = value(tokens)
    expectElseError(tokens, '\n', "after CASE OF")
    stmts = {}
    while not (
        atEnd(tokens)
        or match(tokens, 'OTHERWISE', 'ENDCASE', advance=False)
    ):
        val = value(tokens).evaluate()
        expectElseError(tokens, ':', "after CASE value")
        stmt = statement1(tokens)
        stmts[val] = stmt
    fallback = None
    if match(tokens, 'OTHERWISE'):
        fallback = statement6(tokens)
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
    while not (
        atEnd(tokens)
        or check(tokens).word in ('ELSE', 'ENDIF')
    ):
        true += [statement1(tokens)]
    stmts[True] = true
    fallback = None
    if match(tokens, 'ELSE'):
        expectElseError(tokens, '\n', "after ELSE")
        false = []
        while not atEnd(tokens) and not match(tokens, 'ENDIF', advance=False):
            false += [statement5(tokens)]
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
        stmts += [statement5(tokens)]
    expectElseError(tokens, '\n', "after ENDWHILE")
    return Loop('while', None, cond, stmts)

def repeatStmt(tokens):
    expectElseError(tokens, '\n', "after REPEAT")
    stmts = []
    while not atEnd(tokens) and not match(tokens, 'UNTIL'):
        stmts += [statement5(tokens)]
    cond = expression(tokens)
    expectElseError(tokens, '\n', "at end of UNTIL")
    return Loop('repeat', None, cond, stmts)

def forStmt(tokens):
    init = assignment(tokens)
    # name = identifier(tokens)
    # expectElseError(tokens, '<-', "after name")
    # start = value(tokens)
    expectElseError(tokens, 'TO', "after start value")
    end = value(tokens)
    step = makeExpr(type='INTEGER', value=1, token=init.token())
    if match(tokens, 'STEP'):
        step = value(tokens)
    expectElseError(tokens, '\n', "at end of FOR")
    stmts = []
    while not atEnd(tokens) and not match(tokens, 'ENDFOR'):
        stmts += [statement5(tokens)]
    expectElseError(tokens, '\n', "after ENDFOR")
    # Generate loop cond
    getCounter = makeExpr(
        frame=NULL,
        name=init.name,
        token=init.token(),
    )
    cond = makeExpr(
        left=getCounter,
        oper=lte,
        right=end,
        token=init.token(),
    )
    # Add increment statement
    incr = makeExpr(
        name=init.name,
        assignee=init.assignee,
        expr=makeExpr(
            left=getCounter,
            oper=add,
            right=step,
            token=step.token(),
        ),
        token=init.token(),
    )
    initStmt = ExprStmt('assign', init)
    incrStmt = ExprStmt('assign', incr)
    return Loop('while', initStmt, cond, stmts + [incrStmt])

def procedureStmt(tokens):
    name = identifier(tokens).name
    params = []
    if match(tokens, '('):
        passby = 'BYVALUE'
        if check(tokens).word in ('BYVALUE', 'BYREF'):
            passby = consume(tokens).word
        expr = declare(tokens)
        params += [expr]
        while not atEnd(tokens) and match(tokens, ','):
            expr = declare(tokens)
            params += [expr]
        expectElseError(tokens, ')', "at end of parameters")
    expectElseError(tokens, '\n', "after parameters")
    stmts = []
    while not atEnd(tokens) and not match(tokens, 'ENDPROCEDURE'):
        stmts += [statement3(tokens)]
    expectElseError(tokens, '\n', "after ENDPROCEDURE")
    return ProcFunc('procedure', name, passby, params, stmts, 'NULL')

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
        while not atEnd(tokens) and match(tokens, ','):
            var = declare(tokens)
            params += [var]
        expectElseError(tokens, ')', "at end of parameters")
    expectElseError(tokens, 'RETURNS', "after parameters")
    typetoken = consume(tokens)
    if typetoken.word not in TYPES:
        raise ParseError("Invalid type", typetoken)
    expectElseError(tokens, '\n', "at end of FUNCTION")
    stmts = []
    while not atEnd(tokens) and not match(tokens, 'ENDFUNCTION'):
        stmts += [statement3(tokens)]
    expectElseError(tokens, '\n', "after ENDFUNCTION")
    return ProcFunc(
        'function', name, passby, params, stmts, typetoken.word
    )

def returnStmt(tokens):
    expr = expression(tokens)
    expectElseError(tokens, '\n', "at end of RETURN")
    return ExprStmt('return', expr)

def openfileStmt(tokens):
    name = value(tokens)
    expectElseError(tokens, 'FOR', "after file identifier")
    if match(tokens, 'READ', 'WRITE', 'APPEND', advance=False):
        raise ParseError("Invalid file mode", check(tokens))
    mode = consume(tokens).word
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

# Statement hierarchy
# Statements are parsed in this order (most to least restrictive):
# 1. RETURN -> (3)
#    used within FUNCTION only
# 2. FUNCTION | PROCEDURE -> (3)
#    used within global frame only
# 3. DECLARE -> (4)
#    used within global frame or FUNCTION/PROCEDURE only
#    cannot be used in loops and conditionals
# 4. IF | WHILE | REPEAT | FOR -> (5)
#    can be used anywhere except in CASE option statements
# 5. CASE -> (6)
#    only accepts single-line statements
# 6. OUTPUT | INPUT | CALL | Assign | OPEN/READ/WRITE/CLOSEFILE
#    may be used anywhere in a program

def statement1(tokens):
    if match(tokens, 'RETURN'):
        return returnStmt(tokens)
    return statement3(tokens)

def statement2(tokens):
    if match(tokens, 'FUNCTION'):
        return functionStmt(tokens)
    if match(tokens, 'PROCEDURE'):
        return procedureStmt(tokens)
    return statement3(tokens)

def statement3(tokens):
    if match(tokens, 'DECLARE'):
        return declareStmt(tokens)
    if match(tokens, 'TYPE'):
        return typeStmt(tokens)
    return statement4(tokens)

def statement4(tokens):
    if match(tokens, 'IF'):
        return ifStmt(tokens)
    if match(tokens, 'WHILE'):
        return whileStmt(tokens)
    if match(tokens, 'REPEAT'):
        return repeatStmt(tokens)
    if match(tokens, 'FOR'):
        return forStmt(tokens)
    return statement5(tokens)

def statement5(tokens):
    if match(tokens, 'CASE'):
        return caseStmt(tokens)
    return statement6(tokens)

def statement6(tokens):
    if match(tokens, 'OUTPUT'):
        return outputStmt(tokens)
    if match(tokens, 'INPUT'):
        return inputStmt(tokens)
    if match(tokens, 'CALL'):
        return callStmt(tokens)
    if match(tokens, 'OPENFILE'):
        return openfileStmt(tokens)
    if match(tokens, 'READFILE'):
        return readfileStmt(tokens)
    if match(tokens, 'WRITEFILE'):
        return writefileStmt(tokens)
    if match(tokens, 'CLOSEFILE'):
        return closefileStmt(tokens)
    if matchType(tokens, 'name'):
        return assignStmt(tokens)
    raise ParseError("Unrecognised token", check(tokens))

# Main parsing loop

def parse(tokens):
    lastline = tokens[-1].line
    tokens += [Token(lastline, 0, 'EOF', "", None)]
    statements = []
    while not atEnd(tokens):
        while not atEnd(tokens) and match(tokens, '\n'):
            pass
        statements += [statement2(tokens)]
        while not atEnd(tokens) and match(tokens, '\n'):
            pass
    return statements
