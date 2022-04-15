from builtin import get
from builtin import LogicError



def verify(frame, stmt):
    pass

def inspect(statements):
    frame = {}
    for stmt in statements:
        try:
            verify(frame, stmt)
        except LogicError:
            print()
            break
    return statements, frame