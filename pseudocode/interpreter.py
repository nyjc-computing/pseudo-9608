from .builtin import RuntimeError
from .lang import Object, Array, File, Callable, Builtin
from .lang import Expr, Literal, Unary, Binary, Get, Call, Assign
from .system import EOF



# Helper functions

def expectTypeElseError(
    exprmode,
    expected,
    errmsg="Expected",
    token=None,
):
    if type(expected) is str:
        expected = (expected,)
    if not exprmode in expected:
        if not token: token = exprmode
        raise RuntimeError(f"{errmsg} {expected}", token)

def declaredElseError(frame, name, errmsg="Undeclared", token=None):
    if not frame.has(name):
        raise RuntimeError(errmsg, token)

def undeclaredElseError(
    frame,
    name,
    errmsg="Already declared",
    token=None,
):
    if frame.has(name):
        raise RuntimeError(errmsg, token)



class Interpreter:
    """
    Interprets a list of statements with a given frame.
    """
    outputHandler = print
    def __init__(self, frame, statements):
        self.frame = frame
        self.statements = statements

    def registerOutputHandler(self, handler):
        """
        Register handler as the function to use to handle
        any output from the executed statements.
        The default handler is Python's print().
        """
        self.outputHandler = handler

    def interpret(self):
        executeStmts(
            self.frame,
            self.statements,
            output=self.outputHandler,
        )



# Evaluators

def evalIndex(frame, indexes):
    return tuple((
        evaluate(frame, expr) for expr in indexes
    ))

def evalLiteral(frame, literal):
    return literal.value

def evalUnary(frame, expr):
    rightval = evaluate(frame, expr.right)
    return expr.oper(rightval)

def evalBinary(frame, expr):
    leftval = evaluate(frame, expr.left)
    rightval = evaluate(frame, expr.right)
    return expr.oper(leftval, rightval)

def evalGet(frame, expr):
    # Frame should have been inserted in resolver
    # So ignore the frame that is passed here
    obj = expr.frame
    # evaluate obj until object is retrieved
    if isinstance(obj, Expr):
        obj = evaluate(frame, obj)
    if not isinstance(obj, Object):
        raise RuntimeError("Invalid object", expr.frame.token())
    name = expr.name
    if type(obj) in (Array,):
        name = evalIndex(frame, expr.name)
    return obj.getValue(name)

def evalCall(frame, expr, **kwargs):
    callable = evalGet(frame, expr.callable)
    if isinstance(callable, Builtin):
        if callable.func is EOF:
            name = evaluate(frame, expr.args[0])
            file = frame.getValue(name)
            return callable.func(file.iohandler)
        argvals = [evaluate(frame, arg) for arg in expr.args]
        return callable.func(*argvals)
    elif isinstance(callable, Callable):
        # Assign args to param slots
        for arg, slot in zip(expr.args, callable.params):
            argval = evaluate(frame, arg)
            slot.value = argval
        for stmt in callable.stmts:
            returnval = execute(callable.frame, stmt, **kwargs)
            if returnval is not None:
                return returnval

def evalAssign(frame, expr):
    value = evaluate(frame, expr.expr)
    obj = expr.assignee.frame
    if type(obj) in (Get, Call):
        obj = evaluate(frame, obj)
    name = expr.name
    if type(obj) in (Array,):
        name = evalIndex(frame, expr.name)
    obj.setValue(name, value)

def evaluate(frame, expr, **kwargs):
    if isinstance(expr, Literal):
        return evalLiteral(frame, expr)
    if isinstance(expr, Unary):
        return evalUnary(frame, expr)
    if isinstance(expr, Binary):
        return evalBinary(frame, expr)
    if isinstance(expr, Assign):
        return evalAssign(frame, expr)
    if isinstance(expr, Get):
        return evalGet(frame, expr)
    if isinstance(expr, Call):
        return evalCall(frame, expr)
    else:
        raise TypeError(f"Unexpected expr {expr}")

# Executors

def executeStmts(frame, stmts, *args, **kwargs):
    for stmt in stmts:
        returnval = execute(frame, stmt, *args, **kwargs)
        if returnval is not None:
            return returnval

