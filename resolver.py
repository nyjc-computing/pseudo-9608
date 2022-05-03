from builtin import lt, lte, gt, gte, ne, eq
from builtin import add, sub, mul, div
from builtin import LogicError
from builtin import NULL
from lang import TypedValue, Callable, Function, Procedure
from lang import Literal, Declare, Unary, Binary, Get, Call



# Helper functions

def isProcedure(callable):
    return isinstance(callable, Procedure)

def isFunction(callable):
    return isinstance(callable, Function)

def expectTypeElseError(exprtype, expected, name=None):
    if exprtype != expected:
        if not name: name = exprtype
        raise LogicError(f"{exprtype} <> {expected}", name)

def declaredElseError(frame, name, errmsg="Undeclared", declaredType=None):
    if name not in frame:
        raise LogicError(errmsg, name)
    if declaredType:
        expectTypeElseError(frame[name], declaredType)

def declareVar(frame, name, type):
    """Declare a name in a frame"""
    if name in frame:
        raise LogicError("Already declared", name)
    frame[name] = TypedValue(type, None)

def getType(frame, name):
    declaredElseError(frame, name)
    return frame[name].type

def getValue(frame, name):
    """Retrieve value from a frame using a name"""
    declaredElseError(frame, name)
    if frame[name].value is None:
        raise LogicError("No value assigned", name)
    return frame[name].value

def setValue(frame, name, value):
    """Set a value for a declared variable in a frame"""
    declaredElseError(frame, name)
    frame[name].value = value

def value(frame, expr):
    """Return the value of a Literal"""
    return expr.value

# Resolvers

def resolveExprs(frame, exprs):
    for expr in exprs:
        expr.accept(frame, resolve)

def resolveLiteral(frame, literal):
    return literal.type

def resolveDeclare(frame, expr):
    """Declare variable in frame"""
    declareVar(frame, expr.name, expr.type)
    return expr.type

def resolveUnary(frame, expr):
    righttype = expr.right.accept(frame, resolve)
    if expr.oper is sub:
        expectTypeElseError(righttype, 'INTEGER')
        return 'INTEGER'
    else:
        raise ValueError("Unexpected oper {expr.oper}")

def resolveBinary(frame, expr):
    lefttype = expr.left.accept(frame, resolve)
    righttype = expr.right.accept(frame, resolve)
    if expr.oper in (gt, gte, lt, lte, ne, eq):
        expectTypeElseError(lefttype, 'INTEGER')
        expectTypeElseError(righttype, 'INTEGER')
        return 'BOOLEAN'
    if expr.oper in (add, sub, mul, div):
        # TODO: Handle REAL type
        expectTypeElseError(lefttype, 'INTEGER')
        expectTypeElseError(righttype, 'INTEGER')
        return 'INTEGER'

def resolveGet(frame, expr):
    """Insert frame into Get expr"""
    assert isinstance(expr, Get), "Not a Get Expr"
    expr.frame = frame
    return getType(frame, expr.name)

def resolveProcCall(frame, expr):
    expr.callable.accept(frame, resolveGet)
    callable = getValue(frame, expr.callable.name)
    if not isProcedure(callable):
        raise LogicError("Not PROCEDURE", expr.callable.name)
    resolveCall(frame, expr)

def resolveFuncCall(frame, expr):
    expr.callable.accept(frame, resolveGet)
    callable = getValue(frame, expr.callable.name)
    if not isFunction(callable):
        raise LogicError("Not FUNCTION", expr.callable.name)
    resolveCall(frame, expr)
    
def resolveCall(frame, expr):
    """
    resolveCall() does not carry out any frame insertion or
    type-checking. These should be carried out first (e.g. in a wrapper
    function) before resolveCall() is invoked.
    """
    callable = getValue(frame, expr.callable.name)
    if not (isProcedure(callable) or isFunction(callable)):
        raise LogicError("Not callable", expr.callable.name)
    numArgs, numParams = len(expr.args), len(callable['params'])
    if numArgs != numParams:
        raise LogicError(
            f"Expected {numParams} args, got {numArgs}",
            None,
        )
    # Type-check arguments
    for arg, param in zip(expr.args, callable['params']):
        # param is a slot from either local or frame
        argtype = arg.accept(frame, resolve)
        expectTypeElseError(argtype, param.type)

def resolve(frame, expr):
    if isinstance(expr, Literal):
        return expr.accept(frame, resolveLiteral)
    if isinstance(expr, Declare):
        return expr.accept(frame, resolveDeclare)
    elif isinstance(expr, Unary):
        return expr.accept(frame, resolveUnary)
    elif isinstance(expr, Binary):
        return expr.accept(frame, resolveBinary)
    elif isinstance(expr, Get):
        return expr.accept(frame, resolveGet)
    elif isinstance(expr, Call):
        return expr.accept(frame, resolveFuncCall)


        
