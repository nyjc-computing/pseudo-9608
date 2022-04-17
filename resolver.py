from builtin import get
from builtin import LogicError



def resolve(expr, frame):
    # Resolving tokens
    if 'type' in expr:
        if expr['type'] == 'name':
            return expr['word']
        return expr['value']
    # Resolving exprs
    oper = expr['oper']['value']
    if oper is get:
        expr['left'] = frame

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
        try:
            verify(frame, stmt)
        except LogicError:
            print()
            break
    return statements, frame