from builtin import get, call
from builtin import lt, lte, gt, gte, ne, eq
from builtin import add, sub, mul, div
from builtin import LogicError



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
    lefttype = resolve(frame, expr['left'])
    righttype = resolve(frame, expr['right'])
    if oper in (lt, lte, gt, gte, ne, eq):
        return 'BOOLEAN'
    elif oper in (add, sub, mul, div):
        if lefttype != 'INTEGER':
            raise LogicError(f"{expr['left']} Expected number, got {lefttype}")
        if righttype != 'INTEGER':
            raise LogicError(f"{expr['right']} Expected number, got {righttype}")
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
    valuetype = resolve(frame, stmt['expr'])
    frametype = frame[name]['type']
    if frametype != valuetype:
        raise LogicError(f'Expected {frametype}, got {valuetype}')

def verifyCase(frame, stmt):
    resolve(frame, stmt['cond'])
    for value, casestmt in stmt['stmts'].items():
        verify(frame, casestmt)
    if stmt['fallback']:
        verify(frame, stmt['fallback'])

def verifyIf(frame, stmt):
    condtype = resolve(frame, stmt['cond'])
    if condtype != 'BOOLEAN':
        raise LogicError(f'IF condition must be a BOOLEAN expression, not {condtype}')
    for truestmt in stmt['stmts'][True]:
        verify(frame, truestmt)
    if stmt['fallback']:
        for falsestmt in stmt['fallback']:
            verify(frame, falsestmt)

def verifyWhile(frame, stmt):
    if stmt['init']:
        verify(frame, stmt['init'])
    condtype = resolve(frame, stmt['cond'])
    if condtype != 'BOOLEAN':
        raise LogicError(f'IF condition must be a BOOLEAN expression, not {condtype}')
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
            vartype = resolve(frame, var['type'])
            # Type-check local against global
            if vartype != globvar['type']:
                raise LogicError(
                    f"Expect {globvar['type']} for BYREF {name},"
                    f" got {vartype}"
                )
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
        argtype = resolve(frame, arg)
        paramtype = resolve(local, param['type'])
        # Type-check args against param types
        if argtype != paramtype:
            raise LogicError(f"Expect {paramtype} for {name}, got {argtype}")

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
    elif stmt['rule'] == 'procedure':
        verifyProcedure(frame, stmt)
    elif stmt['rule'] == 'call':
        verifyCall(frame, stmt)
    elif stmt['rule'] in ('while', 'repeat'):
        verifyWhile(frame, stmt)
    elif stmt['rule'] == 'function':
        verifyFunction(frame, stmt)
    elif stmt['rule'] == 'return':
        return verifyReturn(frame, stmt)

def inspect(statements):
    frame = {}
    for stmt in statements:
        verify(frame, stmt)
    return statements, frame
