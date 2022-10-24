"""interpreter

execute(frame: Frame, statements: list) -> None
    Interprets and executes a list of statements
"""

from typing import Optional, Union, Callable as function
from functools import singledispatch
from dataclasses import dataclass, field

from . import (builtin, lang, system)



# ----------------------------------------------------------------------

# Helper functions

def expectTypeElseError(exprmode: str,
                        *expected: str,
                        errmsg: str="Expected",
                        token: lang.Token) -> None:
    """Takes in a type, followed by one or more expected types.
    Raises an error if the given type is not in the expected types.
    """
    if not exprmode in expected:
        raise builtin.RuntimeError(f"{errmsg} {expected}", token=token)

def declaredElseError(frame: lang.Frame,
                      name: lang.NameKey,
                      errmsg: str="Undeclared",
                      token: Optional[lang.Token]=None) -> None:
    """Takes in a frame and a name.
    Raises an error if the name is not declared in the frame.
    """
    if not frame.has(name):
        raise builtin.RuntimeError(errmsg, token)

def undeclaredElseError(frame: lang.Frame,
                        name: lang.NameKey,
                        errmsg="Already declared",
                        token: Optional[lang.Token]=None) -> None:
    """Takes in a frame and a name.
    Raises an error if the name is already declared in the frame.
    """
    if frame.has(name):
        raise builtin.RuntimeError(errmsg, token)



@dataclass
class Interpreter:
    """Interprets a list of statements with a given frame."""
    frame: lang.Frame
    statements: lang.Stmts
    outputHandler: function = field(default=print, init=False)

    def registerOutputHandler(self, handler: function) -> None:
        """Register handler as the function to use to handle any output
        from the executed statements.
        The default handler is Python's print().
        """
        self.outputHandler = handler  # type: ignore

    def interpret(self) -> None:
        executeStmts(
            self.statements,
            self.frame,
            output=self.outputHandler,
        )



# Evaluators
# Evaluation functions return the evaluated value of Exprs.

def evalIndex(indexExpr: lang.IndexExpr, frame: lang.Frame) -> lang.IndexKey:
    """Returns the evaluated value of an Array's index."""
    indexes: lang.IndexKey = tuple()
    for expr in indexExpr:
        index = evaluate(expr, frame)
        indexes += (index,)
    return indexes

def evalLiteral(literal: lang.Literal, frame: lang.Frame) -> lang.PyLiteral:
    return literal.value

def evalUnary(expr: lang.Unary, frame: lang.Frame) -> lang.PyLiteral:
    rightval = evaluate(expr.right, frame)
    return expr.oper(rightval)

def evalBinary(expr: lang.Binary, frame: lang.Frame) -> lang.PyLiteral:
    leftval = evaluate(expr.left, frame)
    rightval = evaluate(expr.right, frame)
    return expr.oper(leftval, rightval)

@singledispatch
def evalCallable(callable, callargs, frame, **kwargs):
    """Returns the evaluated value of a Builtin/Callable."""
    raise TypeError(f"{type(callable)} passed in evalCallable")

# BUG: callargs can't be typed with lang.Exprs
# Raises NameError: name 'Expr' is not defined
# Could be some complex interaction with singledispatch
@evalCallable.register
def _(callable: lang.Builtin, callargs, frame: lang.Frame, **kwargs) -> lang.PyLiteral:
    if callable.func is system.EOF:
        name = evaluate(callargs[0], frame)  # type: ignore
        file = frame.getValue(name)
        assert isinstance(file, lang.File), "Invalid File"
        return callable.func(file.iohandler)
    argvals = [evaluate(arg, frame) for arg in callargs]
    return callable.func(*argvals)

@evalCallable.register
def _(callable: lang.Procedure, callargs, frame: lang.Frame, **kwargs) -> None:
    # Assign args to param slots
    for arg, slot in zip(callargs, callable.params):
        argval = evaluate(arg, frame)
        slot.value = argval
    executeStmts(callable.stmts, callable.frame, **kwargs)

@evalCallable.register
def _(callable: lang.Function, callargs, frame: lang.Frame, **kwargs) -> Union[lang.PyLiteral, lang.Object, lang.Array]:
    # Assign args to param slots
    for arg, slot in zip(callargs, callable.params):
        argval = evaluate(arg, frame)
        slot.value = argval
    returnval = executeStmts(callable.stmts, callable.frame, **kwargs)
    assert returnval, f"None returned from {callable}"
    return returnval

