from .builtin import TYPES, NULL
from .builtin import ParseError
from .builtin import lte, add
from .lang import Token
from .lang import Literal, Name, Unary, Binary, Get, Call, Assign
from .lang import ExprStmt, Output, Input, Declare
from .lang import Conditional, Loop, ProcFunc, TypeStmt, FileAction



# Helper functions

def atEnd(tokens):
    return check(tokens).type == 'EOF'

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
    token=None, metadata=None,
):
    if name is not None:
        if frame is not None:
            return Get(frame, name, token=token)
        elif expr is not None:
            if assignee is None:
                assignee = name
            return Assign(name, assignee, expr, token=token)
        elif type is not None:
            return Declare(name, type, metadata, token=token)
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

def expectWord(tokens, *words):
    if check(tokens).word in words:
        return check(tokens)
    atEndThenError(tokens)
    return None

def expectType(tokens, *types):
    if check(tokens).type in types:
        return check(tokens)
    atEndThenError(tokens)
    return None

def matchWord(tokens, *words):
    if check(tokens).word in words:
        return consume(tokens)
    atEndThenError(tokens)
    return None

def matchType(tokens, *types):
    if check(tokens).type in types:
        return consume(tokens)
    atEndThenError(tokens)
    return None

def matchWordElseError(tokens, *words, msg=''):
    token = matchWord(tokens, *words)
    if token:
        return token
    msg = f"Expected {words}" + (f' {msg}' if msg else '')
    raise ParseError(msg, check(tokens))

def matchTypeElseError(tokens, *types, msg=''):
    token = matchType(tokens, *types)
    if token:
        return token
    msg = f"Expected {types}" + (f' {msg}' if msg else '')
    raise ParseError(msg, check(tokens))

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
    argcount = 0
    while not expectWord(tokens, ')'):
        if argcount == 0:
            matchWordElseError(tokens, ',')
        arg = expression(tokens)
        args += [arg]
        argcount += 1
    matchWordElseError(tokens, ')', msg="after '('")
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

def arrayExpr(tokens, expr):
    index = (expression(tokens),)
    while matchWord(tokens, ','):
        index += (expression(tokens),)
    matchWordElseError(tokens, ']')
    return makeExpr(
        frame=expr,
        name=index,
        token=expr.token(),
    )

def value(tokens):
    token = check(tokens)
    # Unary expressions
    if expectWord(tokens, '-', 'NOT'):
        return unary(tokens)
    #  A grouping
    if matchWord(tokens, '('):
        expr = expression(tokens)
        matchWordElseError(tokens, ')', msg="after '('")
        return expr
    # A single value
    if expectType(tokens, *TYPES):
        return literal(tokens)
    # A name or call or attribute
    if expectType(tokens, 'name'):
        expr = name(tokens)
        while expectWord(tokens, '[', '(', '.'):
            # Array get
            if matchWord(tokens, '['):
                expr = arrayExpr(tokens, expr)
            # Function call
            elif matchWord(tokens, '('):
                expr = callExpr(tokens, expr)
            # Attribute get
            elif matchWord(tokens, '.'):
                expr = attrExpr(tokens, expr)
        return expr
    else:
        raise ParseError("Unexpected token", token)

def muldiv(tokens):
    # *, /
    expr = value(tokens)
    while expectWord(tokens, '*', '/'):
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
    while expectWord(tokens, '+', '-'):
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
    while expectWord(tokens, '<', '<=', '>', '>='):
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
    while expectWord(tokens, '<>', '='):
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
    while expectWord(tokens, 'AND', 'OR'):
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
    while expectWord(tokens, '[', '.'):
        # Array get
        if matchWord(tokens, '['):
            assignee = arrayExpr(tokens, assignee)
        # Attribute get
        elif matchWord(tokens, '.'):
            assignee = attrExpr(tokens, assignee)
    matchWordElseError(tokens, '<-', msg="after name")
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
    while matchWord(tokens, ','):
        exprs += [expression(tokens)]
    matchWordElseError(tokens, '\n', msg="after statement")
    return Output('output', exprs)

