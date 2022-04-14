# Helper functions

def atEnd(code):
    return (len(code['src']) == 0)

def check(code):
    return code['src'][0]

def consume(code):
    char = check(code)
    code['src'] = code['src'][1:]
    return char

# Scanning functions

def word(code):
    token = consume(code)
    while not atEnd(code) and check(code).isalpha():
        token += consume(code)
    return token

def integer(code):
    token = consume(code)
    while not atEnd(code) and check(code).isdigit():
        token += consume(code)
    return token

def string(code):
    token = consume(code)
    while not atEnd(code) and check(code) != '"':
        token += consume(code)
    if not atEnd(code):
        token += consume(code)
    return token

def symbol(code):
    token = consume(code)
    if token in '()[]':
        return token
    # Check if the next character is a valid symbol
    # that forms part of a multi-character symbol.
    while not atEnd(code) and (check(code) in ':.+-/*=<>'):
        token += consume(code)
    return token



# Main scanning loop

def scan(src):
    code = {'src': src}
    tokens = []
    while not atEnd(code):
        char = check(code)
        if char in [' ', '\r', '\t']:
            consume(code)
            continue
        elif char == '\n':
            token = consume(code)
        elif char.isalpha():
            token = word(code)
        elif char.isdigit():
            token = integer(code)
        elif char == '"':
            token = string(code)
        elif char in '()[]:.+-/*=<>':
            token = symbol(code)
        else:
            raise ValueError(f"Unrecognised character {repr(char)}.")
        tokens += [token]
        print('Scanned token:', token, ', characters left:', len(code['src']))
    return tokens