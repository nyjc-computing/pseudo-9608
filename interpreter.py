def evaluate(expr):
    # Evaluating tokens
    if 'type' in expr:
        return expr['value']
    # Evaluating exprs
    left = evaluate(expr['left'])
    right = evaluate(expr['right'])
    oper = expr['oper']['value']
    return oper(left, right)