def inputStmt(tokens):
    name = identifier(tokens)
    matchWordElseError(tokens, '\n', msg="after statement")
    return Input('input', name)

def colonRange(tokens):
    """Parse and return a start:end range as a tuple"""
    range_start = matchTypeElseError(tokens, 'INTEGER')
    matchWordElseError(tokens, ':', msg="in range")
    range_end = matchTypeElseError(tokens, 'INTEGER')
    return (range_start.value, range_end.value)

def declare(tokens):
    def expectTypeToken(tokens):
        if not (expectWord(tokens, *TYPES) or expectType(tokens, 'name')):
            raise ParseError("Invalid type", check(tokens))
        
    name = identifier(tokens)
    matchWordElseError(tokens, ':', msg="after name")
    expectTypeToken(tokens)
    metadata = None
    typetoken = consume(tokens)
    if typetoken.word == 'ARRAY':
        matchWordElseError(tokens, '[')
        metadata = {'size': [colonRange(tokens)], 'type': None}
        while matchWord(tokens, ','):
            metadata['size'] += [colonRange(tokens)]
        matchWordElseError(tokens, ']')
        matchWordElseError(tokens, 'OF')
        expectTypeToken(tokens)
        metadata['type'] = consume(tokens).word
    return makeExpr(
        name=name.name,
        type=typetoken.word,
        metadata=metadata,
        token=name.token(),
    )
    
def declareStmt(tokens):
    expr = declare(tokens)
    matchWordElseError(tokens, '\n', msg="after statement")
    return ExprStmt('declare', expr)

def typeStmt(tokens):
    name = identifier(tokens)
    matchWordElseError(tokens, '\n')
    exprs = []
    while not expectWord(tokens, 'ENDTYPE'):
        matchWordElseError(tokens, 'DECLARE')
        exprs += [declare(tokens)]
        matchWordElseError(tokens, '\n')
    matchWordElseError(tokens, 'ENDTYPE')
    matchWordElseError(tokens, '\n')
    return TypeStmt('declaretype', name.name, exprs)

def assignStmt(tokens):
    expr = assignment(tokens)
    matchWordElseError(tokens, '\n', msg="after statement")
    return ExprStmt('assign', expr)

def caseStmt(tokens):
    matchWordElseError(tokens, 'OF', msg="after CASE")
    cond = value(tokens)
    matchWordElseError(tokens, '\n', msg="after CASE OF")
    stmts = {}
    while not expectWord(tokens, 'OTHERWISE', 'ENDCASE'):
        val = value(tokens).evaluate()
        matchWordElseError(tokens, ':', msg="after CASE value")
        stmt = statement1(tokens)
        stmts[val] = stmt
    fallback = None
    if matchWord(tokens, 'OTHERWISE'):
        fallback = statement6(tokens)
    matchWordElseError(tokens, 'ENDCASE', msg="at end of CASE")
    matchWordElseError(tokens, '\n', msg="after ENDCASE")
    return Conditional('case', cond, stmts, fallback)

def ifStmt(tokens):
    cond = expression(tokens)
    matchWord(tokens, '\n')  # optional line break
    matchWordElseError(tokens, 'THEN')
    matchWordElseError(tokens, '\n', msg="after THEN")
    stmts = {True: []}
    while not expectWord(tokens, 'ELSE', 'ENDIF'):
        stmts[True] += [statement1(tokens)]
    fallback = None
    if matchWord(tokens, 'ELSE'):
        matchWordElseError(tokens, '\n', msg="after ELSE")
        false = []
        while not expectWord(tokens, 'ENDIF'):
            false += [statement5(tokens)]
        fallback = false
    matchWordElseError(tokens, 'ENDIF', msg="at end of IF")
    matchWordElseError(tokens, '\n', msg="after statement")
    return Conditional('if', cond, stmts, fallback)

def whileStmt(tokens):
    cond = expression(tokens)
    matchWordElseError(tokens, 'DO', msg="after WHILE condition")
    matchWordElseError(tokens, '\n', msg="after DO")
    stmts = []
    while not matchWord(tokens, 'ENDWHILE'):
        stmts += [statement5(tokens)]
    matchWordElseError(tokens, '\n', msg="after ENDWHILE")
    return Loop('while', None, cond, stmts)

