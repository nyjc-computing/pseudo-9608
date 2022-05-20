from .builtin import TYPES, NULL
from .builtin import ParseError
from .builtin import lte, add
from .lang import Token
from .lang import Literal, Name, Unary, Binary, Get, Call, Assign
from .lang import ExprStmt, Output, Input, Declare
from .lang import Conditional, Loop, ProcFunc, TypeStmt, FileAction



# Helper functions

def atEnd(tokens):
    if expectType(tokens, 'EOF'):
        return True
    return False

def atEndThenError(tokens):
    if atEnd(tokens):
        raise ParseError("Unexpected EOF", check(tokens))

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

def matchElseError(tokens, word, addmsg=None):
    if matchWord(tokens, word):
        return True
    msg = f"Expected {word}"
    if addmsg: msg += f" {addmsg}"
    raise ParseError(msg, check(tokens))

def matchWord(tokens, *words):
    if check(tokens).word in words:
        return consume(tokens)
    atEndThenError(tokens)
    return False

def expectWord(tokens, *words):
    if check(tokens).word in words:
        return True
    atEndThenError(tokens)
    return False

def expectType(tokens, *types):
    if check(tokens).type in types:
        return True
    atEndThenError(tokens)
    return False

# Precedence parsers
# Expressions are parsed with this precedence (highest to lowest):
# 1. <name> | <literal> | <unary> | calls
# 2. *, /
# 3. +, -
# 4. < | <= | > | >=
# 5. <> | =
# 6. AND | OR

def identifier(tokens):
    if expectType(tokens, 'name'):
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
    while not atEnd(tokens) and not expectWord(tokens, ')'):
        matchWord(tokens, ',')  # ,
        arg = expression(tokens)
        args += [arg]
    matchElseError(tokens, ')', "after '('")
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
    if expectWord(tokens, '-', 'NOT'):
        return unary(tokens)
    # A single value
    if expectType(tokens, *TYPES):
        return literal(tokens)
    #  A grouping
    elif matchWord(tokens, '('):
        expr = expression(tokens)
        matchElseError(tokens, ')', "after '('")
        return expr
    # A name or call or attribute
    elif expectType(tokens, 'name'):
        expr = name(tokens)
        while not atEnd(tokens) and expectWord(tokens, '(', '.'):
            # Function call
            if matchWord(tokens, '('):
                expr = callExpr(tokens, expr)
            # Attribute get
            if matchWord(tokens, '.'):
                expr = attrExpr(tokens, expr)
        return expr
    else:
        raise ParseError("Unexpected token", token)

def muldiv(tokens):
    # *, /
    expr = value(tokens)
    while not atEnd(tokens) and expectWord(tokens, '*', '/'):
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
    while not atEnd(tokens) and expectWord(tokens, '+', '-'):
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
    while not atEnd(tokens) and expectWord(tokens, '<', '<=', '>', '>='):
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
    while not atEnd(tokens) and expectWord(tokens, '<>', '='):
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
    while not atEnd(tokens) and expectWord(tokens, 'AND', 'OR'):
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
    while not atEnd(tokens) and matchWord(tokens, '.'):
        # Attribute get
        assignee = attrExpr(tokens, assignee)
    matchElseError(tokens, '<-', "after name")
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
    while not atEnd(tokens) and matchWord(tokens, ','):
        exprs += [expression(tokens)]
    matchElseError(tokens, '\n', "after statement")
    return Output('output', exprs)

def inputStmt(tokens):
    name = identifier(tokens)
    matchElseError(tokens, '\n', "after statement")
    return Input('input', name)

def declare(tokens):
    name = identifier(tokens)
    matchElseError(tokens, ':', "after name")
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
    matchElseError(tokens, '\n', "after statement")
    return ExprStmt('declare', expr)

def typeStmt(tokens):
    name = identifier(tokens).name
    matchElseError(tokens, '\n')
    exprs = []
    while not atEnd(tokens) and not expectWord(tokens, 'ENDTYPE'):
        matchElseError(tokens, 'DECLARE')
        exprs += [declare(tokens)]
        matchElseError(tokens, '\n')
    matchElseError(tokens, 'ENDTYPE')
    matchElseError(tokens, '\n')
    return TypeStmt('declaretype', name, exprs)

