from builtin import lt, lte, gt, gte, ne, eq
from builtin import add, sub, mul, div
from builtin import NULL



class Expr:
    def resolve(self, frame=None):
        raise NotImplementedError

    def evaluate(self):
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

    def evaluate(self):
        return self.value



class Name(Expr):
    __slots__ = ('name',)
    def __init__(self, name):
        self.name = name

    def resolve(self, frame=None):
        return self.name

    def evaluate(self):
        return self.name



class Unary(Expr):
    __slots__ = ('oper', 'right')
    def __init__(self, oper, right):
        self.oper = oper
        self.right = right

    def resolve(self, frame):
        return self.right.resolve(frame)

    def evaluate(self):
        return self.oper(self.right.value)



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

    def evaluate(self):
        return self.oper(self.left.value, self.right.value)



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

    def evaluate(self):
        name = self.name.evaluate()
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

    def evaluate(self):
        callable = self.callable.evaluate()
        # execute call and return