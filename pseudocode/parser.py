from typing import Optional, Iterable, Tuple, List, Dict

from . import builtin, lang

Tokens = List[lang.Token]



# Helper functions

def atEnd(tokens: Tokens) -> bool:
    return check(tokens).type == 'EOF'

def atEndThenError(tokens: Tokens) -> None:
    if atEnd(tokens):
        raise builtin.ParseError("Unexpected EOF", check(tokens))

def check(tokens: Tokens) -> lang.Token:
    return tokens[0]

def consume(tokens: Tokens) -> lang.Token:
    token = tokens.pop(0)
    return token

def expectWord(tokens: Tokens, *words: str) -> Optional[lang.Token]:
    if check(tokens).word in words:
        return check(tokens)
    atEndThenError(tokens)
    return None

def expectType(tokens: Tokens, *types: lang.Type) -> Optional[lang.Token]:
    if check(tokens).type in types:
        return check(tokens)
    atEndThenError(tokens)
    return None

def matchWord(tokens: Tokens, *words: str) -> Optional[lang.Token]:
    if check(tokens).word in words:
        return consume(tokens)
    atEndThenError(tokens)
    return None

def matchType(tokens: Tokens, *types: lang.Type) -> Optional[lang.Token]:
    if check(tokens).type in types:
        return consume(tokens)
    atEndThenError(tokens)
    return None

def matchWordElseError(
    tokens: Tokens,
    *words: str,
    msg: str='',
) -> lang.Token:
    token = matchWord(tokens, *words)
    if token:
        return token
    msg = f"Expected {words}" + (f' {msg}' if msg else '')
    raise builtin.ParseError(msg, check(tokens))

def matchTypeElseError(
    tokens: Tokens,
    *types: lang.Type,
        msg: str='',
) -> lang.Token:
    token = matchType(tokens, *types)
    if token:
        return token
    msg = f"Expected {types}" + (f' {msg}' if msg else '')
    raise builtin.ParseError(msg, check(tokens))

# Precedence parsers
# Expressions are parsed with this precedence (highest to lowest):
# 1. <name> | <literal> | <unary> | calls
# 2. *, /
# 3. +, -
# 4. < | <= | > | >=
# 5. <> | =
# 6. AND | OR

def identifier(tokens: Tokens) -> lang.Name:
    if expectType(tokens, 'name'):
        token = consume(tokens)
        return lang.Name(token.word, token=token)
    raise builtin.ParseError(f"Expected variable name", consume(tokens))

def literal(tokens: Tokens) -> lang.Literal:
    token = matchTypeElseError(tokens, *builtin.LITERAL, msg="index")
    return lang.Literal(token.type, token.value, token=token)

def unary(tokens: Tokens) -> lang.Unary:
    oper = consume(tokens)
    right = value(tokens)
    return lang.Unary(oper.value, right, token=oper)

# def name(tokens: Tokens) -> lang.Get:
#     iden = identifier(tokens)
#     return lang.Get(builtin.NULL, str(iden), token=iden.token())

def callExpr(tokens: Tokens, callable: lang.Get) -> lang.Call:
    args = []
    argcount = 0
    while not expectWord(tokens, ')'):
        if argcount > 0:
            matchWordElseError(tokens, ',')
        arg = expression(tokens)
        args += [arg]
        argcount += 1
    matchWordElseError(tokens, ')', msg="after '('")
    return lang.Call(callable, args)

def attrExpr(tokens: Tokens, objGet: lang.Get) -> lang.Get:
    name = identifier(tokens)
    return lang.GetAttr(objGet, name)

def indexExpr(tokens: Tokens, objGet: lang.Expr) -> lang.Get:
    indexes: Tuple[lang.Expr] = (literal(tokens),)
    while matchWord(tokens, ','):
        indexes += (literal(tokens),)
    matchWordElseError(tokens, ']')
    return lang.GetIndex(objGet, indexes, token=objGet.token())

def value(tokens: Tokens) -> lang.Expr:
    # Unary expressions
    if expectWord(tokens, '-', 'NOT'):
        return unary(tokens)
    #  A grouping
    if matchWord(tokens, '('):
        expr = expression(tokens)
        matchWordElseError(tokens, ')', msg="after '('")
        return expr
    # A single value
    if expectType(tokens, *builtin.TYPES):
        return literal(tokens)
    # A name or call or attribute
    if expectType(tokens, 'name'):
        getExpr = identifier(tokens)
        while expectWord(tokens, '[', '(', '.'):
            # Array get
            if matchWord(tokens, '['):
                getExpr = indexExpr(tokens, getExpr)
            # Function call
            elif matchWord(tokens, '('):
                getExpr = callExpr(tokens, getExpr)
            # Attribute get
            elif matchWord(tokens, '.'):
                getExpr = attrExpr(tokens, getExpr)
        return getExpr
    else:
        raise builtin.ParseError("Unexpected token", check(tokens))

