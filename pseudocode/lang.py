from typing import Any, Optional, Union, Iterable, Mapping
from typing import Tuple, Dict, NewType
from typing import Callable as function, TextIO

# Pseudocode types
# Type represents a pseudocode type, whether built-in or declared
Type = str
# Varname represents a declared name
Varname = str
# Index represents array indexes used in Array
Index = Tuple[int]
# Key represents names that can be used in an Object
# for storing values
Key = Union[Varname, Index]  # in TypedValue
Lit = Union[bool, int, float, str]  # Simple data types
Val = Union[Lit, "PseudoValue"]  # in TypedValue
Param = Union["Get", "TypedValue"]  # Callable params
Arg = NewType('Arg', "Expr")  # Call args
Rule = str  # Stmt rules

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
        value: Any,
    ) -> None:
        self.line = line
        self.col = column
        self.type = type
        self.word = word
        self.value = value

    def __repr__(self) -> str:
        lineinfo = f"[Line {self.line} column {self.col}]"
        return f"{lineinfo} <{self.value}> {repr(self.word)}"



class TypeSystem:
    """
    Handles registration of types in 9608 pseudocode.
    Each type is registered with a name, and an optional template.
    Existence checks should be carried out (using has()) before using the
    methods here.

    Methods
    -------
    has(name)
        returns True if the type has been declared, otherwise returns False
    declare(name)
        declares the existence of a type
    setTemplate(name, template)
        set the template used to initialise a TypedValue with this type
    getTemplate(name)
        return the template of the type
    """
    def __init__(
        self,
        *types: Type,
    ) -> None:
        self.data: Dict[Type, "TypedValue"] = {}
        for typeName in types:
            self.declare(typeName)
            self.setTemplate(typeName, None)

    def __repr__(self) -> str:
        nameTypePairs = [
            f"{name}: {self.getTemplate(name)}"
            for name in self.data
        ]
        return f"{{{', '.join(nameTypePairs)}}}"

    def has(self, name: str) -> bool:
        return name in self.data

    def declare(self, name: str) -> None:
        self.data[name] = TypedValue(name, None)

    def setTemplate(self, name: str, template: Optional["Object"]) -> None:
        self.data[name].value = template

    def getTemplate(self, name) -> Optional[Val]:
        return self.data[name].value



