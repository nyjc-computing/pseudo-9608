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
        execute(frame, stmt['fallback']

def execIf(frame, stmt):
    pass

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

def interpret(statements, frame=None):
    if frame is None:
        frame = {}
    for stmt in statements:
        execute(frame, stmt)
    return frame
