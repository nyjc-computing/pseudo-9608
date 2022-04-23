from builtin import get, call
from builtin import lt, lte, gt, gte, ne, eq
from builtin import add, sub, mul, div
from builtin import LogicError



# Helper functions

def expectTypeElseError(frame, expr, expected):
    exprtype = resolve(frame, expr)
    if expected != exprtype:
        raise LogicError(f"Expected {repr(expected)}, got {repr(exprtype)}")

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
            raise LogicError(f'{name}: Name not declared')
        return frame[name]['type']
    # Resolving function calls
    if oper is call:
        # Insert frame into get expr
        resolve(frame, expr['left'])
        # Insert frame into args
        args = expr['right']
        for arg in args:
            resolve(frame, arg)
        # Return function type
        functype = resolve(frame, expr['left'])
        return functype
    # Resolving other exprs
    if oper in (lt, lte, gt, gte, ne, eq):
        return 'BOOLEAN'
    elif oper in (add, sub, mul, div):
        expectTypeElseError(frame, expr['left'], 'INTEGER')
        expectTypeElseError(frame, expr['right'], 'INTEGER')
        return 'INTEGER'

def verifyOutput(frame, stmt):
    for expr in stmt['exprs']:
        resolve(frame, expr)

def verifyInput(frame, stmt):
    name = resolve(frame, stmt['name'])
    if name not in frame:
        raise LogicError(f'{name}: Name not declared')

def verifyDeclare(frame, stmt):
    name = resolve(frame, stmt['name'])
    type_ = resolve(frame, stmt['type'])
    frame[name] = {'type': type_, 'value': None}

def verifyAssign(frame, stmt):
    name = resolve(frame, stmt['name'])
    expectTypeElseError(frame, stmt['expr'], frame[name]['type'])

def verifyCase(frame, stmt):
    resolve(frame, stmt['cond'])
    for value, casestmt in stmt['stmts'].items():
        verify(frame, casestmt)
    if stmt['fallback']:
        verify(frame, stmt['fallback'])

def verifyIf(frame, stmt):
    expectTypeElseError(frame, stmt['cond'], 'BOOLEAN')
    for truestmt in stmt['stmts'][True]:
        verify(frame, truestmt)
    if stmt['fallback']:
        for falsestmt in stmt['fallback']:
            verify(frame, falsestmt)

def verifyWhile(frame, stmt):
    if stmt['init']:
        verify(frame, stmt['init'])
    expectTypeElseError(frame, stmt['cond'], 'BOOLEAN')
    for loopstmt in stmt['stmts']:
        verify(frame, loopstmt)

def verifyProcedure(frame, stmt):
    passby = stmt['passby']['word']
    # Set up local frame
    local = {}
    for var in stmt['params']:
        # Declare vars in local
        if passby == 'BYVALUE':
            verifyDeclare(local, var)
        elif passby == 'BYREF':
            name = resolve(frame, var['name'])
            globvar = frame[name]
            expectTypeElseError(frame, var['type'], globvar['type'])
            # Reference global vars in local
            local[name] = globvar
        else:
            # Internal error
            raise TypeError(f"str expected for passby, got {passby}")
    # Resolve procedure statements using local
    for procstmt in stmt['stmts']:
        verify(local, procstmt)
    # Declare procedure in frame
    name = resolve(frame, stmt['name'])
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
    # Insert frame
    stmt['name']['left'] = frame
    # resolve() would return the expr type, but we need the name
    name = resolve(frame, stmt['name']['right'])
    proc = frame[name]
    # Type-check procedure
    if proc['type'] != 'procedure':
        raise LogicError(f"CALL {proc['name']} is not a procedure")
    args, params = stmt['args'], proc['value']['params']
    if len(args) != len(params):
        raise LogicError(f'Expected {len(params)} args, got {len(args)}')
    # Type-check arguments
    local = proc['value']['frame']
    for arg, param in zip(args, params):
        if stmt['passby']['word'] == 'BYREF':
            # Only names allowed for BYREF arguments
            # Check for a get expr
            if arg['oper']['value'] is not get:
                raise LogicError('BYREF arg must be a name, not expression')
        paramtype = resolve(local, param['type'])
        expectTypeElseError(frame, arg, paramtype)

def verifyFunction(frame, stmt):
    # Set up local frame
    local = {}
    for var in stmt['params']:
        # Declare vars in local
        verifyDeclare(local, var)
    # Resolve procedure statements using local
    name = resolve(frame, stmt['name'])
    returns = resolve(frame, stmt['returns'])
    for procstmt in stmt['stmts']:
        returntype = verify(local, procstmt)
        if returntype and (returntype != returns):
            raise LogicError(f"Expect {returns} for {name}, got {returntype}")
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
    return resolve(local, stmt['expr'])

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
    elif stmt['rule'] == 'return':
        return verifyReturn(frame, stmt)

def inspect(statements):
    frame = {}
    for stmt in statements:
        verify(frame, stmt)
    return statements, frame
