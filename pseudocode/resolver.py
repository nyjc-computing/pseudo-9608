from .builtin import AND, OR, NOT
from .builtin import lt, lte, gt, gte, ne, eq
from .builtin import add, sub, mul, div
from .builtin import LogicError
from .builtin import NULL, NUMERIC, EQUATABLE
from .lang import Object, Frame, Builtin, Function, Procedure
from .lang import Literal, Declare, Unary, Binary, Get, Call, Assign



# Helper functions

def isProcedure(callable):
    return isinstance(callable, Procedure)

def isFunction(callable):
    return type(callable) in (Builtin, Function)

def expectTypeElseError(exprtype, *expected, token=None):
    assert token, "Missing token"
    if exprtype not in expected:
        # Stringify expected types
        if len(expected) == 1:
            expected = expected[0]
        else:
            expected = f"({', '.join(expected)})"
        raise LogicError(f"Expected {expected}, is {exprtype}", token)

def declaredElseError(
    frame,
    name,
    errmsg="Undeclared",
    declaredType=None,
    *,
    token=None,
):
    if not frame.has(name):
        raise LogicError(errmsg, name, token)
    if declaredType:
        expectTypeElseError(
            frame.getType(name), declaredType, token=token
        )

def value(frame, expr):
    """Return the value of a Literal"""
    return expr.value



class Resolver:
    """
    Resolves a list of statements with the given frame.
    """
    def __init__(self, frame, statements):
        self.frame = frame
        self.statements = statements

    def inspect(self):
        verifyStmts(self.frame, self.statements)


    
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
    rType = expr.right.accept(frame, resolve)
    if expr.oper is sub:
        expectTypeElseError(rType, *NUMERIC, token=expr.right.token())
        return rType
    if expr.oper is NOT:
        expectTypeElseError(
            rType, 'BOOLEAN', token=expr.right.token()
        )
        return 'BOOLEAN'
    raise ValueError(f"Unexpected oper {expr.oper}")

def resolveBinary(frame, expr):
    lType = expr.left.accept(frame, resolve)
    rType = expr.right.accept(frame, resolve)
    if expr.oper in (AND, OR):
        expectTypeElseError(lType, 'BOOLEAN', token=expr.left.token())
        expectTypeElseError(rType, 'BOOLEAN', token=expr.right.token())
        return 'BOOLEAN'
    if expr.oper in (ne, eq):
        expectTypeElseError(lType, *EQUATABLE, token=expr.left.token())
        expectTypeElseError(rType, *EQUATABLE, token=expr.right.token())
        if not (
            (lType == 'BOOLEAN' and rType == 'BOOLEAN')
            or (lType in NUMERIC and rType in NUMERIC)
        ):
            raise LogicError(
                f"Illegal comparison of {lType} and {rType}",
                token=expr.oper.token(),
            )
        return 'BOOLEAN'
    if expr.oper in (gt, gte, lt, lte):
        expectTypeElseError(lType, *NUMERIC, token=expr.left.token())
        expectTypeElseError(rType, *NUMERIC, token=expr.left.token())
        return 'BOOLEAN'
    if expr.oper in (add, sub, mul, div):
        expectTypeElseError(lType, *NUMERIC, token=expr.left.token())
        expectTypeElseError(rType, *NUMERIC, token=expr.left.token())
        if (expr.oper is not div) and (lType == rType == 'INTEGER'):
            return 'INTEGER'
        return 'REAL'

def resolveAssign(frame, expr):
    # assignee frame might be a Frame or Get(Object)
    assnType = expr.assignee.accept(frame, resolveGet)
    exprType = expr.expr.accept(frame, resolve)
    expectTypeElseError(
        exprType, assnType, token=expr.token()
    )

def resolveGet(frame, expr):
    """Insert frame into Get expr"""
    assert isinstance(expr, Get), "Not a Get Expr"
    # frame can be a Frame, or a Get Expr (for an Object)
    # If frame is a Get Expr, resolve it recursively
    if isinstance(expr.frame, Get):
        # Pass original frame for recursive resolving
        objType = expr.frame.accept(frame, resolveGet)
        # Resolve object type in typesystem
        declaredElseError(
            frame.types, objType,
            errmsg="Undeclared type", token=expr.token()
        )
        objTemplate = frame.types.getTemplate(objType).value
        # Attribute type is different from object type
        declaredElseError(
            objTemplate, expr.name,
            errmsg="Undeclared attribute", token=expr.token()
        )
        return objTemplate.getType(expr.name)
    if expr.frame is NULL:
        while not frame.has(expr.name):
            frame = frame.lookup(expr.name)
            if not frame:
                raise LogicError("Undeclared", expr.token())
        expr.frame = frame
        return frame.getType(expr.name)

