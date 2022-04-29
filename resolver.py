from builtin import lt, lte, gt, gte, ne, eq
from builtin import add, sub, mul, div
from builtin import LogicError
from lang import Literal, Declare, Unary, Binary, Get, Call



# Helper functions

def expectTypeElseError(exprtype, expected):
    if exprtype != expected:
        raise LogicError(f"Expected {expected}", exprtype)

def resolveExprs(frame, exprs):
    for expr in exprs:
        expr.resolve(frame)

def verifyStmts(frame, stmts):
    for stmt in stmts:
        stmt.accept(frame, verify)

def verifyOutput(frame, stmt):
    resolveExprs(frame, stmt.exprs)

def verifyInput(frame, stmt):
    name = stmt.name
    if name not in frame:
        raise LogicError(
            f'Name not declared',
            stmt.name,
        )

def get(frame, expr):
    """Evaluate a Get expr to retrieve value from frame"""
    if expr.name not in frame:
        raise LogicError("Undeclared", expr.name)
    if frame[expr.name] is None:
        raise LogicError("No value assigned", expr.name)
    return frame[expr.name]

def value(frame, expr):
    """Return the value of a Literal"""
    return expr.value

def resolveLiteral(frame, literal):
    return literal.type

def resolveDeclare(frame, expr):
    if expr.name in frame:
        raise LogicError("Already declared", expr.name)
    frame[expr.name] = {'type': expr.type, 'value': None}
    return expr.type

def resolveUnary(frame, expr):
    expr.right.accept(frame, resolve)

def resolveBinary(frame, expr):
    expr.left.accept(frame, resolve)
    expr.right.accept(frame, resolve)

def resolveGet(frame, expr):
    """Insert frame into Get expr"""
    assert isinstance(expr, Get), "Not a Get Expr"
    expr.frame = frame
    return frame[expr.name]['type']

def resolveCall(frame, expr):
    # Insert frame
    breakpoint()
    calltype = expr.callable.accept(frame, resolveGet)
    callable = expr.callable.accept(frame, get)
    breakpoint()
    expectTypeElseError(calltype, 'procedure')
    # if len(stmt.args) != len(proc['params']):
    #     raise LogicError(
    #         f"Expected {len(proc['params'])} args, got {len(stmt.args)}",
    #         None,
    #     )
    # # Type-check arguments
    # local = proc['frame']
    # for arg, param in zip(stmt.args, proc['params']):
    #     if stmt.passby == 'BYREF':
    #         arg.resolve(frame)
    #         # Only names allowed for BYREF arguments
    #         if not isinstance(arg, Get):
    #             raise LogicError(
    #                 'BYREF arg must be a name, not expression',
    #                 None,
    #             )
    #     else:
    #         arg.resolve(local)
    #     paramtype = param['type']
    #     expectTypeElseError(frame, arg, paramtype)



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
        return expr.accept(frame, resolveCall)
        
def verifyAssign(frame, stmt):
    exprtype = stmt.expr.accept(frame, resolve)
    expectTypeElseError(exprtype, frame[stmt.name]['type'])

def verifyCase(frame, stmt):
    stmt.cond.resolve(frame)
    verifyStmts(frame, stmt.stmts.values())
    if stmt.fallback:
        stmt.fallback.accept(frame, verify)

def verifyIf(frame, stmt):
    stmt.cond.resolve(frame)
    expectTypeElseError(stmt.cond, 'BOOLEAN')
    verifyStmts(frame, stmt.stmts[True])
    if stmt.fallback:
        verifyStmts(frame, stmt.fallback)

def verifyLoop(frame, stmt):
    if stmt.init:
        stmt.init.accept(frame, verify)
    stmt.cond.resolve(frame)
    expectTypeElseError(frame, stmt.cond, 'BOOLEAN')
    verifyStmts(frame, stmt.stmts)

