from typing import Any, Optional, Union
from typing import Iterable, Iterator, Mapping, MutableMapping, Protocol
from typing import Tuple, List, Dict
from typing import Callable as function, TextIO
from abc import abstractmethod
from itertools import product

# Pseudocode types
# These are used for type-checking
PyLiteral = Union[bool, int, float, str]  # Simple data types
Type = str  # pseudocode type, whether built-in or declared
NameKey = str  # Key for Object/Frame
IndexKey = Tuple[int, ...]  # Key for Array
IndexExpr = Tuple["Literal", ...]  # Array indexes
IndexRange = Tuple["Literal", "Literal"]  # Array ranges (declared)
Args = Iterable["Expr"]  # Callable args
ParamDecl = "Declare"  # ProcFunc params (in statement)
Param = "TypedValue"  # Callable params (in the frame)
Value = Union[PyLiteral, "PseudoValue"]  # in TypedValue
Cases = MutableMapping[PyLiteral, List["Stmt"]]  # For Conditionals
# Rule = str  # Stmt rules
# FileData = Optional[Union["Expr", str]]

# ----------------------------------------------------------------------
class Token:
    """
    Encapsulates data for a token.
    """
    def __init__(
        self,
        line: int,
        column: int,
        type: Type,
        word: str,
        value: PyLiteral,
    ) -> None:
        self.line = line
        self.col = column
        self.type = type
        self.word = word
        self.value = value

    def __repr__(self) -> str:
        lineinfo = f"[Line {self.line} column {self.col}]"
        return f"{lineinfo} <{self.value}> {repr(self.word)}"



class Name:
    __slots__ = ('name', '_token')
    def __init__(
        self,
        name: NameKey,
        *,
        token: "Token",
    ) -> None:
        self.name = name
        self._token = token

    def __str__(self) -> NameKey:
        return self.name

    def token(self) -> "Token":
        return self._token



class PseudoMap(Protocol):
    """
    Represents a mapping of keys to values used in pseudo.

    Methods
    -------
    has(key)
        returns True if the key exists in the map
    """
    @abstractmethod
    def has(self, key) -> bool:
        raise NotImplementedError



class TypedValue:
    """
    Represents a value in 9608 pseudocode.
    Each TypedValue has a type and a value.
    """
    def __init__(
        self,
        type: Type,
        value: Optional[Value],
    ) -> None:
        self.type = type
        self.value = value

    def __repr__(self) -> str:
        return f"<{self.type}: {repr(self.value)}>"



class TypeTemplate:
    """
    Represents a type template in 9608 pseudocode.
    A type template can be cloned to create a TypedValue slot
    (for an Object or Frame).
    """
    def __init__(
        self,
        type: Type,
        value: Optional["Object"],
    ) -> None:
        self.type = type
        self.value = value

    def __repr__(self) -> str:
        return f"<{self.type}: {type(self.value)}>"

    def clone(self) -> "TypedValue":
        """
        This returns an empty TypedValue of the same type
        """
        if isinstance(self.value, Object):
            return TypedValue(self.type, self.value.copy())
        return TypedValue(self.type, self.value)



class TypeSystem:
    """
    A space that maps Types to TypeTemplates.
    Handles registration of types in 9608 pseudocode.
    Each type is registered with a name, and an optional template.
    Existence checks should be carried out (using has()) before using the
    methods here.

    Methods
    -------
    has(type)
        returns True if the type has been registered, otherwise returns False
    register(type)
        declares the existence of a type
    setTemplate(type, template)
        set the template used to initialise a TypedValue with this type
    cloneType(type)
        return a copy of the template for the type
    """
    def __init__(
        self,
        *types: Type,
    ) -> None:
        self.data: Mapping[Type, "TypedValue"] = {}
        for typeName in types:
            self.declare(typeName)

    def __repr__(self) -> str:
        nameTypePairs = [
            f"{name}: {repr(self.data[name])}"
            for name in self.data
        ]
        return f"{{{', '.join(nameTypePairs)}}}"

    def has(self, name: str) -> bool:
        return name in self.data

    def declare(self, name: str) -> None:
        self.data[name] = TypeTemplate(name, None)

    def setTemplate(self, name: Type, template: "Object") -> None:
        self.data[name].value = template

    def cloneType(self, name: Type) -> Optional["Object"]:
        return self.data[name].clone()



class PseudoValue:
    """
    Base class for pseudo values.
    Represents a value stored in the frame.
    """



