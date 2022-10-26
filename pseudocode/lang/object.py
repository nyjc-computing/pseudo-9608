"""object.py

Defines internal Pseudo objects that do not interact with the user.

Object
    Allows attributes to be addressed by name

Array
    Allows elements to be addressed by index

Frame
    Allows values to be addressed by name
"""

from abc import ABC
from dataclasses import dataclass
from itertools import product
from typing import (
    Iterator,
    MutableMapping,
    Optional,
    Sequence,
    Union,
)

from . import types as t

__all__ = [
    'Array',
    'Assignable',
    'Container',
    'Frame',
    'NameMap',
    'Object',
    'Params',
    'PseudoValue',
    'PyLiteral',
    'TypedValue',
    'Value',
]

PyLiteral = Union[bool, int, float, str]
Value = Union[PyLiteral, "PseudoValue"]

NameMap = MutableMapping[t.NameKey, "TypedValue"]
IndexMap = MutableMapping[t.IndexKey, "TypedValue"]

Params = Sequence["TypedValue"]


@dataclass
class TypedValue:
    """All pseudocode values are encapsulated in a TypedValue.
    Each TypedValue has a type and a value.
    """
    __slots__ = ("type", "value")
    type: t.Type
    value: Optional[Value]

    def __repr__(self) -> str:
        return f"<{self.type}: {repr(self.value)}>"


class Frame:
    """Frames differ from Objects in that they can be chained (with a
    reference to an outer Frame, names can be reassigned to a different
    TypedValue, and slots can be deleted after declaration.
    Existence checks should be carried out (using has()) before using
    the methods here.

    Methods
    -------
    has(name)
        returns True if the var exists in frame,
        otherwise returns False
    declare(name, typedValue)
        associates name with typedValue in the Frame
    get(name)
        retrieves the slot associated with the name
    getType(name)
        retrieves the type information associated with the name
    getValue(name)
        retrieves the value associated with the name
    set(name, typedValue)
        assigns the given TypedValue to the name
    setValue(name, value)
        updates the value associated with the name
    delete(name)
        deletes the slot associated with the name
    lookup(name)
        returns the first frame containing the name
    """
    __slots__ = ("data", "outer")

    def __init__(self, outer: "Frame" = None) -> None:
        self.data: NameMap = {}
        self.outer = outer

    def __repr__(self) -> str:
        nameTypePairs = [f"{name}: {self.getType(name)}" for name in self.data]
        return f"{{{', '.join(nameTypePairs)}}}"

    def has(self, name: t.NameKey) -> bool:
        return name in self.data

    def declare(self, name: t.NameKey, typedValue: TypedValue) -> None:
        self.data[name] = typedValue

    def get(self, name: t.NameKey) -> TypedValue:
        return self.data[name]

    def getType(self, name: t.NameKey) -> t.Type:
        return self.data[name].type

    def getValue(self, name: t.NameKey) -> Value:
        returnval = self.data[name].value
        if returnval is None:
            raise ValueError(f"Accessed unassigned variable {name!r}")
        return returnval

    def set(self, name: t.NameKey, typedValue: TypedValue) -> None:
        self.data[name] = typedValue

    def setValue(self, name: t.NameKey, value: Value) -> None:
        self.data[name].value = value

    def delete(self, name: t.NameKey) -> None:
        del self.data[name]

    def lookup(self, name: t.NameKey) -> Optional["Frame"]:
        if self.has(name):
            return self
        if self.outer:
            return self.outer.lookup(name)
        return None


class PseudoValue(ABC):
    """Base class for pseudo values which are not PyLiterals.
    This includes Arrays, Objects, and Callables.
    PseudoValues may be stored in Arrays, Objects, or Callables, wrapped
    in a TypedValue.
    """


class Container(PseudoValue):
    """Base class for Array and Object.
    Represents a Container in Pseudo, which maps keys to TypedValues.

    Attributes
    ----------
    - type
      Type name of the container
      e.g. Student, e.g. ARRAY[1:3] OF INTEGER
    - data
      A MutableMapping used to map keys to TypedValues
    """
    type: t.Type
    data: MutableMapping


