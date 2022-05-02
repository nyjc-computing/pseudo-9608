from builtin import RuntimeError
from lang import TypedValue
from lang import Literal, Unary, Binary, Get, Call



# Helper functions

def executeStmts(frame, stmts):
    for stmt in stmts:
        returnval = stmt.accept(frame, execute)
        if returnval:
            return returnval

def getValue(frame, expr):
    """Evaluate a Get expr to retrieve value from frame"""
    if expr.name not in frame:
        raise RuntimeError("Undeclared", expr.name)
    if frame[expr.name].value is None:
        raise RuntimeError("No value assigned", expr.name)
    return frame[expr.name].value

def setValue(frame, name, value):
    """Set a new value in the frame slot"""
    if name not in frame:
        raise RuntimeError("Undeclared", name)
    frame[name].value = value

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
    return expr.accept(frame, getValue)

def evalCall(frame, expr):
    callable = expr.callable.accept(frame, evalGet)
    # Assign args to param slots
    for arg, slot in zip(expr.args, callable['params']):
        argval = arg.accept(frame, evaluate)
        slot.value = argval
    local = callable['frame']
    for stmt in callable['stmts']:
        returnval = stmt.accept(local, execute)
        if returnval:
            return returnval

def evaluate(frame, expr):
    if isinstance(expr, Literal):
        return expr.accept(frame, evalLiteral)
    if isinstance(expr, Unary):
        return expr.accept(frame, evalUnary)
    if isinstance(expr, Binary):
        return expr.accept(frame, evalBinary)
    if isinstance(expr, Get):
        return expr.accept(frame, evalGet)
    if isinstance(expr, Call):
        return expr.accept(frame, evalCall)
    else:
        raise TypeError(f"Unexpected expr {expr}")

# Executors

def execOutput(frame, stmt):
    for expr in stmt.exprs:
        print(str(expr.accept(frame, evaluate)), end='')
    print('')  # Add \n

def execInput(frame, stmt):
    name = stmt.name
    setValue(frame, name, input())

def execAssign(frame, stmt):
    value = stmt.expr.accept(frame, evaluate)
    setValue(frame, stmt.name, value)

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
    name = stmt.name.accept(frame, evaluate)
    if stmt.action == 'open':
        assert stmt.mode  # Internal check
        if name in frame:
            raise RuntimeError("File already opened", name)
        frame[name] = TypedValue(
            type=stmt.mode,
            value=open(name, stmt.mode[0].lower()),
        )
    elif stmt.action == 'read':
        if name not in frame:
            raise RuntimeError("File not open", name)
        file = getValue(frame, name)
        if file.type != 'READ':
            raise RuntimeError("File opened for {file.type}", name)
        varname = stmt.data.accept(frame, evaluate)
        line = file.readline().rstrip()
        # TODO: Type conversion
        setValue(frame, varname, line)
    elif stmt.action == 'write':
        if name not in frame:
            raise RuntimeError("File not open", name)
        file = getValue(frame, name)
        if file.type != 'WRITE':
            raise RuntimeError("File opened for {file.type}", name)
        writedata = str(stmt.data.accept(frame, evaluate))
        # Move pointer to next line after writing
        if not writedata.endswith('\n'):
            writedata += '\n'
        file.write(writedata)
    elif stmt.action == 'close':
        if name not in frame:
            raise RuntimeError("File not open", name)
        file = getValue(frame, name)
        file.close()
        del frame[name]

def execute(frame, stmt):
    if stmt.rule == 'output':
        stmt.accept(frame, execOutput)
    if stmt.rule == 'input':
        stmt.accept(frame, execInput)
    if stmt.rule == 'declare':
        pass
    if stmt.rule == 'assign':
        stmt.accept(frame, execAssign)
    if stmt.rule == 'case':
        stmt.accept(frame, execCase)
    if stmt.rule == 'if':
        stmt.accept(frame, execIf)
    if stmt.rule == 'while':
        stmt.accept(frame, execWhile)
    if stmt.rule == 'repeat':
        stmt.accept(frame, execRepeat)
    if stmt.rule == 'procedure':
        pass
    if stmt.rule == 'call':
        stmt.expr.accept(frame, evalCall)
    if stmt.rule == 'function':
        pass
    if stmt.rule == 'return':
        return stmt.expr.accept(frame, evaluate)
    if stmt.rule == 'file':
        stmt.accept(frame, execFile)

def interpret(statements, frame=None):
    if frame is None:
        frame = {}
    executeStmts(frame, statements)
    return frame
