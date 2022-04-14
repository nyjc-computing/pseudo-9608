# Helper functions

def atEnd(code):
    return (len(code['src']) == 0)

def check(code):
    return code['src'][0]

def consume(code):
    char = check(code)
    code['src'] = code['src'][1:]  # Remove first char
    return char

# Scanning functions

def word(code):
    # We know the first character is an alphabet letter
    # because we checked in main()
    token = consume(code)
    while not atEnd(code) and check(code).isalpha():
        # Keep adding letters to token
        # and removing from src
        token += consume(code)
    return token

def integer(code):
    # Starting with digits
    token = consume(code)
    while not atEnd(code) and check(code).isdigit():
        # Keep adding digits to token
        # and removing from src
        token += consume(code)
    return token

def string(code):
    token = consume(code)
    # Stop at next double-quote (")
    while not atEnd(code) and check(code) != '"':
        # Keep adding letters to token
        # and removing from src
        token += consume(code)
    # Remember to consume the ending double-quote '"'
    if not atEnd(code):
        token += consume(code)
    return token

def symbol(code):
    token = consume(code)
    if token in '()[]':  # single-character tokens
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
        # If it is whitespace, ignore it.
        if char in [' ', '\r', '\t']:
            consume(code)
            continue
        # Line break
        elif char == '\n':
            token = consume(code)
        # Tokenise words
        elif char.isalpha():
            token = word(code)
        # Tokenise integers
        elif char.isdigit():
            token = integer(code)
        # Tokenise strings
        elif char == '"':
            token = string(code)
        # Tokenise symbols
        elif char in '()[]:.+-/*=<>':
            token = symbol(code)
        else:
            # We want an internal representation of the character for
            # error reporting, and we get that using the repr() function
            raise ValueError(f"Unrecognised character {repr(char)}.")
        tokens += [token]
        print('Scanned token:', token, ', characters left:', len(code['src']))
    return tokens