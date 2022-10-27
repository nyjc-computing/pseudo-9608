# Introduction

This reference guide is heavily adopted from the official Cambrdige 9608 pseudocode guide, with modifications describing the functionality of pseudo instead of recommendations of communication style. Unsupported features are ~~struck through~~.

# Variables, constants and data types
## Atomic type names

The following keywords are used to designate atomic data types:
- `INTEGER:` A whole number
- `REAL:`    A number capable of containing a fractional part
- ~~`CHAR:`    A single character~~
- `STRING:`  A sequence of zero or more characters
- `BOOLEAN:` The logical values `TRUE` and `FALSE`
- ~~`DATE:`    A valid calendar date~~

## Literals

Literals of the above data types must be written as follows:
- Integers : Written as normal in the denary system, e.g. `5`, `-3`
- Real : Always written with at least one digit on either side of the decimal point, zeros being added if necessary, e.g. `4.7`, `0.3`, `-4.0`, `0.0`
- ~~Char: A single character delimited by single quotes e.g. `ꞌxꞌ`, `ꞌCꞌ`, `ꞌ@ꞌ`~~
- String: Delimited by double quotes. A string may contain no characters (i.e. the empty string) e.g. `"This is a string"`, `""`
- Boolean: `TRUE`, `FALSE`
- ~~Date: This will normally be written in the format `dd/mm/yyyy`.~~

## Identifiers

Identifiers (the names given to variables, constants, procedures and functions) can only contain letters (`A–Z`, `a–z`) and digits (`0–9`). They must start with a letter and not a digit. Accented letters and other characters, including the underscore, cannot be used.

Keywords cannot be used as variables.

~~Identifiers are case-insensitive, for example, `Countdown` and `CountDown` cannot be used as separate variables.~~

## Variable declarations

All variables must be explicitly declared.

Declarations are made as follows:

    DECLARE <identifier> : <data type>

> **Example – variable declarations**
> 
>     DECLARE Counter : INTEGER
>     DECLARE TotalToPay : REAL
>     DECLARE GameOver : BOOLEAN

## Constants

~~Constants are declared at the beginning of a piece of pseudocode (unless it is desirable to restrict the scope of the constant).~~

~~Constants are declared by stating the identifier and the literal value in the following format:~~

~~CONSTANT <identifier> = <value>~~

~~**Example – CONSTANT declarations**~~

~~CONSTANT HourlyRate = 6.50~~
~~CONSTANT DefaultText = "N/A"~~

~~Only literals can be used as the value of a constant. A variable, another constant or an expression cannot be used.~~

## Assignments

The assignment operator is `<-`. Assignments are made in the following format:

    <identifier> <- <value>

The identifier must refer to a variable (this can be an individual element in a data structure such as an array or an abstract data type). The value may be any expression that evaluates to a value of the same data type as the variable.

> **Example – assignments**
> 
>     Counter <- 0
>     Counter <- Counter + 1
>     TotalToPay <- NumberOfHours * HourlyRate

# Arrays

## Declaring arrays

Arrays are fixed-length structures of elements of identical data type, accessible by consecutive index (subscript) numbers.

The lower bound of the array (i.e. the index of the first element) must be stated. Usually a lower bound of 1 is used.

Square brackets are used to indicate the array indices.

One-dimensional and two-dimensional arrays are declared as follows (where `l`, `l1`, `l2` are lower bounds and `u`, `u1`, `u2` are upper bounds):

    DECLARE <identifier> : ARRAY[<l>:<u>] OF <data type>
    DECLARE <identifier> : ARRAY[<l1>:<u1>,<l2>:<u2>] OF <data type>

> **Example – array declaration**
> 
>     DECLARE StudentNames : ARRAY[1:30] OF STRING
>     DECLARE NoughtsAndCrosses : ARRAY[1:3,1:3] OF CHAR

## Using arrays

In pseudocode statements, only one index value is used for each dimension in the square brackets.

> **Example – using arrays**
> 
>     StudentNames[1] <- "Ali"
>     NoughtsAndCrosses[2,3] <- ꞌXꞌ
>     StudentNames[n+1] <- StudentNames[n]

Arrays can be used in assignment statements (provided they have same size and data type):

> **Example – assigning an array**
> 
>     SavedGame <- NoughtsAndCrosses

A statement **cannot**, however, refer to a group of array elements individually. For example, the following construction is not supported:

    StudentNames [1 TO 30] <- ""

Instead, an appropriate loop structure has to be used to assign the elements individually. For example:

> **Example – assigning a group of array elements**
> 
>     FOR Index <- 1 TO 30
>         StudentNames[Index] <- ""
>     ENDFOR
    
