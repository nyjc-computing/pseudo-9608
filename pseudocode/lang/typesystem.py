"""typesystem.py

Template
    Used to clone abstract data types

TypeSystem
    A manager for built-in and declared types
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from .object import Object, PyLiteral, TypedValue
from .types import (
    Type, Key, NameKey, IndexKey, IndexRange, IndexRanges
)


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
