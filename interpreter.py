from builtin import RuntimeError
from lang import Literal, Declare, Unary, Binary, Get, Call



# Helper functions

def executeStmts(frame, stmts):
    for stmt in stmts:
        returnval = stmt.accept(frame, execute)
        if returnval:
            return returnval

def assignArgsParams(frame, args, callable):
    for arg, param in zip(args, callable['params']):
        name = param['name'].evaluate(callable['frame'])
        callable['frame'][name]['value'] = arg.accept(frame, evaluate)

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
    return frame[expr.name]

def evalCall(frame, expr):
    callable = expr.callable.accept(frame, evalGet)['value']
    # Assign args to param slots
    for arg, slot in zip(expr.args, callable['params']):
        argval = arg.accept(frame, evaluate)
        slot['value'] = argval
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

def execOutput(frame, stmt):
    for expr in stmt.exprs:
        print(str(expr.accept(frame, evaluate)), end='')
    print('')  # Add \n

def execInput(frame, stmt):
    name = stmt.name
    frame[name]['value'] = input()

def execAssign(frame, stmt):
    name = stmt.name
    value = stmt.expr.accept(frame, evaluate)
    frame[name]['value'] = value

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
        file = {
            'type': stmt.mode,
            'value': open(name, stmt.mode[0].lower()),
        }
        frame[name] = file
    elif stmt.action == 'read':
        file = frame[name]
        varname = stmt.data.accept(frame, evaluate)
        line = file['value'].readline().rstrip()
        frame[varname]['value'] = line
    elif stmt.action == 'write':
        file = frame[name]
        writedata = str(stmt.data.accept(frame, evaluate))
        # Move pointer to next line after writing
        if not writedata.endswith('\n'):
            writedata += '\n'
        file['value'].write(writedata)
    elif stmt.action == 'close':
        file = frame[name]
        file['value'].close()
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
