from typing import Optional, Union
from typing import Iterable, Callable as function
from typing import overload

from . import builtin, lang, system



# ----------------------------------------------------------------------

# Helper functions

def expectTypeElseError(
    exprmode: str,
    *expected: str,
    errmsg: str="Expected",
    token: lang.Token,
) -> None:
    if not exprmode in expected:
        raise builtin.RuntimeError(f"{errmsg} {expected}", token=token)

def declaredElseError(
    frame: lang.Frame,
    name: lang.NameKey,
    errmsg: str="Undeclared",
    token: lang.Token=None,
) -> None:
    if not frame.has(name):
        raise builtin.RuntimeError(errmsg, token)

def undeclaredElseError(
    frame: lang.Frame,
    name: lang.NameKey,
    errmsg="Already declared",
    token: lang.Token=None,
) -> None:
    if frame.has(name):
        raise builtin.RuntimeError(errmsg, token)



class Interpreter:
    """
    Interprets a list of statements with a given frame.
    """
    outputHandler: function = print
    def __init__(
        self,
        frame: lang.Frame,
        statements: Iterable[lang.Stmt],
    ) -> None:
        self.frame = frame
        self.statements = statements

    def registerOutputHandler(self, handler: function) -> None:
        """
        Register handler as the function to use to handle
        any output from the executed statements.
        The default handler is Python's print().
        """
        self.outputHandler = handler  # type: ignore

    def interpret(self) -> None:
        executeStmts(
            self.frame,
            self.statements,
            output=self.outputHandler,
        )



# Evaluators

def evalIndex(
    frame: lang.Frame,
    indexExpr: lang.IndexExpr,
) -> lang.IndexKey:
    indexes: lang.IndexKey = tuple()
    for expr in indexExpr:
        index = evaluate(frame, expr)
        assert isinstance(index, int), "Invalid index (must be int)"
        indexes += (index,)
    return indexes

def evalLiteral(
    frame: lang.Frame,
    literal: lang.Literal,
) -> lang.PyLiteral:
    return literal.value

def evalUnary(frame: lang.Frame, expr: lang.Unary) -> lang.PyLiteral:
    rightval = evaluate(frame, expr.right)
    return expr.oper(rightval)

def evalBinary(frame: lang.Frame, expr: lang.Binary) -> lang.PyLiteral:
    leftval = evaluate(frame, expr.left)
    rightval = evaluate(frame, expr.right)
    return expr.oper(leftval, rightval)

def evalGet(frame: lang.Frame, expr: lang.NameExpr, **kwargs) -> lang.Value:
    assert not isinstance(expr, lang.UnresolvedName), "Unexpected UnresolvedName"
    if isinstance(expr, lang.GetName):
        return expr.frame.getValue(str(expr.name))
    if isinstance(expr, lang.GetIndex):
        array = evalGet(frame, expr.array)
        assert isinstance(array, lang.Array), "Invalid Array"
        indexes = evalIndex(frame, expr.index)
        return array.getValue(indexes)
    if isinstance(expr, lang.GetAttr):
        obj = evalGet(frame, expr.object)
        assert isinstance(obj, lang.Object), "Invalid Object"
        return obj.getValue(str(expr.name))
    if isinstance(expr, lang.Call):
        callable = evalGet(frame, expr.callable)
        assert isinstance(callable, lang.Function), \
            f"Invalid Function {callable}"
        return evalCallable(frame, callable, expr.args)

@overload
def evalCallable(frame: lang.Frame, callable: lang.Builtin, args: lang.Args, **kwargs) -> lang.PyLiteral: ...
@overload
def evalCallable(frame: lang.Frame, callable: lang.Procedure, args: lang.Args, **kwargs) -> None: ...
@overload
def evalCallable(frame: lang.Frame, callable: lang.Function, args: lang.Args, **kwargs) -> lang.Value: ...
def evalCallable(
    frame: lang.Frame,
    callable: Union[lang.Builtin, lang.Callable],
    args: lang.Args,
    **kwargs,
):
    if isinstance(callable, lang.Builtin):
        if callable.func is system.EOF:
            name = evaluate(frame, args[0])  # type: ignore
            assert isinstance(name, str), "Invalid name"
            file = frame.getValue(name)
            assert isinstance(file, lang.File), "Invalid File"
            return callable.func(file.iohandler)
        argvals = [evaluate(frame, arg) for arg in args]
        return callable.func(*argvals)
    elif isinstance(callable, lang.Callable):
        # Assign args to param slots
        for arg, slot in zip(args, callable.params):
            argval = evaluate(frame, arg)
            slot.value = argval
        returnval = executeStmts(frame, callable.stmts, **kwargs)
        if isinstance(callable, lang.Function):
            assert returnval, f"None returned from {callable}"
            return returnval