def muldiv(tokens: Tokens) -> lang.Binary:
    # *, /
    expr = value(tokens)
    while expectWord(tokens, '*', '/'):
        oper = consume(tokens)
        right = value(tokens)
        expr = lang.Binary(expr, oper.value, right, token=oper)
    return expr

def addsub(tokens: Tokens) -> lang.Binary:
    expr = muldiv(tokens)
    while expectWord(tokens, '+', '-'):
        oper = consume(tokens)
        right = muldiv(tokens)
        expr = lang.Binary(expr, oper.value, right, token=oper)
    return expr

def comparison(tokens: Tokens) -> lang.Binary:
    # <, <=, >, >=
    expr = addsub(tokens)
    while expectWord(tokens, '<', '<=', '>', '>='):
        oper = consume(tokens)
        right = addsub(tokens)
        expr = lang.Binary(expr, oper.value, right, token=oper)
    return expr

def equality(tokens: Tokens) -> lang.Binary:
    # <>, =
    expr = comparison(tokens)
    while expectWord(tokens, '<>', '='):
        oper = consume(tokens)
        right = comparison(tokens)
        expr = lang.Binary(expr, oper.value, right, token=oper)
    return expr

def logical(tokens: Tokens) -> lang.Binary:
    # AND, OR
    expr = equality(tokens)
    while expectWord(tokens, 'AND', 'OR'):
        oper = consume(tokens)
        right = equality(tokens)
        expr = lang.Binary(expr, oper.value, right, token=oper)
    return expr

def expression(tokens: Tokens) -> lang.Expr:
    expr = logical(tokens)
    return expr

def assignment(tokens: Tokens) -> lang.Assign:
    assignee = identifier(tokens)
    while expectWord(tokens, '[', '.'):
        # Array get
        if matchWord(tokens, '['):
            assignee = arrayExpr(tokens, assignee)
        # Attribute get
        elif matchWord(tokens, '.'):
            assignee = attrExpr(tokens, assignee)
    matchWordElseError(tokens, '<-', msg="after name")
    expr = expression(tokens)
    return lang.Assign(assignee, expr)

# Statement parsers

def outputStmt(tokens: Tokens) -> lang.Output:
    exprs = [expression(tokens)]
    while matchWord(tokens, ','):
        exprs += [expression(tokens)]
    matchWordElseError(tokens, '\n', msg="after statement")
    return lang.Output('output', exprs)

def inputStmt(tokens: Tokens) -> lang.Input:
    name = identifier(tokens)
    matchWordElseError(tokens, '\n', msg="after statement")
    return lang.Input('input', name)

def colonRange(tokens: Tokens) -> Tuple:
    """Parse and return a start:end range as a tuple"""
    range_start = matchTypeElseError(tokens, 'INTEGER')
    matchWordElseError(tokens, ':', msg="in range")
    range_end = matchTypeElseError(tokens, 'INTEGER')
    return (range_start.value, range_end.value)

def declare(tokens: Tokens) -> lang.Declare:
    def expectTypeToken(tokens: Tokens):
        if not (expectWord(tokens, *builtin.TYPES) or expectType(tokens, 'name')):
            raise builtin.ParseError("Invalid type", check(tokens))
        
    name = identifier(tokens)
    matchWordElseError(tokens, ':', msg="after name")
    expectTypeToken(tokens)
    metadata = None
    typetoken = consume(tokens)
    if typetoken.word == 'ARRAY':
        matchWordElseError(tokens, '[')
        metadata = {'size': [colonRange(tokens)]}
        while matchWord(tokens, ','):
            metadata['size'] += [colonRange(tokens)]
        matchWordElseError(tokens, ']')
        matchWordElseError(tokens, 'OF')
        expectTypeToken(tokens)
        metadata['type'] = consume(tokens).word
    return lang.Declare(str(name), typetoken.word, metadata, token=name.token())
    
