"""parser

parse(tokens: str) -> statements: list
    Parses tokens and returns a list of statements.
"""

from typing import Any, Optional, Union, Iterable, Mapping, Tuple, List
from typing import TypeVar, Callable as function

from . import builtin, lang

Tokens = List[lang.Token]
E = TypeVar('E')  # Expression type
R = TypeVar('R')  # Return type
R1 = TypeVar('R1')  # Additional return type
R2 = TypeVar('R2')  # Additional return type



# Helper functions

def atEnd(tokens: Tokens) -> bool:
    """Returns True if at last token."""
    return check(tokens).type == 'EOF'

def atEndThenError(tokens: Tokens) -> None:
    """Raises ParseError if at last token.
    This helps prevent infinite looping while parsing
    statements/expressions.
    """
    if atEnd(tokens):
        raise builtin.ParseError("Unexpected EOF", check(tokens))

def check(tokens: Tokens) -> lang.Token:
    """Returns token at cursor."""
    return tokens[0]

def consume(tokens: Tokens) -> lang.Token:
    """Returns token at cursor, advances cursor."""
    token = tokens.pop(0)
    return token

def expectWord(tokens: Tokens, *words: str) -> Optional[lang.Token]:
    """Returns token at cursor if its word matches given sequence of
    words, otherwise returns None.
    """
    if check(tokens).word in words:
        return check(tokens)
    atEndThenError(tokens)
    return None

def expectType(
    tokens: Tokens,
    *types: lang.Type,
) -> Optional[lang.Token]:
    """Returns token at cursor if its type matches given sequence of
    types, otherwise returns None.
    """
    if check(tokens).type in types:
        return check(tokens)
    atEndThenError(tokens)
    return None

def matchWord(tokens: Tokens, *words: str) -> Optional[lang.Token]:
    """Returns token at cursor if its word matches given sequence of
    words, otherwise returns None.

    matchWord differs from expectWord by advancing the cursor upon a
    match.
    """
    if check(tokens).word in words:
        return consume(tokens)
    atEndThenError(tokens)
    return None

def matchType(
    tokens: Tokens,
    *types: lang.Type,
) -> Optional[lang.Token]:
    """Returns token at cursor if its type matches given sequence of
    types, otherwise returns None.

    matchType differs from expectType by advancing the cursor upon a
    match.
    """
    if check(tokens).type in types:
        return consume(tokens)
    atEndThenError(tokens)
    return None

def matchWordElseError(
    tokens: Tokens,
    *words: str,
    msg: str='',
) -> lang.Token:
    """Returns token at cursor if its word matches given sequence of
    words, otherwise returns None.

    matchWordElseError differs from matchWord by raising an error
    instead of returning None if there is no match.
    """
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
    """Returns token at cursor if its type matches given sequence of
    types, otherwise returns None.

    matchTypeElseError differs from matchType by raising an error
    instead of returning None if there is no match.
    """
    token = matchType(tokens, *types)
    if token:
        return token
    msg = f"Expected {types}" + (f' {msg}' if msg else '')
    raise builtin.ParseError(msg, check(tokens))

def parseUntilExpectWord(
    tokens: Tokens,
    expectWords: Iterable[str],
    parse: function[[Tokens], R],
) -> List[R]:
    """
    Calls a parser until a matching word is found.
    Returns a list of all parsed statements.
    """
    parsedStmts = []
    while not expectWord(tokens, *expectWords):
        parsedStmts += [parse(tokens)]
    return parsedStmts

def parseUntilMatchWord(
    tokens: Tokens,
    matchWords: Iterable[str],
    parse: function[[Tokens], R],
) -> List[R]:
    """
    Calls a parser until a matching word is found.
    Consumes matched word.
    Returns a list of all parsed statements.
    """
    parsedStmts = []
    while not matchWord(tokens, *matchWords):
        parsedStmts += [parse(tokens)]
    return parsedStmts

def buildExprWhileWord(
    tokens: Tokens,
    parserMap: Mapping[str, function[[Tokens, E], R]],
    rootExpr,  # type: ignore
    advance: bool = False,
) -> R:
    """
    Builds an expression tree from a starting expr, using the parser
    provided for each matching word.

    Used mainly for binary expressions
    """
    while expectWord(tokens, *parserMap.keys()):
        parser = parserMap[check(tokens).word]
        if advance: consume(tokens)
        # Leave rootExpr untyped because its type keeps changing
        # and mypy hates that
        rootExpr = parser(tokens, rootExpr)
    return rootExpr

