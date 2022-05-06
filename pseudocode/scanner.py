from .builtin import ParseError
from .builtin import KEYWORDS, VALUES, OPERATORS
from .builtin import NULL
from .lang import Token



# Helper functions

def atEnd(code):
    return code['cursor'] >= code['length']

def check(code):
    return code['src'][code['cursor']]

def consume(code):
    char = check(code)
    code['cursor'] += 1
    return char

def makeToken(code, type, word, value):
    line = code['line']
    column = code['cursor'] - code['lineStart'] - len(word)
    return Token(line, column, type, word, value)


# Scanning functions

def word(code):
    token = consume(code)
    while not atEnd(code) and check(code).isalpha():
        token += consume(code)
    return token

def number(code):
    token = consume(code)
    while not atEnd(code) and check(code).isdigit():
        token += consume(code)
    if check(code) != '.':
        return token  # INTEGER
    # Scan REAL
    token += consume(code)  # '.'
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
    while not atEnd(code) and (check(code) in ':.+-/*=<>'):
        token += consume(code)
    return token



# Main scanning loop

def scan(src):
    if not src.endswith('\n'):
        src = src + '\n'
    code = {
        'src': src,
        'length': len(src),
        'cursor': 0,
        'line': 1,
        'lineStart': 0,
        'lines': [],
    }
    tokens = []
    while not atEnd(code):
        char = check(code)
        if char in [' ', '\r', '\t']:
            consume(code)
            continue
        elif char == '\n':
            text = consume(code)
            token = makeToken(code, 'keyword', text, None)
            start, end = code['lineStart'], code['cursor'] - 1
            code['lines'] += [code['src'][start:end]]
            code['line'] += 1
            code['lineStart'] = code['cursor']
        elif char.isalpha():
            text = word(code)
            if text in KEYWORDS:
                token = makeToken(code, 'keyword', text, None)
            elif text in VALUES:
                if text == 'NULL':
                    token = makeToken(code, 'NULL', text, NULL)
                elif text == 'TRUE':
                    token = makeToken(code, 'BOOLEAN', text, True)
                elif text == 'FALSE':
                    token = makeToken(code, 'BOOLEAN', text, False)
                else:
                    raise ValueError(f"Unrecognised value {text}")
            elif text in OPERATORS:  # AND, OR, NOT
                oper = OPERATORS.get(text, None)
                token = makeToken(code, 'symbol', text, oper)
            else:
                token = makeToken(code, 'name', text, None)
        elif char.isdigit():
            text = number(code)
            if '.' in text:
                token = makeToken(code, 'REAL', text, float(text))
            else:
                token = makeToken(code, 'INTEGER', text, int(text))
        elif char == '"':
            text = string(code)
            token = makeToken(code, 'STRING', text, text[1:-1])
        elif char in '()[]:,.+-/*=<>':
            text = symbol(code)
            oper = OPERATORS.get(text, None)
            token = makeToken(code, 'symbol', text, oper)
        else:
            raise ParseError(
                f"Unrecognised character",
                token=char,
                line=code['line'],
            )
        tokens += [token]
    return tokens, code['lines']