# Abstract data types

## Defining custom types

A custom type is a collection of data that can consist of different data types, grouped under one identifier.

The custom type is declared as follows:

    TYPE <identifier1>
        DECLARE <identifier2> : <data type>
        DECLARE <identifier3> : <data type>
        ...
    ENDTYPE

> **Example – declaration of custom type**
> 
> This user type holds data about a student.
> 
>     TYPE Student
>         DECLARE Surname : STRING
>         DECLARE FirstName : STRING
>         DECLARE DateOfBirth : DATE
>         DECLARE YearGroup : INTEGER
>         DECLARE FormGroup : CHAR
>     ENDTYPE

## Using custom types

When a custom type has been defined it can be used in the same way as any other data type in declarations.

Variables of a custom data type can be assigned to each other. Individual data items are accessed using dot (`.`) notation.

> **Example – using custom types**
> 
> This pseudocode uses the custom type `Student` defined in the previous section.
> 
>     DECLARE Pupil1 : Student
>     DECLARE Pupil2 : Student
>     DECLARE Form : ARRAY[1:30] OF Student
>     DECLARE Index : INTEGER
>     
>     Pupil1.Surname <- "Johnson"
>     Pupil1.FirstName <- "Leroy"
>     Pupil1.DateOfBirth <- 02/01/2005
>     Pupil1.YearGroup <- 6
>     Pupil1.FormGroup <- ꞌAꞌ
>     Pupil2 <- Pupil1
>     FOR Index <- 1 TO 30
>         Form[Index].YearGroup <- Form[Index].YearGroup + 1
>     ENDFOR

# Common operations

## Input and output

Values are input using the INPUT command as follows:

    INPUT <identifier>

The identifier should be a variable (that may be an individual element of a data structure such as an array, or a custom data type).

Values are output using the OUTPUT command as follows:

    OUTPUT <value(s)>

Several values, separated by commas, can be output using the same command.

> **Examples – INPUT and OUTPUT statements**
> 
>     INPUT Answer
>     OUTPUT Score
>     OUTPUT "You have ", Lives, " lives left"

## Arithmetic operations

Standard arithmetic operator symbols are used:
- `+` Addition
- `-` Subtraction
- `*` Multiplication
- `/` Division

The resulting value of the division operation is of data type `REAL`, even if the operands are integers.

~~The integer division operators MOD and DIV can be used. However, their use should be explained explicitly and not assumed.~~

Multiplication and division have higher precedence over addition and subtraction (this is the normal mathematical convention). However, it is good practice to make the order of operations in complex expressions explicit by using parentheses.

The following functions will be supported in future:
- `INT(x)` returns the integer part of `x`  
Example: `INT(27.5415)` returns `27`

## Relational operations

The following symbols are used for relational operators (also known as comparison operators):

- `>`  Greater than
- `<`  Less than
- `>=` Greater than or equal to
- `<=` Less than or equal to
- `=`  Equal to
- `<>` Not equal to

The result of these operations is always of data type `BOOLEAN`.

In complex expressions it is advisable to use parentheses to make the order of operations explicit.

## Logic operators

The only logic operators (also called relational operators) used are `AND`, `OR` and `NOT`. The operands and results of these operations are always of data type `BOOLEAN`.

In complex expressions it is advisable to use parentheses to make the order of operations explicit.

## String operations

Not yet supported.

~~The `&` concatenation operator concatenates (joins) two strings. Example: `"Summer" & " " & "Pudding"` produces `"Summer Pudding"`~~

The following functions will be supported in future:
- `MID(ThisString, x, y)` returns a string of length `y` starting at position `x` from `ThisString`.  
Example: `MID("ABCDEFGH", 2, 3)` returns `"BCD"`
- `LENGTH(ThisString)` returns the integer value representing the length of `ThisString`  
Example: `LENGTH("Happy Days")` returns `10`
- `LEFT(ThisString, x)` returns leftmost `x` characters from `ThisString`  
Example: `LEFT("ABCDEFGH", 3)` returns `"ABC"`
- `RIGHT(ThisString, x)` returns rightmost `x` characters from `ThisString`  
Example: `RIGHT("ABCDEFGH", 3)` returns `"FGH"`
- `ASC(ThisChar)` returns the ASCII value of character `ThisChar`  
Example: `ASC('A')` returns `65`

## Random number generation

The following functions can be used:
- `RANDOMBETWEEN(min, max)` generates a random integer between the integers `min` and `max` (inclusive)
- `RND()` generates a random real number between 0 and 1.

# Selection

## IF statements

**Note:** Strict enforcement of indentation is not yet supported in pseudo.

