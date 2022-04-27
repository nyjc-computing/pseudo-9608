class Expr:
    def resolve(self):
        raise NotImplementedError

    def evaluate(self):
        raise NotImplementedError



class Unary(Expr):
    def __init__(self, oper, right):
        self.oper = oper
        self.right = right

    def __repr__(self):
        return f'{type(self).__class__}(oper={self.oper}, right={self.right})'



class Binary(Expr):
    def __init__(self, left, oper, right):
        self.left = left
        self.oper = oper
        self.right = right

    def __repr__(self):
        return f'{type(self).__class__}(left={self.left}, oper={self.oper}, right={self.right})'



class Get(Expr):
    def __init__(self, frame, name):
        self.frame = frame
        self.name = name

    def __repr__(self):
        return f'{type(self).__class__}(name={self.name})'



class Call(Expr):
    def __init__(self, callable, args):
        self.callable = callable
        self.args = args

    def __repr__(self):
        return f'{type(self).__class__}(callable={self.callable}, args={self.args})'
