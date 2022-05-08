import random

from .lang import Frame, Builtin, TypedValue



system = Frame()



def RND():
    return random.random()
system.declare('RND', 'REAL')
system.setValue('RND', Builtin(
    params=[],
    func=RND,
))

def RANDOMBETWEEN(start, end):
    if not (start < end):
        raise RuntimeError(f"{start} not less than {end}", None)
    return random.randint(start, end)
system.declare('RANDOMBETWEEN', 'INTEGER')
system.setValue('RANDOMBETWEEN', Builtin(
    params=[
        TypedValue(type='INTEGER', value=None),
        TypedValue(type='INTEGER', value=None),
    ],
    func=RANDOMBETWEEN,
))
