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

- [01a Scanning](https://github.com/nyjc-computing/pseudo/pull/1)
- [01b Tokens](https://github.com/nyjc-computing/pseudo/pull/2)
- [02 Expressions](https://github.com/nyjc-computing/pseudo/pull/3)
- [03 Evaluation](https://github.com/nyjc-computing/pseudo/pull/8)
- [04 Statements](https://github.com/nyjc-computing/pseudo/pull/9)
- [05 Interpreting](https://github.com/nyjc-computing/pseudo/pull/10)
- [06a Variables](https://github.com/nyjc-computing/pseudo/pull/11)
- [06b Assignment](https://github.com/nyjc-computing/pseudo/pull/12)
- [06c Retrieving variables](https://github.com/nyjc-computing/pseudo/pull/13)
- [07 Resolving](https://github.com/nyjc-computing/pseudo/pull/14)
- [08 Static typing](https://github.com/nyjc-computing/pseudo/pull/15)
- [09 Conditionals](https://github.com/nyjc-computing/pseudo/pull/17)
- [10 Loops](https://github.com/nyjc-computing/pseudo/pull/18)
- [11 Input](https://github.com/nyjc-computing/pseudo/pull/19)
- [12a Procedures](https://github.com/nyjc-computing/pseudo/pull/20)
- [12b Procedure calls](https://github.com/nyjc-computing/pseudo/pull/22)
- [12c Passing by reference](https://github.com/nyjc-computing/pseudo/pull/24)
- [13a Functions](https://github.com/nyjc-computing/pseudo/pull/25)
- [13b Loose ends](https://github.com/nyjc-computing/pseudo/pull/26)
- [14a Reading from source](https://github.com/nyjc-computing/pseudo/pull/28)
- [14b Line numbers](https://github.com/nyjc-computing/pseudo/pull/29)
- [14c Referencing source code](https://github.com/nyjc-computing/pseudo/pull/30)
- [14d Column info](https://github.com/nyjc-computing/pseudo/pull/31)
- [15 File IO](https://github.com/nyjc-computing/pseudo/pull/32)
- [16a OOP: Expressions](https://github.com/nyjc-computing/pseudo/pull/34)
- [16b OOP: Statements](https://github.com/nyjc-computing/pseudo/pull/35)
- [16c OOP: Expression Statements](https://github.com/nyjc-computing/pseudo/pull/36)
- [16d OOP: Variables](https://github.com/nyjc-computing/pseudo/pull/37)
- [16e OOP: Values](https://github.com/nyjc-computing/pseudo/pull/38)
- [16f OOP: Frames](https://github.com/nyjc-computing/pseudo/pull/40)
- [16g OOP: Error reporting](https://github.com/nyjc-computing/pseudo/pull/41)
- [16h OOP: Tokens](https://github.com/nyjc-computing/pseudo/pull/43)
- [17 Statement hierarchies](https://github.com/nyjc-computing/pseudo/pull/44)
- [18a Boolean](https://github.com/nyjc-computing/pseudo/pull/45)
- [18b Logical operators](https://github.com/nyjc-computing/pseudo/pull/48)
- [18c Fix: logical operators](https://github.com/nyjc-computing/pseudo/pull/49) (This is an addendum to 18b)
- [19 REALs](https://github.com/nyjc-computing/pseudo/pull/51)
- [20 Packaging](https://github.com/nyjc-computing/pseudo-9608/pull/52)
- [21a Test: Data passing](https://github.com/nyjc-computing/pseudo-9608/pull/53)
- [21b Test: Checking output](https://github.com/nyjc-computing/pseudo-9608/pull/54)
- [21c Test: Checking Errors](https://github.com/nyjc-computing/pseudo-9608/pull/55)
- [22a Scoping: Recursion](https://github.com/nyjc-computing/pseudo-9608/pull/56)
- [22b Scoping: System](https://github.com/nyjc-computing/pseudo-9608/pull/57)
- [23a Object: Scopes](https://github.com/nyjc-computing/pseudo-9608/pull/58)
- [23b Object: Attributes](https://github.com/nyjc-computing/pseudo-9608/pull/59)
- [23c Object: ARRAY](https://github.com/nyjc-computing/pseudo-9608/pull/60)
- [24a Improvements: type annotation](https://github.com/nyjc-computing/pseudo-9608/pull/61)
- [24b Improvements: Decoupling](https://github.com/nyjc-computing/pseudo-9608/pull/64)
- [24c Improvements: Type Relationship](https://github.com/nyjc-computing/pseudo-9608/pull/65)
- [24d Improvements: Parser](https://github.com/nyjc-computing/pseudo-9608/pull/67)
- [24e Improvements: Resolver](https://github.com/nyjc-computing/pseudo-9608/pull/69)
- [24f Improvements: Interpreter](https://github.com/nyjc-computing/pseudo-9608/pull/70)
- [24g Improvements: Pseudo](https://github.com/nyjc-computing/pseudo-9608/pull/71)
- [25a Automation: Testing](https://github.com/nyjc-computing/pseudo-9608/pull/72)
- [25b Automation: Setup](https://github.com/nyjc-computing/pseudo-9608/pull/73)
- [25c Automation: Security](https://github.com/nyjc-computing/pseudo-9608/pull/75)
- [26a Release: Usage](https://github.com/nyjc-computing/pseudo-9608/pull/74)
