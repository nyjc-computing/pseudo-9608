# Helper functions

def atEnd(code):
    return (len(code['src']) == 0)

def check(code):
    return code['src'][0]

def consume(code):
    char = check(code)
    code['src'] = code['src'][1:]  # Remove first char
    return char



# Main scanning loop

def scan(src):
    code = {'src': src}
    while not atEnd(code):
        char = check(code)
        # If it is whitespace, ignore it.
        if char in [' ', '\r', '\t']:
            consume(code)
            continue
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