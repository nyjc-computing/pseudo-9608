from typing import Any, Optional, Union, Iterable, Tuple, List
from typing import Callable as function

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

def expectType(
    tokens: Tokens,
    *types: lang.Type,
) -> Optional[lang.Token]:
    if check(tokens).type in types:
        return check(tokens)
    atEndThenError(tokens)
    return None

def matchWord(tokens: Tokens, *words: str) -> Optional[lang.Token]:
    if check(tokens).word in words:
        return consume(tokens)
    atEndThenError(tokens)
    return None

def matchType(
    tokens: Tokens,
    *types: lang.Type,
) -> Optional[lang.Token]:
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

def identifier(tokens: Tokens) -> lang.UnresolvedName:
    if expectType(tokens, 'name'):
        token = consume(tokens)
        name = lang.Name(token.word, token=token)
        return lang.UnresolvedName(name)
    raise builtin.ParseError(f"Expected variable name", consume(tokens))

def literal(tokens: Tokens) -> lang.Literal:
    token = matchTypeElseError(tokens, *builtin.LITERAL, msg="index")
    return lang.Literal(token.type, token.value, token=token)

def unary(tokens: Tokens) -> lang.Unary:
    oper = consume(tokens)
    parse = parser(tokens)
    right: lang.Expr = parse(tokens)
    return lang.Unary(oper.value, right, token=oper)

def grouping(tokens: Tokens) -> lang.Expr:
    matchWord(tokens, '(')
    expr = expression(tokens)
    matchWordElseError(tokens, ')', msg="after '('")
    return expr

def callExpr(
    tokens: Tokens,
    callableExpr: lang.NameKeyExpr,
) -> lang.Call:
    args: Tuple[lang.Expr, ...] = tuple()
    while not expectWord(tokens, ')'):
        if len(args) > 0:
            matchWordElseError(tokens, ',')
        args += (expression(tokens)),
    matchWordElseError(tokens, ')', msg="after '('")
    return lang.Call(callableExpr, args)

def attrExpr(tokens: Tokens, objExpr: lang.NameExpr) -> lang.GetAttr:
    name = identifier(tokens).name  # Extract Name from UnresolvedName
    return lang.GetAttr(objExpr, name)

def indexExpr(
    tokens: Tokens,
    arrayExpr: lang.NameExpr,
) -> lang.GetIndex:
    parse = parser(tokens)
    indexes: lang.IndexExpr = (parse(tokens),)
    while matchWord(tokens, ','):
        parse = parser(tokens)
        indexes += (parse(tokens),)
    matchWordElseError(tokens, ']')
    return lang.GetIndex(arrayExpr, indexes)

def name(tokens: Tokens) -> lang.NameExpr:
    unresolvedName = identifier(tokens)
    # After Call Expr, we expect to have any Value except Callable
    unresolvedNameOrCall: Union[lang.UnresolvedName, lang.Call] = unresolvedName
    # Function call
    if matchWord(tokens, '('):
       unresolvedNameOrCall = callExpr(tokens, unresolvedName)
    nameExpr: lang.NameExpr = unresolvedNameOrCall
    while expectWord(tokens, '[', '.'):
        # Array get
        if matchWord(tokens, '['):
            nameExpr = indexExpr(tokens, nameExpr)
        # Attribute get
        if matchWord(tokens, '.'):
            nameExpr = attrExpr(tokens, nameExpr)
    return nameExpr

def parser(tokens: Tokens) -> function[[Tokens], Any]:
    # Unary expressions
    if expectWord(tokens, '-', 'NOT'):
        return unary
    #  A grouping
    if expectWord(tokens, '('):
        return grouping
    # A single value
    if expectType(tokens, *builtin.TYPES):
        return literal
    # A name or call or attribute
    if expectType(tokens, 'name'):
        return name
    else:
        raise builtin.ParseError("Unexpected token", check(tokens))

def muldiv(tokens: Tokens) -> lang.Expr:
    # *, /
    parse = parser(tokens)
    expr: lang.Expr = parse(tokens)
    while expectWord(tokens, '*', '/'):
        oper = consume(tokens)
        parse = parser(tokens)
        right: lang.Expr = parse(tokens)
        expr = lang.Binary(expr, oper.value, right, token=oper)
    return expr

