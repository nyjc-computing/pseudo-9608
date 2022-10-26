"""lang.py
This module defines the entities and types used by pseudo-9608.

types.py contains definitions for attribute types used in object.py
and typesystem.py
object.py contains definitions for object types in Pseudo.
typesystem.py contains definitions that make up the typesystem used in Pseudo.

Token
    A token in the source code

Name
    A named reference

Builtin, Function, Procedure
    Callables invoked with arguments

File
    An open file
"""
from dataclasses import dataclass, field
from typing import (
    get_args,
    Any,
    Callable as function,
    IO,
    Iterable,
    Literal as LiteralType,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
)

# Merge namespace
from .object import *
from .types import *
from .typesystem import *

from . import (
    object as o,
    types as t,
    typesystem as ts,
)

# Pseudocode types
# PyLiteral = Union[bool, int, float, str]  # Simple data types
# Type = str  # pseudocode type, whether built-in or declared
Index = Union["Expr"]
Indices = Tuple[Index, ...]  # Array indexes
Passby = LiteralType["BYREF", "BYVALUE"]
PASSTYPE = get_args(Passby)
FileMode = LiteralType["READ", "WRITE", "APPEND", "RANDOM"]
FILEMODES = get_args(FileMode)

# Plurals
Exprs = Iterable["Expr"]
Stmts = Iterable["Stmt"]
Args = Sequence["Expr"]  # Callable args
Declares = Sequence["Declare"]

# Mappings
CaseMap = MutableMapping["Literal", Stmts]  # for Conditionals

# CallTargets resolve to function names
CallTarget = Union["UnresolvedName", "GetName"]

# While SetExprs represent targets that values can be assigned to,
# GetExprs represent sources that evaluate to targets.
GetExpr = Union["SetExpr", "Call"]
# TargetExprs and SourceExprs are SetExprs and GetExprs that include
# UnresolvedNames
TargetExpr = Union["UnresolvedName", "SetExpr"]
SourceExpr = Union["UnresolvedName", "GetExpr"]


class TypeMetadata(TypedDict, total=False):
    """The metadata dict passed to an Array declaration"""
    size: t.IndexRanges
    type: t.Type


@dataclass(eq=False, frozen=True)
class Token:
    """Tokens encapsulate data needed by the parser to construct Exprs
    and Stmts.
    It also encapsulates code information for error reporting.
    """
    __slots__ = ("line", "column", "type", "word", "value")
    line: int
    column: int
    type: t.Type
    word: str
    value: Any

    def __str__(self) -> str:
        lineinfo = f"[Line {self.line} column {self.column}]"
        valuestr = self.value or self.word
        return f"{lineinfo} {valuestr!r}"


@dataclass
class Environment:
    """Encapsulates the environment in which interpreting pseudocode is carried out.

    Arguments/Attributes
    --------------------
    - frame: Frame
    - typesys: TypeSystem
    """
    frame: o.Frame
    types: ts.TypeSystem

    def with_frame(self, frame: Union[o.Frame, ts.ObjectTemplate]) -> "Environment":
        """Returns a new Environment with the new frame."""
        return type(self)(frame, self.types)


@dataclass(frozen=True)
class Name:
    """Name represents a meaningful name, either a custom type or a
    variable name.
    """
    # dataclass doesn't play well with __slots__ and prevents use of field
    name: t.NameKey
    token: "Token" = field(repr=False)

    def __str__(self) -> t.NameKey:
        return self.name


class Callable(o.PseudoValue):
    """Base class for Builtin, Function and Procedure.
    Represents a Callable in pseudo.

    Attributes
    ----------
    - env
        The environment used by the callable
    - params
        A list of parameters used by the callable
    """


@dataclass
class Builtin(Callable):
    """Represents a system function in pseudo.

    Attributes
    ----------
    - func
        the Python function to call when invoked
    """
    __slots__ = ("env", "params", "func")
    env: "Environment"
    params: o.Params
    func: function


@dataclass
class Function(Callable):
    """Functions are evaluated to return a value.
    - stmts
      A list of statements the Function executes when called
    """
    __slots__ = ("env", "params", "stmts")
    env: "Environment"
    params: o.Params
    stmts: Stmts


@dataclass
class Procedure(Callable):
    """Procedures are called to execute its statements.
    - stmts
      A list of statements the Procedure executes when called
    """
    __slots__ = ("env", "params", "stmts")
    env: "Environment"
    params: o.Params
    stmts: Stmts


@dataclass
class File(o.PseudoValue):
    """Represents a file object in pseudo.
    Files can be opened in READ, WRITE, or APPEND, or RANDOM mode.

    *Note:* RANDOM mode is not yet supported.

    Attributes
    ----------
    - name
        Name of the file that is open
    - mode
        The mode that the file was opened in
    - iohandler
        An object for accessing the file
    """
    __slots__ = ("name", "mode", "iohandler")
    name: t.NameKey
    mode: FileMode
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
    def token(self) -> Token:
        raise NotImplementedError


@dataclass
class Literal(Expr):
    """A Literal represents any value coming directly from the source
    code.
    """
    __slots__ = ("type", "value", "token")
    type: t.Type
    value: o.PyLiteral
    
    token: Token

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Literal):
            # Allow Python to try other.__eq__(self)
            # See: https://stackoverflow.com/a/54816069
            return NotImplemented
        return self.value == other.value


@dataclass
class Declare(Expr):
    """A Declare Expr associates a Name with its declared Type."""
    __slots__ = ("name", "type", "metadata")
    name: Name
    type: t.Type
    metadata: TypeMetadata

    @property
    def token(self):
        return self.name.token