class Object(PseudoValue):
    """
    A space that maps NameKeys to TypedValues.
    Existence checks should be carried out (using has()) before using the
    methods here.

    Methods
    -------
    has(name)
        returns True if the var exists in frame,
        otherwise returns False
    declare(name, type)
        initialises a named TypedValue from the type system
    get(name)
        retrieves the slot associated with the name
    getType(name)
        retrieves the type information associated
        the name
    getValue(name)
        retrieves the value associated with the name
    setValue(name, value)
        updates the value associated with the name
    copy()
        return a copy of the object
    """
    def __init__(
        self,
        typesys: "TypeSystem",
    ) -> None:
        self.data: Dict[NameKey, "TypedValue"] = {}
        self.types = typesys

    def __repr__(self) -> str:
        nameTypePairs = [
            f"{name}: {self.getType(name)}"
            for name in self.data
        ]
        return f"{{{', '.join(nameTypePairs)}}}"

    def has(self, name: NameKey) -> bool:
        return name in self.data

    def declare(self, name: NameKey, type: str) -> None:
        self.data[name] = self.types.cloneType(type)

    def getType(self, name: NameKey) -> Type:
        return self.data[name].type

    def getValue(self, name: NameKey) -> Optional[Value]:
        return self.data[name].value

    def get(self, name: NameKey) -> "TypedValue":
        return self.data[name]

    def setValue(self, name: NameKey, value: Value) -> None:
        self.data[name].value = value



class Frame(Object):
    """
    Frames differ from Objects in that they can be chained (with a reference to an
    outer Frame, names can be reassigned to a different TypedValue, and slots can
    be deleted after declaration.
    Existence checks should be carried out (using has()) before using the
    methods here.

    Methods
    -------
    set(name, typedValue)
        assigns the given TypedValue to the name
    delete(name)
        deletes the slot associated with the name
    lookup(name)
        returns the first frame containing the name
    """
    def __init__(
        self,
        typesys: "TypeSystem",
        outer: "Frame"=None,
    ) -> None:
        super().__init__(typesys=typesys)
        self.outer = outer

    def set(self, name: NameKey, typedValue: TypedValue) -> None:
        self.data[name] = typedValue

    def delete(self, name: NameKey) -> None:
        del self.data[name]

    def lookup(self, name: NameKey) -> Optional["Frame"]:
        if self.has(name):
            return self
        if self.outer:
            return self.outer.lookup(name)
        return None



class Array(PseudoValue):
    """
    A space that maps IndexKeys to TypedValues.
    Arrays differ from Objects in the use of IndexKey instead of NameKey,
    and in being statically allocated at init.

    Attributes
    ----------
    dim: int
        integer representing the number of dimensions of the array
    ranges: Iterable[Tuple[int, int]]
        an interable containing (start, end) tuple pairs of the array indexes
    elementType: Type
        The type of each array element

    Methods
    -------
    has(index)
        returns True if the index exists in frame,
        otherwise returns False
    get(name)
        retrieves the slot associated with the name
    getType(name)
        retrieves the type information associated
        the name
    getValue(name)
        retrieves the value associated with the name
    setValue(name, value)
        updates the value associated with the name
    """
    def __init__(
        self,
        typesys: "TypeSystem",
        ranges: Iterable[Tuple[int, int]],
    ) -> None:
        self.types = typesys
        # ranges is an iterable of (start, end) indexes
        self.ranges = ranges
        self.data: Dict[IndexKey, "TypedValue"] = {
            index: self.types.cloneType(type)
            for index in self.rangeProduct(ranges)
        }

    def __repr__(self) -> str:
        nameValuePairs = [
            f"{index}: {self.getValue(index)}"
            for index in self.data
        ]
        return f"{{{', '.join(nameValuePairs)}}}: {self.elementType}"

    @staticmethod
    def rangeProduct(indexes: Iterable[Tuple[int, int]]) -> Iterator:
        """
        Returns an iterator from an interable of (start, end) tuples.
        E.g. ((0, 2), (0, 3)) will return the following iterations:
            (0, 0), ..., (0, 3),
            (1, 0), ..., (1, 3),
            (2, 0), ..., (2, 3),
        """
        ranges = (
            range(start, end + 1)
            for (start, end) in indexes
        )
        return product(*ranges)

    @property
    def dim(self) -> int:
        """
        Returns the number of dimensions the array has, as an integer.
        E.g. a 1D array would return 1, 2D array would return 2, ...
        """
        return len(self.ranges)

    @property
    def elementType(self) -> Type:
        for elem in self.data.values():
            return elem.type

    def has(self, index: IndexKey) -> bool:
        return index in self.data

    def getType(self, index: IndexKey) -> Type:
        return self.data[index].type

    def getValue(self, index: IndexKey) -> Optional[Value]:
        return self.data[index].value

    def get(self, index: IndexKey) -> "TypedValue":
        return self.data[index]

    def setValue(self, index: IndexKey, value: Value) -> None:
        self.data[index].value = value



