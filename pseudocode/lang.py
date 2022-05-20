class Token:
    """
    Encapsulates data for a token.
    """
    def __init__(self, line, column, type, word, value):
        self.line = line
        self.col = column
        self.type = type
        self.word = word
        self.value = value

    def __repr__(self):
        lineinfo = f"[Line {self.line} column {self.col}]"
        return f"{lineinfo} <{self.value}> {repr(self.word)}"



class Value:
    """
    Base class for pseudo values.
    Represents a value stored in the frame.
    """



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
    def __init__(self, frame, params, stmts):
        self.frame = frame
        self.params = params
        self.stmts = stmts

    def __repr__(self):
        attrstr = ", ".join([
            repr(getattr(self, attr)) for attr in self.__slots__
        ])
        return f'{type(self).__name__}({attrstr})'



class Function(Callable):
    """Functions are evaluated to return a value."""



class Procedure(Callable):
    """Procedures are called to execute its statements."""



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
    def __init__(self, params, func):
        self.params = params
        self.func = func

    def __repr__(self):
        attrstr = ", ".join([
            repr(getattr(self, attr)) for attr in self.__slots__
        ])
        return f'{type(self).__name__}({attrstr})'



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
    def __init__(self, name, mode, iohandler):
        self.name = name
        self.mode = mode
        self.iohandler = iohandler

    def __repr__(self):
        return f"<{self.mode}: {self.name}>"



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
    def __init__(self, *types):
        self.data = {}
        for typeName in types:
            self.declare(typeName)
            self.setTemplate(typeName, None)

    def __repr__(self):
        nameTypePairs = [
            f"{name}: {self.getTemplate(name)}"
            for name in self.data
        ]
        return f"{{{', '.join(nameTypePairs)}}}"

    def has(self, name):
        return name in self.data

    def declare(self, name):
        self.data[name] = None

    def setTemplate(self, name, template):
        self.data[name] = TypedValue(name, template)

    def getTemplate(self, name):
        return self.data[name]



