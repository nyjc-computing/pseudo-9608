from builtin import lt, lte, gt, gte, ne, eq
from builtin import add, sub, mul, div
from builtin import NULL
from interpreter import execute



class Expr:
    def resolve(self, frame=None):
        raise NotImplementedError

    def evaluate(self, frame=None):
        raise NotImplementedError

    def __repr__(self):
        attrstr = ", ".join([
            repr(getattr(self, attr)) for attr in self.__slots__
        ])
        return f'{type(self).__name__}({attrstr})'



class Literal(Expr):
    __slots__ = ('type', 'value')
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def resolve(self, frame=None):
        return self.type

    def evaluate(self, frame=None):
        return self.value



class Name(Expr):
    __slots__ = ('name',)
    def __init__(self, name):
        self.name = name

    def resolve(self, frame=None):
        return self.name

    def evaluate(self, frame=None):
        return self.name



class Unary(Expr):
    __slots__ = ('oper', 'right')
    def __init__(self, oper, right):
        self.oper = oper
        self.right = right

    def resolve(self, frame):
        return self.right.resolve(frame)

    def evaluate(self, frame):
        right = self.right.evaluate(frame)
        return self.oper(right)



class Binary(Expr):
    __slots__ = ('left', 'oper', 'right')
    def __init__(self, left, oper, right):
        self.left = left
        self.oper = oper
        self.right = right

    def resolve(self, frame):
        self.left.resolve(frame)
        self.right.resolve(frame)
        if self.oper in (lt, lte, gt, gte, ne, eq):
            return 'BOOLEAN'
        elif self.oper in (add, sub, mul, div):
            return 'INTEGER'

    def evaluate(self, frame):
        left = self.left.evaluate(frame)
        right = self.right.evaluate(frame)
        return self.oper(left, right)



class Get(Expr):
    __slots__ = ('frame', 'name')
    def __init__(self, frame, name):
        self.frame = frame
        self.name = name

    def resolve(self, frame=None):
        if frame and self.frame is NULL:
            self.frame = frame
        name = self.name.evaluate()
        slot = self.frame[name]
        return slot['type']

    def evaluate(self, frame):
        name = self.name.evaluate(frame)
        slot = self.frame[name]
        return slot['value']



class Call(Expr):
    __slots__ = ('callable', 'args')
    def __init__(self, callable, args):
        self.callable = callable
        self.args = args

    def resolve(self, frame=None):
        self.callable.resolve(frame)
        return self.callable.resolve()

    def evaluate(self, frame):
        callable = self.callable.evaluate(frame)
        proc = callable['name'].evaluate(frame)
        for arg, param in zip(callable['args'], proc['params']):
            name = param['name'].evaluate(proc['frame'])
            proc['frame'][name]['value'] = arg.evaluate(frame)
        for stmt in proc['stmts']:
            returnval = execute(frame, stmt)
            if returnval:
                    return returnval



class Stmt:
    def accept(self, frame, visitor):
        # visitor must be a function that takes
        # a frame and a Stmt
        return visitor(frame, self)

    def verify(self, frame=None):
        raise NotImplementedError

    def execute(self, frame=None):
        raise NotImplementedError

    def __repr__(self):
        attrstr = ", ".join([
            repr(getattr(self, attr)) for attr in self.__slots__
        ])
        return f'{type(self).__name__}({attrstr})'



class Output(Stmt):
    __slots__ = ('rule', 'exprs')
    def __init__(self, rule, exprs):
        self.rule = rule
        self.exprs = exprs

    def verify(self, frame):
        pass

    def execute(self, frame):
        pass



class Input(Stmt):
    __slots__ = ('rule', 'name')
    def __init__(self, rule, name):
        self.rule = rule
        self.name = name

    def verify(self, frame):
        pass

    def execute(self, frame):
        pass



class Declare(Stmt):
    __slots__ = ('rule', 'name', 'type')
    def __init__(self, rule, name, type):
        self.rule = rule
        self.name = name
        self.type = type

    def verify(self, frame):
        pass

    def execute(self, frame):
        pass



class Assign(Stmt):
    __slots__ = ('rule', 'name', 'expr')
    def __init__(self, rule, name, expr):
        self.rule = rule
        self.name = name
        self.expr = expr

    def verify(self, frame):
        pass

    def execute(self, frame):
        pass



class Conditional(Stmt):
    __slots__ = ('rule', 'cond', 'stmtMap', 'fallback')
    def __init__(self, rule, cond, stmtMap, fallback):
        self.rule = rule
        self.cond = cond
        self.stmtMap = stmtMap
        self.fallback = fallback

    def verify(self, frame):
        pass

    def execute(self, frame):
        pass



class Loop(Stmt):
    __slots__ = ('rule', 'init', 'cond', 'stmts')
    def __init__(self, rule, init, cond, stmts):
        self.rule = rule
        self.init = init
        self.cond = cond
        self.stmts = stmts

    def verify(self, frame):
        pass

    def execute(self, frame):
        pass



class Callable(Stmt):
    __slots__ = ('rule', 'name', 'passby', 'params', 'stmts', 'returnType')
    def __init__(self, rule, name, passby, params, stmts, returnType):
        self.rule = rule
        self.name = name
        self.passby = passby
        self.params = params
        self.stmts = stmts
        self.returnType = returnType

    def verify(self, frame):
        pass

    def execute(self, frame):
        pass



class Calling(Stmt):
    # HACK: Temporary replacement for a lack of an ExprStmt
    # Should attempt to use Call Expr
    __slots__ = ('rule', 'callable', 'args')
    def __init__(self, rule, callable, args):
        self.rule = rule
        self.callable = callable
        self.args = args

    def verify(self, frame):
        pass

    def execute(self, frame):
        pass



class Return(Stmt):
    __slots__ = ('rule', 'expr')
    def __init__(self, rule, expr):
        self.rule = rule
        self.expr = expr

    def verify(self, frame):
        pass

    def execute(self, frame):
        pass



class File(Stmt):
    __slots__ = ('rule', 'action', 'name', 'mode', 'data')
    def __init__(self, rule, action, name, mode, data):
        self.rule = rule
        self.action = action
        self.name = name
        self.mode = mode
        self.data = data

    def verify(self, frame):
        pass

    def execute(self, frame):
        pass