def collectExprsWhileWord(
    tokens: Tokens,
    goWords: Iterable[str],
    parse: function[[Tokens], R],
) -> List[R]:
    """
    Parses an expression, then continues parsing for more expressions
    if a matching word is found.
    """
    parsedExprs = [parse(tokens)]
    while matchWord(tokens, *goWords):
        parsedExprs += [parse(tokens)]
    return parsedExprs

def colonPair(
    tokens: Tokens,
    parseLeft: function[[Tokens], R1],
    parseRight: function[[Tokens], R2],
) -> Tuple[R1, R2]:
    """
    Matches a <left> : <right> colon pair.
    Returns a (left, right) tuple.
    """
    left = parseLeft(tokens)
    matchWordElseError(tokens, ':')
    right = parseRight(tokens)
    return left, right

def makeBinary(
    expr: lang.Expr, operToken: lang.Token, right: lang.Expr
) -> lang.Binary:
    return lang.Binary(expr, operToken.value, right, token=operToken)



# Precedence parsers
# The expression parsers use the recrusive descent parsing technique to
# handle expression precedence.
#
# Expressions are parsed with this precedence (highest to lowest):
# 1. <name> | <literal> | <unary> | <grouping> | <attr> | <index> | calls
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
    right: lang.Expr = value(tokens)
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

def attrExpr(tokens: Tokens, objExpr: lang.Expr) -> lang.GetAttr:
    assert (
        isinstance(objExpr, lang.UnresolvedName)
        or isinstance(objExpr, lang.Call)
        or isinstance(objExpr, lang.GetAttr)
        or isinstance(objExpr, lang.GetIndex)
    ), f"{objExpr!r}: Invalid NameExpr"
    name = identifier(tokens).name  # Extract Name from UnresolvedName
    return lang.GetAttr(objExpr, name)

def indexExpr(tokens: Tokens, arrayExpr: lang.Expr) -> lang.GetIndex:
    assert (
        isinstance(arrayExpr, lang.UnresolvedName)
        or isinstance(arrayExpr, lang.Call)
        or isinstance(arrayExpr, lang.GetAttr)
        or isinstance(arrayExpr, lang.GetIndex)
    ), f"{arrayExpr!r}: Invalid NameExpr"
    index = tuple(collectExprsWhileWord(tokens, [','], expression))
    matchWordElseError(tokens, ']')
    return lang.GetIndex(arrayExpr, index)

def name(tokens: Tokens) -> lang.NameExpr:
    expr: lang.UnresolvedName = identifier(tokens)
    nameExpr = buildExprWhileWord(
        tokens,
        parserMap={'[': indexExpr, '.': attrExpr},
        # Check for function call
        rootExpr=callExpr(tokens, expr) if matchWord(tokens, '(') else expr,
        advance=True,
    )
    assert (
        isinstance(nameExpr, lang.UnresolvedName)
        or isinstance(nameExpr, lang.Call)
        or isinstance(nameExpr, lang.GetAttr)
        or isinstance(nameExpr, lang.GetIndex)
    ), f"{nameExpr!r}: Invalid NameExpr"
    return nameExpr

def value(tokens: Tokens):
    """Dispatcher for highest-precedence parsing functions.
    """
    # Unary expressions
    if expectWord(tokens, '-', 'NOT'):
        return unary(tokens)
    #  A grouping
    if expectWord(tokens, '('):
        return grouping(tokens)
    # A single value
    if expectType(tokens, *builtin.TYPES):
        return literal(tokens)
    # A name or call or attribute
    if expectType(tokens, 'name'):
        return name(tokens)
    else:
        raise builtin.ParseError("Unexpected token", check(tokens))

def muldiv(tokens: Tokens) -> lang.Expr:
    # *, /
    expr: lang.Expr = value(tokens)
    parser = lambda tokens, expr: makeBinary(expr, consume(tokens), value(tokens))
    expr = buildExprWhileWord(
        tokens,
        parserMap={'*': parser, '/': parser},
        rootExpr=expr,
    )
    return expr

def addsub(tokens: Tokens) -> lang.Expr:
    expr = muldiv(tokens)
    parser = lambda tokens, expr: makeBinary(expr, consume(tokens), muldiv(tokens))
    expr = buildExprWhileWord(
        tokens,
        parserMap={'+': parser, '-': parser},
        rootExpr=expr,
    )
    return expr

def comparison(tokens: Tokens) -> lang.Expr:
    # <, <=, >, >=
    expr = addsub(tokens)
    parser = lambda tokens, expr: makeBinary(expr, consume(tokens), addsub(tokens))
    expr = buildExprWhileWord(
        tokens,
        parserMap={
            '<': parser,
            '<=': parser,
            '>': parser,
            '>=': parser
        },
        rootExpr=expr,
    )
    return expr