class TypedValue:
    """
    Represents a value in 9608 pseudocode.
    Each TypedValue has a type and a value.
    """
    __slots__ = ('type', 'value')
    def __init__(self, type, value, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = type
        self.value = value

    def __repr__(self):
        return f"<{self.type}: {repr(self.value)}>"

    def copy(self):
        """This returns an empty copy of the typedvalue"""
        Class = type(self)
        if isinstance(self.value, Object):
            return Class(self.type, self.value.copy())
        return Class(self.type, self.value)



class Object:
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
    def __init__(self, typesys):
        self.data = {}
        self.types = typesys

    def __repr__(self):
        nameTypePairs = [
            f"{name}: {self.getType(name)}"
            for name in self.data
        ]
        return f"{{{', '.join(nameTypePairs)}}}"

    def has(self, name):
        return name in self.data

    def declare(self, name, type):
        template = self.types.getTemplate(type)
        self.data[name] = template.copy()

    def getType(self, name):
        return self.data[name].type

    def getValue(self, name):
        return self.data[name].value

    def get(self, name):
        return self.data[name]

    def setValue(self, name, value):
        self.data[name].value = value

    def copy(self):
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
    def __init__(self, typesys, outer=None):
        super().__init__(typesys=typesys)
        self.outer = outer

    def set(self, name, typedValue):
        self.data[name] = typedValue

    def delete(self, name):
        del self.data[name]

    def lookup(self, name):
        if self.has(name):
            return self
        if self.outer:
            return self.outer.lookup(name)



class Expr:
    """
    Represents an expression in 9608 pseudocode.
    An expression resolves to a type, and evaluates
    to a value.
    An Expr object has an accept() method which implements
    the Visitor pattern.

    Methods
    -------
    - token() -> dict
        Returns the token asociated with the expr, for error
        reporting purposes.
    - accept(frame, visitor) -> Any
        Enables a visitor to carry out operations on the
        Expr (with a provided frame).
        The visitor should take in two arguments: a frame,
        and an Expr.
    """
    def __init__(self, token=None):
        self._token = token

    def token(self):
        return self._token

    def accept(self, frame, visitor, *args, **kwargs):
        # visitor must be a function that takes
        # a frame and an Expr
        return visitor(frame, self, *args, **kwargs)

    def __repr__(self):
        attrstr = ", ".join([
            repr(getattr(self, attr)) for attr in self.__slots__
        ])
        return f'{type(self).__name__}({attrstr})'



class Literal(TypedValue, Expr):
    """
    A Literal represents any value coming directly from
    the source code.
    """



class Name(Expr):
    __slots__ = ('name',)
    def __init__(self, name, token=None):
        super().__init__(token=token)
        self.name = name



class Declare(Expr):
    __slots__ = ('name', 'type')
    def __init__(self, name, type, token=None):
        super().__init__(token=token)
        self.name = name
        self.type = type



class Assign(Expr):
    __slots__ = ('name', 'assignee', 'expr')
    def __init__(self, name, assignee, expr, token=None):
        super().__init__(token=token)
        self.name = name
        self.assignee = assignee
        self.expr = expr



class Unary(Expr):
    __slots__ = ('oper', 'right')
    def __init__(self, oper, right, token=None):
        super().__init__(token=token)
        self.oper = oper
        self.right = right



class Binary(Expr):
    __slots__ = ('left', 'oper', 'right')
    def __init__(self, left, oper, right, token=None):
        super().__init__(token=token)
        self.left = left
        self.oper = oper
        self.right = right



class Get(Expr):
    __slots__ = ('frame', 'name')
    def __init__(self, frame, name, token=None):
        super().__init__(token=token)
        self.frame = frame
        self.name = name



class Call(Expr):
    __slots__ = ('callable', 'args')
    def __init__(self, callable, args, token=None):
        super().__init__(token=token)
        self.callable = callable
        self.args = args



class Stmt:
    def accept(self, frame, visitor, *args, **kwargs):
        # visitor must be a function that takes
        # a frame and a Stmt
        return visitor(frame, self, *args, **kwargs)

    def __repr__(self):
        attrstr = ", ".join([
            repr(getattr(self, attr)) for attr in self.__slots__
        ])
        return f'{type(self).__name__}({attrstr})'



class ExprStmt(Stmt):
    __slots__ = ('rule', 'expr')
    def __init__(self, rule, expr):
        self.rule = rule
        self.expr = expr



class Output(Stmt):
    __slots__ = ('rule', 'exprs')
    def __init__(self, rule, exprs):
        self.rule = rule
        self.exprs = exprs



class Input(Stmt):
    __slots__ = ('rule', 'name')
    def __init__(self, rule, name):
        self.rule = rule
        self.name = name



class Conditional(Stmt):
    __slots__ = ('rule', 'cond', 'stmtMap', 'fallback')
    def __init__(self, rule, cond, stmtMap, fallback):
        self.rule = rule
        self.cond = cond
        self.stmtMap = stmtMap
        self.fallback = fallback



class Loop(Stmt):
    __slots__ = ('rule', 'init', 'cond', 'stmts')
    def __init__(self, rule, init, cond, stmts):
        self.rule = rule
        self.init = init
        self.cond = cond
        self.stmts = stmts



class ProcFunc(Stmt):
    __slots__ = ('rule', 'name', 'passby', 'params', 'stmts', 'returnType')
    def __init__(self, rule, name, passby, params, stmts, returnType):
        self.rule = rule
        self.name = name
        self.passby = passby
        self.params = params
        self.stmts = stmts
        self.returnType = returnType



class TypeStmt(Stmt):
    __slots__ = ('rule', 'name', 'exprs')
    def __init__(self, rule, name, exprs):
        self.rule = rule
        self.name = name
        self.exprs = exprs



class FileAction(Stmt):
    __slots__ = ('rule', 'action', 'name', 'mode', 'data')
    def __init__(self, rule, action, name, mode, data):
        self.rule = rule
        self.action = action
        self.name = name
        self.mode = mode
        self.data = data