`IF` statements may or may not have an `ELSE` clause.
`IF` statements without an else clause are written as follows:

    IF <condition>
      THEN
        <statements>
    ENDIF

`IF` statements with an else clause are written as follows:

    IF <condition>
      THEN
        <statements>
      ELSE
        <statements>
    ENDIF

Note that the `THEN` and `ELSE` clauses are only indented by two spaces.

When `IF` statements are nested, the nesting should continue the indentation of two spaces. Run-on `THEN IF` and `ELSE IF` lines are not supported; a line break is expected after `THEN` and `ELSE`.

> **Example – nested IF statements**
> 
>     IF ChallengerScore > ChampionScore
>       THEN
>         IF ChallengerScore > HighestScore
>           THEN
>             OUTPUT ChallengerName, " is champion and highest scorer"
>           ELSE
>             OUTPUT Player1Name, " is the new champion"
>         ENDIF
>       ELSE
>         OUTPUT ChampionName, " is still the champion"
>         IF ChampionScore > HighestScore
>           THEN
>             OUTPUT ChampionName, " is also the highest scorer"
>         ENDIF
>     ENDIF

## CASE statements

`CASE` statements allow one out of several branches of code to be executed, depending on the value of a variable.

`CASE` statements are written as follows:

    CASE OF <identifier>
      <value 1> : <statement>
      <value 2> : <statement>
      ...
    ENDCASE

An `OTHERWISE` clause can be the last case:

    CASE OF <identifier>
      <value 1> : <statement>
      <value 2> : <statement>
      ...
      OTHERWISE <statement>
    ENDCASE

Branches only allow single statements, and single values should be used for each case. If the cases are more complex, the use of an `IF` statement, rather than a `CASE` statement, is required.

Each case clause is indented by two spaces. They can be seen as continuations of the `CASE` statement rather than new statements.

The case clauses are tested in sequence. When a case that applies is found, its statement is executed and the `CASE` statement is complete. Control is passed to the statement after the `ENDCASE`. Any remaining cases are not tested.

If present, an OTHERWISE clause must be the last case. Its statement will be executed if none of the preceding cases apply.

> **Example – formatted CASE statement**
> 
>     INPUT Move
>     CASE OF Move
>       ꞌWꞌ: Position <- Position – 10
>       ꞌSꞌ: Position <- Position + 10
>       ꞌAꞌ: Position <- Position – 1
>       ꞌDꞌ: Position <- Position + 1
>     OTHERWISE : Beep
>     ENDCASE

# Iteration

## Count-controlled (FOR) loops

Count-controlled loops are written as follows:

    FOR <identifier> <- <value1> TO <value2>
        <statements>
    ENDFOR

The identifier must be a variable of data type `INTEGER`, and the values must be expressions that evaluate to integers.

The variable is assigned each of the integer values from `value1` to `value2` inclusive, running the statements inside the `FOR` loop after each assignment. If `value1 = value2` the statements will be executed once, and if `value1 > value2` the statements will not be executed.

An increment can be specified as follows:

    FOR <identifier> <- <value1> TO <value2> STEP <increment>
        <statements>
    ENDFOR

The increment must be an expression that evaluates to an integer. The identifier is assigned the values from `value1` in successive increments of `increment` until it reaches `value2`. If it goes past `value2`, the loop terminates. The `increment` can be negative.

> **Example – nested FOR loops**
> 
>     Total = 0
>     FOR Row = 1 TO MaxRow
>         RowTotal = 0
>         FOR Column = 1 TO 10
>             RowTotal <- RowTotal + Amount[Row,Column]
>         ENDFOR Column
>         OUTPUT "Total for Row ", Row, " is ", RowTotal
>         Total <- Total + RowTotal
>     ENDFOR Row
>     OUTPUT "The grand total is ", Total

## Post-condition (REPEAT UNTIL) loops

Post-condition loops are written as follows:

    REPEAT
        <Statements>
    UNTIL <condition>

The condition must be an expression that evaluates to a Boolean.

The statements in the loop are executed at least once. The condition is tested after the statements are executed and if it evaluates to `TRUE` the loop terminates, otherwise the statements are executed again.

> **Example – REPEAT UNTIL statement**
> 
>     REPEAT
>         OUTPUT "Please enter the password"
>         INPUT Password
>     UNTIL Password = "Secret"

## Pre-condition (WHILE) loops

Pre-condition loops are written as follows:

    WHILE <condition> DO
        <statements>
    ENDWHILE

The condition must be an expression that evaluates to a Boolean.

