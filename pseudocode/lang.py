"""Entities and types used by pseudo-9608.

Token
    A token in the source code

Name
    A named reference

TypeSystem
    A manager for built-in and declared types

Object
    Allows attributes to be addressed by name

Array
    Allows elements to be addressed by index

Frame
    Allows values to be addressed by name

Builtin, Function, Procedure
    Callables invoked with arguments

File
    An open file
"""
from typing import Any, Optional, Union, TypedDict
from typing import Iterable, Iterator, Mapping, MutableMapping, Collection
from typing import Literal as LiteralType, Tuple, List
from typing import Callable as function, IO
from dataclasses import dataclass
from itertools import product

# Pseudocode types
# These are used for type-checking
PyLiteral = Union[bool, int, float, str]  # Simple data types
Type = str  # pseudocode type, whether built-in or declared
NameKey = str  # Key for Object/Frame
IndexKey = Tuple[int, ...]  # Key for Array
IndexExpr = Tuple["Expr", ...]  # Array indexes
IndexRange = Tuple[int, int]  # Array ranges (declared)
Passby = LiteralType['BYREF', 'BYVALUE']
Args = Collection["Expr"]  # Callable args
ParamDecl = "Declare"  # ProcFunc params (in statement)
# HACK: Should use TypeAlias but not yet supported in Python 3.8
Param = Union["TypedValue"]  # Callable params (in the frame)
Value = Union[PyLiteral, "Object", "Array", "Builtin", "Callable", "File"]  # in TypedValue
Cases = MutableMapping[PyLiteral, List["Stmt"]]  # For Conditionals
# NameExprs are GetExprs that use a NameKey
NameKeyExpr = Union["UnresolvedName", "GetName"]
# GetExprs hold Exprs that evaluate to a KeyMap and a Key
GetExpr = Union["UnresolvedName", "GetName", "GetAttr", "GetIndex"]
# NameExprs start with a name
NameExpr = Union[GetExpr, "Call"]
class TypeMetadata(TypedDict, total=False):
    """The metadata dict passed to an Array declaration"""
    size: Tuple[IndexRange, ...]
    type: Type
    

# ----------------------------------------------------------------------
@dataclass(eq=False, frozen=True)
class Token:
    """Tokens encapsulate data needed by the parser to construct Exprs
    and Stmts.
    It also encapsulates code information for error reporting.
    """
    __slots__ = ('line', 'column', 'type', 'word', 'value')
    line: int
    column: int
    type: Type
    word: str
    value: Any

    def __repr__(self) -> str:
        lineinfo = f"[Line {self.line} column {self.column}]"
        return f"{lineinfo} <{self.value}> {repr(self.word)}"



class Name:
    """Name represents a meaningful name, either a custom type or a
    variable name.
    """
    __slots__ = ('name', '_token')
    def __init__(
        self,
        name: NameKey,
        *,
        token: "Token",
    ) -> None:
        self.name = name
        self._token = token

    def __repr__(self) -> str:
        return f'Name({self.name})'

    def __str__(self) -> NameKey:
        return self.name

    def token(self) -> "Token":
        return self._token



@dataclass
class TypedValue:
    """All pseudocode values are encapsulated in a TypedValue.
    Each TypedValue has a type and a value.
    """
    __slots__ = ('type', 'value')
    type: Type
    value: Optional[Value]

    def __repr__(self) -> str:
        return f"<{self.type}: {repr(self.value)}>"



@dataclass
class TypeTemplate:
    """Represents a type template in 9608 pseudocode.
    A type template can be cloned to create a TypedValue slot
    (in a Frame or Object).

    Methods
    -------
    clone()
        Returns a TypedValue of the same type
    """
    __slots__ = ('type', 'value')
    type: Type
    value: Optional["ObjectTemplate"]

    def clone(self) -> "TypedValue":
        """
        This returns an empty TypedValue of the same type
        """
        if isinstance(self.value, ObjectTemplate):
            return TypedValue(self.type, self.value.clone())
        return TypedValue(self.type, self.value)



