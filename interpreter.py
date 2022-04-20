from builtin import RuntimeError



def evaluate(expr, frame=None):
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
    left = evaluate(expr['left'])
    right = evaluate(expr['right'])
    return oper(left, right)

def execOutput(frame, stmt):
    for expr in stmt['exprs']:
        print(str(evaluate(expr, frame)), end='')
    print('')  # Add \n

def execDeclare(frame, stmt):
    name = evaluate(stmt['name'], frame)
    type_ = evaluate(stmt['type'], frame)
    frame[name] = {'type': type_, 'value': None}

def execAssign(frame, stmt):
    name = evaluate(stmt['name'], frame)
    value = evaluate(stmt['expr'], frame)
    frame[name]['value'] = value

def execCase(frame, stmt):
    cond = evaluate(stmt['cond'], frame)
    if cond in stmt['stmts']:
        execute(frame, stmt['stmts'][cond])
    elif stmt['fallback']:
        execute(frame, stmt['fallback'])

def execIf(frame, stmt):
    if evaluate(stmt['cond'], frame):
        for substmt in stmt['stmts'][True]:
            execute(frame, substmt)
    elif stmt['fallback']:
        for substmt in stmt['fallback']:
            execute(frame, substmt)

def execWhile(frame, stmt):
    if stmt['init']:
        execute(frame, stmt['init'])
    while evaluate(stmt['cond'], frame) is True:
        for loopstmt in stmt['stmts']:
            execute(frame, loopstmt)

def execRepeat(frame, stmt):
    for loopstmt in stmt['stmts']:
        execute(frame, loopstmt)
    while evaluate(stmt['cond'], frame) is True:
        for loopstmt in stmt['stmts']:
            execute(frame, loopstmt)

def execute(frame, stmt):
    if stmt['rule'] == 'output':
        execOutput(frame, stmt)
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

def interpret(statements, frame=None):
    if frame is None:
        frame = {}
    for stmt in statements:
        execute(frame, stmt)
    return frame
