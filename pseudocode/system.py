"""system
Sets up built-in functions and types for pseudo-9608.

system
    A Frame containing built-in functions, and with a TypeSystem
    containing builtin-types.
"""

import random
from typing import (
    Callable as function,
    List,
    TextIO,
    Tuple,
)

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



funcReturnParams: List[Tuple[function, lang.Type, List[lang.TypedValue]]] = [
    (RND, 'REAL', []),
    (RANDOMBETWEEN, 'INTEGER', [
        lang.TypedValue(type='INTEGER', value=None),
        lang.TypedValue(type='INTEGER', value=None),
    ]),
    (EOF, 'BOOLEAN', [lang.TypedValue(type='STRING', value=None)]),
]

def initFrame() -> lang.Frame:
    """
    Return a system frame with function declarations.
    Functions are not yet defined.
    """
    sysFrame = lang.Frame(typesys=lang.TypeSystem(*builtin.TYPES))
    for func, retType, _ in funcReturnParams:
        sysFrame.declare(func.__name__, retType)
    return sysFrame

def resolveGlobal(sysFrame: lang.Frame, globalFrame: lang.Frame) -> None:
    """
    Resolve all system functions in sysFrame to point to global frame.
    """
    # Be careful to avoid recursion
    for func, retType, params in funcReturnParams:
        sysFrame.setValue(
            func.__name__,
            lang.Builtin(globalFrame, params, func)
        )