class ObjectTemplate:
    """Represents an object template in 9608 pseudocode.
    A space that maps Names to Types.
    An object template can be cloned to create an Object
    (in a Frame or nested Object).

    Methods
    -------
    clone()
        Returns an empty Object of the same type
    """

    def __init__(
        self,
        typesys: "TypeSystem",
    ) -> None:
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
        obj = Object(typesys=self.types)
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
        returns True if the type has been registered,
        otherwise returns False
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
        self.data: MutableMapping[Type, TypeTemplate] = {}
        for typeName in types:
            self.declare(typeName)

    def __repr__(self) -> str:
       return f"{{{', '.join(self.data.keys())}}}"

    def has(self, type: Type) -> bool:
        return type in self.data

    def declare(self, type: Type) -> None:
        self.data[type] = TypeTemplate(type, None)

    def setTemplate(
        self,
        type: Type,
        template: "ObjectTemplate",
    ) -> None:
        self.data[type].value = template

    def cloneType(self, type: Type) -> "TypedValue":
        return self.data[type].clone()



class PseudoValue:
    """Base class for pseudo values which are not PyLiterals.
    This includes Arrays, Objects, and Callables.
    PseudoValues may be stored in Arrays, Objects, or Callables, wrapped
    in a TypedValue.
    """



class Object(PseudoValue):
    """A space that maps NameKeys to TypedValues.
    Existence checks should be carried out (using has()) before using
    the methods here.

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
    """

    def __init__(
        self,
        typesys: "TypeSystem",
    ) -> None:
        self.data: MutableMapping[NameKey, "TypedValue"] = {}
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

    def getValue(self, name: NameKey) -> Union[PyLiteral, "Object"]:
        returnval = self.data[name].value
        if returnval is None:
            raise ValueError(f"Accessed unassigned variable {name!r}")
        assert not isinstance(returnval, Array), "Unexpected Array"
        assert not isinstance(returnval, Builtin), "Unexpected Builtin"
        assert not isinstance(returnval, Callable), "Unexpected Callable"
        assert not isinstance(returnval, File), "Unexpected File"
        return returnval

    def get(self, name: NameKey) -> "TypedValue":
        return self.data[name]

    def setValue(self, name: NameKey, value: Value) -> None:
        self.data[name].value = value



