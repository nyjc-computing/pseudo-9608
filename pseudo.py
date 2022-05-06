import sys

import pseudocode



HELP = f"""
Pseudo {pseudocode.__version__}
""".strip()



if __name__ == "__main__":
    print(HELP)
    if len(sys.argv) <= 1:
        print("""Usage: pseudo [FILE]""")
        sys.exit(65)
    srcfile = sys.argv[1]
    pseudocode.run(srcfile)
    