def evalAssign(frame: lang.Frame, expr: lang.Assign) -> lang.Value:
    value = evaluate(frame, expr.expr)
    if isinstance(expr.assignee, lang.GetName):
        frameMap = expr.assignee.frame
        name = str(expr.assignee.name)
        frameMap.setValue(name, value)
    elif isinstance(expr.assignee, lang.GetIndex):
        array = evalGet(frame, expr.assignee.array)
        assert isinstance(array, lang.Array), "Invalid Array"
        index = evalIndex(frame, expr.assignee.index)
        array.setValue(index, value)
    elif isinstance(expr.assignee, lang.GetAttr):
        obj = evalGet(frame, expr.assignee.object)
        assert isinstance(obj, lang.Object), "Invalid Object"
        name = str(expr.assignee.name)
        obj.setValue(name, value)
    else:
        raise builtin.RuntimeError(
            "Invalid Input assignee", token=expr.assignee.token()
        )
    return value

def evaluate(
    frame: lang.Frame,
    expr: lang.Expr,
    **kwargs,
) -> lang.Value:
    if isinstance(expr, lang.Literal):
        return evalLiteral(frame, expr)
    if isinstance(expr, lang.Unary):
        return evalUnary(frame, expr)
    if isinstance(expr, lang.Binary):
        return evalBinary(frame, expr)
    if isinstance(expr, lang.Assign):
        return evalAssign(frame, expr)
    if isinstance(expr, lang.GetName):
        return evalGet(frame, expr)
    if isinstance(expr, lang.GetIndex):
        return evalGet(frame, expr)
    if isinstance(expr, lang.GetAttr):
        return evalGet(frame, expr)
    if isinstance(expr, lang.Call):
        callable = evalGet(frame, expr.callable)
        assert (
            isinstance(callable, lang.Builtin)
            or isinstance(callable, lang.Function)
        ), \
            f"Invalid Builtin/Function {callable}"
        return evalCallable(frame, callable, expr.args)
    else:
        raise TypeError(f"Unexpected expr {expr}")

# Executors

def executeStmts(
    frame: lang.Frame,
    stmts: Iterable[lang.Stmt],
    **kwargs,
) -> Optional[lang.Value]:
    for stmt in stmts:
        if isinstance(stmt, lang.Return):
            return execReturn(frame, stmt, **kwargs)
        else:
            execute(frame, stmt, **kwargs)
    return None

def execOutput(
    frame: lang.Frame,
    stmt: lang.Output,
    *,
    output: function,
    **kwargs,
) -> None:
    for expr in stmt.exprs:
        value = evaluate(frame, expr)
        if type(value) is bool:
            value = str(value).upper()
        output(str(value), end='')
    output('')  # Add \n

def execInput(
    frame: lang.Frame,
    stmt: lang.Input,
    **kwargs,
) -> None:
    if isinstance(stmt.key, lang.GetName):
        stmt.key.frame.setValue(str(stmt.key.name), input())
    elif isinstance(stmt.key, lang.GetIndex):
        array = evalGet(frame, stmt.key.array)
        assert isinstance(array, lang.Array), "Invalid Array"
        index = evalIndex(frame, stmt.key.index)
        array.setValue(index, input())
    elif isinstance(stmt.key, lang.GetAttr):
        obj = evalGet(frame, stmt.key.object)
        assert isinstance(obj, lang.Object), "Invalid Object"
        name = str(stmt.key.name)
        obj.setValue(name, input())
    raise builtin.RuntimeError(
        "Invalid Input assignee", token=stmt.key.token()
    )

def execCase(
    frame: lang.Frame,
    stmt: lang.Conditional,
    **kwargs,
) -> None:
    cond = evaluate(frame, stmt.cond)
    assert not isinstance(cond, lang.PseudoValue), f"Invalid cond {cond}"
    if cond in stmt.stmtMap:
        executeStmts(frame, stmt.stmtMap[cond], **kwargs)
    elif stmt.fallback:
        executeStmts(frame, stmt.fallback, **kwargs)

def execIf(
    frame: lang.Frame,
    stmt: lang.Conditional,
    **kwargs,
) -> None:
    cond = evaluate(frame, stmt.cond)
    if cond in stmt.stmtMap:
        executeStmts(frame, stmt.stmtMap[True], **kwargs)
    elif stmt.fallback:
        executeStmts(frame, stmt.fallback, **kwargs)

def execWhile(
    frame: lang.Frame,
    stmt: lang.Loop,
    **kwargs,
) -> None:
    if stmt.init:
        execute(frame, stmt.init, **kwargs)
    while evaluate(frame, stmt.cond) is True:
        executeStmts(frame, stmt.stmts, **kwargs)

def execRepeat(
    frame: lang.Frame,
    stmt: lang.Loop,
    **kwargs,
) -> None:
    executeStmts(frame, stmt.stmts)
    while evaluate(frame, stmt.cond) is False:
        executeStmts(frame, stmt.stmts)