def equality(tokens: Tokens) -> lang.Expr:
    # <>, =
    expr = comparison(tokens)
    parser = lambda tokens, expr: makeBinary(
        expr, consume(tokens), comparison(tokens)
    )
    expr = buildExprWhileWord(
        tokens,
        parserMap={'<>': parser, '=': parser},
        rootExpr=expr,
    )
    return expr

def logical(tokens: Tokens) -> lang.Expr:
    # AND, OR
    expr = equality(tokens)
    parser = lambda tokens, expr: makeBinary(
        expr, consume(tokens), equality(tokens)
    )
    expr = buildExprWhileWord(
        tokens,
        parserMap={'AND': parser, 'OR': parser},
        rootExpr=expr,
    )
    return expr

def expression(tokens: Tokens) -> lang.Expr:
    expr = logical(tokens)
    return expr

def assignment(tokens: Tokens) -> lang.Assign:
    unresolvedName: lang.UnresolvedName = identifier(tokens)
    assignee = buildExprWhileWord(
        tokens,
        parserMap={'[': indexExpr, '.': attrExpr},
        rootExpr=unresolvedName,
        advance=True,
    )
    assert (
        isinstance(assignee, lang.UnresolvedName)
        or isinstance(assignee, lang.GetAttr)
        or isinstance(assignee, lang.GetIndex)
    ), f"{assignee!r}: Invalid assignee"
    matchWordElseError(tokens, '<-', msg="after name")
    expr = expression(tokens)
    return lang.Assign(assignee, expr)

# Statement parsers
# Statements are detected based on the first keyword of the line.
# Statements beginning with a name are assumed to be AssignStmts.

def outputStmt(tokens: Tokens) -> lang.Output:
    exprs = collectExprsWhileWord(tokens, [','], expression)
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

    name, typetoken = colonPair(tokens, identifier, consume)
    expectTypeToken([typetoken])
    metadata: lang.TypeMetadata = {}
    if typetoken.word == 'ARRAY':
        matchWordElseError(tokens, '[')
        indexRanges: List[lang.IndexRange] = collectExprsWhileWord(
            tokens, [','], colonRange
        )
        metadata['size'] = indexRanges
        matchWordElseError(tokens, ']')
        matchWordElseError(tokens, 'OF')
        expectTypeToken(tokens)
        metadata['type'] = consume(tokens).word
    return lang.Declare(name.name, typetoken.word, metadata)
    
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
        exprs += [declareStmt(tokens).expr]
    matchWordElseError(tokens, 'ENDTYPE')
    matchWordElseError(tokens, '\n')
    return lang.TypeStmt(name, exprs)

def assignStmt(tokens: Tokens) -> lang.AssignStmt:
    expr = assignment(tokens)
    matchWordElseError(tokens, '\n', msg="after statement")
    return lang.AssignStmt(expr)

def caseStmt(tokens: Tokens) -> lang.Case:
    matchWordElseError(tokens, 'OF', msg="after CASE")
    cond: lang.Expr = value(tokens)
    matchWordElseError(tokens, '\n', msg="after CASE OF")
    stmts: lang.CaseMap = dict(parseUntilExpectWord(
        tokens,
        ['OTHERWISE', 'ENDCASE'],
        lambda tokens: colonPair(tokens,
                                 lambda tokens: literal(tokens).value,
                                 lambda tokens: [statement1(tokens)])
    ))
    if matchWord(tokens, 'OTHERWISE'):
        fallback = [statement6(tokens)]
    else:
        fallback = None
    matchWordElseError(tokens, 'ENDCASE', msg="at end of CASE")
    matchWordElseError(tokens, '\n', msg="after ENDCASE")
    return lang.Case(cond, stmts, fallback)

def ifStmt(tokens: Tokens) -> lang.If:
    cond = expression(tokens)
    matchWord(tokens, '\n')  # optional line break
    matchWordElseError(tokens, 'THEN')
    matchWordElseError(tokens, '\n', msg="after THEN")
    stmts: lang.CaseMap = {
        True: parseUntilExpectWord(tokens, ['ELSE', 'ENDIF'], statement1)
    }
    if matchWord(tokens, 'ELSE'):
        matchWordElseError(tokens, '\n', msg="after ELSE")
        fallback = parseUntilMatchWord(tokens, ['ENDIF'], statement4)
    else:
        fallback = None
        matchWordElseError(tokens, 'ENDIF', msg="at end of IF")
    matchWordElseError(tokens, '\n', msg="after statement")
    return lang.If(cond, stmts, fallback)