def evalAssign(expr: lang.Assign, frame: lang.Frame) -> Union[lang.PyLiteral, lang.Object, lang.Array]:
    value = evaluate(expr.expr, frame)
    """Handles assignment of a value to an Object attribute, Array
    index, or Frame name.
    """
    if isinstance(expr.assignee, lang.GetName):
        frameMap = expr.assignee.frame
        name = str(expr.assignee.name)
        frameMap.setValue(name, value)
    elif isinstance(expr.assignee, lang.GetIndex):
        array = evaluate(expr.assignee.array, frame)
        index = evalIndex(expr.assignee.index, frame)
        array.setValue(index, value)
    elif isinstance(expr.assignee, lang.GetAttr):
        obj = evaluate(expr.assignee.object, frame)
        name = str(expr.assignee.name)
        obj.setValue(name, value)
    else:
        raise builtin.RuntimeError(
            "Invalid Input assignee", token=expr.assignee.token
        )
    return value

@singledispatch
def evaluate(expr, frame, **kwargs):
    """Dispatcher for Expr evaluators."""
    raise TypeError(f"Unexpected expr {expr}")

@evaluate.register
def _(expr: lang.Literal, frame: lang.Frame, **kw) -> lang.PyLiteral:
    return evalLiteral(expr, frame)

@evaluate.register
def _(expr: lang.Unary, frame: lang.Frame, **kw) -> lang.PyLiteral:
    return evalUnary(expr, frame)

@evaluate.register
def _(expr: lang.Binary, frame: lang.Frame, **kw) -> lang.PyLiteral:
    return evalBinary(expr, frame)

@evaluate.register
def _(expr: lang.Assign, frame: lang.Frame, **kw) -> Union[lang.PyLiteral, lang.Object, lang.Array]:
    return evalAssign(expr, frame)

@evaluate.register
def _(expr: lang.GetName, frame: lang.Frame, **kw) -> Union[lang.PyLiteral, lang.Object, lang.Array, lang.Builtin, lang.Callable]:
    value = expr.frame.getValue(str(expr.name))
    assert not isinstance(value, lang.File), "Unexpected File"
    return value

@evaluate.register
def _(expr: lang.GetIndex, frame: lang.Frame, **kw) -> Union[lang.PyLiteral, lang.Object]:
    array = evaluate(expr.array, frame)
    indexes = evalIndex(expr.index, frame)
    return array.getValue(indexes)
    
@evaluate.register
def _(expr: lang.GetAttr, frame: lang.Frame, **kw) -> Union[lang.PyLiteral, lang.Object]:
    obj = evaluate(expr.object, frame)
    return obj.getValue(str(expr.name))
    
@evaluate.register
def _(expr: lang.Call, frame: lang.Frame, **kw) -> Union[None, lang.PyLiteral, lang.Object, lang.Array]:
    callable = evaluate(expr.callable, frame)
    return evalCallable(callable, expr.args, callable.frame)

# Executors

def executeStmts(stmts: lang.Stmts, frame: lang.Frame, **kwargs) -> Union[None, lang.PyLiteral, lang.Object, lang.Array]:
    """Execute a list of statements."""
    for stmt in stmts:
        if isinstance(stmt, lang.Return):
            return execReturn(stmt, frame, **kwargs)
        else:
            execute(stmt, frame, **kwargs)
    return None

def execReturn(stmt: lang.Return, frame: lang.Frame, **kwargs) -> Union[lang.PyLiteral, lang.Object, lang.Array]:
    """Return statements should be explicitly checked for and the
    return value passed back. They should not be dispatched through
    execute().
    """
    return evaluate(stmt.expr, frame, **kwargs)



@singledispatch
def execute(stmt: lang.Stmt, frame: lang.Frame, **kwargs) -> None:
    """Dispatcher for statement executors."""
    raise TypeError(f"Invalid Stmt {stmt}")

@execute.register
def _(stmt: lang.Return, frame: lang.Frame, **kwargs) -> None:
    raise TypeError("Return Stmts should not be dispatched from execute()")
    
@execute.register
def _(stmt: lang.Output, frame: lang.Frame, *, output: function, **kwargs) -> None:
    for expr in stmt.exprs:
        value = evaluate(expr, frame)
        if type(value) is bool:
            value = str(value).upper()
        output(str(value), end='')
    output('')  # Add \n

@execute.register
def _(stmt: lang.Input, frame: lang.Frame, **kwargs) -> None:
    if isinstance(stmt.key, lang.GetName):
        stmt.key.frame.setValue(str(stmt.key.name), input())
    elif isinstance(stmt.key, lang.GetIndex):
        array = evaluate(stmt.key.array, frame)
        index = evalIndex(stmt.key.index, frame)
        array.setValue(index, input())
    elif isinstance(stmt.key, lang.GetAttr):
        obj = evaluate(stmt.key.object, frame)
        name = str(stmt.key.name)
        obj.setValue(name, input())
    raise builtin.RuntimeError(
        "Invalid Input assignee", token=stmt.key.token
    )

@execute.register
def _(stmt: lang.Case, frame: lang.Frame, **kwargs) -> None:
    condValue = evaluate(stmt.cond, frame)
    for caseValue, stmts in stmt.stmtMap.items():
        if evaluate(caseValue, frame) == condValue:
            executeStmts(stmts, frame, **kwargs)
            break
    else:  # for loop completed normally, i.e. no matching cases
        if stmt.fallback:
            executeStmts(stmt.fallback, frame, **kwargs)

