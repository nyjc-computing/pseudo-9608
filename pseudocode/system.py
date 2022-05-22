from typing import TextIO
import random

from .builtin import TYPES, RuntimeError
from .lang import Frame, TypeSystem, Builtin, TypedValue



system = Frame(typesys=TypeSystem(*TYPES))



def RND() -> float:
    return random.random()
system.declare('RND', 'REAL')
system.setValue('RND', Builtin(
    params=[],
    func=RND,
))

def RANDOMBETWEEN(start: int, end: int) -> int:
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

def EOF(file: TextIO) -> bool:
    # Python has no in-built EOF support;
    # if read() or readline() return an empty string,
    # that's considered EOF
    # So we'll have to seek back to the previous position
    # after read()
    pos = file.tell()
    iseof = (file.read(1) == '')
    file.seek(pos)
    return iseof
system.declare('EOF', 'BOOLEAN')
system.setValue('EOF', Builtin(
    params=[
        TypedValue(type='STRING', value=None),
    ],
    func=EOF,
))