The condition is tested before the statements, and the statements will only be executed if the condition evaluates to `TRUE`. After the statements have been executed the condition is tested again. The loop terminates when the condition evaluates to `FALSE`.

The statements are not executed if, on the first test, the condition evaluates to `FALSE`.

> **Example – WHILE loop**
> 
>     WHILE Number > 9 DO
>         Number <- Number – 9
>     ENDWHILE

# Procedures and functions

## Defining and calling procedures

A procedure with no parameters is defined as follows:

    PROCEDURE <identifier>
        <statements>
    ENDPROCEDURE

A procedure with parameters is defined as follows:

    PROCEDURE <identifier>(<param1>:<datatype>,<param2>:<datatype>...)
        <statements>
    ENDPROCEDURE

The `<identifier>` is the identifier used to call the procedure. Where used, `param1`, `param2` etc. are identifiers for the parameters of the procedure. These will be used as variables in the statements of the procedure.

Procedures defined as above are called as follows, respectively:

    CALL <identifier>

    CALL <identifier>(Value1,Value2...)

These calls are complete program statements.

When parameters are used, `Value1`, `Value2`... must be of the correct data type as in the definition of the procedure.

Optional parameters and overloaded procedures (where alternative definitions are given for the same identifier with different sets of parameters) are not supported in pseudo.

Unless otherwise stated, it is assumed that parameters are passed by value.

When the procedure is called, control is passed to the procedure. If there are any parameters, these are substituted by their values, and the statements in the procedure are executed. Control is then returned to the line that follows the procedure call.

> **Example – use of procedures with and without parameters**
> 
>     PROCEDURE DefaultSquare
>         CALL Square(100)
>     ENDPROCEDURE
>     
>     PROCEDURE Square(Size : integer)
>         FOR Side <- 1 TO 4
>             MoveForward Size
>             Turn 90
>         ENDFOR
>     ENDPROCEDURE
>     
>     IF Size = Default
>       THEN
>         CALL DefaultSquare
>       ELSE
>         CALL Square(Size)
>     ENDIF

## Defining and calling functions

Functions operate in a similar way to procedures, except that in addition they return a single value to the point at which they are called. Their definition includes the data type of the value returned.

A procedure with no parameters is defined as follows:

    FUNCTION <identifier> RETURNS <data type>
        <statements>
    ENDFUNCTION

A procedure with parameters is defined as follows:

    FUNCTION <identifier>(<param1>:<datatype>,<param2>:<datatype>...) RETURNS <data type>
        <statements>
    ENDFUNCTION

The keyword `RETURN` is used as one of the statements within the body of the function to specify the value to be returned. Normally, this will be the last statement in the function definition.

Because a function returns a value that is used when the function is called, function calls are not complete program statements. The keyword `CALL` cannot be used when calling a function. Functions can only be called as part of an expression. When the `RETURN` statement is executed, the value returned replaces the function call in the expression and the expression is then evaluated.

> **Example – definition and use of a function**
> 
>     FUNCTION Max(Number1:INTEGER, Number2:INTEGER) RETURNS INTEGER
>         IF Number1 > Number2
>           THEN
>             RETURN Number1
>           ELSE
>             RETURN Number2
>         ENDIF
>     ENDFUNCTION
>     OUTPUT "Penalty Fine = ", Max(10,Distance*2)

## Passing parameters by value or by reference

Parameters can be passed either by value or by reference. The difference between these only matters if, in the statements of the procedure, the value of the parameter is changed, for example if the parameter is the subject (on the left hand side) of an assignment.

To specify whether a parameter is passed by value or by reference, the keywords `BYVALUE` and `BYREF` precede the parameter in the definition of the procedure. If there are several parameters, they are all passed by the same method and the `BYVALUE` or `BYREF` keyword need not be repeated.

> **Example – passing parameters by reference**
> 
>     PROCEDURE SWAP(BYREF X : INTEGER, Y : INTEGER)
>         Temp <- X
>         X <- Y
>         Y <- Temp
>     ENDPROCEDURE

If the method for passing parameters is not specified, passing by value is assumed.

If parameters are passed by reference (as in the above example), when the procedure is called an identifier for a variable of the correct data type must be given (rather than any expression which evaluates to a value of the correct type). A reference (address) to that variable is passed to the procedure when it is called and if the value is changed in the procedure, this change is reflected in the variable which was passed into it, after the procedure has terminated.

In principle, parameters can also be passed by value or by reference to functions and will operate in a similar way. However, it should be considered bad practice to pass parameters by reference to a function and this should be avoided. Functions should have no other side effect on the program other than to return the designated value.

# File handling

## Handling text files

Text files consist of lines of text that are read or written consecutively as strings.