def assignStmt(tokens):
    expr = assignment(tokens)
    matchElseError(tokens, '\n', "after statement")
    return ExprStmt('assign', expr)

def caseStmt(tokens):
    matchElseError(tokens, 'OF', "after CASE")
    cond = value(tokens)
    matchElseError(tokens, '\n', "after CASE OF")
    stmts = {}
    while not (
        atEnd(tokens)
        or expectWord(tokens, 'OTHERWISE', 'ENDCASE')
    ):
        val = value(tokens).evaluate()
        matchElseError(tokens, ':', "after CASE value")
        stmt = statement1(tokens)
        stmts[val] = stmt
    fallback = None
    if matchWord(tokens, 'OTHERWISE'):
        fallback = statement6(tokens)
    matchElseError(tokens, 'ENDCASE', "at end of CASE")
    matchElseError(tokens, '\n', "after ENDCASE")
    return Conditional('case', cond, stmts, fallback)

def ifStmt(tokens):
    cond = expression(tokens)
    matchWord(tokens, '\n')  # optional line break
    matchElseError(tokens, 'THEN', "after IF")
    matchElseError(tokens, '\n', "after THEN")
    stmts = {}
    true = []
    while not (
        atEnd(tokens)
        or check(tokens).word in ('ELSE', 'ENDIF')
    ):
        true += [statement1(tokens)]
    stmts[True] = true
    fallback = None
    if matchWord(tokens, 'ELSE'):
        matchElseError(tokens, '\n', "after ELSE")
        false = []
        while not atEnd(tokens) and not expectWord(tokens, 'ENDIF'):
            false += [statement5(tokens)]
        fallback = false
    matchElseError(tokens, 'ENDIF', "at end of IF")
    matchElseError(tokens, '\n', "after statement")
    return Conditional('if', cond, stmts, fallback)

def whileStmt(tokens):
    cond = expression(tokens)
    matchElseError(tokens, 'DO', "after WHILE condition")
    matchElseError(tokens, '\n', "after DO")
    stmts = []
    while not atEnd(tokens) and not matchWord(tokens, 'ENDWHILE'):
        stmts += [statement5(tokens)]
    matchElseError(tokens, '\n', "after ENDWHILE")
    return Loop('while', None, cond, stmts)

def repeatStmt(tokens):
    matchElseError(tokens, '\n', "after REPEAT")
    stmts = []
    while not atEnd(tokens) and not matchWord(tokens, 'UNTIL'):
        stmts += [statement5(tokens)]
    cond = expression(tokens)
    matchElseError(tokens, '\n', "at end of UNTIL")
    return Loop('repeat', None, cond, stmts)

def forStmt(tokens):
    init = assignment(tokens)
    # name = identifier(tokens)
    # matchElseError(tokens, '<-', "after name")
    # start = value(tokens)
    matchElseError(tokens, 'TO', "after start value")
    end = value(tokens)
    step = makeExpr(type='INTEGER', value=1, token=init.token())
    if matchWord(tokens, 'STEP'):
        step = value(tokens)
    matchElseError(tokens, '\n', "at end of FOR")
    stmts = []
    while not atEnd(tokens) and not matchWord(tokens, 'ENDFOR'):
        stmts += [statement5(tokens)]
    matchElseError(tokens, '\n', "after ENDFOR")
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
    if matchWord(tokens, '('):
        passby = 'BYVALUE'
        if check(tokens).word in ('BYVALUE', 'BYREF'):
            passby = consume(tokens).word
        expr = declare(tokens)
        params += [expr]
        while not atEnd(tokens) and matchWord(tokens, ','):
            expr = declare(tokens)
            params += [expr]
        matchElseError(tokens, ')', "at end of parameters")
    matchElseError(tokens, '\n', "after parameters")
    stmts = []
    while not atEnd(tokens) and not matchWord(tokens, 'ENDPROCEDURE'):
        stmts += [statement3(tokens)]
    matchElseError(tokens, '\n', "after ENDPROCEDURE")
    return ProcFunc('procedure', name, passby, params, stmts, 'NULL')

def callStmt(tokens):
    callable = value(tokens)
    matchElseError(tokens, '\n', "at end of CALL")
    return ExprStmt('call', callable)

