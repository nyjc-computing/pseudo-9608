"""interpreter

execute(frame: Frame, statements: list) -> None
    Interprets and executes a list of statements
"""

from typing import Optional, Union
from typing import Iterable, Callable as function
from typing import overload
from functools import singledispatch
from dataclasses import dataclass, field

from . import builtin, lang, system



# ----------------------------------------------------------------------

# Helper functions

def expectTypeElseError(
    exprmode: str,
    *expected: str,
    errmsg: str="Expected",
    token: lang.Token,
) -> None:
    """Takes in a type, followed by one or more expected types.
    Raises an error if the given type is not in the expected types.
    """
    if not exprmode in expected:
        raise builtin.RuntimeError(f"{errmsg} {expected}", token=token)

def declaredElseError(
    frame: lang.Frame,
    name: lang.NameKey,
    errmsg: str="Undeclared",
    token: lang.Token=None,
) -> None:
    """Takes in a frame and a name.
    Raises an error if the name is not declared in the frame.
    """
    if not frame.has(name):
        raise builtin.RuntimeError(errmsg, token)

def undeclaredElseError(
    frame: lang.Frame,
    name: lang.NameKey,
    errmsg="Already declared",
    token: lang.Token=None,
) -> None:
    """Takes in a frame and a name.
    Raises an error if the name is already declared in the frame.
    """
    if frame.has(name):
        raise builtin.RuntimeError(errmsg, token)



@dataclass
class Interpreter:
    """Interprets a list of statements with a given frame."""
    frame: lang.Frame
    statements: Iterable[lang.Stmt]
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

def evalIndex(
    indexExpr: lang.IndexExpr,
    frame: lang.Frame,
) -> lang.IndexKey:
    """Returns the evaluated value of an Array's index."""
    indexes: lang.IndexKey = tuple()
    for expr in indexExpr:
        index = evaluate(expr, frame)
        assert isinstance(index, int), "Invalid index (must be int)"
        indexes += (index,)
    return indexes

def evalLiteral(
    literal: lang.Literal,
    frame: lang.Frame,
) -> lang.PyLiteral:
    return literal.value

def evalUnary(
    expr: lang.Unary,
    frame: lang.Frame,
) -> lang.PyLiteral:
    rightval = evaluate(expr.right, frame)
    return expr.oper(rightval)

def evalBinary(
    expr: lang.Binary,
    frame: lang.Frame,
) -> lang.PyLiteral:
    leftval = evaluate(expr.left, frame)
    rightval = evaluate(expr.right, frame)
    return expr.oper(leftval, rightval)

def evalGet(
    expr: lang.NameExpr,
    frame: lang.Frame,
    **kwargs,
) -> lang.Value:
    """Returns the name's associated value in a Frame."""
    assert not isinstance(expr, lang.UnresolvedName), "Unexpected UnresolvedName"
    if isinstance(expr, lang.GetName):
        return expr.frame.getValue(str(expr.name))
    if isinstance(expr, lang.GetIndex):
        array = evalGet(expr.array, frame)
        assert isinstance(array, lang.Array), "Invalid Array"
        indexes = evalIndex(expr.index, frame)
        return array.getValue(indexes)
    if isinstance(expr, lang.GetAttr):
        obj = evalGet(expr.object, frame)
        assert isinstance(obj, lang.Object), "Invalid Object"
        return obj.getValue(str(expr.name))
    if isinstance(expr, lang.Call):
        callable = evalGet(expr.callable, frame)
        assert isinstance(callable, lang.Function), \
            f"Invalid Function {callable}"
        return evalCallable(callable, expr.args, frame)

@overload
def evalCallable(
    callable: lang.Builtin,
    args: lang.Args,
    frame: lang.Frame,
    **kwargs,
) -> lang.PyLiteral: ...
@overload
def evalCallable(
    callable: lang.Procedure,
    args: lang.Args,
    frame: lang.Frame,
    **kwargs,
) -> None: ...
@overload
def evalCallable(
    callable: lang.Function,
    args: lang.Args,
    frame: lang.Frame,
    **kwargs,
) -> lang.Value: ...
def evalCallable(
    callable: Union[lang.Builtin, lang.Callable],
    args: lang.Args,
    frame: lang.Frame,
    **kwargs,
):
    """Returns the evaluated value of a Builtin/Callable."""
    if isinstance(callable, lang.Builtin):
        if callable.func is system.EOF:
            name = evaluate(args[0], frame)  # type: ignore
            assert isinstance(name, str), "Invalid name"
            file = frame.getValue(name)
            assert isinstance(file, lang.File), "Invalid File"
            return callable.func(file.iohandler)
        argvals = [evaluate(arg, frame) for arg in args]
        return callable.func(*argvals)
    elif isinstance(callable, lang.Callable):
        # Assign args to param slots
        for arg, slot in zip(args, callable.params):
            argval = evaluate(arg, frame)
            slot.value = argval
        returnval = executeStmts(callable.stmts, frame, **kwargs)
        if isinstance(callable, lang.Function):
            assert returnval, f"None returned from {callable}"
            return returnval

