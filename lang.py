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
    def __init__(self, frame, params, stmts):
        self.frame = frame
        self.params = params
        self.stmts = stmts



class Function(Callable):
    """Functions are evaluated to return a value."""



class Procedure(Callable):
    """Procedures are called to execute its statements."""



class TypedValue:
    """
    Represents a value in 9608 pseudocode.
    Each TypedValue has a type and a value.
    """
    __slots__ = ('type', 'value')
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def __repr__(self):
        return f"<{self.type}: {repr(self.value)}>"



class Expr:
    """
    Represents an expression in 9608 pseudocode.
    An expression resolves to a type, and evaluates
    to a value.
    An Expr object has an accept() method which implements
    the Visitor pattern.

    Methods
    -------
    - accept(frame, visitor) -> Any
        Enables a visitor to carry out operations on the
        Expr (with a provided frame).
        The visitor should take in two arguments: a frame,
        and an Expr.
    """
    def accept(self, frame, visitor):
        # visitor must be a function that takes
        # a frame and an Expr
        return visitor(frame, self)

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
    def __init__(self, name):
        self.name = name



class Declare(Expr):
    __slots__ = ('name', 'type')
    def __init__(self, name, type):
        self.name = name
        self.type = type



class Unary(Expr):
    __slots__ = ('oper', 'right')
    def __init__(self, oper, right):
        self.oper = oper
        self.right = right



class Binary(Expr):
    __slots__ = ('left', 'oper', 'right')
    def __init__(self, left, oper, right):
        self.left = left
        self.oper = oper
        self.right = right



class Get(Expr):
    __slots__ = ('frame', 'name')
    def __init__(self, frame, name):
        self.frame = frame
        self.name = name



class Call(Expr):
    __slots__ = ('callable', 'args')
    def __init__(self, callable, args):
        self.callable = callable
        self.args = args



class Stmt:
    def accept(self, frame, visitor):
        # visitor must be a function that takes
        # a frame and a Stmt
        return visitor(frame, self)

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



class Assign(Stmt):
    __slots__ = ('rule', 'name', 'expr')
    def __init__(self, rule, name, expr):
        self.rule = rule
        self.name = name
        self.expr = expr



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



class Return(Stmt):
    __slots__ = ('rule', 'expr')
    def __init__(self, rule, expr):
        self.rule = rule
        self.expr = expr



class File(Stmt):
    __slots__ = ('rule', 'action', 'name', 'mode', 'data')
    def __init__(self, rule, action, name, mode, data):
        self.rule = rule
        self.action = action
        self.name = name
        self.mode = mode
        self.data = data