def addsub(tokens: Tokens) -> lang.Expr:
    expr = muldiv(tokens)
    while expectWord(tokens, '+', '-'):
        oper = consume(tokens)
        right = muldiv(tokens)
        expr = lang.Binary(expr, oper.value, right, token=oper)
    return expr

def comparison(tokens: Tokens) -> lang.Expr:
    # <, <=, >, >=
    expr = addsub(tokens)
    while expectWord(tokens, '<', '<=', '>', '>='):
        oper = consume(tokens)
        right = addsub(tokens)
        expr = lang.Binary(expr, oper.value, right, token=oper)
    return expr

def equality(tokens: Tokens) -> lang.Expr:
    # <>, =
    expr = comparison(tokens)
    while expectWord(tokens, '<>', '='):
        oper = consume(tokens)
        right = comparison(tokens)
        expr = lang.Binary(expr, oper.value, right, token=oper)
    return expr

def logical(tokens: Tokens) -> lang.Expr:
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
    assignee: lang.GetExpr = identifier(tokens)
    while expectWord(tokens, '[', '.'):
        # Array get
        if matchWord(tokens, '['):
            assignee = indexExpr(tokens, assignee)
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
    return lang.Output(exprs)

def inputStmt(tokens: Tokens) -> lang.Input:
    name = identifier(tokens)
    matchWordElseError(tokens, '\n', msg="after statement")
    return lang.Input(name)

def colonRange(tokens: Tokens) -> lang.IndexRange:
    """Parse and return a start:end range as a tuple"""
    range_start = matchTypeElseError(tokens, 'INTEGER')
    matchWordElseError(tokens, ':', msg="in range")
    range_end = matchTypeElseError(tokens, 'INTEGER')
    return (range_start.value, range_end.value)

def declare(tokens: Tokens) -> lang.Declare:
    def expectTypeToken(tokens: Tokens):
        if not (
            expectWord(tokens, *builtin.TYPES)
            or expectType(tokens, 'name')
        ):
            raise builtin.ParseError("Invalid type", check(tokens))
        
    name = identifier(tokens).name  # Extract Name from UnresolvedName
    matchWordElseError(tokens, ':', msg="after name")
    expectTypeToken(tokens)
    metadata: lang.TypeMetadata = {}
    typetoken = consume(tokens)
    if typetoken.word == 'ARRAY':
        matchWordElseError(tokens, '[')
        metadata['size'] = (colonRange(tokens),)
        while matchWord(tokens, ','):
            metadata['size'] += (colonRange(tokens),)
        matchWordElseError(tokens, ']')
        matchWordElseError(tokens, 'OF')
        expectTypeToken(tokens)
        metadata['type'] = consume(tokens).word
    return lang.Declare(
        name,
        typetoken.word,
        metadata,
    )
    
def declareStmt(tokens: Tokens) -> lang.DeclareStmt:
    expr = declare(tokens)
    matchWordElseError(tokens, '\n', msg="after statement")
    return lang.DeclareStmt(expr)

def typeStmt(tokens: Tokens) -> lang.TypeStmt:
    name = identifier(tokens).name  # Extract Name from UnresolvedName
    matchWordElseError(tokens, '\n')
    exprs = []
    while not expectWord(tokens, 'ENDTYPE'):
        matchWordElseError(tokens, 'DECLARE')
        exprs += [declare(tokens)]
        matchWordElseError(tokens, '\n')
    matchWordElseError(tokens, 'ENDTYPE')
    matchWordElseError(tokens, '\n')
    return lang.TypeStmt(name, exprs)

def assignStmt(tokens: Tokens) -> lang.AssignStmt:
    expr = assignment(tokens)
    matchWordElseError(tokens, '\n', msg="after statement")
    return lang.AssignStmt(expr)

def caseStmt(tokens: Tokens) -> lang.Case:
    matchWordElseError(tokens, 'OF', msg="after CASE")
    parse = parser(tokens)
    cond: lang.Expr = parse(tokens)
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
    return lang.Case(cond, stmts, fallback)

def ifStmt(tokens: Tokens) -> lang.If:
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
    return lang.If(cond, stmts, fallback)

def whileStmt(tokens: Tokens) -> lang.While:
    cond = expression(tokens)
    matchWordElseError(tokens, 'DO', msg="after WHILE condition")
    matchWordElseError(tokens, '\n', msg="after DO")
    stmts = []
    while not matchWord(tokens, 'ENDWHILE'):
        stmts += [statement5(tokens)]
    matchWordElseError(tokens, '\n', msg="after ENDWHILE")
    return lang.While(None, cond, stmts)

