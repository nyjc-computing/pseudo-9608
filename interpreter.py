from builtin import call
from builtin import RuntimeError



# Helper functions

def executeStmts(frame, stmts):
    for stmt in stmts:
        returnval = execute(frame, stmt)
        if returnval:
                return returnval

def assignArgsParams(frame, args, callable):
    for arg, param in zip(args, callable['params']):
        name = evaluate(callable['frame'], param['name'])
        callable['frame'][name]['value'] = evaluate(frame, arg)

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
    for expr in stmt['exprs']:
        print(str(evaluate(frame, expr)), end='')
    print('')  # Add \n

def execInput(frame, stmt):
    name = evaluate(frame, stmt['name'])
    frame[name]['value'] = input()

def execDeclare(frame, stmt):
    pass

def execAssign(frame, stmt):
    name = evaluate(frame, stmt['name'])
    value = evaluate(frame, stmt['expr'])
    frame[name]['value'] = value

def execCase(frame, stmt):
    cond = evaluate(frame, stmt['cond'])
    if cond in stmt['stmts']:
        execute(frame, stmt['stmts'][cond])
    elif stmt['fallback']:
        execute(frame, stmt['fallback'])

def execIf(frame, stmt):
    if evaluate(frame, stmt['cond']):
        executeStmts(frame, stmt['stmts'][True])
    elif stmt['fallback']:
        executeStmts(frame, stmt['fallback'])

def execWhile(frame, stmt):
    if stmt['init']:
        execute(frame, stmt['init'])
    while evaluate(frame, stmt['cond']) is True:
        executeStmts(frame, stmt['stmts'])

def execRepeat(frame, stmt):
    executeStmts(frame, stmt['stmts'])
    while evaluate(frame, stmt['cond']) is False:
        executeStmts(frame, stmt['stmts'])

def execProcedure(frame, stmt):
    pass

def execFunction(frame, stmt):
    pass

def execCall(frame, stmt):
    proc = evaluate(frame, stmt['name'])
    assignArgsParams(frame, stmt['args'], proc)
    return executeStmts(frame, proc['stmts'])

def execReturn(local, stmt):
    # This will typically be execute()ed within
    # evaluate() in a function call, so frame is expected
    # to be local
    return evaluate(local, stmt['expr'])

def execFile(frame, stmt):
    name = evaluate(frame, stmt['name'])
    if stmt['action'] == 'open':
        mode = evaluate(frame, stmt['mode'])
        assert mode  # Internal check
        file = {
            'type': mode,
            'value': open(name, mode[0].lower()),
        }
        frame[name] = file
    elif stmt['action'] == 'read':
        file = frame[name]
        varname = evaluate(frame, stmt['data'])
        line = file['value'].readline().rstrip()
        frame[varname]['value'] = line
    elif stmt['action'] == 'write':
        file = frame[name]
        writedata = evaluate(frame, stmt['data'])
        # Move pointer to next line after writing
        if not writedata.endswith('\n'):
            writedata += '\n'
        file['value'].write(writedata)
    elif stmt['action'] == 'close':
        file = frame[name]
        file['value'].close()
        del frame[name]

def execute(frame, stmt):
    if stmt['rule'] == 'output':
        execOutput(frame, stmt)
    if stmt['rule'] == 'input':
        execInput(frame, stmt)
    if stmt['rule'] == 'declare':
        execDeclare(frame, stmt)
    if stmt['rule'] == 'assign':
        execAssign(frame, stmt)
    if stmt['rule'] == 'case':
        execCase(frame, stmt)
    if stmt['rule'] == 'if':
        execIf(frame, stmt)
    if stmt['rule'] == 'while':
        execWhile(frame, stmt)
    if stmt['rule'] == 'repeat':
        execRepeat(frame, stmt)
    if stmt['rule'] == 'procedure':
        execProcedure(frame, stmt)
    if stmt['rule'] == 'call':
        execCall(frame, stmt)
    if stmt['rule'] == 'function':
        execFunction(frame, stmt)
    if stmt['rule'] == 'return':
        return execReturn(frame, stmt)
    if stmt['rule'] == 'file':
        execFile(frame, stmt)

def interpret(statements, frame=None):
    if frame is None:
        frame = {}
    executeStmts(frame, statements)
    return frame
