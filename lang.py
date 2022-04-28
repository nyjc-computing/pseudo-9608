from builtin import lt, lte, gt, gte, ne, eq
from builtin import add, sub, mul, div



class Expr:
    def resolve(self):
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

    def resolve(self):
        return self.type

    def evaluate(self):
        return self.value



class Name(Expr):
    __slots__ = ('name',)
    def __init__(self, name):
        self.name = name

    def resolve(self):
        return 'NAME'

    def evaluate(self):
        return self.name['word']



class Unary(Expr):
    __slots__ = ('oper', 'right')
    def __init__(self, oper, right):
        self.oper = oper
        self.right = right

    def resolve(self):
        return self.right.resolve()

    def evaluate(self):
        return self.oper(self.right.value)



class Binary(Expr):
    __slots__ = ('left', 'oper', 'right')
    def __init__(self, left, oper, right):
        self.left = left
        self.oper = oper
        self.right = right

    def resolve(self):
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

    def resolve(self):
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

    def resolve(self):
        slot = self.callable.evaluate()
        return slot['type']

    def evaluate(self):
        slot = self.callable.evaluate()
        callable = slot['value']
        # execute call and return