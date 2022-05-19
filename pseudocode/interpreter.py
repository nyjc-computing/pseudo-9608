from .builtin import RuntimeError
from .lang import Frame, File, Callable, Builtin
from .lang import Literal, Unary, Binary, Get, Call, Assign
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

def evalLiteral(frame, literal):
    return literal.value

def evalUnary(frame, expr):
    rightval = expr.right.accept(frame, evaluate)
    return expr.oper(rightval)

def evalBinary(frame, expr):
    leftval = expr.left.accept(frame, evaluate)
    rightval = expr.right.accept(frame, evaluate)
    return expr.oper(leftval, rightval)

def evalGet(frame, expr):
    # Frame should have been inserted in resolver
    # So ignore the frame that is passed here
    obj = expr.frame
    # evaluate obj until object is retrieved
    return obj.getValue(expr.name)

def evalCall(frame, expr, **kwargs):
    callable = expr.callable.accept(frame, evalGet)
    if isinstance(callable, Builtin):
        if callable.func is EOF:
            name = expr.args[0].accept(frame, evaluate)
            file = frame.getValue(name)
            return callable.func(file.iohandler)
        argvals = [arg.accept(frame, evaluate) for arg in expr.args]
        return callable.func(*argvals)
    elif isinstance(callable, Callable):
        # Assign args to param slots
        for arg, slot in zip(expr.args, callable.params):
            argval = arg.accept(frame, evaluate)
            slot.value = argval
        for stmt in callable.stmts:
            returnval = stmt.accept(callable.frame, execute, **kwargs)
            if returnval is not None:
                return returnval

def evalAssign(frame, expr):
    value = expr.expr.accept(frame, evaluate)
    obj = expr.assignee
    # evaluate assignee until object is retrieved
    obj.setValue(expr.name, value)

def evaluate(frame, expr):
    if isinstance(expr, Literal):
        return expr.accept(frame, evalLiteral)
    if isinstance(expr, Unary):
        return expr.accept(frame, evalUnary)
    if isinstance(expr, Binary):
        return expr.accept(frame, evalBinary)
    if isinstance(expr, Assign):
        return expr.accept(frame, evalAssign)
    if isinstance(expr, Get):
        return expr.accept(frame, evalGet)
    if isinstance(expr, Call):
        return expr.accept(frame, evalCall)
    else:
        raise TypeError(f"Unexpected expr {expr}")

# Executors

def executeStmts(frame, stmts, *args, **kwargs):
    for stmt in stmts:
        returnval = stmt.accept(frame, execute, *args, **kwargs)
        if returnval is not None:
            return returnval

def execOutput(frame, stmt, *, output=None, **kwargs):
    for expr in stmt.exprs:
        value = expr.accept(frame, evaluate)
        if type(value) is bool:
            value = str(value).upper()
        output(str(value), end='')
    output('')  # Add \n

def execInput(frame, stmt, **kwargs):
    name = stmt.name
    frame.setValue(name, input())

def execCase(frame, stmt, **kwargs):
    cond = stmt.cond.accept(frame, evaluate)
    if cond in stmt.stmtMap:
        execute(frame, stmt.stmtMap[cond], **kwargs)
    elif stmt.fallback:
        execute(frame, stmt.fallback, **kwargs)

def execIf(frame, stmt, **kwargs):
    if stmt.cond.accept(frame, evaluate):
        executeStmts(frame, stmt.stmtMap[True], **kwargs)
    elif stmt.fallback:
        executeStmts(frame, stmt.fallback, **kwargs)

def execWhile(frame, stmt, **kwargs):
    if stmt.init:
        execute(frame, stmt.init, **kwargs)
    while stmt.cond.accept(frame, evaluate) is True:
        executeStmts(frame, stmt.stmts, **kwargs)

def execRepeat(frame, stmt, **kwargs):
    executeStmts(frame, stmt.stmts)
    while stmt.cond.accept(frame, evaluate) is False:
        executeStmts(frame, stmt.stmts)

def execFile(frame, stmt, **kwargs):
    name = stmt.name.accept(frame, evalLiteral)
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
        varname = stmt.data.accept(frame, evaluate)
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
        writedata = stmt.data.accept(frame, evaluate)
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
        stmt.accept(frame, execOutput, **kwargs)
    if stmt.rule == 'input':
        stmt.accept(frame, execInput, **kwargs)
    if stmt.rule == 'assign':
        stmt.expr.accept(frame, evaluate, **kwargs)
    if stmt.rule == 'case':
        stmt.accept(frame, execCase, **kwargs)
    if stmt.rule == 'if':
        stmt.accept(frame, execIf, **kwargs)
    if stmt.rule == 'while':
        stmt.accept(frame, execWhile, **kwargs)
    if stmt.rule == 'repeat':
        stmt.accept(frame, execRepeat, **kwargs)
    if stmt.rule == 'call':
        stmt.expr.accept(frame, evalCall, **kwargs)
    if stmt.rule == 'return':
        return stmt.expr.accept(frame, evaluate, **kwargs)
    if stmt.rule == 'file':
        stmt.accept(frame, execFile, **kwargs)
    if stmt.rule in ('declare', 'procedure', 'function'):
        pass
