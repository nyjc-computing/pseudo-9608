from typing import (
    Hashable,
    Sequence,
    Tuple,
    Union,
)

__all__ = [
    'PyLiteral',
    'Type',
    'Key',
    'NameKey',
    'IndexKey',
    'IndexRange',
    'IndexRanges',
]

PyLiteral = Union[bool, int, float, str]  # Simple data types
Type = str  # pseudocode type, whether built-in or declared

Key = Hashable
NameKey = str  # for Object/Frame
IndexKey = Tuple[int, ...]  # for Array

IndexRange = Tuple[int, int]  # Array ranges (start, end)
IndexRanges = Sequence[IndexRange]
