"""system
Sets up built-in functions and types for pseudo-9608.

system
    A Frame containing built-in functions, and with a TypeSystem
    containing builtin-types.
"""

import random
from typing import TextIO

from . import(builtin, lang)



def RND() -> float:
    """Returns a random REAL between 0 and 1."""
    return random.random()

def RANDOMBETWEEN(start: int, end: int) -> int:
    """Returns a random INTEGER between start and end."""
    if not (start < end):
        raise builtin.RuntimeError(f"{start} not less than {end}", None)
    return random.randint(start, end)

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



system = lang.Frame(typesys=lang.TypeSystem(*builtin.TYPES))

system.declare('RND', 'REAL')
system.setValue('RND', lang.Builtin(
    params=[],
    func=RND,
))
system.declare('RANDOMBETWEEN', 'INTEGER')
system.setValue('RANDOMBETWEEN', lang.Builtin(
    params=[
        lang.TypedValue(type='INTEGER', value=None),
        lang.TypedValue(type='INTEGER', value=None),
    ],
    func=RANDOMBETWEEN,
))
system.declare('EOF', 'BOOLEAN')
system.setValue('EOF', lang.Builtin(
    params=[
        lang.TypedValue(type='STRING', value=None),
    ],
    func=EOF,
))