class Array(Container):
    """A Container that maps Index: TypedValue.

    Attributes
    ----------
    dim: int
        integer representing the number of dimensions of the array
    elementType: Type
        The type of each array element

    Methods
    -------
    has(index)
        returns True if the index exists in frame,
        otherwise returns False
    get(index)
        retrieves the slot associated with the index
    getType(index)
        retrieves the type information associated with the index
    getValue(index)
        retrieves the value associated with the index
    setValue(index, value)
        updates the value associated with the index
    """
    __slots__ = ("ranges", "data", "type")

    def __init__(self, ranges: t.IndexRanges, type: t.Type) -> None:
        self.ranges = ranges
        self.data: IndexMap = {}

    def __repr__(self) -> str:
        nameValuePairs = [
            f"{index}: {self.getValue(index)}" for index in self.data
        ]
        return f"{{{', '.join(nameValuePairs)}}}: {self.elementType}"

    @staticmethod
    def rangeProduct(indexes: t.IndexRanges) -> Iterator:
        """Returns an iterator from an interable of (start, end) tuples.
        E.g. ((0, 2), (0, 3)) will return the following iterations:
            (0, 0), ..., (0, 3),
            (1, 0), ..., (1, 3),
            (2, 0), ..., (2, 3),
        """
        ranges = (range(start, end + 1) for (start, end) in indexes)
        return product(*ranges)

    @property
    def dim(self) -> int:
        """Returns the number of dimensions the array has, as an
        integer.
        E.g. a 1D array would return 1, 2D array would return 2, ...
        """
        return len(self.ranges)

    @property
    def elementType(self) -> t.Type:
        return tuple(self.data.values())[0].type

    def has(self, index: t.IndexKey) -> bool:
        return index in self.data

    def declare(self, index: t.IndexKey, typedValue: TypedValue) -> None:
        self.data[index] = typedValue

    def getType(self, index: t.IndexKey) -> t.Type:
        return self.data[index].type

    def getValue(self, index: t.IndexKey) -> Union[PyLiteral, "Object"]:
        returnval = self.data[index].value
        if returnval is None:
            raise ValueError(f"Accessed unassigned index {index!r}")
        assert (isinstance(returnval, bool) or isinstance(returnval, int)
                or isinstance(returnval, float) or isinstance(returnval, str)
                or isinstance(returnval,
                              Object)), f"Unexpected {type(returnval)}"
        return returnval

    def get(self, index: t.IndexKey) -> "TypedValue":
        return self.data[index]

    def setValue(self, index: t.IndexKey, value: Union[PyLiteral,
                                                       "Object"]) -> None:
        self.data[index].value = value


class Object(Container):
    """A Container that maps Name: TypedValue.
    Existence checks should be carried out (using has()) before using
    the methods here.

    Methods
    -------
    has(name)
        returns True if the var exists in frame,
        otherwise returns False
    declare(name, typedValue)
        associates name with typedValue in the Container
    get(name)
        retrieves the slot associated with the name
    getType(name)
        retrieves the type information associated with the name
    getValue(name)
        retrieves the value associated with the name
    setValue(name, value)
        updates the value associated with the name
    """
    __slots__ = ("data", "type")

    def __init__(self) -> None:
        self.data: NameMap = {}

    def __repr__(self) -> str:
        nameTypePairs = [f"{name}: {self.getType(name)}" for name in self.data]
        return f"{{{', '.join(nameTypePairs)}}}"

    def has(self, name: t.NameKey) -> bool:
        return name in self.data

    def declare(self, name: t.NameKey, typedValue: TypedValue) -> None:
        self.data[name] = typedValue

    def getType(self, name: t.NameKey) -> t.Type:
        return self.data[name].type

    def getValue(self, name: t.NameKey) -> "Assignable":
        returnval = self.data[name].value
        if returnval is None:
            raise ValueError(f"Accessed unassigned variable {name!r}")
        assert (isinstance(returnval, bool) or isinstance(returnval, int)
                or isinstance(returnval, float)
                or isinstance(returnval, str) or isinstance(
                    returnval, Container)), f"Unexpected {type(returnval)}"
        return returnval

    def get(self, name: t.NameKey) -> "TypedValue":
        return self.data[name]

    def setValue(self, name: t.NameKey, value: "Assignable") -> None:
        self.data[name].value = value


Assignable = Union[PyLiteral, Container]
