from .builtin import RuntimeError
from .lang import Frame, File
from .lang import Literal, Unary, Binary, Get, Call, Assign



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
    return expr.frame.getValue(expr.name)

def evalCall(frame, expr):
    callable = expr.callable.accept(frame, evalGet)
    # Assign args to param slots
    for arg, slot in zip(expr.args, callable.params):
        argval = arg.accept(frame, evaluate)
        slot.value = argval
    for stmt in callable.stmts:
        returnval = stmt.accept(callable.frame, execute)
        if returnval is not None:
            return returnval

def evalAssign(frame, expr):
    value = expr.expr.accept(frame, evaluate)
    frame.setValue(expr.name, value)

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

def executeStmts(frame, stmts):
    for stmt in stmts:
        returnval = stmt.accept(frame, execute)
        if returnval is not None:
            return returnval

def execOutput(frame, stmt):
    for expr in stmt.exprs:
        value = expr.accept(frame, evaluate)
        if type(value) is bool:
            value = str(value).upper()
        print(str(value), end='')
    print('')  # Add \n

def execInput(frame, stmt):
    name = stmt.name
    frame.setValue(name, input())

def execCase(frame, stmt):
    cond = stmt.cond.accept(frame, evaluate)
    if cond in stmt.stmtMap:
        execute(frame, stmt.stmtMap[cond])
    elif stmt.fallback:
        execute(frame, stmt.fallback)

def execIf(frame, stmt):
    if stmt.cond.accept(frame, evaluate):
        executeStmts(frame, stmt.stmtMap[True])
    elif stmt.fallback:
        executeStmts(frame, stmt.fallback)

def execWhile(frame, stmt):
    if stmt.init:
        execute(frame, stmt.init)
    while stmt.cond.accept(frame, evaluate) is True:
        executeStmts(frame, stmt.stmts)

def execRepeat(frame, stmt):
    executeStmts(frame, stmt.stmts)
    while stmt.cond.accept(frame, evaluate) is False:
        executeStmts(frame, stmt.stmts)

def execFile(frame, stmt):
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

def execute(frame, stmt):
    if stmt.rule == 'output':
        stmt.accept(frame, execOutput)
    if stmt.rule == 'input':
        stmt.accept(frame, execInput)
    if stmt.rule == 'assign':
        stmt.expr.accept(frame, evaluate)
    if stmt.rule == 'case':
        stmt.accept(frame, execCase)
    if stmt.rule == 'if':
        stmt.accept(frame, execIf)
    if stmt.rule == 'while':
        stmt.accept(frame, execWhile)
    if stmt.rule == 'repeat':
        stmt.accept(frame, execRepeat)
    if stmt.rule == 'call':
        stmt.expr.accept(frame, evalCall)
    if stmt.rule == 'return':
        return stmt.expr.accept(frame, evaluate)
    if stmt.rule == 'file':
        stmt.accept(frame, execFile)
    if stmt.rule in ('declare', 'procedure', 'function'):
        pass

def interpret(statements, frame=None):
    if frame is None:
        frame = Frame()
    executeStmts(frame, statements)
    return frame
