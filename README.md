# An interpreter for 9608 pseudocode

Pseudo is an interpreter for 9608 pseudocode, a pseudocode syntax used in Cambridge International AS & A Level Computer Science.

## Setup

```
pip install pseudo-9608
```

## Usage

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

# Chapters

This project is also an attempt to write a programming book in a new style. Each chapter of this book is written as a pull request.

Links to each chapter's pull request can be found in [CONTENTS.md](/CONTENTS.md).