def declareStmt(tokens: Tokens) -> lang.ExprStmt:
    expr = declare(tokens)
    matchWordElseError(tokens, '\n', msg="after statement")
    return lang.ExprStmt('declare', expr)

def typeStmt(tokens: Tokens) -> lang.TypeStmt:
    name = identifier(tokens)
    matchWordElseError(tokens, '\n')
    exprs = []
    while not expectWord(tokens, 'ENDTYPE'):
        matchWordElseError(tokens, 'DECLARE')
        exprs += [declare(tokens)]
        matchWordElseError(tokens, '\n')
    matchWordElseError(tokens, 'ENDTYPE')
    matchWordElseError(tokens, '\n')
    return lang.TypeStmt('declaretype', str(name), exprs)

def assignStmt(tokens: Tokens) -> lang.ExprStmt:
    expr = assignment(tokens)
    matchWordElseError(tokens, '\n', msg="after statement")
    return lang.ExprStmt('assign', expr)

def caseStmt(tokens: Tokens) -> lang.Conditional:
    matchWordElseError(tokens, 'OF', msg="after CASE")
    cond = value(tokens)
    matchWordElseError(tokens, '\n', msg="after CASE OF")
    stmts: lang.Cases = {}
    while not expectWord(tokens, 'OTHERWISE', 'ENDCASE'):
        val: lang.PyLiteral = literal(tokens).value
        matchWordElseError(tokens, ':', msg="after CASE value")
        stmts[val] = [statement1(tokens)]
    fallback = None
    if matchWord(tokens, 'OTHERWISE'):
        fallback = [statement6(tokens)]
    matchWordElseError(tokens, 'ENDCASE', msg="at end of CASE")
    matchWordElseError(tokens, '\n', msg="after ENDCASE")
    return lang.Conditional('case', cond, stmts, fallback)

def ifStmt(tokens: Tokens) -> lang.Conditional:
    cond = expression(tokens)
    matchWord(tokens, '\n')  # optional line break
    matchWordElseError(tokens, 'THEN')
    matchWordElseError(tokens, '\n', msg="after THEN")
    stmts: lang.Cases = {True: []}
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
    return lang.Conditional('if', cond, stmts, fallback)

def whileStmt(tokens: Tokens) -> lang.Loop:
    cond = expression(tokens)
    matchWordElseError(tokens, 'DO', msg="after WHILE condition")
    matchWordElseError(tokens, '\n', msg="after DO")
    stmts = []
    while not matchWord(tokens, 'ENDWHILE'):
        stmts += [statement5(tokens)]
    matchWordElseError(tokens, '\n', msg="after ENDWHILE")
    return lang.Loop('while', None, cond, stmts)

def repeatStmt(tokens: Tokens) -> lang.Loop:
    matchWordElseError(tokens, '\n', msg="after REPEAT")
    stmts = []
    while not matchWord(tokens, 'UNTIL'):
        stmts += [statement5(tokens)]
    cond = expression(tokens)
    matchWordElseError(tokens, '\n', msg="at end of UNTIL")
    return lang.Loop('repeat', None, cond, stmts)

def forStmt(tokens: Tokens) -> lang.Loop:
    init = assignment(tokens)
    matchWordElseError(tokens, 'TO')
    end = value(tokens)
    step: lang.Expr = lang.Literal('INTEGER', 1, token=init.token())
    if matchWord(tokens, 'STEP'):
        step = value(tokens)
    matchWordElseError(tokens, '\n', msg="at end of FOR")
    stmts = []
    while not matchWord(tokens, 'ENDFOR'):
        stmts += [statement5(tokens)]
    matchWordElseError(tokens, '\n', msg="after ENDFOR")
    # Generate loop cond
    getCounter = lang.Get(builtin.NULL, init.assignee.name, token=init.token())
    cond = lang.Binary(getCounter, builtin.lte, end, token=init.token())
    # Add increment statement
    incr = lang.Assign(
        init.assignee,
        lang.Binary(getCounter, builtin.add, step, token=step.token()),
    )
    initStmt = lang.ExprStmt('assign', init)
    incrStmt = lang.ExprStmt('assign', incr)
    return lang.Loop('while', initStmt, cond, stmts + [incrStmt])

def procedureStmt(tokens: Tokens) -> lang.ProcFunc:
    name = identifier(tokens)
    params = []
    if matchWord(tokens, '('):
        passbyToken = matchWord(tokens, 'BYVALUE', 'BYREF')
        if passbyToken:
            passby = passbyToken.word
        else:
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
    return lang.ProcFunc('procedure', str(name), passby, params, stmts, 'NULL')