def repeatStmt(tokens: Tokens) -> lang.Repeat:
    matchWordElseError(tokens, '\n', msg="after REPEAT")
    stmts = []
    while not matchWord(tokens, 'UNTIL'):
        stmts += [statement5(tokens)]
    cond = expression(tokens)
    matchWordElseError(tokens, '\n', msg="at end of UNTIL")
    return lang.Repeat(None, cond, stmts)

def forStmt(tokens: Tokens) -> lang.While:
    init = assignment(tokens)
    matchWordElseError(tokens, 'TO')
    parse = parser(tokens)
    end: lang.Expr = parse(tokens)
    step: lang.Expr = lang.Literal('INTEGER', 1, token=init.token())
    if matchWord(tokens, 'STEP'):
        parse = parser(tokens)
        step = parse(tokens)
    matchWordElseError(tokens, '\n', msg="at end of FOR")
    stmts = []
    while not matchWord(tokens, 'ENDFOR'):
        stmts += [statement5(tokens)]
    matchWordElseError(tokens, '\n', msg="after ENDFOR")
    # Generate loop cond
    cond = lang.Binary(init.assignee, builtin.lte, end, token=init.token())
    # Add increment statement
    incr = lang.Assign(
        init.assignee,
        lang.Binary(
            init.assignee,
            builtin.add,
            step,
            token=step.token(),
        ),
    )
    initStmt = lang.AssignStmt(init)
    incrStmt = lang.AssignStmt(incr)
    return lang.While(initStmt, cond, stmts + [incrStmt])

def procedureStmt(tokens: Tokens) -> lang.ProcedureStmt:
    name = identifier(tokens).name  # Extract Name from UnresolvedName
    params: List[lang.Declare] = []
    if matchWord(tokens, '('):
        passby: lang.Passby = 'BYVALUE'
        passbyToken = matchWord(tokens, 'BYVALUE', 'BYREF')
        if passbyToken:
            passby = passbyToken.word
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
    return lang.ProcedureStmt(name, passby, params, stmts, 'NULL')

def callStmt(tokens: Tokens) -> lang.CallStmt:
    parse = parser(tokens)
    callable: lang.Call = parse(tokens)
    matchWordElseError(tokens, '\n')
    return lang.CallStmt(callable)

def functionStmt(tokens: Tokens) -> lang.FunctionStmt:
    name = identifier(tokens).name  # Extract Name from UnresolvedName
    params: List[lang.Declare] = []
    if matchWord(tokens, '('):
        passby: lang.Passby = 'BYVALUE'
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
    return lang.FunctionStmt(
        name,
        passby,
        params,
        stmts,
        typetoken.word,
    )

def returnStmt(tokens: Tokens) -> lang.Return:
    expr = expression(tokens)
    matchWordElseError(tokens, '\n', msg="at end of RETURN")
    return lang.Return(expr)

def openfileStmt(tokens: Tokens) -> lang.OpenFile:
    parse = parser(tokens)
    filename: lang.Expr = parse(tokens)
    matchWordElseError(tokens, 'FOR', msg="after file identifier")
    mode = matchWordElseError(
        tokens, 'READ', 'WRITE', 'APPEND', msg="Invalid file mode"
    )
    matchWordElseError(tokens, '\n')
    return lang.OpenFile(filename, mode.word)

def readfileStmt(tokens: Tokens) -> lang.ReadFile:
    parse = parser(tokens)
    filename: lang.Expr = parse(tokens)
    matchWordElseError(tokens, ',', msg="after file identifier")
    varname = identifier(tokens)  # TODO: support other kinds of Gets
    matchWordElseError(tokens, '\n')
    return lang.ReadFile(filename, varname)

def writefileStmt(tokens: Tokens) -> lang.WriteFile:
    parse = parser(tokens)
    filename: lang.Expr = parse(tokens)
    matchWordElseError(tokens, ',', msg="after file identifier")
    data = expression(tokens)
    matchWordElseError(tokens, '\n')
    return lang.WriteFile(filename, data)

def closefileStmt(tokens: Tokens) -> lang.CloseFile:
    parse = parser(tokens)
    filename: lang.Expr = parse(tokens)
    matchWordElseError(tokens, '\n')
    return lang.CloseFile(filename)

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