def evalAssign(
    expr: lang.Assign,
    frame: lang.Frame,
) -> lang.Value:
    value = evaluate(expr.expr, frame)
    """Handles assignment of a value to an Object attribute, Array
    index, or Frame name.
    """
    if isinstance(expr.assignee, lang.GetName):
        frameMap = expr.assignee.frame
        name = str(expr.assignee.name)
        frameMap.setValue(name, value)
    elif isinstance(expr.assignee, lang.GetIndex):
        array = evalGet(expr.assignee.array, frame)
        assert isinstance(array, lang.Array), "Invalid Array"
        index = evalIndex(expr.assignee.index, frame)
        array.setValue(index, value)
    elif isinstance(expr.assignee, lang.GetAttr):
        obj = evalGet(expr.assignee.object, frame)
        assert isinstance(obj, lang.Object), "Invalid Object"
        name = str(expr.assignee.name)
        obj.setValue(name, value)
    else:
        raise builtin.RuntimeError(
            "Invalid Input assignee", token=expr.assignee.token
        )
    return value

def evaluate(
    expr: lang.Expr,
    frame: lang.Frame,
    **kwargs,
) -> lang.Value:
    """Dispatcher for Expr evaluators."""
    if isinstance(expr, lang.Literal):
        return evalLiteral(expr, frame)
    if isinstance(expr, lang.Unary):
        return evalUnary(expr, frame)
    if isinstance(expr, lang.Binary):
        return evalBinary(expr, frame)
    if isinstance(expr, lang.Assign):
        return evalAssign(expr, frame)
    if isinstance(expr, lang.GetName):
        return evalGet(expr, frame)
    if isinstance(expr, lang.GetIndex):
        return evalGet(expr, frame)
    if isinstance(expr, lang.GetAttr):
        return evalGet(expr, frame)
    if isinstance(expr, lang.Call):
        callable = evalGet(expr.callable, frame)
        assert (
            isinstance(callable, lang.Builtin)
            or isinstance(callable, lang.Function)
        ), \
            f"Invalid Builtin/Function {callable}"
        return evalCallable(callable, expr.args, frame)
    else:
        raise TypeError(f"Unexpected expr {expr}")

# Executors

def executeStmts(
    stmts: Iterable[lang.Stmt],
    frame: lang.Frame,
    **kwargs,
) -> Optional[lang.Value]:
    """Execute a list of statements."""
    for stmt in stmts:
        if isinstance(stmt, lang.Return):
            return execReturn(stmt, frame, **kwargs)
        else:
            execute(stmt, frame, **kwargs)
    return None

def execOutput(
    stmt: lang.Output,
    frame: lang.Frame,
    *,
    output: function,
    **kwargs,
) -> None:
    for expr in stmt.exprs:
        value = evaluate(expr, frame)
        if type(value) is bool:
            value = str(value).upper()
        output(str(value), end='')
    output('')  # Add \n

def execInput(
    stmt: lang.Input,
    frame: lang.Frame,
    **kwargs,
) -> None:
    if isinstance(stmt.key, lang.GetName):
        stmt.key.frame.setValue(str(stmt.key.name), input())
    elif isinstance(stmt.key, lang.GetIndex):
        array = evalGet(stmt.key.array, frame)
        assert isinstance(array, lang.Array), "Invalid Array"
        index = evalIndex(stmt.key.index, frame)
        array.setValue(index, input())
    elif isinstance(stmt.key, lang.GetAttr):
        obj = evalGet(stmt.key.object, frame)
        assert isinstance(obj, lang.Object), "Invalid Object"
        name = str(stmt.key.name)
        obj.setValue(name, input())
    raise builtin.RuntimeError(
        "Invalid Input assignee", token=stmt.key.token
    )

def execCase(
    stmt: lang.Conditional,
    frame: lang.Frame,
    **kwargs,
) -> None:
    cond = evaluate(stmt.cond, frame)
    assert not isinstance(cond, lang.PseudoValue), \
        f"Invalid cond {cond}"
    if cond in stmt.stmtMap:
        executeStmts(stmt.stmtMap[cond], frame, **kwargs)
    elif stmt.fallback:
        executeStmts(stmt.fallback, frame, **kwargs)

