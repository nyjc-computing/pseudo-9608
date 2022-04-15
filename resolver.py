from builtin import get
from builtin import LogicError



def resolve(expr, frame):
    # Tokens
    if 'type' in expr:
        # ignore for now
        return
    # Exprs
    oper = expr['oper']['value']
    if oper is get:
        expr['left'] = frame

def verifyOutput(frame, stmt):
    for expr in stmt['exprs']:
        resolve(expr, frame)

def verifyDeclare(frame, stmt):
    # No exprs to resolve
    pass

def verifyAssign(frame, stmt):
    resolve(stmt['expr'], frame)

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