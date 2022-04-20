from builtin import get
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
    # Resolving gets requires special handling
    # of expr's left and right
    oper = expr['oper']['value']
    if oper is get:
        expr['left'] = frame
        name = resolve(frame, expr['right'])
        if name not in frame:
            raise LogicError(f'{name}: Name not declared')
        return frame[name]['type']
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

def verify(frame, stmt):
    if 'rule' not in stmt: breakpoint()
    if stmt['rule'] == 'output':
        verifyOutput(frame, stmt)
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

def inspect(statements):
    frame = {}
    for stmt in statements:
        verify(frame, stmt)
    return statements, frame
