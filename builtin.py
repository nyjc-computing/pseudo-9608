# Errors

class ParseError(Exception): pass



# Token types

KEYWORDS = [
    'DECLARE', 'OUTPUT',
    'WHILE', 'DO', 'ENDWHILE',
    'CASE', 'OF', 'OTHERWISE', 'ENDCASE',
]

TYPES = ['INTEGER', 'STRING']

OPERATORS = [
    '+', '-', '/', '*', '=',
    '<', '<-', '<=', '>', '>=', '<>',
]

SYMBOLS = [':']