def execOutput(frame, stmt, *, output=None, **kwargs):
    for expr in stmt.exprs:
        value = evaluate(frame, expr)
        if type(value) is bool:
            value = str(value).upper()
        output(str(value), end='')
    output('')  # Add \n

def execInput(frame, stmt, **kwargs):
    name = stmt.name
    frame.setValue(name, input())

def execCase(frame, stmt, **kwargs):
    cond = evaluate(frame, stmt.cond)
    if cond in stmt.stmtMap:
        execute(frame, stmt.stmtMap[cond], **kwargs)
    elif stmt.fallback:
        execute(frame, stmt.fallback, **kwargs)

def execIf(frame, stmt, **kwargs):
    if evaluate(frame, stmt.cond):
        executeStmts(frame, stmt.stmtMap[True], **kwargs)
    elif stmt.fallback:
        executeStmts(frame, stmt.fallback, **kwargs)

def execWhile(frame, stmt, **kwargs):
    if stmt.init:
        execute(frame, stmt.init, **kwargs)
    while evaluate(frame, stmt.cond) is True:
        executeStmts(frame, stmt.stmts, **kwargs)

def execRepeat(frame, stmt, **kwargs):
    executeStmts(frame, stmt.stmts)
    while evaluate(frame, stmt) is False:
        executeStmts(frame, stmt.stmts)

def execFile(frame, stmt, **kwargs):
    name = evalLiteral(frame, stmt.name)
    if stmt.action == 'open':
        undeclaredElseError(
            frame, name, "File already opened", stmt.name.token()
        )
        frame.declare(name, 'FILE')
        file = File(name, stmt.mode, open(name, stmt.mode[0].lower()))
        frame.setValue(name, file)
    elif stmt.action == 'read':
        declaredElseError(
            frame, name, "File not open", stmt.name.token()
        )
        file = frame.getValue(name)
        expectTypeElseError(
            frame.getType(name), 'FILE', stmt.name.token()
        )
        expectTypeElseError(file.mode, 'READ', stmt.name.token())
        varname = evaluate(frame, stmt.data)
        declaredElseError(frame, varname, stmt.data.token())
        # TODO: Catch and handle Python file io errors
        line = file.iohandler.readline().rstrip()
        # TODO: Type conversion
        frame.setValue(varname, line)
    elif stmt.action == 'write':
        declaredElseError(
            frame, name, "File not open", stmt.name.token()
        )
        file = frame.getValue(name)
        expectTypeElseError(
            frame.getType(name), 'FILE', stmt.name.token()
        )
        expectTypeElseError(
            file.mode, ('WRITE', 'APPEND'), stmt.name.token()
        )
        writedata = evaluate(frame, stmt.data)
        if type(writedata) is bool:
            writedata = str(writedata).upper()
        else:
            writedata = str(writedata)
        # Move pointer to next line after writing
        if not writedata.endswith('\n'):
            writedata += '\n'
        # TODO: Catch and handle Python file io errors
        file.iohandler.write(writedata)
    elif stmt.action == 'close':
        declaredElseError(
            frame, name, "File not open", stmt.name.token()
        )
        file = frame.getValue(name)
        expectTypeElseError(
            frame.getType(name), 'FILE', stmt.name.token()
        )
        file.iohandler.close()
        frame.delete(name)

def execute(frame, stmt, *args, **kwargs):
    if stmt.rule == 'output':
        execOutput(frame, stmt, **kwargs)
    if stmt.rule == 'input':
        stmt.accept(frame, execInput(frame, stmt, **kwargs)
    if stmt.rule == 'assign':
        evaluate(frame, stmt.expr, **kwargs)
    if stmt.rule == 'case':
        execCase(frame, stmt, **kwargs)
    if stmt.rule == 'if':
        execIf(frame, stmt, **kwargs)
    if stmt.rule == 'while':
        execWhile(frame, stmt, **kwargs)
    if stmt.rule == 'repeat':
        execRepeat(frame, stmt, **kwargs)
    if stmt.rule == 'call':
        evalCall(frame, stmt.expr, **kwargs)
    if stmt.rule == 'return':
        return evaluate(frame, stmt.expr, **kwargs)
    if stmt.rule == 'file':
        execFile(frame, stmt, **kwargs)
    if stmt.rule in ('declare', 'procedure', 'function'):
        pass
