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
    Union,
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
    # Python has no in-built EOF support; if read() or readline()
    # return an empty string, that's considered EOF.
    # So we'll have to seek back to the previous position after read()
    pos = file.tell()
    iseof = (file.read(1) == '')
    file.seek(pos)
    return iseof

def LENGTH(thisStr: str) -> int:
    """Returns integer value representing the length of thisStr."""
    return len(thisStr)

def LEFT(thisStr: str, x: int) -> str:
    """Returns leftmost x characters from thisStr."""
    if x < 0:
        raise builtin.RuntimeError("Expected integer >= 0", None)
    if x > len(thisStr):
        raise builtin.RuntimeError("String length exceeded", None)
    return thisStr[:x]

def RIGHT(thisStr: str, x: int) -> str:
    """Returns rightmost x characters from thisStr."""
    if x < 0:
        raise builtin.RuntimeError("Expected integer >= 0", None)
    if x > len(thisStr):
        raise builtin.RuntimeError("String length exceeded", None)
    return thisStr[-x:]

def INT(x: float) -> int:
    """Returns the integer part of x."""
    return int(x)

def MOD(thisNum: int, thisDiv: int) -> int:
    """
    Returns the integer value representing the remainder when
    thisNum is divided by thisDiv.
    """
    return thisNum % thisDiv

def MID(thisStr: str, x: int, y: int) -> str:
    """
    Returns string of length y starting at position x from thisStr.
    """
    if x < 0 or y < 0:
        raise builtin.RuntimeError("Expected integer >= 0", None)
    if x + y > len(thisStr):
        raise builtin.RuntimeError("String length exceeded", None)
    return thisStr[x:x + y]

def LCASE(thisChar: str) -> str:
    """
    Returns the character value representing the lower case equivalent
    of thisChar.
    If thisChar is not an uppercase alphabetic character, it is
    returned unchanged.
    """
    # TODO: Change type signature to take CHAR type only
    return thisChar.lower()

def DIV(thisNum: int, thisDiv: int) -> int:
    """
    Returns the integer value representing the whole number part of
    the result when thisNum is divided by thisDiv.
    """
    return thisNum // thisDiv

def INT_TO_STRING(x: int) -> str:
    """Returns a string representation of an INTEGER value."""
    return str(x)

def REAL_TO_STRING(x: float) -> str:
    """Returns a string representation of a REAL value."""
    return str(x)



funcReturnParams: List[Tuple[function, lang.Type, List[lang.TypedValue]]] = [
    (RND, 'REAL', []),
    (RANDOMBETWEEN, 'INTEGER', [
        lang.TypedValue(type='INTEGER', value=None),
        lang.TypedValue(type='INTEGER', value=None),
    ]),
    (EOF, 'BOOLEAN', [lang.TypedValue(type='STRING', value=None)]),
    (LENGTH, 'INTEGER', [lang.TypedValue(type='STRING', value=None)]),
    (LEFT, 'STRING', [
        lang.TypedValue(type='STRING', value=None),
        lang.TypedValue(type='INTEGER', value=None),
    ]),
    (RIGHT, 'STRING', [
        lang.TypedValue(type='STRING', value=None),
        lang.TypedValue(type='INTEGER', value=None),
    ]),
    (INT, 'INTEGER', [lang.TypedValue(type='REAL', value=None)]),
    (MOD, 'INTEGER', [
        lang.TypedValue(type='INTEGER', value=None),
        lang.TypedValue(type='INTEGER', value=None),
    ]),
    (MID, 'STRING', [
        lang.TypedValue(type='INTEGER', value=None),
        lang.TypedValue(type='INTEGER', value=None),
    ]),
    (LCASE, 'STRING', [lang.TypedValue(type='STRING', value=None)]),
    (DIV, 'INTEGER', [
        lang.TypedValue(type='INTEGER', value=None),
        lang.TypedValue(type='INTEGER', value=None),
    ]),
    (INT_TO_STRING, 'STRING', [lang.TypedValue(type='INTEGER', value=None)]),
    (REAL_TO_STRING, 'STRING', [lang.TypedValue(type='REAL', value=None)]),
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
