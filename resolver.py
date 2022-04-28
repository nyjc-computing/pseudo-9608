from builtin import get, call
from builtin import lt, lte, gt, gte, ne, eq
from builtin import add, sub, mul, div
from builtin import LogicError



# Helper functions

def expectTypeElseError(frame, expr, expected):
    exprtype = expr.resolve(frame)
    if expected != exprtype:
        token = None
        if type(expr) is dict:
            if 'line' in expr:
                token = expr
            elif 'line' in expr['left']:
                token = expr['left']
            elif 'line' in expr['right']:
                token = expr['right']
        raise LogicError(
            f"Expected {repr(expected)}, got {repr(exprtype)}",
            token,
        )

def resolveExprs(frame, exprs):
    for expr in exprs:
        expr.resolve(frame)

def verifyStmts(frame, stmts):
    for stmt in stmts:
        verify(frame, stmt)

def resolve(frame, expr):
    # Resolving tokens
    if 'type' in expr:
        if expr['type'] == 'name':
            return expr['word']
        elif expr['type'] in ('integer', 'string'):
            return expr['type'].upper()
        else:
            # internal error
            raise TypeError(f'Cannot resolve type for {expr}')
    # Resolving get expressions
    oper = expr['oper']['value']
    if oper is get:
        expr['left'] = frame
        name = resolve(frame, expr['right'])
        if name not in frame:
            raise LogicError(
                f'Name not declared',
                expr['right'],
            )
        return frame[name]['type']
    # Resolving function calls
    if oper is call:
        # Insert frame into get expr
        resolve(frame, expr['left'])
        # Insert frame into args
        args = expr['right']
        resolveExprs(frame, args)
        # Return function type
        functype = resolve(frame, expr['left'])
        return functype
    # Resolving other exprs
    if oper in (lt, lte, gt, gte, ne, eq):
        resolve(frame, expr['left'])
        resolve(frame, expr['right'])
        return 'BOOLEAN'
    elif oper in (add, sub, mul, div):
        resolve(frame, expr['left'])
        resolve(frame, expr['right'])
        expectTypeElseError(frame, expr['left'], 'INTEGER')
        expectTypeElseError(frame, expr['right'], 'INTEGER')
        return 'INTEGER'

def verifyOutput(frame, stmt):
    resolveExprs(frame, stmt['exprs'])

def verifyInput(frame, stmt):
    name = stmt['name'].resolve(frame)
    if name not in frame:
        raise LogicError(
            f'Name not declared',
            stmt['name'].name,
        )

def verifyDeclare(frame, stmt):
    name = stmt['name'].resolve(frame)
    type_ = stmt['type']['word']
    frame[name] = {'type': type_, 'value': None}

def verifyAssign(frame, stmt):
    name = stmt['name'].resolve(frame)
    expectTypeElseError(frame, stmt['expr'], frame[name]['type'])

def verifyCase(frame, stmt):
    stmt['cond'].resolve(frame)
    verifyStmts(frame, stmt['stmts'].values())
    if stmt['fallback']:
        verify(frame, stmt['fallback'])

def verifyIf(frame, stmt):
    stmt['cond'].resolve(frame)
    expectTypeElseError(frame, stmt['cond'], 'BOOLEAN')
    verifyStmts(frame, stmt['stmts'][True])
    if stmt['fallback']:
        verifyStmts(frame, stmt['fallback'])

def verifyWhile(frame, stmt):
    if stmt['init']:
        verify(frame, stmt['init'])
    stmt['cond'].resolve(frame)
    expectTypeElseError(frame, stmt['cond'], 'BOOLEAN')
    verifyStmts(frame, stmt['stmts'])

def verifyProcedure(frame, stmt):
    passby = stmt['passby']['word']
    # Set up local frame
    local = {}
    for var in stmt['params']:
        # Declare vars in local
        if passby == 'BYVALUE':
            verifyDeclare(local, var)
        elif passby == 'BYREF':
            name = var['name'].resolve(frame)
            globvar = frame[name]
            expectTypeElseError(frame, var['type'], globvar['type'])
            # Reference global vars in local
            local[name] = globvar
        else:
            # Internal error
            raise TypeError(stmt['passby'], f"str expected for passby, got {passby}")
    # Resolve procedure statements using local
    verifyStmts(local, stmt['stmts'])
    # Declare procedure in frame
    name = stmt['name'].resolve(frame)
    frame[name] = {
        'type': 'procedure',
        'value': {
            'frame': local,
            'passby': passby,
            'params': stmt['params'],
            'stmts': stmt['stmts'],
        }
    }

