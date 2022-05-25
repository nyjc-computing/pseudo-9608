from typing import Any
from typing import List, Tuple

from . import builtin, lang



# Helper functions

def atEnd(code: "Code") -> bool:
    return code.cursor >= code.length

def check(code: "Code") -> str:
    return code.src[code.cursor]

def consume(code: "Code") -> str:
    char = check(code)
    code.cursor += 1
    return char

def makeToken(
    code: "Code",
    type: lang.Type,
    word: str,
    value: Any,
) -> lang.Token:
    column = code.cursor - code.lineStart - len(word)
    return lang.Token(code.line, column, type, word, value)



# Scanning functions

def word(code: "Code") -> str:
    token = consume(code)
    while not atEnd(code) and (check(code).isalpha() or check(code).isdigit()):
        token += consume(code)
    return token

def number(code: "Code") -> str:
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

def string(code: "Code") -> str:
    token = consume(code)
    while not atEnd(code) and check(code) != '"':
        token += consume(code)
    if not atEnd(code):
        token += consume(code)
    return token

def symbol(code: "Code") -> str:
    token = consume(code)
    if token in builtin.SYM_SINGLE:
        return token
    while not atEnd(code) and (check(code) in builtin.SYM_MULTI):
        token += consume(code)
    return token



class Code:
    """
    Encapsulates the source code and its properties.

    Used by the scanner.
    """
    def __init__(
        self,
        src: str,
    ):
        self.src = src
        self.cursor: int = 0
        self.line: int = 1
        self.lineStart: int = 0
        self.lines: List[str] = []

    @property
    def length(self):
        return len(self.src)

    def nextLine(self):
        start, end = self.lineStart, self.cursor - 1
        self.lines += [self.src[start:end]]
        self.line += 1
        self.lineStart = self.cursor
        
    

    
# Main scanning loop

def scan(src: str) -> Tuple[List[lang.Token], List[str]]:
    if not src.endswith('\n'):
        src = src + '\n'
    code = Code(src)
    tokens = []
    while not atEnd(code):
        char = check(code)
        if char in [' ', '\r', '\t']:
            consume(code)
            continue
        elif char == '\n':
            text = consume(code)
            token = makeToken(code, 'keyword', text, None)
            code.nextLine()
        elif char.isalpha():
            text = word(code)
            if text in builtin.KEYWORDS:
                token = makeToken(code, 'keyword', text, None)
            elif text in builtin.VALUES:
                if text == 'NULL':
                    token = makeToken(code, 'NULL', text, builtin.NULL)
                elif text == 'TRUE':
                    token = makeToken(code, 'BOOLEAN', text, True)
                elif text == 'FALSE':
                    token = makeToken(code, 'BOOLEAN', text, False)
                else:
                    raise ValueError(f"Unrecognised value {text}")
            elif text in builtin.OPERATORS:  # AND, OR, NOT
                oper = builtin.OPERATORS.get(text, None)
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
        elif char in builtin.SYMBOLS:
            text = symbol(code)
            oper = builtin.OPERATORS.get(text, None)
            token = makeToken(code, 'symbol', text, oper)
        else:
            raise builtin.ParseError(
                f"Unrecognised character",
                token=char,
                line=code.line,
            )
        tokens += [token]
    return tokens, code.lines