def execIf(
    stmt: lang.Conditional,
    frame: lang.Frame,
    **kwargs,
) -> None:
    cond = evaluate(stmt.cond, frame)
    if cond in stmt.stmtMap:
        executeStmts(stmt.stmtMap[True], frame, **kwargs)
    elif stmt.fallback:
        executeStmts(stmt.fallback, frame, **kwargs)

def execWhile(
    stmt: lang.Loop,
    frame: lang.Frame,
    **kwargs,
) -> None:
    if stmt.init:
        execute(stmt.init, frame, **kwargs)
    while evaluate(stmt.cond, frame) is True:
        executeStmts(stmt.stmts, frame, **kwargs)

def execRepeat(
    stmt: lang.Loop,
    frame: lang.Frame,
    **kwargs,
) -> None:
    executeStmts(stmt.stmts, frame)
    while evaluate(stmt.cond, frame) is False:
        executeStmts(stmt.stmts, frame)

def execOpenFile(
    stmt: lang.OpenFile,
    frame: lang.Frame,
    **kwargs,
) -> None:
    filename = evaluate(stmt.filename, frame)
    assert isinstance(filename, str), f"Invalid filename {filename}"
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

def execReadFile(
    stmt: lang.ReadFile,
    frame: lang.Frame,
    **kwargs,
) -> None:
    filename = evaluate(stmt.filename, frame)
    assert isinstance(filename, str), f"Invalid filename {filename}"
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

def execWriteFile(
    stmt: lang.WriteFile,
    frame: lang.Frame,
    **kwargs,
) -> None:
    filename = evaluate(stmt.filename, frame)
    assert isinstance(filename, str), f"Invalid filename {filename}"
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

def execCloseFile(
    stmt: lang.CloseFile,
    frame: lang.Frame,
    **kwargs,
) -> None:
    filename = evaluate(stmt.filename, frame)
    assert isinstance(filename, str), f"Invalid filename {filename}"
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

def execFile(
    stmt: lang.FileStmt,
    frame: lang.Frame,
    **kwargs,
) -> None:
    """Dispatcher for File executors."""
    if isinstance(stmt, lang.OpenFile):
        execOpenFile(stmt, frame, **kwargs)
    elif isinstance(stmt, lang.ReadFile):
        execReadFile(stmt, frame, **kwargs)
    elif isinstance(stmt, lang.WriteFile):
        execWriteFile(stmt, frame, **kwargs)
    elif isinstance(stmt, lang.CloseFile):
        execCloseFile(stmt, frame, **kwargs)

def execCall(
    stmt: lang.CallStmt,
    frame: lang.Frame,
    **kwargs,
) -> None:
    callable = evalGet(stmt.expr.callable, frame)
    assert isinstance(callable, lang.Procedure), \
        f"Invalid Procedure {callable}"
    evalCallable(callable, stmt.expr.args, frame, **kwargs)

def execAssign(
    stmt: lang.AssignStmt,
    frame: lang.Frame,
    **kwargs,
) -> None:
    evaluate(stmt.expr, frame, **kwargs)

def execReturn(
    stmt: lang.Return,
    frame: lang.Frame,
    **kwargs,
) -> lang.Value:
    return evaluate(stmt.expr, frame, **kwargs)



def execute(
    stmt: lang.Stmt,
    frame: lang.Frame,
    **kwargs,
) -> None:
    """Dispatcher for statement executors."""
    if isinstance(stmt, lang.Output):
        execOutput(stmt, frame, **kwargs)
    elif isinstance(stmt, lang.Input):
        execInput(stmt, frame, **kwargs)
    elif isinstance(stmt, lang.Case):
        execCase(stmt, frame, **kwargs)
    elif isinstance(stmt, lang.If):
        execIf(stmt, frame, **kwargs)
    elif isinstance(stmt, lang.While):
        execWhile(stmt, frame, **kwargs)
    elif isinstance(stmt, lang.Repeat):
        execRepeat(stmt, frame, **kwargs)
    elif (
        isinstance(stmt, lang.OpenFile)
        or isinstance(stmt, lang.ReadFile)
        or isinstance(stmt, lang.WriteFile)
        or isinstance(stmt, lang.CloseFile)
    ):
        execFile(stmt, frame, **kwargs)
    elif isinstance(stmt, lang.CallStmt):
        execCall(stmt, frame, **kwargs)
    elif isinstance(stmt, lang.AssignStmt):
        execAssign(stmt, frame, **kwargs)
    elif isinstance(stmt, lang.Return):
        execReturn(stmt, frame, **kwargs)
    elif (
        isinstance(stmt, lang.DeclareStmt)
        or isinstance(stmt, lang.TypeStmt)
        or isinstance(stmt, lang.ProcedureStmt)
        or isinstance(stmt, lang.FunctionStmt)
    ):
        pass
    else:
        raise ValueError(f"Invalid Stmt {stmt}")