# Verifiers

def verifyStmts(frame, stmts):
    for stmt in stmts:
        stmt.accept(frame, verify)

def verifyOutput(frame, stmt):
    resolveExprs(frame, stmt.exprs)

def verifyInput(frame, stmt):
    declaredElseError(frame, stmt.name)

def verifyAssign(frame, stmt):
    declaredElseError(frame, stmt.name)
    exprtype = stmt.expr.accept(frame, resolve)
    expectTypeElseError(exprtype, getType(frame, stmt.name))

def verifyCase(frame, stmt):
    stmt.cond.accept(frame, resolve)
    verifyStmts(frame, stmt.stmts.values())
    if stmt.fallback:
        stmt.fallback.accept(frame, verify)

def verifyIf(frame, stmt):
    stmt.cond.accept(frame, resolve)
    expectTypeElseError(stmt.cond, 'BOOLEAN')
    verifyStmts(frame, stmt.stmts[True])
    if stmt.fallback:
        verifyStmts(frame, stmt.fallback)

def verifyLoop(frame, stmt):
    if stmt.init:
        stmt.init.accept(frame, verify)
    condtype = stmt.cond.accept(frame, resolve)
    expectTypeElseError(condtype, 'BOOLEAN')
    verifyStmts(frame, stmt.stmts)

def verifyProcedure(frame, stmt):
    # Set up local frame
    local = {}
    for i, expr in enumerate(stmt.params):
        if stmt.passby == 'BYREF':
            exprtype = expr.accept(local, resolveDeclare)
            expectTypeElseError(exprtype, getType(frame, expr.name))
            # Reference frame vars in local
            local[expr.name] = getValue(frame, expr.name)
        else:
            declareVar(local, expr.name, expr.type)
        # params: replace Declare Expr with slot
        stmt.params[i] = local[expr.name]
    # Resolve procedure statements using local
    verifyStmts(local, stmt.stmts)
    # Declare procedure in frame
    declareVar(frame, stmt.name, 'procedure')
    setValue(frame, stmt.name, Procedure(
        local, stmt.params, stmt.stmts
    ))

def verifyFunction(frame, stmt):
    # Set up local frame
    local = {}
    for expr in stmt.params:
        # Declare vars in local
        expr.accept(local, resolveDeclare)
    # Resolve procedure statements using local
    hasReturn = False
    for procstmt in stmt.stmts:
        stmtType = procstmt.accept(local, verify)
        if stmtType:
            hasReturn = True
            expectTypeElseError(stmtType, stmt.returnType, stmt.name)
    if not hasReturn:
        raise LogicError("No RETURN in function", None)
    # Declare function in frame
    declareVar(frame, stmt.name, stmt.returnType)
    setValue(frame, stmt.name, Function(
        local, stmt.params, stmt.stmts
    ))

def verifyFile(frame, stmt):
    stmt.name.accept(frame, value)
    if stmt.action == 'open':
        pass
    elif stmt.action == 'read':
        stmt.data.accept(frame, resolve)
    elif stmt.action == 'write':
        stmt.data.accept(frame, resolve)
    elif stmt.action == 'close':
        pass

def verify(frame, stmt):
    if stmt.rule == 'output':
        stmt.accept(frame, verifyOutput)
    if stmt.rule == 'input':
        stmt.accept(frame, verifyInput)
    elif stmt.rule == 'declare':
        stmt.expr.accept(frame, resolveDeclare)
    elif stmt.rule == 'assign':
        stmt.accept(frame, verifyAssign)
    elif stmt.rule == 'case':
        stmt.accept(frame, verifyCase)
    elif stmt.rule == 'if':
        stmt.accept(frame, verifyIf)
    elif stmt.rule in ('while', 'repeat', 'for'):
        stmt.accept(frame, verifyLoop)
    elif stmt.rule == 'procedure':
        stmt.accept(frame, verifyProcedure)
    elif stmt.rule == 'call':
        stmt.expr.accept(frame, resolveProcCall)
    elif stmt.rule == 'function':
        stmt.accept(frame, verifyFunction)
    elif stmt.rule == 'file':
        stmt.accept(frame, verifyFile)
    elif stmt.rule == 'return':
        return stmt.expr.accept(frame, resolve)



def inspect(statements):
    frame = {}
    verifyStmts(frame, statements)
    return statements, frame
