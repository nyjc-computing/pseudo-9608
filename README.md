# An interpreter for 9608 pseudocode
[![Run on Repl.it](https://replit.com/badge/github/nyjc-computing/pseudo-9608)](https://replit.com/@nyjc-computing/pseudo-9608)

Pseudo is an interpreter for 9608 pseudocode, a pseudocode syntax used in Cambridge International AS & A Level Computer Science.

The latest version is 0.4.1.

## Setup

```
pip install pseudo-9608
```

## Usage

To try `pseudo` without installing it, fork the Replit repl at
https://replit.com/@nyjc-computing/pseudocode-repl.

### Shell: Running with a pseudocode file

```
$ pseudo myfile.pseudo
```

This will run the pseudocode interpreter on the file `myfile.pseudo`.

### Python: Running with a pseudocode file

```
import pseudocode

pseudocode.runFile('myfile.pseudo')
```

This will run the pseudocode interpreter on the file `myfile.pseudo`.

### Python: Running with a pseudocode string

```
import pseudocode

code = """
OUTPUT "Hello World!"
"""

pseudocode.run(code)
```

This will run the pseudocode interpreter on the string `code`.

# Build Instructions

I don't have a build process for Windows yet; if you are experienced in this area and can offer help, please contact me!

On Unix, Linux:
```
poetry build
poetry install
```

This will install Pseudo as `pseudo`.

# Chapters

This project is also an attempt to write a programming book in a new style. Each chapter of this book is written as a pull request.

Links to each chapter's pull request can be found in [CONTENTS.md](/CONTENTS.md).