@dataclass
class Assign(Expr):
    """An Assign Expr represents an assignment operation.
    The Expr"s evaluated value should be assigned to the Name/Index
    represented by the assignee.
    """
    __slots__ = ("assignee", "expr")
    assignee: "SetExpr"
    expr: "Expr"

    @property
    def token(self):
        return self.assignee.token


@dataclass
class Unary(Expr):
    """A Unary Expr represents the invocation of a unary callable with a
    single operand.
    """
    __slots__ = ("oper", "right", "token")
    oper: function
    right: "Expr"
    token: Token


@dataclass
class Binary(Expr):
    """A Binary Expr represents the invocation of a binary callable
    with two operands.
    """
    __slots__ = ("left", "oper", "right", "token")
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

    UnresolvedNames are assumed to be variables or callables; type tokens
    where expected will be parsed to extract the name attribute.
    """
    __slots__ = ("name", )
    name: Name

    @property
    def token(self):
        return self.name.token


@dataclass
class SetExpr(Expr):
    """Base class for Exprs that form valid assignment targets.

    Such expressions involve a context, and a key for extracting data
    from the context.
    
    E.g. Variable evaluation, array indexing, object attribute access
    """


@dataclass
class GetName(SetExpr):
    """A GetName Expr represents a Name with a Frame context."""
    __slots__ = ("frame", "name")
    frame: o.Frame
    name: Name

    @property
    def token(self):
        return self.name.token


@dataclass
class GetIndex(SetExpr):
    """A GetName Expr represents a Index with an Array context."""
    __slots__ = ("array", "index")
    array: SetExpr
    index: Indices

    @property
    def token(self):
        return self.index[0].token


@dataclass
class GetAttr(SetExpr):
    """A GetName Expr represents a Name with an Object context."""
    __slots__ = ("object", "name")
    object: SetExpr
    name: Name

    @property
    def token(self):
        return self.name.token


@dataclass
class Call(Expr):
    """A Call Expr represents the invocation of a Callable with arguments.
    """
    __slots__ = ("callable", "args")
    callable: CallTarget
    args: Args

    @property
    def token(self):
        return self.callable.token


class Stmt:
    """Represents a statement in 9608 pseudocode.
    A statement usually has one or more expressions, and represents an
    effect: console output, user input, or frame mutation.
    """
    __slots__ = tuple()

class ExprStmt(Stmt):
    """Base class for statements that contain only a single Expr."""
    __slots__ = ("expr", )


@dataclass
class Return(ExprStmt):
    """Return encapsulates the value to be returned from a Function."""
    expr: "Expr"


@dataclass
class AssignStmt(ExprStmt):
    """AssignStmt encapsulates an Assign Expr."""
    expr: "Assign"


@dataclass
class DeclareStmt(ExprStmt):
    """DeclareStmt encapsulates a Declare Expr."""
    expr: "Declare"


@dataclass
class CallStmt(ExprStmt):
    """CallStmt encapsulates a Call Expr."""
    expr: "Call"


@dataclass
class Output(Stmt):
    """Output encapsulates values to be displayed in a terminal/console.
    """
    __slots__ = ("exprs", )
    exprs: Exprs


@dataclass
class Input(Stmt):
    """Input encapsulates a SetExpr to which user input should be
    assigned.
    """
    __slots__ = ("key", )
    key: "SetExpr"


@dataclass
class Conditional(Stmt):
    """Conditional encapsulates a mapping of values to statements.
    A provided condition cond, when evaluated to a value, results in
    the associated statement(s) being executed.
    """
    __slots__ = ("cond", "cases", "fallback")
    cond: "Expr"
    cases: CaseMap
    fallback: Optional[Stmts]


@dataclass
class Case(Conditional):
    ...


@dataclass
class If(Conditional):
    ...


class Loop(Stmt):
    """Loop encapsulates statements to be executed repeatedly until its
    cond evaluates to a False value.
    """
    __slots__ = ("init", "cond", "stmts")
    init: Optional["Expr"]
    cond: "Expr"
    stmts: Stmts


@dataclass
class While(Loop):
    """While represents a pre-condition Loop, executed only if the cond
    evaluates to True.
    """
    init: Optional["Expr"]
    cond: "Expr"
    stmts: Stmts


@dataclass
class Repeat(Loop):
    """Repeat represents a post-condition Loop, executed at least once,
    and then again only if the cond evaluates to True.
    """
    init: None
    cond: "Expr"
    stmts: Stmts


@dataclass
class ProcFunc(Stmt):
    """ProcFunc encapsulates a declared Procedure or Function."""
    __slots__ = ("name", "passby", "params", "stmts", "returnType")
    name: Name
    passby: Passby
    params: Declares
    stmts: Stmts
    returnType: t.Type


class ProcedureStmt(ProcFunc):
    ...


class FunctionStmt(ProcFunc):
    ...


@dataclass
class TypeStmt(Stmt):
    """TypeStmt encapsulates a declared custom Type."""
    __slots__ = ("name", "exprs")
    name: Name
    exprs: Declares


class FileStmt(Stmt):
    """Base class for Stmts involving Files."""
    filename: "Expr"


@dataclass
class OpenFile(FileStmt):
    __slots__ = ("filename", "mode")
    filename: "Expr"
    mode: FileMode


@dataclass
class ReadFile(FileStmt):
    __slots__ = ("filename", "target")
    filename: "Expr"
    target: "SetExpr"


@dataclass
class WriteFile(FileStmt):
    __slots__ = ("filename", "data")
    filename: "Expr"
    data: "Expr"


@dataclass
class CloseFile(FileStmt):
    __slots__ = ("filename", )
    filename: "Expr"
