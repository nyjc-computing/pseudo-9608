"""types.py

Attribute types used in Pseudo objects.
"""

from typing import (
    Hashable,
    Sequence,
    Tuple,
)

__all__ = [
    'Type',
    'Key',
    'NameKey',
    'IndexKey',
    'IndexRange',
    'IndexRanges',
]

Type = str  # pseudocode type, whether built-in or declared

Key = Hashable
NameKey = str  # for Object/Frame
IndexKey = Tuple[int, ...]  # for Array

IndexRange = Tuple[int, int]  # Array ranges (start, end)
IndexRanges = Sequence[IndexRange]