class TypedValue:
    """
    Represents a value in 9608 pseudocode.
    Each TypedValue has a type and a value.
    """
    __slots__ = ('type', 'value')
    def __init__(
        self,
        type: Type,
        value: Optional[Val],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.type = type
        self.value = value

    def __repr__(self) -> str:
        return f"<{self.type}: {repr(self.value)}>"

    def copy(self) -> "TypedValue":
        """This returns an empty copy of the typedvalue"""
        Class = type(self)
        if isinstance(self.value, Object):
            return Class(self.type, self.value.copy())
        return Class(self.type, self.value)



class Value:
    """
    Base class for pseudo values.
    Represents a value stored in the frame.
    """



class Object(Value):
    """
    Represents a space for storing of TypedValues in 9608 pseudocode.
    Provides methods for managing TypedValues.

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
        self.data: Dict[Key, "TypedValue"] = {}
        self.types = typesys

    def __repr__(self) -> str:
        nameTypePairs = [
            f"{name}: {self.getType(name)}"
            for name in self.data
        ]
        return f"{{{', '.join(nameTypePairs)}}}"

    def has(self, name: Key) -> bool:
        return name in self.data

    def declare(self, name: Key, type: str) -> None:
        template = self.types.getTemplate(type)
        self.data[name] = template.copy()

    def getType(self, name: Key) -> Type:
        return self.data[name].type

    def getValue(self, name: Key) -> Optional[Val]:
        return self.data[name].value

    def get(self, name: Key) -> "TypedValue":
        return self.data[name]

    def setValue(self, name: Key, value: Any) -> None:
        self.data[name].value = value

    def copy(self) -> "Object":
        """This returns an empty copy of the object"""
        Class = type(self)
        newobj = Class(typesys=self.types)
        for name in self.data:
            newobj.declare(name, self.getType(name))
        return newobj



class Frame(Object):
    """
    Represents a space for storing of TypedValues in 9608 pseudocode.
    Frames differ from Objects in that they can be chained, and slots can be
    deleted after declaration.

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

    def set(self, name, typedValue) -> None:
        self.data[name] = typedValue

    def delete(self, name) -> None:
        del self.data[name]

    def lookup(self, name) -> "Frame":
        if self.has(name):
            return self
        if self.outer:
            return self.outer.lookup(name)



class Array(Object):
    """
    Represents a space containing elements of identical type in 9608
    pseudocode.
    Each element is indexed by N integers.

    Attributes
    ----------
    elementType: str
       The common type of each element
    """
    @property
    def elementType(self) -> Type:
        for elem in self.data.values():
            return elem.type



class Builtin(Value):
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



class Callable(Value):
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



class File(Value):
    """
    Represents a file object in a frame.

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
        name: Name,
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
    An expression resolves to a type, and evaluates
    to a value.

    Methods
    -------
    - token() -> dict
        Returns the token asociated with the expr, for error
        reporting purposes.
    """
    __slots__ = NotImplemented
    def __init__(
        self,
        token: "Token",
    ) -> None:
        self._token = token

    def __repr__(self) -> str:
        attrstr = ", ".join([
            repr(getattr(self, attr)) for attr in self.__slots__
        ])
        return f'{type(self).__name__}({attrstr})'

    def token(self) -> "Token":
        return self._token



class Literal(TypedValue, Expr):
    """
    A Literal represents any value coming directly from
    the source code.
    """



class Name(Expr):
    __slots__ = ('name',)
    def __init__(
        self,
        name: Name,
        token: "Token"=None,
    ) -> None:
        super().__init__(token=token)
        self.name = name



class Declare(Expr):
    __slots__ = ('name', 'type', 'metadata')
    def __init__(
        self,
        name: Name,
        type: Type,
        metadata: Mapping=None,
        token: "Token"=None,
    ) -> None:
        super().__init__(token=token)
        self.name = name
        self.type = type
        self.metadata = metadata



class Assign(Expr):
    __slots__ = ('name', 'assignee', 'expr')
    def __init__(
        self,
        name: Name,
        assignee: "Get",
        expr: "Expr",
        token: "Token"=None) -> None:
        super().__init__(token=token)
        self.name = name
        self.assignee = assignee
        self.expr = expr



class Unary(Expr):
    __slots__ = ('oper', 'right')
    def __init__(
        self,
        oper: function,
        right: "Expr",
        token: "Token"=None,
    ) -> None:
        super().__init__(token=token)
        self.oper = oper
        self.right = right



class Binary(Expr):
    __slots__ = ('left', 'oper', 'right')
    def __init__(
        self,
        left: "Expr",
        oper: function,
        right: "Expr",
        token: "Token"=None,
    ) -> None:
        super().__init__(token=token)
        self.left = left
        self.oper = oper
        self.right = right



class Get(Expr):
    __slots__ = ('frame', 'name')
    def __init__(
        self,
        frame: "Frame",
        name: Name,
        token: "Token"=None,
    ) -> None:
        super().__init__(token=token)
        self.frame = frame
        self.name = name



class Call(Expr):
    __slots__ = ('callable', 'args')
    def __init__(
        self,
        callable: "Callable",
        args: Iterable[Arg],
        token: "Token"=None,
    ) -> None:
        super().__init__(token=token)
        self.callable = callable
        self.args = args



class Stmt:
    def __repr__(self) -> str:
        attrstr = ", ".join([
            repr(getattr(self, attr)) for attr in self.__slots__
        ])
        return f'{type(self).__name__}({attrstr})'



class ExprStmt(Stmt):
    __slots__ = ('rule', 'expr')
    def __init__(
        self,
        rule: Rule,
        expr: "Expr",
    ) -> None:
        self.rule = rule
        self.expr = expr



class Output(Stmt):
    __slots__ = ('rule', 'exprs')
    def __init__(
        self,
        rule: Rule,
        exprs: Iterable["Expr"],
    ) -> None:
        self.rule = rule
        self.exprs = exprs



class Input(Stmt):
    __slots__ = ('rule', 'name')
    def __init__(
        self,
        rule: Rule,
        name: Name,
    ) -> None:
        self.rule = rule
        self.name = name



class Conditional(Stmt):
    __slots__ = ('rule', 'cond', 'stmtMap', 'fallback')
    def __init__(
        self,
        rule: Rule,
        cond: "Expr",
        stmtMap: Mapping[Lit, "Stmt"],
        fallback: "Stmt",
    ) -> None:
        self.rule = rule
        self.cond = cond
        self.stmtMap = stmtMap
        self.fallback = fallback



class Loop(Stmt):
    __slots__ = ('rule', 'init', 'cond', 'stmts')
    def __init__(
        self,
        rule: Rule,
        init: "Stmt",
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
        rule: Rule,
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
        rule: Rule,
        name: Name,
        exprs: Iterable["Expr"],
    ) -> None:
        self.rule = rule
        self.name = name
        self.exprs = exprs



class FileAction(Stmt):
    __slots__ = ('rule', 'action', 'name', 'mode', 'data')
    def __init__(
        self,
        rule: Rule,
        action: str,
        name: Name,
        mode: str,
        data: "Expr",
    ) -> None:
        self.rule = rule
        self.action = action
        self.name = name
        self.mode = mode
        self.data = data