class Builtin(PseudoValue):
    """
    Represents a system function in pseudo.

    Attributes
    ----------
    - params
        A list of parameters used by the callable
    - func
        the Python function to call when invoked
    """
    __slots__ = ('params', 'func')
    def __init__(
        self,
        params: Iterable,
        func: function,
    ) -> None:
        self.params = params
        self.func = func

    def __repr__(self) -> str:
        attrstr = ", ".join([
            repr(getattr(self, attr)) for attr in self.__slots__
        ])
        return f'{type(self).__name__}({attrstr})'



class Callable(PseudoValue):
    """
    Base class for Function and Procedure.
    Represents a Callable in pseudo.

    Attributes
    ----------
    - frame
        The frame used by the callable
    - params
        A list of parameters used by the callable
    - stmts
        A list of statements the callable executes when called
    """
    __slots__ = ('frame', 'params', 'stmts')
    def __init__(
        self,
        frame: "Frame",
        params: Iterable[Param],
        stmts: Iterable["Stmt"],
    ) -> None:
        self.frame = frame
        self.params = params
        self.stmts = stmts

    def __repr__(self) -> str:
        attrstr = ", ".join([
            repr(getattr(self, attr)) for attr in self.__slots__
        ])
        return f'{type(self).__name__}({attrstr})'



class Function(Callable):
    """Functions are evaluated to return a value."""



class Procedure(Callable):
    """Procedures are called to execute its statements."""



class File(PseudoValue):
    """
    Represents a file object in pseudo.
    Files can be opened in READ, WRITE, or APPEND mode.

    Attributes
    ----------
    - name
        Name of the file that is open
    - mode
        The mode that the file was opened in
    - iohandler
        An object for accessing the file
    """
    __slots__ = ('name', 'mode', 'iohandler')
    def __init__(
        self,
        name: NameKey,
        mode: str,
        iohandler: TextIO,
    ) -> None:
        self.name = name
        self.mode = mode
        self.iohandler = iohandler

    def __repr__(self) -> str:
        return f"<{self.mode}: {self.name}>"



class Expr:
    """
    Represents an expression in 9608 pseudocode.
    An expression can be resolved to a Type,
    and evaluated to a Value.
    An Expr must return an associated token for error-reporting purposes.

    Methods
    -------
    - token() -> Token
        Returns the token asociated with the expr
    """
    __slots__: Iterable[str] = NotImplemented
    def __repr__(self) -> str:
        attrstr = ", ".join([
            repr(getattr(self, attr)) for attr in self.__slots__
        ])
        return f'{type(self).__name__}({attrstr})'

    @abstractmethod
    def token(self) -> "Token":
        raise NotImplementedError



class Literal(Expr):
    """
    A Literal represents any value coming directly from
    the source code.
    """
    __slots__ = ('type', 'value', '_token')
    def __init__(self, type: Type, value: PyLiteral, *, token: "Token") -> None:
        self.type = type
        self.value = value
        self._token = token

    def token(self) -> "Token":
        return self._token



class Declare(Expr):
    __slots__ = ('name', 'type', 'metadata', '_token')
    def __init__(
        self,
        name: NameKey,
        type: Type,
        metadata: Mapping=None,
        *,
        token: "Token",
    ) -> None:
        self.name = name
        self.type = type
        self.metadata = metadata
        self._token = token

    def token(self):
        return self._token



class Assign(Expr):
    __slots__ = ('assignee', 'expr')
    def __init__(
        self,
        assignee: "Get",
        expr: "Expr",
    ) -> None:
        self.assignee = assignee
        self.expr = expr

    def token(self):
        return self.assignee.token()



class Unary(Expr):
    __slots__ = ('oper', 'right', '_token')
    def __init__(
        self,
        oper: function,
        right: "Expr",
        *,
        token: "Token",
    ) -> None:
        self.oper = oper
        self.right = right
        self._token = token

    def token(self):
        return self._token