def whileStmt(tokens: Tokens) -> lang.While:
    cond = expression(tokens)
    matchWordElseError(tokens, 'DO', msg="after WHILE condition")
    matchWordElseError(tokens, '\n', msg="after DO")
    stmts = parseUntilMatchWord(tokens, ['ENDWHILE'], statement4)
    matchWordElseError(tokens, '\n', msg="after ENDWHILE")
    return lang.While(None, cond, stmts)

def repeatStmt(tokens: Tokens) -> lang.Repeat:
    matchWordElseError(tokens, '\n', msg="after REPEAT")
    stmts = parseUntilMatchWord(tokens, ['UNTIL'], statement4)
    cond = expression(tokens)
    matchWordElseError(tokens, '\n', msg="at end of UNTIL")
    return lang.Repeat(None, cond, stmts)

def forStmt(tokens: Tokens) -> lang.While:
    init = assignment(tokens)
    matchWordElseError(tokens, 'TO')
    end: lang.Expr = expression(tokens)
    step: lang.Expr = lang.Literal('INTEGER', 1, token=init.token)
    if matchWord(tokens, 'STEP'):
        step = expression(tokens)
    matchWordElseError(tokens, '\n', msg="at end of FOR")
    stmts = parseUntilMatchWord(tokens, ['ENDFOR'], statement4)
    matchWordElseError(tokens, '\n', msg="after ENDFOR")
    # Generate loop cond
    cond = lang.Binary(init.assignee, builtin.lte, end, token=init.token)
    # Add increment statement
    incr = lang.Assign(
        init.assignee,
        lang.Binary(
            init.assignee,
            builtin.add,
            step,
            token=step.token,
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
            passby = passbyToken.word  # type: ignore
        params = collectExprsWhileWord(tokens, [','], declare)
        matchWordElseError(tokens, ')')
    matchWordElseError(tokens, '\n', msg="after parameters")
    stmts = parseUntilMatchWord(tokens, ['ENDPROCEDURE'], statement3)
    matchWordElseError(tokens, '\n', msg="after ENDPROCEDURE")
    return lang.ProcedureStmt(name, passby, params, stmts, 'NULL')

def callStmt(tokens: Tokens) -> lang.CallStmt:
    callable: lang.Call = value(tokens)
    matchWordElseError(tokens, '\n')
    return lang.CallStmt(callable)

def functionStmt(tokens: Tokens) -> lang.FunctionStmt:
    name = identifier(tokens).name  # Extract Name from UnresolvedName
    params: List[lang.Declare] = []
    if matchWord(tokens, '('):
        passby: lang.Passby = 'BYVALUE'
        params = collectExprsWhileWord(tokens, [','], declare)
        matchWordElseError(tokens, ')', msg="at end of parameters")
    matchWordElseError(tokens, 'RETURNS', msg="after parameters")
    typetoken = matchWordElseError(tokens, *builtin.TYPES, msg="Invalid type")
    matchWordElseError(tokens, '\n', msg="at end of FUNCTION")
    stmts = parseUntilMatchWord(tokens, ['ENDFUNCTION'], statement3)
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
    filename: lang.Expr = value(tokens)
    matchWordElseError(tokens, 'FOR', msg="after file identifier")
    mode = matchWordElseError(
        tokens, 'READ', 'WRITE', 'APPEND', msg="Invalid file mode"
    )
    matchWordElseError(tokens, '\n')
    return lang.OpenFile(filename, mode.word)

def readfileStmt(tokens: Tokens) -> lang.ReadFile:
    filename: lang.Expr = value(tokens)
    matchWordElseError(tokens, ',', msg="after file identifier")
    varname = identifier(tokens)  # TODO: support other kinds of Gets
    matchWordElseError(tokens, '\n')
    return lang.ReadFile(filename, varname)

def writefileStmt(tokens: Tokens) -> lang.WriteFile:
    filename: lang.Expr = value(tokens)
    matchWordElseError(tokens, ',', msg="after file identifier")
    data = expression(tokens)
    matchWordElseError(tokens, '\n')
    return lang.WriteFile(filename, data)

def closefileStmt(tokens: Tokens) -> lang.CloseFile:
    filename: lang.Expr = value(tokens)
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
    """Select a parsing function to use, from the next token, and use it.
    """
    lastline = tokens[-1].line
    tokens += [lang.Token(lastline, 0, 'EOF', "", None)]
    statements = []
    while not atEnd(tokens):
        # ignore empty lines
        collectExprsWhileWord(tokens, ['\n'], lambda tokens: None)
        statements += [statement2(tokens)]
    return statements