def resolveProcCall(frame, expr):
    expr.callable.accept(frame, resolveGet)
    # Resolve global frame where procedure is declared
    callFrame = expr.callable.frame
    callable = callFrame.getValue(expr.callable.name)
    if not isProcedure(callable):
        raise LogicError("Not PROCEDURE", token=expr.callable.token())
    resolveCall(frame, expr)

def resolveFuncCall(frame, expr):
    expr.callable.accept(frame, resolveGet)
    # Resolve global frame where function is declared
    callFrame = expr.callable.frame
    callable = callFrame.getValue(expr.callable.name)
    if not isFunction(callable):
        raise LogicError("Not FUNCTION", token=expr.callable.token())
    resolveCall(frame, expr)
    
def resolveCall(frame, expr):
    """
    resolveCall() does not carry out any frame insertion or
    type-checking. These should be carried out first (e.g. in a wrapper
    function) before resolveCall() is invoked.
    """
    callable = expr.callable.frame.getValue(expr.callable.name)
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
        stmtType = stmt.accept(frame, verify)
        # For Return statements
        if stmtType:
            expectTypeElseError(
                stmtType, stmt.returnType, token=stmt.name.token()
            )

def verifyOutput(frame, stmt):
    resolveExprs(frame, stmt.exprs)

def verifyInput(frame, stmt):
    declaredElseError(frame, stmt.name)

def verifyCase(frame, stmt):
    stmt.cond.accept(frame, resolve)
    verifyStmts(frame, stmt.stmtMap.values())
    if stmt.fallback:
        stmt.fallback.accept(frame, verify)

def verifyIf(frame, stmt):
    condType = stmt.cond.accept(frame, resolve)
    expectTypeElseError(condType, 'BOOLEAN', token=stmt.cond.token())
    verifyStmts(frame, stmt.stmtMap[True])
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
    local = Frame(outer=frame)
    # Assign procedure in frame first, to make recursive calls work
    frame.declare(stmt.name, 'NULL')
    frame.setValue(stmt.name, Procedure(
        local, stmt.params, stmt.stmts
    ))
    for i, expr in enumerate(stmt.params):
        if stmt.passby == 'BYREF':
            exprtype = expr.accept(local, resolveDeclare)
            expectTypeElseError(
                exprtype, frame.getType(expr.name), token=expr.token()
            )
            # Reference frame vars in local
            local.setValue(expr.name, frame.getValue(expr.name))
        else:
            expr.accept(local, resolveDeclare)
        # params: replace Declare Expr with slot
        stmt.params[i] = local.get(expr.name)
    # Resolve procedure statements using local
    verifyStmts(local, stmt.stmts)

def verifyFunction(frame, stmt):
    # Set up local frame
    local = Frame(outer=frame)
    # Assign function in frame first, to make recursive calls work
    frame.declare(stmt.name, stmt.returnType)
    frame.setValue(stmt.name, Function(
        local, stmt.params, stmt.stmts
    ))
    for expr in stmt.params:
        # Declare vars in local
        expr.accept(local, resolveDeclare)
    # Resolve procedure statements using local
    hasReturn = False
    for procstmt in stmt.stmts:
        stmtType = procstmt.accept(local, verify)
        if stmtType:
            hasReturn = True
            expectTypeElseError(
                stmtType, stmt.returnType, token=stmt.name.token()
            )
    if not hasReturn:
        raise LogicError("No RETURN in function", stmt.name.token())

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

def verifyDeclareType(frame, stmt):
    frame.types.declare(stmt.name)
    obj = Object(typesys=frame.types)
    for expr in stmt.exprs:
        resolveDeclare(obj, expr)
    frame.types.setTemplate(stmt.name, obj)
    


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
    elif stmt.rule == 'declaretype':
        stmt.accept(frame, verifyDeclareType)
    elif stmt.rule in ('assign', 'declare', 'return'):
        return stmt.expr.accept(frame, resolve)
    elif stmt.rule == 'call':
        stmt.expr.accept(frame, resolveProcCall)
