class Expr:
    def resolve(self):
        raise NotImplementedError

    def evaluate(self):
        raise NotImplementedError

    def __repr__(self):
        return (
            f'{type(self).__class__}('
            f'{", ".join((
                getattr(self, attr) for attr in self.__slots__
            ))}'
            ')'
        )



class Literal(Expr):
    __slots__ = ('type', 'value')
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def resolve(self):
        return self.type

    def evaluate(self):
        return self.value



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
        return self.oper(self.left.value, self.right.)



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
