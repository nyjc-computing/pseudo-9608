#!/usr/bin/env python
import sys

import pseudocode
from pseudocode.builtin import ParseError, LogicError, RuntimeError



HELP = f"""
Pseudo {pseudocode.__version__}
""".strip()



def run():
    srcfile = "main.pseudo"
    if len(sys.argv) > 1:
        srcfile = sys.argv[1]
    # print(HELP)
    # print("""Usage: pseudo [FILE]""")
    # sys.exit(65)

    pseudo = pseudocode.Pseudo()
    result = pseudo.runFile(srcfile)
    lines = result['lines']
    err = result['error']
    if err:
        if type(err) in (ParseError, LogicError):
            pseudocode.error(lines, err)
            sys.exit(65)
        elif type(err) in (RuntimeError,):
            pseudocode.error(lines, err)
            sys.exit(70)



if __name__ == "__main__":
    run()