def verifyProcedure(frame, stmt):
    # Set up local frame
    local = {}
    for expr in stmt.params:
        if stmt.passby == 'BYREF':
            expectTypeElseError(frame, expr.type, frame[expr.name]['type'])
            # Reference frame vars in local
            local[expr.name] = frame[expr.name]
        else:
            local[expr.name] = {'type': expr.type, 'value': None}
    # Resolve procedure statements using local
    verifyStmts(local, stmt.stmts)
    # Declare procedure in frame
    name = stmt.name
    frame[name] = {
        'type': 'procedure',
        'value': {
            'frame': local,
            'passby': stmt.passby,
            'params': stmt.params,
            'stmts': stmt.stmts,
        }
    }

def verifyCall(frame, stmt):
    stmt.callable.resolve(frame)
    proc = stmt.callable.callable.evaluate(frame)
    expectTypeElseError(frame, stmt.callable, 'procedure')
    # if len(stmt.args) != len(proc['params']):
    #     raise LogicError(
    #         f"Expected {len(proc['params'])} args, got {len(stmt.args)}",
    #         None,
    #     )
    # # Type-check arguments
    # local = proc['frame']
    # for arg, param in zip(stmt.args, proc['params']):
    #     if stmt.passby == 'BYREF':
    #         arg.resolve(frame)
    #         # Only names allowed for BYREF arguments
    #         if not isinstance(arg, Get):
    #             raise LogicError(
    #                 'BYREF arg must be a name, not expression',
    #                 None,
    #             )
    #     else:
    #         arg.resolve(local)
    #     paramtype = param['type']
    #     expectTypeElseError(frame, arg, paramtype)

def verifyFunction(frame, stmt):
    # Set up local frame
    local = {}
    for expr in stmt.params:
        # Declare vars in local
        expr.accept(local, resolveDeclare)
    name = stmt.name
    returnType = stmt.returnType
    # Resolve procedure statements using local
    hasReturn = False
    for procstmt in stmt.stmts:
        stmtType = procstmt.accept(local, verify)
        if stmtType:
            hasReturn = True
            if stmtType != returnType:
                raise LogicError(
                    f"Expect {returnType}, got {stmtType}",
                    stmt.name,
                )
    if not hasReturn:
        raise LogicError("No RETURN in function", None)
     # Declare function in frame
    frame[name] = {
        'type': returnType,
        'value': {
            'frame': local,
            'passby': 'BYVALUE',
            'params': stmt.params,
            'stmts': stmt.stmts,
        }
    }

def verifyReturn(local, stmt):
    # This will typically be verify()ed within
    # verifyFunction(), so frame is expected to
    # be local
    return stmt.expr.resolve(local)

def verifyFile(frame, stmt):
    name = stmt.name.accept(frame, value)
    if stmt.action == 'open':
        if name in frame:
            raise LogicError("File already opened", stmt.name)
        file = {'type': stmt.mode, 'value': None}
        frame[name] = file
    elif stmt.action == 'read':
        if name not in frame:
            raise LogicError("File not open", stmt.name)
        file = frame[name]
        if file['type'] != 'READ':
            raise LogicError("File mode is {file['type']}", stmt.name)
    elif stmt.action == 'write':
        stmt.data.resolve(frame)
        if name not in frame:
            raise LogicError("File not open", stmt.name)
        file = frame[name]
        if file['type'] not in ('WRITE', 'APPEND'):
            raise LogicError("File mode is {file['type']}", stmt.name)
    elif stmt.action == 'close':
        if name not in frame:
            raise LogicError("File not open", stmt.name)
        del frame[name]

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
        stmt.expr.accept(frame, resolveCall)
    elif stmt.rule == 'function':
        stmt.accept(frame, verifyFunction)
    elif stmt.rule == 'file':
        stmt.accept(frame, verifyFile)
    elif stmt.rule == 'return':
        return stmt.accept(frame, verifyReturn)

def inspect(statements):
    frame = {}
    verifyStmts(frame, statements)
    return statements, frame
