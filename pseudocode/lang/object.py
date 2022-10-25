"""object.py: PseudoValues for Pseudo

TypeSystem
    A manager for built-in and declared types

Object
    Allows attributes to be addressed by name

Array
    Allows elements to be addressed by index

Frame
    Allows values to be addressed by name

File
    An open file
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import product
from typing import (
    Iterator,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

__all__ = [
    'Array',
    'Assignable',
    'Container',
    'Frame',
    'IndexKey',
    'IndexRange',
    'IndexRanges',
    'NameKey',
    'NameMap',
    'Object',
    'ObjectTemplate',
    'Params',
    'PseudoValue',
    'PyLiteral',
    'Type',
    'TypedValue',
    'TypeSystem',
    'TypeTemplate',
    'Value',
]

PyLiteral = Union[bool, int, float, str]  # Simple data types
Type = str  # pseudocode type, whether built-in or declared
Value = Union[PyLiteral, "PseudoValue"]

# Mapping for Frame and Containers
NameKey = str  # for Object/Frame
IndexKey = Tuple[int, ...]  # for Array
NameMap = MutableMapping[NameKey, "TypedValue"]
IndexMap = MutableMapping[IndexKey, "TypedValue"]

IndexRange = Tuple[int, int]  # Array ranges (start, end)
IndexRanges = Sequence[IndexRange]
Params = Sequence["TypedValue"]


@dataclass
class TypedValue:
    """All pseudocode values are encapsulated in a TypedValue.
    Each TypedValue has a type and a value.
    """
    __slots__ = ("type", "value")
    type: Type
    value: Optional[Value]

    def __repr__(self) -> str:
        return f"<{self.type}: {repr(self.value)}>"


class Template(ABC):
    """Base class for ObjectTemplate and TypeTemplate.
    Templates are used to clone objects and types.
    They do not store values.

    Methods
    -------
    clone()
    """
    @abstractmethod
    def clone(self):
        """Returns a copy of what the template represemts"""


@dataclass
class TypeTemplate(Template):
    """Represents a type template in 9608 pseudocode.
    A type template can be cloned to create a TypedValue slot
    (in a Frame or Object).

    Methods
    -------
    clone()
    """
    __slots__ = ("type", "value")
    type: Type
    value: Optional["ObjectTemplate"]

    def clone(self) -> "TypedValue":
        """This returns an empty TypedValue of the same type."""
        if isinstance(self.value, ObjectTemplate):
            return TypedValue(self.type, self.value.clone())
        return TypedValue(self.type, self.value)


class ObjectTemplate(Template):
    """Represents an object template in 9608 pseudocode.
    A space that maps Names to Types.
    An object template can be cloned to create an Object
    (in a Frame or nested Object).

    Methods
    -------
    clone()
    """
    __slots__ = ("types", "data")

    def __init__(self, typesys: "TypeSystem") -> None:
        self.types = typesys
        self.data: MutableMapping[NameKey, Type] = {}

    def __repr__(self) -> str:
        return repr(self.data)

    def declare(self, name: NameKey, type: Type) -> None:
        self.data[name] = type

    def clone(self) -> "Object":
        """
        This returns an empty Object with the same names
        declared.
        """
        obj = Object()
        for name, type in self.data.items():
            obj.declare(name, type)
        return obj


class TypeSystem:
    """A space that maps Types to TypeTemplates.
    Handles registration of types in 9608 pseudocode.
    Each type is registered with a name, and an optional template.
    Existence checks should be carried out (using has()) before using
    the methods here.

    Methods
    -------
    has(type)
    declare(type)
    setTemplate(type, template)
    cloneType(type)
    """
    __slots__ = ("data", )

    def __init__(self, *types: Type) -> None:
        self.data: MutableMapping[Type, TypeTemplate] = {}
        for typeName in types:
            self.declare(typeName)

    def __repr__(self) -> str:
        return f"{{{', '.join(self.data.keys())}}}"

    def has(self, type: Type) -> bool:
        """returns True if the type has been registered,
        otherwise returns False.
        """
        return type in self.data

    def declare(self, type: Type) -> None:
        """declares the existence of type in the TypeSystem.
        Use setTemplate(type, template) to set the template for this type.
        """
        self.data[type] = TypeTemplate(type, None)

    def setTemplate(self, type: Type, template: "ObjectTemplate") -> None:
        """Set the template used to initialise a TypedValue with this type."""
        self.data[type].value = template

    def cloneType(self, type: Type) -> "TypedValue":
        """Return a copy of the template for the type."""
        return self.data[type].clone()


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

    def has(self, name: NameKey) -> bool:
        return name in self.data

    def declare(self, name: NameKey, typedValue: TypedValue) -> None:
        self.data[name] = typedValue

    def get(self, name: NameKey) -> TypedValue:
        return self.data[name]

    def getType(self, name: NameKey) -> Type:
        return self.data[name].type

    def getValue(self, name: NameKey) -> Value:
        returnval = self.data[name].value
        if returnval is None:
            raise ValueError(f"Accessed unassigned variable {name!r}")
        return returnval

    def set(self, name: NameKey, typedValue: TypedValue) -> None:
        self.data[name] = typedValue

    def setValue(self, name: NameKey, value: Value) -> None:
        self.data[name].value = value

    def delete(self, name: NameKey) -> None:
        del self.data[name]

    def lookup(self, name: NameKey) -> Optional["Frame"]:
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
    - data
        A MutableMapping used to map keys to TypedValues
    """
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
    __slots__ = ("ranges", "data")

    def __init__(self, ranges: IndexRanges, type: Type) -> None:
        self.ranges = ranges
        self.data: IndexMap = {}

    def __repr__(self) -> str:
        nameValuePairs = [
            f"{index}: {self.getValue(index)}" for index in self.data
        ]
        return f"{{{', '.join(nameValuePairs)}}}: {self.elementType}"

    @staticmethod
    def rangeProduct(indexes: IndexRanges) -> Iterator:
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
    def elementType(self) -> Type:
        return tuple(self.data.values())[0].type

    def has(self, index: IndexKey) -> bool:
        return index in self.data

    def declare(self, index: IndexKey, typedValue: TypedValue) -> None:
        self.data[index] = typedValue

    def getType(self, index: IndexKey) -> Type:
        return self.data[index].type

    def getValue(self, index: IndexKey) -> Union[PyLiteral, "Object"]:
        returnval = self.data[index].value
        if returnval is None:
            raise ValueError(f"Accessed unassigned index {index!r}")
        assert (isinstance(returnval, bool) or isinstance(returnval, int)
                or isinstance(returnval, float) or isinstance(returnval, str)
                or isinstance(returnval,
                              Object)), f"Unexpected {type(returnval)}"
        return returnval

    def get(self, index: IndexKey) -> "TypedValue":
        return self.data[index]

    def setValue(self, index: IndexKey, value: Union[PyLiteral,
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
    __slots__ = ("data", )

    def __init__(self) -> None:
        self.data: NameMap = {}

    def __repr__(self) -> str:
        nameTypePairs = [f"{name}: {self.getType(name)}" for name in self.data]
        return f"{{{', '.join(nameTypePairs)}}}"

    def has(self, name: NameKey) -> bool:
        return name in self.data

    def declare(self, name: NameKey, typedValue: TypedValue) -> None:
        self.data[name] = typedValue

    def getType(self, name: NameKey) -> Type:
        return self.data[name].type

    def getValue(self, name: NameKey) -> "Assignable":
        returnval = self.data[name].value
        if returnval is None:
            raise ValueError(f"Accessed unassigned variable {name!r}")
        assert (isinstance(returnval, bool) or isinstance(returnval, int)
                or isinstance(returnval, float)
                or isinstance(returnval, str) or isinstance(
                    returnval, Container)), f"Unexpected {type(returnval)}"
        return returnval

    def get(self, name: NameKey) -> "TypedValue":
        return self.data[name]

    def setValue(self, name: NameKey, value: "Assignable") -> None:
        self.data[name].value = value


Assignable = Union[PyLiteral, Container]