def repeatStmt(tokens):
    matchWordElseError(tokens, '\n', msg="after REPEAT")
    stmts = []
    while not matchWord(tokens, 'UNTIL'):
        stmts += [statement5(tokens)]
    cond = expression(tokens)
    matchWordElseError(tokens, '\n', msg="at end of UNTIL")
    return Loop('repeat', None, cond, stmts)

def forStmt(tokens):
    init = assignment(tokens)
    matchWordElseError(tokens, 'TO')
    end = value(tokens)
    step = makeExpr(type='INTEGER', value=1, token=init.token())
    if matchWord(tokens, 'STEP'):
        step = value(tokens)
    matchWordElseError(tokens, '\n', msg="at end of FOR")
    stmts = []
    while not matchWord(tokens, 'ENDFOR'):
        stmts += [statement5(tokens)]
    matchWordElseError(tokens, '\n', msg="after ENDFOR")
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
        passby = matchWord(tokens, 'BYVALUE', 'BYREF')
        if not passby:
            passby = 'BYVALUE'
        expr = declare(tokens)
        params += [expr]
        while matchWord(tokens, ','):
            expr = declare(tokens)
            params += [expr]
        matchWordElseError(tokens, ')')
    matchWordElseError(tokens, '\n', msg="after parameters")
    stmts = []
    while not matchWord(tokens, 'ENDPROCEDURE'):
        stmts += [statement3(tokens)]
    matchWordElseError(tokens, '\n', msg="after ENDPROCEDURE")
    return ProcFunc('procedure', name, passby, params, stmts, 'NULL')

def callStmt(tokens):
    callable = value(tokens)
    matchWordElseError(tokens, '\n', msg="at end of CALL")
    return ExprStmt('call', callable)

def functionStmt(tokens):
    name = identifier(tokens).name
    params = []
    if matchWord(tokens, '('):
        passby = 'BYVALUE'
        var = declare(tokens)
        params += [var]
        while matchWord(tokens, ','):
            var = declare(tokens)
            params += [var]
        matchWordElseError(tokens, ')', msg="at end of parameters")
    matchWordElseError(tokens, 'RETURNS', msg="after parameters")
    typetoken = matchWordElseError(tokens, *TYPES, msg="Invalid type")
    matchWordElseError(tokens, '\n', msg="at end of FUNCTION")
    stmts = []
    while not matchWord(tokens, 'ENDFUNCTION'):
        stmts += [statement3(tokens)]
    matchWordElseError(tokens, '\n', msg="after ENDFUNCTION")
    return ProcFunc(
        'function', name, passby, params, stmts, typetoken.word
    )

def returnStmt(tokens):
    expr = expression(tokens)
    matchWordElseError(tokens, '\n', msg="at end of RETURN")
    return ExprStmt('return', expr)

def openfileStmt(tokens):
    name = value(tokens)
    matchWordElseError(tokens, 'FOR', msg="after file identifier")
    mode = matchWordElseError(
        tokens, 'READ', 'WRITE', 'APPEND', msg="Invalid file mode"
    )
    matchWordElseError(tokens, '\n')
    return FileAction('file', 'open', name, mode, None)

def readfileStmt(tokens):
    name = value(tokens)
    matchWordElseError(tokens, ',', msg="after file identifier")
    data = identifier(tokens)
    matchWordElseError(tokens, '\n')
    return FileAction('file', 'read', name, None, data.name)

def writefileStmt(tokens):
    name = value(tokens)
    matchWordElseError(tokens, ',', msg="after file identifier")
    data = expression(tokens)
    matchWordElseError(tokens, '\n')
    return FileAction('file', 'write', name, None, data)

def closefileStmt(tokens):
    name = value(tokens)
    matchWordElseError(tokens, '\n')
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
        while matchWord(tokens, '\n'):
            pass
        statements += [statement2(tokens)]
    return statements
