from builtin import call
from builtin import RuntimeError



# Helper functions

def executeStmts(frame, stmts):
    for stmt in stmts:
        returnval = stmt.accept(frame, execute)
        if returnval:
            return returnval

def assignArgsParams(frame, args, callable):
    for arg, param in zip(args, callable['params']):
        name = param['name'].evaluate(callable['frame'])
        callable['frame'][name]['value'] = arg.evaluate(frame)

def evaluate(frame, expr):
    # Evaluating tokens
    if 'type' in expr:
        if expr['type'] == 'name':
            return expr['word']
        return expr['value']
    # Passing frames
    if 'oper' not in expr:
        return expr
    # Evaluating exprs
    oper = expr['oper']['value']
    if oper is call:
        return execCall(
            frame,
            {'name': expr['left'], 'args': expr['right']},
        )
    left = evaluate(frame, expr['left'])
    right = evaluate(frame, expr['right'])
    return oper(left, right)

def execOutput(frame, stmt):
    for expr in stmt.exprs:
        print(str(expr.evaluate(frame)), end='')
    print('')  # Add \n

def execInput(frame, stmt):
    name = stmt.name.evaluate(frame)
    frame[name]['value'] = input()

def execDeclare(frame, stmt):
    pass

def execAssign(frame, stmt):
    name = stmt.name.evaluate(frame)
    value = stmt.expr.evaluate(frame)
    frame[name]['value'] = value

def execCase(frame, stmt):
    cond = stmt.cond.evaluate(frame)
    if cond in stmt.stmtMap:
        execute(frame, stmt.stmtMap[cond])
    elif stmt.fallback:
        execute(frame, stmt.fallback)

def execIf(frame, stmt):
    if stmt.cond.evaluate(frame):
        executeStmts(frame, stmt.stmtMap[True])
    elif stmt.fallback:
        executeStmts(frame, stmt.fallback)

def execWhile(frame, stmt):
    if stmt.init:
        execute(frame, stmt.init)
    while stmt.cond.evaluate(frame) is True:
        executeStmts(frame, stmt.stmts)

def execRepeat(frame, stmt):
    executeStmts(frame, stmt.stmts)
    while stmt.cond.evaluate(frame) is False:
        executeStmts(frame, stmt.stmts)

def execProcedure(frame, stmt):
    pass

def execFunction(frame, stmt):
    pass

def execCall(frame, stmt):
    proc = stmt.callable.evaluate(frame)
    assignArgsParams(frame, stmt.args, proc)
    return executeStmts(frame, proc.stmts)

def execReturn(local, stmt):
    # This will typically be execute()ed within
    # evaluate() in a function call, so frame is expected
    # to be local
    return stmt.expr.evaluate(local)

def execFile(frame, stmt):
    name = stmt.name.evaluate(frame)
    if stmt.action == 'open':
        assert stmt.mode  # Internal check
        file = {
            'type': stmt.mode,
            'value': open(name, mode[0].lower()),
        }
        frame[name] = file
    elif stmt.action == 'read':
        file = frame[name]
        varname = stmt.data.evaluate(frame)
        line = file['value'].readline().rstrip()
        frame[varname]['value'] = line
    elif stmt.action == 'write':
        file = frame[name]
        writedata = str(stmt.data.evaluate(frame))
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
        stmt.accept(frame, execDeclare)
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
        stmt.accept(frame, execProcedure)
    if stmt.rule == 'call':
        stmt.accept(frame, execCall)
    if stmt.rule == 'function':
        stmt.accept(frame, execFunction)
    if stmt.rule == 'return':
        return stmt.accept(frame, execReturn)
    if stmt.rule == 'file':
        stmt.accept(frame, execFile)

def interpret(statements, frame=None):
    if frame is None:
        frame = {}
    executeStmts(frame, statements)
    return frame