def callStmt(tokens: Tokens) -> lang.ExprStmt:
    callable: lang.Call = value(tokens)
    matchWordElseError(tokens, '\n')
    return lang.ExprStmt('call', callable)

def functionStmt(tokens: Tokens) -> lang.ProcFunc:
    name = identifier(tokens)
    params = []
    if matchWord(tokens, '('):
        passby: str = 'BYVALUE'
        var = declare(tokens)
        params += [var]
        while matchWord(tokens, ','):
            var = declare(tokens)
            params += [var]
        matchWordElseError(tokens, ')', msg="at end of parameters")
    matchWordElseError(tokens, 'RETURNS', msg="after parameters")
    typetoken = matchWordElseError(tokens, *builtin.TYPES, msg="Invalid type")
    matchWordElseError(tokens, '\n', msg="at end of FUNCTION")
    stmts = []
    while not matchWord(tokens, 'ENDFUNCTION'):
        stmts += [statement3(tokens)]
    matchWordElseError(tokens, '\n', msg="after ENDFUNCTION")
    return lang.ProcFunc(
        'function', str(name), passby, params, stmts, typetoken.word
    )

def returnStmt(tokens: Tokens) -> lang.ExprStmt:
    expr = expression(tokens)
    matchWordElseError(tokens, '\n', msg="at end of RETURN")
    return lang.ExprStmt('return', expr)

def openfileStmt(tokens: Tokens) -> lang.FileAction:
    name = value(tokens)
    matchWordElseError(tokens, 'FOR', msg="after file identifier")
    mode = matchWordElseError(
        tokens, 'READ', 'WRITE', 'APPEND', msg="Invalid file mode"
    )
    matchWordElseError(tokens, '\n')
    return lang.FileAction('file', 'open', name, mode.word, None)

def readfileStmt(tokens: Tokens) -> lang.FileAction:
    name = value(tokens)
    matchWordElseError(tokens, ',', msg="after file identifier")
    varname = identifier(tokens)
    matchWordElseError(tokens, '\n')
    return lang.FileAction('file', 'read', name, None, str(varname))

def writefileStmt(tokens: Tokens) -> lang.FileAction:
    name = value(tokens)
    matchWordElseError(tokens, ',', msg="after file identifier")
    data = expression(tokens)
    matchWordElseError(tokens, '\n')
    return lang.FileAction('file', 'write', name, None, data)

def closefileStmt(tokens: Tokens) -> lang.FileAction:
    name = value(tokens)
    matchWordElseError(tokens, '\n')
    return lang.FileAction('file', 'close', name, None, None)

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

def statement1(tokens: Tokens) -> lang.Stmt:
    if matchWord(tokens, 'RETURN'):
        return returnStmt(tokens)
    return statement3(tokens)

def statement2(tokens: Tokens) -> lang.Stmt:
    if matchWord(tokens, 'FUNCTION'):
        return functionStmt(tokens)
    if matchWord(tokens, 'PROCEDURE'):
        return procedureStmt(tokens)
    return statement3(tokens)

def statement3(tokens: Tokens) -> lang.Stmt:
    if matchWord(tokens, 'DECLARE'):
        return declareStmt(tokens)
    if matchWord(tokens, 'TYPE'):
        return typeStmt(tokens)
    return statement4(tokens)

def statement4(tokens: Tokens) -> lang.Stmt:
    if matchWord(tokens, 'IF'):
        return ifStmt(tokens)
    if matchWord(tokens, 'WHILE'):
        return whileStmt(tokens)
    if matchWord(tokens, 'REPEAT'):
        return repeatStmt(tokens)
    if matchWord(tokens, 'FOR'):
        return forStmt(tokens)
    return statement5(tokens)

def statement5(tokens: Tokens) -> lang.Stmt:
    if matchWord(tokens, 'CASE'):
        return caseStmt(tokens)
    return statement6(tokens)

def statement6(tokens: Tokens) -> lang.Stmt:
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
    raise builtin.ParseError("Unrecognised token", check(tokens))

# Main parsing loop

def parse(tokens: Tokens) -> Iterable[lang.Stmt]:
    lastline = tokens[-1].line
    tokens += [lang.Token(lastline, 0, 'EOF', "", None)]
    statements = []
    while not atEnd(tokens):
        while matchWord(tokens, '\n'):
            pass
        statements += [statement2(tokens)]
    return statements