def verifyCall(frame, stmt):
    name = stmt['name'].resolve(frame)
    proc = frame[name]
    expectTypeElseError(frame, proc, 'procedure')
    args, params = stmt['args'], proc['value']['params']
    if len(args) != len(params):
        raise LogicError(
            f'Expected {len(params)} args, got {len(args)}',
            stmt['name']['right'],
        )
    # Type-check arguments
    local = proc['value']['frame']
    for arg, param in zip(args, params):
        if stmt['passby']['word'] == 'BYREF':
            # Only names allowed for BYREF arguments
            # Check for a get expr
            if arg['oper']['value'] is not get:
                raise LogicError(
                    'BYREF arg must be a name, not expression',
                    stmt['passby'],
                )
        paramtype = param['type']['word']
        expectTypeElseError(frame, arg, paramtype)

def verifyFunction(frame, stmt):
    # Set up local frame
    local = {}
    for var in stmt['params']:
        # Declare vars in local
        verifyDeclare(local, var)
    name = stmt['name'].resolve(frame)
    returns = stmt['returns'].resolve(frame)
    # Resolve procedure statements using local
    for procstmt in stmt['stmts']:
        returntype = verify(local, procstmt)
        if returntype and (returntype != returns):
            raise LogicError(
                f"Expect {returns}, got {returntype}",
                stmt['name'],
            )
    # Declare function in frame
    frame[name] = {
        'type': returns,
        'value': {
            'frame': local,
            'passby': 'BYVALUE',
            'params': stmt['params'],
            'stmts': stmt['stmts'],
        }
    }

def verifyReturn(local, stmt):
    # This will typically be verify()ed within
    # verifyFunction(), so frame is expected to
    # be local
    return stmt['expr'].resolve(local)

def verifyFile(frame, stmt):
    name = stmt['name'].resolve(frame)
    if stmt['action'] == 'open':
        if name in frame:
            raise LogicError("File already opened", stmt['name'])
        file = {'type': stmt['mode']['word'], 'value': None}
        frame[name] = file
    elif stmt['action'] == 'read':
        if name not in frame:
            raise LogicError("File not open", stmt['name'])
        file = frame[name]
        if file['type'] != 'READ':
            raise LogicError("File mode is {file['type']}", stmt['name'])
    elif stmt['action'] == 'write':
        stmt['data'].resolve(frame)
        if name not in frame:
            raise LogicError("File not open", stmt['name'])
        file = frame[name]
        if file['type'] not in ('WRITE', 'APPEND'):
            raise LogicError("File mode is {file['type']}", stmt['name'])
    elif stmt['action'] == 'close':
        if name not in frame:
            raise LogicError("File not open", stmt['name'])
        del frame[name]

def verify(frame, stmt):
    if 'rule' not in stmt: breakpoint()
    if stmt['rule'] == 'output':
        verifyOutput(frame, stmt)
    if stmt['rule'] == 'input':
        verifyInput(frame, stmt)
    elif stmt['rule'] == 'declare':
        verifyDeclare(frame, stmt)
    elif stmt['rule'] == 'assign':
        verifyAssign(frame, stmt)
    elif stmt['rule'] == 'case':
        verifyCase(frame, stmt)
    elif stmt['rule'] == 'if':
        verifyIf(frame, stmt)
    elif stmt['rule'] in ('while', 'repeat'):
        verifyWhile(frame, stmt)
    elif stmt['rule'] == 'procedure':
        verifyProcedure(frame, stmt)
    elif stmt['rule'] == 'call':
        verifyCall(frame, stmt)
    elif stmt['rule'] == 'function':
        verifyFunction(frame, stmt)
    elif stmt['rule'] == 'file':
        verifyFile(frame, stmt)
    elif stmt['rule'] == 'return':
        return verifyReturn(frame, stmt)

def inspect(statements):
    frame = {}
    verifyStmts(frame, statements)
    return statements, frame
