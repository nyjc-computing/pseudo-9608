from builtin import get, call
from builtin import lt, lte, gt, gte, ne, eq
from builtin import add, sub, mul, div
from builtin import LogicError
from lang import Get



# Helper functions

def expectTypeElseError(frame, expr, expected):
    exprtype = expr.resolve(frame)
    if expected != exprtype:
        token = None
        # if type(expr) is dict:
        #     if 'line' in expr:
        #         token = expr
        #     elif 'line' in expr['left']:
        #         token = expr['left']
        #     elif 'line' in expr['right']:
        #         token = expr['right']
        raise LogicError(
            f"Expected {repr(expected)}, got {repr(exprtype)}",
            token,
        )

def resolveExprs(frame, exprs):
    for expr in exprs:
        expr.resolve(frame)

def verifyStmts(frame, stmts):
    for stmt in stmts:
        stmt.accept(frame, verify)

def verifyOutput(frame, stmt):
    resolveExprs(frame, stmt.exprs)

def verifyInput(frame, stmt):
    name = stmt.name.resolve(frame)
    if name not in frame:
        raise LogicError(
            f'Name not declared',
            stmt.name,
        )

def resolveDeclare(frame, expr):
    if expr.name in frame:
        raise LogicError("Already declared", expr.name)
    frame[expr.name] = {'type': expr.type, 'value': None}
    return expr.type

def verifyAssign(frame, stmt):
    name = stmt.name.resolve(frame)
    expectTypeElseError(frame, stmt.expr, frame[name]['type'])

def verifyCase(frame, stmt):
    stmt.cond.resolve(frame)
    verifyStmts(frame, stmt.stmts.values())
    if stmt.fallback:
        stmt.fallback.accept(frame, verify)

def verifyIf(frame, stmt):
    stmt.cond.resolve(frame)
    expectTypeElseError(frame, stmt.cond, 'BOOLEAN')
    verifyStmts(frame, stmt.stmts[True])
    if stmt.fallback:
        verifyStmts(frame, stmt.fallback)

def verifyWhile(frame, stmt):
    if stmt.init:
        stmt.init.accept(frame, verify)
    stmt.cond.resolve(frame)
    expectTypeElseError(frame, stmt.cond, 'BOOLEAN')
    verifyStmts(frame, stmt.stmts)

def verifyProcedure(frame, stmt):
    # Set up local frame
    local = {}
    for var in stmt.params:
        if stmt.passby == 'BYREF':
            name = var['name'].resolve(frame)
            expectTypeElseError(frame, var['type'], frame[name]['type'])
            # Reference frame vars in local
            local[name] = frame[name]
        else:
            name = var['name'].resolve(frame)
            local[name] = {'type': var['type'], 'value': None}
    # Resolve procedure statements using local
    verifyStmts(local, stmt.stmts)
    # Declare procedure in frame
    name = stmt.name.resolve(frame)
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
    name = stmt.name.resolve(frame)
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
    name = stmt.name.resolve(frame)
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
        stmt.expr.accept(resolveDeclare)
    elif stmt.rule == 'assign':
        stmt.accept(frame, verifyAssign)
    elif stmt.rule == 'case':
        stmt.accept(frame, verifyCase)
    elif stmt.rule == 'if':
        stmt.accept(frame, verifyIf)
    elif stmt.rule in ('while', 'repeat', 'for'):
        stmt.accept(frame, verifyWhile)
    elif stmt.rule == 'procedure':
        stmt.accept(frame, verifyProcedure)
    elif stmt.rule == 'call':
        stmt.accept(frame, verifyCall)
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
