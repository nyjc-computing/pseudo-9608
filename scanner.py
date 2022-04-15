from builtin import ParseError
from builtin import KEYWORDS, TYPES, OPERATORS, SYMBOLS
from builtin import operators



# Helper functions

def atEnd(code):
    return (len(code['src']) == 0)

def check(code):
    return code['src'][0]

def consume(code):
    char = check(code)
    code['src'] = code['src'][1:]
    return char

def makeToken(tokentype, word, value):
    return {
        'type': tokentype,
        'word': word,
        'value': value,
    }

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
    while not atEnd(code) and (check(code) in ':.+-/*=<>'):
        token += consume(code)
    return token



# Main scanning loop

def scan(src):
    code = {'src': src + '\n'}
    tokens = []
    while not atEnd(code):
        char = check(code)
        if char in [' ', '\r', '\t']:
            consume(code)
            continue
        elif char == '\n':
            text = consume(code)
            token = makeToken('keyword', text, None)
        elif char.isalpha():
            text = word(code)
            if text in KEYWORDS:
                token = makeToken('keyword', text, None)
            else:
                token = makeToken('name', text, None)
        elif char.isdigit():
            text = integer(code)
            token = makeToken('integer', text, int(text))
        elif char == '"':
            text = string(code)
            token = makeToken('string', text, text[1:-1])
        elif char in '()[]:,.+-/*=<>':
            text = symbol(code)
            oper = operators.get(text, None)
            token = makeToken('symbol', text, oper)
        else:
            raise ParseError(f"Unrecognised character {repr(char)}.")
        tokens += [token]
    return tokens