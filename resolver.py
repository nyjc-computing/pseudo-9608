from builtin import get
from builtin import lt, lte, gt, gte, ne, eq
from builtin import add, sub, mul, div
from builtin import LogicError



def resolve(expr, frame):
    # Resolving tokens
    if 'type' in expr:
        if expr['type'] == 'name':
            return expr['word']
        elif expr['type'] in ('integer', 'string'):
            return expr['type'].upper()
        else:
            # internal error
            raise TypeError(f'Cannot resolve type for {expr}')    # Resolving exprs
    oper = expr['oper']['value']
    if oper is get:
        expr['left'] = frame
        name = resolve(expr['right'], frame)
        return frame[name]['type']
    elif oper in (lt, lte, gt, gte, ne, eq):
        return 'BOOLEAN'
    elif oper in (add, sub, mul, div):
        lefttype = resolve(expr['left'], frame)
        righttype = resolve(expr['right'], frame)
        if lefttype != 'INTEGER':
            raise LogicError(f"{expr['left']} Expected number, got {lefttype}")
        if righttype != 'INTEGER':
            raise LogicError(f"{expr['right']} Expected number, got {righttype}")
        return 'INTEGER'

def verifyOutput(frame, stmt):
    for expr in stmt['exprs']:
        resolve(expr, frame)

def verifyDeclare(frame, stmt):
    name = resolve(stmt['name'], frame)
    type_ = resolve(stmt['type'], frame)
    frame[name] = {'type': type_, 'value': None}

def verifyAssign(frame, stmt):
    name = resolve(stmt['name'], frame)
    valuetype = resolve(stmt['expr'], frame)
    if name not in frame:
        raise LogicError(f'Variable')
    frametype = frame[name]['type']
    if frametype != valuetype:
        raise LogicError(f'Expected {frametype}, got {valuetype}')

def verify(frame, stmt):
    if stmt['rule'] == 'output':
        verifyOutput(frame, stmt)
    elif stmt['rule'] == 'declare':
        verifyDeclare(frame, stmt)
    elif stmt['rule'] == 'assign':
        verifyAssign(frame, stmt)

def inspect(statements):
    frame = {}
    for stmt in statements:
        verify(frame, stmt)
    return statements, frame