class Binary(Expr):
    __slots__ = ('left', 'oper', 'right', '_token')
    def __init__(
        self,
        left: "Expr",
        oper: function,
        right: "Expr",
        *,
        token: "Token",
    ) -> None:
        self.left = left
        self.oper = oper
        self.right = right
        self._token = token

    def token(self):
        return self._token



class Get(Expr):
    __slots__ = ('frame', 'name', '_token')
    def __init__(
        self,
        frame: "Frame",
        name: Name,
        *,
        token: "Token",
    ) -> None:
        self.frame = frame
        self.name = name
        self._token = token

    def token(self):
        return self._token



class Call(Expr):
    __slots__ = ('callable', 'args')
    def __init__(
        self,
        callable: "Get",
        args: Args,
    ) -> None:
        self.callable = callable
        self.args = args

    def token(self):
        return self.callable.token()



class Stmt:
    rule: str = NotImplemented
    def __repr__(self) -> str:
        attrstr = ", ".join([
            repr(getattr(self, attr)) for attr in self.__slots__
        ])
        return f'{type(self).__name__}({attrstr})'



class ExprStmt(Stmt):
    __slots__ = ('rule', 'expr')
    def __init__(
        self,
        rule: str,
        expr: "Expr",
    ) -> None:
        self.rule = rule
        self.expr = expr



class Output(Stmt):
    __slots__ = ('rule', 'exprs')
    def __init__(
        self,
        rule: str,
        exprs: Iterable["Expr"],
    ) -> None:
        self.rule = rule
        self.exprs = exprs



class Input(Stmt):
    __slots__ = ('rule', 'name')
    def __init__(
        self,
        rule: str,
        name: "Name",
    ) -> None:
        self.rule = rule
        self.name = name



class Conditional(Stmt):
    __slots__ = ('rule', 'cond', 'stmtMap', 'fallback')
    def __init__(
        self,
        rule: str,
        cond: "Expr",
        stmtMap: Mapping[PyLiteral, Iterable["Stmt"]],
        fallback: Optional[Iterable["Stmt"]],
    ) -> None:
        self.rule = rule
        self.cond = cond
        self.stmtMap = stmtMap
        self.fallback = fallback



class Loop(Stmt):
    __slots__ = ('rule', 'init', 'cond', 'stmts')
    def __init__(
        self,
        rule: str,
        init: Optional["Stmt"],
        cond: "Expr",
        stmts: Iterable["Stmt"],
    ) -> None:
        self.rule = rule
        self.init = init
        self.cond = cond
        self.stmts = stmts



class ProcFunc(Stmt):
    __slots__ = ('rule', 'name', 'passby', 'params', 'stmts', 'returnType')
    def __init__(
        self,
        rule: str,
        name: Name,
        passby: str,
        params: Iterable[Param],
        stmts: Iterable["Stmt"],
        returnType: Type,
    ) -> None:
        self.rule = rule
        self.name = name
        self.passby = passby
        self.params = params
        self.stmts = stmts
        self.returnType = returnType



class TypeStmt(Stmt):
    __slots__ = ('rule', 'name', 'exprs')
    def __init__(
        self,
        rule: str,
        name: Name,
        exprs: Iterable["Expr"],
    ) -> None:
        self.rule = rule
        self.name = name
        self.exprs = exprs



class OpenFile(Stmt):
    __slots__ = ('rule', 'filename', 'mode')
    def __init__(
        self,
        rule: str,
        filename: "Expr",
        mode: str,
    ) -> None:
        self.rule = rule
        self.filename = filename
        self.mode = mode

class ReadFile(Stmt):
    __slots__ = ('rule', 'filename', 'target')
    def __init__(
        self,
        rule: str,
        filename: "Expr",
        target: Name,  # TODO: Support other Gets
    ) -> None:
        self.rule = rule
        self.filename = filename
        self.target = target

class WriteFile(Stmt):
    __slots__ = ('rule', 'filename', 'data')
    def __init__(
        self,
        rule: str,
        filename: "Expr",
        data: "Expr",  # TODO: Support other Gets
    ) -> None:
        self.rule = rule
        self.filename = filename
        self.data = data

class CloseFile(Stmt):
    __slots__ = ('rule', 'filename')
    def __init__(
        self,
        rule: str,
        filename: "Expr",
    ) -> None:
        self.rule = rule
        self.filename = filename