def functionStmt(tokens):
    name = identifier(tokens).name
    params = []
    if matchWord(tokens, '('):
        passby = 'BYVALUE'
        var = declare(tokens)
        params += [var]
        while not atEnd(tokens) and matchWord(tokens, ','):
            var = declare(tokens)
            params += [var]
        matchElseError(tokens, ')', "at end of parameters")
    matchElseError(tokens, 'RETURNS', "after parameters")
    typetoken = consume(tokens)
    if typetoken.word not in TYPES:
        raise ParseError("Invalid type", typetoken)
    matchElseError(tokens, '\n', "at end of FUNCTION")
    stmts = []
    while not atEnd(tokens) and not matchWord(tokens, 'ENDFUNCTION'):
        stmts += [statement3(tokens)]
    matchElseError(tokens, '\n', "after ENDFUNCTION")
    return ProcFunc(
        'function', name, passby, params, stmts, typetoken.word
    )

def returnStmt(tokens):
    expr = expression(tokens)
    matchElseError(tokens, '\n', "at end of RETURN")
    return ExprStmt('return', expr)

def openfileStmt(tokens):
    name = value(tokens)
    matchElseError(tokens, 'FOR', "after file identifier")
    if not expectWord(tokens, 'READ', 'WRITE', 'APPEND'):
        raise ParseError("Invalid file mode", check(tokens))
    mode = consume(tokens).word
    matchElseError(tokens, '\n')
    return FileAction('file', 'open', name, mode, None)

def readfileStmt(tokens):
    name = value(tokens)
    matchElseError(tokens, ',', "after file identifier")
    data = identifier(tokens).name
    matchElseError(tokens, '\n')
    return FileAction('file', 'read', name, None, data)

def writefileStmt(tokens):
    name = value(tokens)
    matchElseError(tokens, ',', "after file identifier")
    data = expression(tokens)
    matchElseError(tokens, '\n')
    return FileAction('file', 'write', name, None, data)

def closefileStmt(tokens):
    name = value(tokens)
    matchElseError(tokens, '\n')
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
    if matchWord(tokens, 'RETURN'):
        return returnStmt(tokens)
    return statement3(tokens)

def statement2(tokens):
    if matchWord(tokens, 'FUNCTION'):
        return functionStmt(tokens)
    if matchWord(tokens, 'PROCEDURE'):
        return procedureStmt(tokens)
    return statement3(tokens)

def statement3(tokens):
    if matchWord(tokens, 'DECLARE'):
        return declareStmt(tokens)
    if matchWord(tokens, 'TYPE'):
        return typeStmt(tokens)
    return statement4(tokens)

def statement4(tokens):
    if matchWord(tokens, 'IF'):
        return ifStmt(tokens)
    if matchWord(tokens, 'WHILE'):
        return whileStmt(tokens)
    if matchWord(tokens, 'REPEAT'):
        return repeatStmt(tokens)
    if matchWord(tokens, 'FOR'):
        return forStmt(tokens)
    return statement5(tokens)

def statement5(tokens):
    if matchWord(tokens, 'CASE'):
        return caseStmt(tokens)
    return statement6(tokens)

def statement6(tokens):
    if matchWord(tokens, 'OUTPUT'):
        return outputStmt(tokens)
    if matchWord(tokens, 'INPUT'):
        return inputStmt(tokens)
    if matchWord(tokens, 'CALL'):
        return callStmt(tokens)
    if matchWord(tokens, 'OPENFILE'):
        return openfileStmt(tokens)
    if matchWord(tokens, 'READFILE'):
        return readfileStmt(tokens)
    if matchWord(tokens, 'WRITEFILE'):
        return writefileStmt(tokens)
    if matchWord(tokens, 'CLOSEFILE'):
        return closefileStmt(tokens)
    if expectType(tokens, 'name'):
        return assignStmt(tokens)
    raise ParseError("Unrecognised token", check(tokens))

# Main parsing loop

def parse(tokens):
    lastline = tokens[-1].line
    tokens += [Token(lastline, 0, 'EOF', "", None)]
    statements = []
    while not atEnd(tokens):
        while not atEnd(tokens) and matchWord(tokens, '\n'):
            pass
        statements += [statement2(tokens)]
        while not atEnd(tokens) and matchWord(tokens, '\n'):
            pass
    return statements
