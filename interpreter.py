from builtin import RuntimeError, LogicError, get



def evaluate(expr, frame=None):
    # Evaluating tokens
    if 'type' in expr:
        if expr['type'] == 'name':
            return expr['word']
        return expr['value']
    # Evaluating exprs
    oper = expr['oper']['value']
    if oper is get:
        left = frame  # <-- expr['left'] is None
    else:
        left = evaluate(expr['left'])
    right = evaluate(expr['right'])
    return oper(left, right)

def execOutput(frame, stmt):
    for expr in stmt['exprs']:
        print(str(evaluate(expr)), end='')
    print('')  # Add \n

def execDeclare(frame, stmt):
    name = evaluate(stmt['name'], frame)
    type_ = evaluate(stmt['type'], frame)
    frame[name] = {'type': type_, 'value': None}

def execAssign(frame, stmt):
    name = evaluate(stmt['name'], frame)
    value = evaluate(stmt['expr'], frame)
    if name not in frame:
        raise LogicError(f'Undeclared name {repr(name)}')
    # HACK: type-check values before storing
    frametype = frame[name]['type']
    valuetype = type(value)
    if frametype == 'INTEGER' and valuetype != int:
        raise LogicError(f'Expected {frametype}, got {valuetype}')
    elif frametype == 'STRING' and valuetype != str:
        raise LogicError(f'Expected {frametype}, got {valuetype}')
    frame[name]['value'] = value

def execute(frame, stmt):
    if stmt['rule'] == 'output':
        execOutput(frame, stmt)
    if stmt['rule'] == 'declare':
        execDeclare(frame, stmt)
    if stmt['rule'] == 'assign':
        execAssign(frame, stmt)

def interpret(statements):
    frame = {}
    for stmt in statements:
        try:
            execute(frame, stmt)
        except RuntimeError:
            print()
            break
    return frame