@execute.register
def _(stmt: lang.If, frame: lang.Frame, **kwargs) -> None:
    condValue = evaluate(stmt.cond, frame)
    for caseValue, stmts in stmt.stmtMap.items():
        if evaluate(caseValue, frame) == condValue:
            executeStmts(stmts, frame, **kwargs)
            break
    else:  # for loop completed normally, i.e. no matching cases
        if stmt.fallback:
            executeStmts(stmt.fallback, frame, **kwargs)
    
@execute.register
def _(stmt: lang.While, frame: lang.Frame, **kwargs) -> None:
    if stmt.init:
        evaluate(stmt.init, frame, **kwargs)
    while evaluate(stmt.cond, frame) is True:
        executeStmts(stmt.stmts, frame, **kwargs)
    
@execute.register
def _(stmt: lang.Repeat, frame: lang.Frame, **kwargs) -> None:
    executeStmts(stmt.stmts, frame)
    while evaluate(stmt.cond, frame) is False:
        executeStmts(stmt.stmts, frame)

@execute.register
def _(stmt: lang.OpenFile, frame: lang.Frame, **kwargs) -> None:
    filename = evaluate(stmt.filename, frame)
    undeclaredElseError(
        frame, filename, "File already opened", 
        token=stmt.filename.token
    )
    frame.declare(filename, 'FILE')
    frame.setValue(
        filename,
        lang.File(
            filename,
            stmt.mode,
            open(filename, stmt.mode[0].lower())
        ),
    )
    
@execute.register
def _(stmt: lang.ReadFile, frame: lang.Frame, **kwargs) -> None:
    filename = evaluate(stmt.filename, frame)
    declaredElseError(
        frame, filename, "File not open", token=stmt.filename.token
    )
    file = frame.getValue(filename)
    assert isinstance(file, lang.File), f"Invalid file {file}"
    expectTypeElseError(
        frame.getType(filename), 'FILE', token=stmt.filename.token
    )
    expectTypeElseError(file.mode, 'READ', token=stmt.filename.token)
    varname = evaluate(stmt.target, frame)
    assert isinstance(varname, str), f"Expected str, got {varname!r}"
    declaredElseError(frame, varname, token=stmt.target.token)
    # TODO: Catch and handle Python file io errors
    line = file.iohandler.readline().rstrip()
    # TODO: Type conversion
    frame.setValue(varname, line)
    
@execute.register
def _(stmt: lang.WriteFile, frame: lang.Frame, **kwargs) -> None:
    filename = evaluate(stmt.filename, frame)
    declaredElseError(
        frame, filename, "File not open", token=stmt.filename.token
    )
    file = frame.getValue(filename)
    assert isinstance(file, lang.File), f"Invalid file {file}"
    expectTypeElseError(
        frame.getType(filename), 'FILE', token=stmt.filename.token
    )
    expectTypeElseError(
        file.mode, 'WRITE', 'APPEND', token=stmt.filename.token
    )
    writedata = evaluate(stmt.data, frame)
    if type(writedata) is bool:
        writedata = str(writedata).upper()
    else:
        writedata = str(writedata)
    # Move pointer to next line after writing
    if not writedata.endswith('\n'):
        writedata += '\n'
    # TODO: Catch and handle Python file io errors
    file.iohandler.write(writedata)
    
@execute.register
def _(stmt: lang.CloseFile, frame: lang.Frame, **kwargs) -> None:
    filename = evaluate(stmt.filename, frame)
    declaredElseError(
        frame, filename, "File not open", token=stmt.filename.token
    )
    file = frame.getValue(filename)
    assert isinstance(file, lang.File), f"Invalid file {file}"
    expectTypeElseError(
        frame.getType(filename), 'FILE', token=stmt.filename.token
    )
    file.iohandler.close()
    frame.delete(filename)
    
@execute.register
def _(stmt: lang.CallStmt, frame: lang.Frame, **kwargs) -> None:
    callable = evaluate(stmt.expr.callable, frame)
    evalCallable(callable, stmt.expr.args, callable.frame, **kwargs)
    
@execute.register
def _(stmt: lang.AssignStmt, frame: lang.Frame, **kwargs) -> None:
    evaluate(stmt.expr, frame, **kwargs)
    
@execute.register
def _(stmt: lang.DeclareStmt, frame: lang.Frame, **kwargs) -> None:
    pass

@execute.register
def _(stmt: lang.TypeStmt, frame: lang.Frame, **kwargs) -> None:
    pass

@execute.register
def _(stmt: lang.ProcedureStmt, frame: lang.Frame, **kwargs) -> None:
    pass

@execute.register
def _(stmt: lang.FunctionStmt, frame: lang.Frame, **kwargs) -> None:
    pass