class Frame:
    """Frames differ from Objects in that they can be chained (with a
    reference to an outer Frame, names can be reassigned to a different
    TypedValue, and slots can be deleted after declaration.
    Existence checks should be carried out (using has()) before using
    the methods here.

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
        self.data: MutableMapping[NameKey, "TypedValue"] = {}
        self.types = typesys
        self.outer = outer

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

    def getValue(self, name: NameKey) -> Value:
        returnval = self.data[name].value
        if returnval is None:
            raise ValueError(f"Accessed unassigned variable {name!r}")
        return returnval

    def get(self, name: NameKey) -> "TypedValue":
        return self.data[name]

    def setValue(self, name: NameKey, value: Value) -> None:
        self.data[name].value = value

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
    """A space that maps IndexKeys to TypedValues.
    Arrays differ from Objects in the use of IndexKey instead of
    NameKey, and in being statically allocated at init.

    Attributes
    ----------
    dim: int
        integer representing the number of dimensions of the array
    ranges: Iterable[Tuple[int, int]]
        an interable containing (start, end) tuple pairs of the
        array indexes
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
        ranges: Collection[IndexRange],
        type: Type,
    ) -> None:
        self.types = typesys
        # ranges is an iterable of (start, end) indexes
        self.ranges = ranges
        self.data: MutableMapping[IndexKey, "TypedValue"] = {
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
        """Returns an iterator from an interable of (start, end) tuples.
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

    def getType(self, index: IndexKey) -> Type:
        return self.data[index].type

    def getValue(self, index: IndexKey) -> Union[PyLiteral, Object]:
        returnval = self.data[index].value
        if returnval is None:
            raise ValueError(f"Accessed unassigned index {index!r}")
        assert not isinstance(returnval, Array), "Unexpected Array"
        assert not isinstance(returnval, Builtin), "Unexpected Builtin"
        assert not isinstance(returnval, Callable), "Unexpected Callable"
        assert not isinstance(returnval, File), "Unexpected File"
        return returnval

    def get(self, index: IndexKey) -> "TypedValue":
        return self.data[index]

    def setValue(self, index: IndexKey, value: Value) -> None:
        self.data[index].value = value



@dataclass
class Builtin(PseudoValue):
    """Represents a system function in pseudo.

    Attributes
    ----------
    - params
        A list of parameters used by the callable
    - func
        the Python function to call when invoked
    """
    __slots__ = ('params', 'func')
    params: Collection[Param]
    func: function



@dataclass
class Callable(PseudoValue):
    """Base class for Function and Procedure.
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
    frame: "Frame"
    params: Collection[Param]
    stmts: Iterable["Stmt"]



class Function(Callable):
    """Functions are evaluated to return a value."""



class Procedure(Callable):
    """Procedures are called to execute its statements."""



@dataclass
class File(PseudoValue):
    """Represents a file object in pseudo.
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
    name: NameKey
    mode: str
    iohandler: IO



class Expr:
    """Represents an expression in 9608 pseudocode.
    An expression can be resolved to a Type, and evaluated to a Value.
    An Expr must return an associated token for error-reporting
    purposes.

    Attributes
    ----------
    token: Token
        Returns the token asociated with the expr
    """

    __slots__: Iterable[str] = tuple()

    @property
    def token(self) -> "Token":
        raise NotImplementedError



@dataclass
class Literal(Expr):
    """A Literal represents any value coming directly from the source
    code.
    """
    __slots__ = ('type', 'value', 'token')
    type: Type
    value: PyLiteral
    token: Token



@dataclass
class Declare(Expr):
    """A Declare Expr associates a Name with its declared Type."""
    __slots__ = ('name', 'type', 'metadata')
    name: Name
    type: Type
    metadata: Mapping

    @property
    def token(self):
        return self.name.token



@dataclass
class Assign(Expr):
    """An Assign Expr represents an assignment operation.
    The Expr's evaluated value should be assigned to the Name/Index
    represented by the assignee.
    """
    __slots__ = ('assignee', 'expr')
    assignee: GetExpr
    expr: "Expr"

    @property
    def token(self):
        return self.assignee.token



@dataclass
class Unary(Expr):
    """A Unary Expr represents the invocation of a unary callable with a
    single operand.
    """
    __slots__ = ('oper', 'right', 'token')
    oper: function
    right: "Expr"
    token: Token



@dataclass
class Binary(Expr):
    """A Binary Expr represents the invocation of a binary callable
    with two operands.
    """
    __slots__ = ('left', 'oper', 'right', 'token')
    left: "Expr"
    oper: function
    right: "Expr"
    token: Token



@dataclass
class UnresolvedName(Expr):
    """An UnresolvedName is a Name which has been parsed, and whose
    context is not yet determined.

    The context is usually determined at the resolving stage. When
    determined, the UnresolvedName should not be mutated; an
    appropriate Get Expr should be used to contain the name and context
    instead.
    """
    __slots__ = ('name',)
    name: Name

    @property
    def token(self):
        return self.name.token



@dataclass
class GetName(Expr):
    """A GetName Expr represents a Name with a Frame context.
    """
    __slots__ = ('frame', 'name')
    frame: "Frame"
    name: Name

    @property
    def token(self):
        return self.name.token



@dataclass
class GetIndex(Expr):
    """A GetName Expr represents a Index with an Array context.
    """
    __slots__ = ('array', 'index')
    array: NameExpr
    index: IndexExpr

    @property
    def token(self):
        return self.index[0].token



@dataclass
class GetAttr(Expr):
    """A GetName Expr represents a Name with an Object context.
    """
    __slots__ = ('object', 'name')
    object: NameExpr
    name: Name

    @property
    def token(self):
        return self.name.token



@dataclass
class Call(Expr):
    """A Call Expr represents the invocation of a Callable (Function or
    Procedure) with arguments.
    """
    __slots__ = ('callable', 'args')
    callable: NameKeyExpr
    args: Args

    @property 
    def token(self):
        return self.callable.token



class Stmt:
    """Represents a statement in 9608 pseudocode.
    A statement usually has one or more expressions, and represents an
    effect: console output, user input, or frame mutation.
    """

    __slots__: Iterable[str] = tuple()



class ExprStmt(Stmt):
    """Base class for statements that contain only a single Expr.
    """
    __slots__ = ('expr',)

@dataclass
class Return(ExprStmt):
    """Return encapsulates the value to be returned from a Function.
    """
    expr: "Expr"

@dataclass
class AssignStmt(ExprStmt):
    """AssignStmt encapsulates an Assign Expr.
    """
    expr: "Assign"

@dataclass
class DeclareStmt(ExprStmt):
    """DeclareStmt encapsulates a Declare Expr.
    """
    expr: "Declare"

@dataclass
class CallStmt(ExprStmt):
    """CallStmt encapsulates a Call Expr.
    """
    expr: "Call"



@dataclass
class Output(Stmt):
    """Output encapsulates values to be displayed in a terminal/console.
    """
    __slots__ = ('exprs',)
    exprs: Iterable["Expr"]



@dataclass
class Input(Stmt):
    """Output encapsulates a GetExpr to which user input should be
    assigned.
    """
    __slots__ = ('keyExpr',)
    key: GetExpr



@dataclass
class Conditional(Stmt):
    """Conditional encapsulates a mapping of values to statements.
    A provided condition cond, when evaluated to a value, results in
    the associated statement(s) being executed.
    """
    __slots__ = ('cond', 'stmtMap', 'fallback')
    cond: "Expr"
    stmtMap: Mapping[PyLiteral, Iterable["Stmt"]]
    fallback: Optional[Iterable["Stmt"]]

class Case(Conditional): ...

class If(Conditional): ...



class Loop(Stmt):
    """Loop encapsulates statements to be executed repeatedly until its
    cond evaluates to a False value.
    """
    __slots__ = ('init', 'cond', 'stmts')
    init: Optional["Stmt"]
    cond: "Expr"
    stmts: Iterable["Stmt"]

@dataclass
class While(Loop):
    """While represents a pre-condition Loop, executed only if the cond
    evaluates to True.
    """
    init: Optional["Stmt"]
    cond: "Expr"
    stmts: Iterable["Stmt"]

@dataclass
class Repeat(Loop):
    """Repeat represents a post-condition Loop, executed at least once,
    and then again only if the cond evaluates to True.
    """
    init: None
    cond: "Expr"
    stmts: Iterable["Stmt"]



@dataclass
class ProcFunc(Stmt):
    """ProcFunc encapsulates a declared Procedure or Function."""    
    __slots__ = ('name', 'passby', 'params', 'stmts', 'returnType')
    name: Name
    passby: LiteralType['BYVALUE', 'BYREF']
    params: Iterable[Declare]
    stmts: Iterable["Stmt"]
    returnType: Type

class ProcedureStmt(ProcFunc): ...

class FunctionStmt(ProcFunc): ...



@dataclass
class TypeStmt(Stmt):
    """TypeStmt encapsulates a declared custom Type."""    
    __slots__ = ('name', 'exprs')
    name: Name
    exprs: Iterable["Declare"]



class FileStmt(Stmt):
    """Base class for Stmts involving Files."""
    filename: "Expr"

@dataclass
class OpenFile(FileStmt):
    __slots__ = ('filename', 'mode')
    filename: "Expr"
    mode: str

@dataclass
class ReadFile(FileStmt):
    __slots__ = ('filename', 'target')
    filename: "Expr"
    target: GetExpr

@dataclass
class WriteFile(FileStmt):
    __slots__ = ('filename', 'data')
    filename: "Expr"
    data: "Expr"

@dataclass
class CloseFile(FileStmt):
    __slots__ = ('filename',)
    filename: "Expr"
