"""system
Sets up built-in functions and types for pseudo-9608.

system
    A Frame containing built-in functions, and with a TypeSystem
    containing builtin-types.
"""

from typing import TextIO
import random

from .builtin import TYPES, RuntimeError
from .lang import Frame, TypeSystem, Builtin, TypedValue



system = Frame(typesys=TypeSystem(*TYPES))



def RND() -> float:
    """Returns a random REAL between 0 and 1."""
    return random.random()
system.declare('RND', 'REAL')
system.setValue('RND', Builtin(
    params=[],
    func=RND,
))

def RANDOMBETWEEN(start: int, end: int) -> int:
    """Returns a random INTEGER between start and end."""
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
    """Returns True if the file's cursor is at the end of the file."""
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
