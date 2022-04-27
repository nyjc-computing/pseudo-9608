class Expr:
    def resolve(self):
        raise NotImplementedError

    def evaluate(self):
        raise NotImplementedError



class Unary(Expr):
    def __init__(self, oper, right):
        self.oper = oper
        self.right = right



class Binary(Expr):
    def __init__(self, left, oper, right):
        self.left = left
        self.oper = oper
        self.right = right



class Get(Expr):
    def __init__(self, frame, name):
        self.frame = frame
        self.name = name



class Call(Expr):
    def __init__(self, callable, args):
        self.callable = callable
        self.args = args