Files must be explicitly opened, stating the mode of operation, before reading from or writing to it. This is written as follows:

    OPENFILE <File identifier> FOR <File mode>

The file identifier is a String whose value is the name of the file, or an expression that evaluates to such a String. The following file modes are used:

- `READ` : for data to be read from the file
- `WRITE` : for data to be written to the file. A new file will be created and any existing data in the file will be lost.
- `APPEND` : for data to be added to the file, after any existing data.

A file can be opened in only one mode at a time.

Data is read from the file (after the file has been opened in `READ` mode) using the `READFILE` command as follows:

    READFILE <File Identifier>, <Variable>

The data read is assigned to `Variable`, which must be of data type `STRING`. When the command is executed, the next line of text in the file is read and assigned to the variable.

It is useful to think of the file as having a pointer which indicates the next line to be read. When the file is opened, the file pointer points to the first line of the file. After each `READFILE` command is executed the file pointer moves to the next line, or to the end of the file if there are no more lines.

The function `EOF` is used to test whether the file pointer is at the end of the file. It is called as follows:

    EOF(<File Identifier>)

This function returns a Boolean value: `TRUE` if the file pointer is at the end of the file and `FALSE` otherwise.

Data is written into the file (after the file has been opened in `WRITE` or `APPEND` mode) using the `WRITEFILE` command as follows:

    WRITEFILE <File identifier>, <String>

When the command is executed, the string is written into the file and the file pointer moves to the next line.

Files should be closed when they are no longer needed using the `CLOSEFILE` command as follows:

    CLOSEFILE <File identifier>

> **Example – file handling operations**
> 
> This example uses the operations together, to copy all the lines from `FileA.txt` to `FileB.txt`, replacing any blank lines by a line of dashes.
> 
>     DECLARE LineOfText : STRING
>     OPENFILE FileA.txt FOR READ
>     OPENFILE FileB.txt FOR WRITE
>     WHILE NOT EOF(FileA.txt) DO
>         READFILE FileA.txt, LineOfText
>         IF LineOfText = ""
>           THEN
>             WRITEFILE FileB.txt, "-------------------------"
>           ELSE
>             WRITEFILE FILEB.txt, LineOfText
>         ENDIF
>     ENDWHILE
>     CLOSEFILE FileA.txt
>     CLOSEFILE FileB.txt

## Handling random files

~~Random files (also called binary files) contain a collection of data in their binary representation, normally as records of fixed length. They can be thought of as having a file pointer which can be moved to any location or address in the file. The record at that location can then be read or written.~~

~~Random files are opened using the RANDOM file mode as follows:~~

~~OPENFILE <File identifier> FOR RANDOM~~

~~As with text files, the file identifier will normally be the name of the file.~~

~~The `SEEK` command moves the file pointer to a given location:~~

~~SEEK <File identifier>, <address>~~

~~The address should be an expression that evaluates to an integer which indicates the location of a record to be read or written. This is usually the number of records from the beginning of the file.~~

~~The command `GETRECORD` should be used to read the record at the file pointer:~~

~~GETRECORD <File identifier>, <Variable>~~

~~When this command is executed, the variable is assigned to the record that is read, and must be of the appropriate data type for that record (usually a custom type).~~

~~The command `PUTRECORD` is used to write a record into the file at the file pointer:~~

~~PUTRECORD <File identifier>, <Variable>~~

~~When this command is executed, the data in the variable is inserted into the record at the file pointer. Any data that was previously at this location will be replaced.~~

> **Example – handling random files**
> 
> The records from positions 10 to 20 of a file `StudentFile.Dat` are moved to the next position and a new record is inserted into position 10. The example uses the custom type `Student` defined earlier.
> 
>     DECLARE Pupil : Student
>     DECLARE NewPupil : Student
>     DECLARE Position : INTEGER
>     
>     NewPupil.Surname <- "Johnson"
>     NewPupil.Firstname <- "Leroy"
>     NewPupil.DateOfBirth <- 02/01/2005
>     NewPupil.YearGroup <- 6
>     NewPupil.FormGroup <- ꞌAꞌ
>     
>     OPENFILE StudentFile.Dat FOR RANDOM
>     FOR Position = 20 TO 10 STEP -1
>         SEEK StudentFile.Dat, Position
>         GETRECORD StudentFile.Dat, Pupil
>         SEEK StudentFile.Dat, Position + 1
>         PUTRECORD StudentFile.Dat, Pupil
>     ENDFOR
>     
>     SEEK StudentFile.Dat, 10
>     PUTRECORD StudentFile.Dat, NewPupil
>     
>     CLOSEFILE StudentFile.dat