def execOpenFile(
    frame: lang.Frame,
    stmt: lang.OpenFile,
    **kwargs,
) -> None:
    filename = evaluate(frame, stmt.filename)
    assert isinstance(filename, str), f"Invalid filename {filename}"
    undeclaredElseError(
        frame, filename, "File already opened", 
        token=stmt.filename.token()
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
    frame: lang.Frame,
    stmt: lang.ReadFile,
    **kwargs,
) -> None:
    filename = evaluate(frame, stmt.filename)
    assert isinstance(filename, str), f"Invalid filename {filename}"
    declaredElseError(
        frame, filename, "File not open", token=stmt.filename.token()
    )
    file = frame.getValue(filename)
    assert isinstance(file, lang.File), f"Invalid file {file}"
    expectTypeElseError(
        frame.getType(filename), 'FILE', token=stmt.filename.token()
    )
    expectTypeElseError(file.mode, 'READ', token=stmt.filename.token())
    varname = evaluate(frame, stmt.target)
    assert isinstance(varname, str), f"Expected str, got {varname!r}"
    declaredElseError(frame, varname, token=stmt.target.token())
    # TODO: Catch and handle Python file io errors
    line = file.iohandler.readline().rstrip()
    # TODO: Type conversion
    frame.setValue(varname, line)

def execWriteFile(
    frame: lang.Frame,
    stmt: lang.WriteFile,
    **kwargs,
) -> None:
    filename = evaluate(frame, stmt.filename)
    assert isinstance(filename, str), f"Invalid filename {filename}"
    declaredElseError(
        frame, filename, "File not open", token=stmt.filename.token()
    )
    file = frame.getValue(filename)
    assert isinstance(file, lang.File), f"Invalid file {file}"
    expectTypeElseError(
        frame.getType(filename), 'FILE', token=stmt.filename.token()
    )
    expectTypeElseError(
        file.mode, 'WRITE', 'APPEND', token=stmt.filename.token()
    )
    writedata = evaluate(frame, stmt.data)
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
    frame: lang.Frame,
    stmt: lang.CloseFile,
    **kwargs,
) -> None:
    filename = evaluate(frame, stmt.filename)
    assert isinstance(filename, str), f"Invalid filename {filename}"
    declaredElseError(
        frame, filename, "File not open", token=stmt.filename.token()
    )
    file = frame.getValue(filename)
    assert isinstance(file, lang.File), f"Invalid file {file}"
    expectTypeElseError(
        frame.getType(filename), 'FILE', token=stmt.filename.token()
    )
    file.iohandler.close()
    frame.delete(filename)

def execFile(
    frame: lang.Frame,
    stmt: lang.FileStmt,
    **kwargs,
) -> None:
    if isinstance(stmt, lang.OpenFile):
        execOpenFile(frame, stmt, **kwargs)
    elif isinstance(stmt, lang.ReadFile):
        execReadFile(frame, stmt, **kwargs)
    elif isinstance(stmt, lang.WriteFile):
        execWriteFile(frame, stmt, **kwargs)
    elif isinstance(stmt, lang.CloseFile):
        execCloseFile(frame, stmt, **kwargs)

def execCall(
    frame: lang.Frame,
    stmt: lang.CallStmt,
    **kwargs,
) -> None:
    callable = evalGet(frame, stmt.expr.callable)
    assert isinstance(callable, lang.Procedure), \
        f"Invalid Procedure {callable}"
    evalCallable(frame, callable, stmt.expr.args, **kwargs)

def execAssign(
    frame: lang.Frame,
    stmt: lang.AssignStmt,
    **kwargs,
) -> None:
    evaluate(frame, stmt.expr, **kwargs)

def execReturn(
    frame: lang.Frame,
    stmt: lang.Return,
    **kwargs,
) -> lang.Value:
    return evaluate(frame, stmt.expr, **kwargs)



def execute(
    frame: lang.Frame,
    stmt: lang.Stmt,
    **kwargs,
) -> None:
    if isinstance(stmt, lang.Output):
        execOutput(frame, stmt, **kwargs)
    elif isinstance(stmt, lang.Input):
        execInput(frame, stmt, **kwargs)
    elif isinstance(stmt, lang.Case):
        execCase(frame, stmt, **kwargs)
    elif isinstance(stmt, lang.If):
        execIf(frame, stmt, **kwargs)
    elif isinstance(stmt, lang.While):
        execWhile(frame, stmt, **kwargs)
    elif isinstance(stmt, lang.Repeat):
        execRepeat(frame, stmt, **kwargs)
    elif (
        isinstance(stmt, lang.OpenFile)
        or isinstance(stmt, lang.ReadFile)
        or isinstance(stmt, lang.WriteFile)
        or isinstance(stmt, lang.CloseFile)
    ):
        execFile(frame, stmt, **kwargs)
    elif isinstance(stmt, lang.CallStmt):
        execCall(frame, stmt, **kwargs)
    elif isinstance(stmt, lang.AssignStmt):
        execAssign(frame, stmt, **kwargs)
    elif isinstance(stmt, lang.Return):
        execReturn(frame, stmt, **kwargs)
    elif (
        isinstance(stmt, lang.DeclareStmt)
        or isinstance(stmt, lang.TypeStmt)
        or isinstance(stmt, lang.ProcedureStmt)
        or isinstance(stmt, lang.FunctionStmt)
    ):
        pass
    else:
        raise ValueError(f"Invalid Stmt {stmt}")
