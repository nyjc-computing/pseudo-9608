from builtin import lt, lte, gt, gte, ne, eq
from builtin import add, sub, mul, div
from builtin import LogicError
from lang import Frame, Function, Procedure
from lang import Literal, Declare, Unary, Binary, Get, Call, Assign



# Helper functions

def isProcedure(callable):
    return isinstance(callable, Procedure)

def isFunction(callable):
    return isinstance(callable, Function)

def expectTypeElseError(exprtype, expected, *, token=None):
    if exprtype != expected:
        if not token: token = exprtype
        raise LogicError(f"{exprtype} <> {expected}", token)

def declaredElseError(frame, name, errmsg="Undeclared", declaredType=None, *, token=None):
    if not frame.has(name):
        raise LogicError(errmsg, name, token)
    if declaredType:
        expectTypeElseError(frame.getType(name), declaredType, token=token)

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
    frame.declare(expr.name, expr.type)
    return expr.type

def resolveUnary(frame, expr):
    righttype = expr.right.accept(frame, resolve)
    if expr.oper is sub:
        expectTypeElseError(righttype, 'INTEGER', token=expr.right.token())
        return 'INTEGER'
    else:
        raise ValueError("Unexpected oper {expr.oper}")

def resolveBinary(frame, expr):
    lefttype = expr.left.accept(frame, resolve)
    righttype = expr.right.accept(frame, resolve)
    if expr.oper in (gt, gte, lt, lte, ne, eq):
        expectTypeElseError(lefttype, 'INTEGER', token=expr.left.token())
        expectTypeElseError(righttype, 'INTEGER', token=expr.right.token())
        return 'BOOLEAN'
    if expr.oper in (add, sub, mul, div):
        # TODO: Handle REAL type
        expectTypeElseError(lefttype, 'INTEGER', token=expr.left.token())
        expectTypeElseError(righttype, 'INTEGER', token=expr.right.token())
        return 'INTEGER'

def resolveAssign(frame, expr):
    declaredElseError(frame, expr.name)
    exprType = expr.expr.accept(frame, resolve)
    expectTypeElseError(exprType, frame.getType(expr.name), token=expr.token())

def resolveGet(frame, expr):
    """Insert frame into Get expr"""
    assert isinstance(expr, Get), "Not a Get Expr"
    expr.frame = frame
    return frame.getType(expr.name)

def resolveProcCall(frame, expr):
    expr.callable.accept(frame, resolveGet)
    callable = frame.getValue(expr.callable.name)
    if not isProcedure(callable):
        raise LogicError("Not PROCEDURE", token=expr.callable.token())
    resolveCall(frame, expr)

def resolveFuncCall(frame, expr):
    expr.callable.accept(frame, resolveGet)
    callable = frame.getValue(expr.callable.name)
    if not isFunction(callable):
        raise LogicError("Not FUNCTION", token=expr.callable.token())
    resolveCall(frame, expr)
    
def resolveCall(frame, expr):
    """
    resolveCall() does not carry out any frame insertion or
    type-checking. These should be carried out first (e.g. in a wrapper
    function) before resolveCall() is invoked.
    """
    callable = frame.getValue(expr.callable.name)
    numArgs, numParams = len(expr.args), len(callable.params)
    if numArgs != numParams:
        raise LogicError(
            f"Expected {numParams} args, got {numArgs}",
            token=expr.callable.token(),
        )
    # Type-check arguments
    for arg, param in zip(expr.args, callable.params):
        # param is a slot from either local or frame
        argtype = arg.accept(frame, resolve)
        expectTypeElseError(argtype, param.type, token=arg.token())

def resolve(frame, expr):
    if isinstance(expr, Literal):
        return expr.accept(frame, resolveLiteral)
    if isinstance(expr, Declare):
        return expr.accept(frame, resolveDeclare)
    elif isinstance(expr, Unary):
        return expr.accept(frame, resolveUnary)
    elif isinstance(expr, Binary):
        return expr.accept(frame, resolveBinary)
    elif isinstance(expr, Assign):
        return expr.accept(frame, resolveAssign)
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

def verifyCase(frame, stmt):
    stmt.cond.accept(frame, resolve)
    verifyStmts(frame, stmt.stmts.values())
    if stmt.fallback:
        stmt.fallback.accept(frame, verify)

def verifyIf(frame, stmt):
    condType = stmt.cond.accept(frame, resolve)
    expectTypeElseError(condType, 'BOOLEAN', token=stmt.cond.token())
    verifyStmts(frame, stmt.stmts[True])
    if stmt.fallback:
        verifyStmts(frame, stmt.fallback)

def verifyLoop(frame, stmt):
    if stmt.init:
        stmt.init.accept(frame, verify)
    condtype = stmt.cond.accept(frame, resolve)
    expectTypeElseError(condtype, 'BOOLEAN', token=stmt.cond.token())
    verifyStmts(frame, stmt.stmts)

def verifyProcedure(frame, stmt):
    # Set up local frame
    local = Frame()
    for i, expr in enumerate(stmt.params):
        if stmt.passby == 'BYREF':
            exprtype = expr.accept(local, resolveDeclare)
            expectTypeElseError(exprtype, frame.getType(expr.name), token=expr.token())
            # Reference frame vars in local
            local.setValue(expr.name, frame.getValue(expr.name))
        else:
            expr.accept(local, resolveDeclare)
        # params: replace Declare Expr with slot
        stmt.params[i] = local.get(expr.name)
    # Resolve procedure statements using local
    verifyStmts(local, stmt.stmts)
    # Declare procedure in frame
    frame.declare(stmt.name, 'NULL')
    frame.setValue(stmt.name, Procedure(
        local, stmt.params, stmt.stmts
    ))

def verifyFunction(frame, stmt):
    # Set up local frame
    local = Frame()
    for expr in stmt.params:
        # Declare vars in local
        expr.accept(local, resolveDeclare)
    # Resolve procedure statements using local
    hasReturn = False
    for procstmt in stmt.stmts:
        stmtType = procstmt.accept(local, verify)
        if stmtType:
            hasReturn = True
            expectTypeElseError(stmtType, stmt.returnType, token=stmt.name.token())
    if not hasReturn:
        raise LogicError("No RETURN in function", stmt.name.token())
    # Declare function in frame
    frame.declare(stmt.name, stmt.returnType)
    frame.setValue(stmt.name, Function(
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
    elif stmt.rule == 'case':
        stmt.accept(frame, verifyCase)
    elif stmt.rule == 'if':
        stmt.accept(frame, verifyIf)
    elif stmt.rule in ('while', 'repeat', 'for'):
        stmt.accept(frame, verifyLoop)
    elif stmt.rule == 'procedure':
        stmt.accept(frame, verifyProcedure)
    elif stmt.rule == 'function':
        stmt.accept(frame, verifyFunction)
    elif stmt.rule == 'file':
        stmt.accept(frame, verifyFile)
    elif stmt.rule in ('assign', 'declare', 'return'):
        return stmt.expr.accept(frame, resolve)
    elif stmt.rule == 'call':
        stmt.expr.accept(frame, resolveProcCall)



def inspect(statements):
    frame = Frame()
    verifyStmts(frame, statements)
    return statements, frame
