"""interpreter

execute(frame: Frame, statements: list) -> None
    Interprets and executes a list of statements
"""

from typing import (
    Callable as function,
    Optional,
    Union,
)
from functools import singledispatch
from dataclasses import dataclass, field

from . import (builtin, lang, system)

# ----------------------------------------------------------------------

# Helper functions


def expectTypeElseError(exprmode: str,
                        *expected: str,
                        errmsg: str = "Expected",
                        token: lang.Token) -> None:
    """Takes in a type, followed by one or more expected types.
    Raises an error if the given type is not in the expected types.
    """
    if not exprmode in expected:
        raise builtin.RuntimeError(f"{errmsg} {expected}", token=token)


def declaredElseError(env: lang.Environment, name: lang.NameKey,
                      errmsg: str = "Undeclared",
                      token: Optional[lang.Token] = None) -> None:
    """Takes in an environment and a name.
    Raises an error if the name is not declared in the environment's
    frame.
    """
    if not env.frame.has(name):
        raise builtin.RuntimeError(errmsg, token)


def undeclaredElseError(env: lang.Environment,
                        name: lang.NameKey,
                        errmsg="Already declared",
                        token: Optional[lang.Token] = None) -> None:
    """Takes in an environment and a name.
    Raises an error if the name is already declared in the environment's frame.
    """
    if env.frame.has(name):
        raise builtin.RuntimeError(errmsg, token)


@dataclass
class Interpreter:
    """Interprets a list of statements with a given environment."""
    env: lang.Environment
    statements: lang.Stmts
    outputHandler: function = field(default=print, init=False)

    def registerOutputHandler(self, handler: function) -> None:
        """Register handler as the function to use to handle any output
        from the executed statements.
        The default handler is Python's print().
        """
        self.outputHandler = handler  # type: ignore

    def interpret(self) -> None:
        executeStmts(self.statements, self.env,
                     output=self.outputHandler)


# Evaluators
# Evaluation functions return the evaluated value of Exprs.


def evalIndex(indexExpr: lang.Indices, env: lang.Environment) -> lang.IndexKey:
    """Returns the evaluated value of an Array's index."""
    indexes: lang.IndexKey = tuple()
    for expr in indexExpr:
        index = evaluate(expr, env)
        indexes += (index, )
    return indexes


def evalLiteral(literal: lang.Literal, env: lang.Environment) -> lang.PyLiteral:
    return literal.value


def evalUnary(expr: lang.Unary, env: lang.Environment) -> lang.PyLiteral:
    rightval = evaluate(expr.right, env)
    return expr.oper(rightval)


def evalBinary(expr: lang.Binary, env: lang.Environment) -> lang.PyLiteral:
    leftval = evaluate(expr.left, env)
    rightval = evaluate(expr.right, env)
    return expr.oper(leftval, rightval)


@singledispatch
def evalCallable(callable, callargs, env, **kwargs):
    """Returns the evaluated value of a Builtin/Callable."""
    raise TypeError(f"{type(callable)} passed in evalCallable")


# BUG: callargs can't be typed with lang.Exprs
# Raises NameError: name 'Expr' is not defined
# Could be some complex interaction with singledispatch
@evalCallable.register
def _(callable: lang.Builtin, callargs, env: lang.Environment,
      **kwargs) -> lang.PyLiteral:
    if callable.func is system.EOF:
        name = evaluate(callargs[0], env)  # type: ignore
        file = env.frame.getValue(name)
        assert isinstance(file, lang.File), "Invalid File"
        return callable.func(file.iohandler)
    argvals = [evaluate(arg, env) for arg in callargs]
    return callable.func(*argvals)


@evalCallable.register
def _(callable: lang.Procedure, callargs, env: lang.Environment, **kwargs) -> None:
    # Assign args to param slots
    for arg, slot in zip(callargs, callable.params):
        argval = evaluate(arg, env)
        slot.value = argval
    executeStmts(callable.stmts, callable.env, **kwargs)


@evalCallable.register
def _(callable: lang.Function, callargs, env: lang.Environment,
      **kwargs) -> lang.Assignable:
    # Assign args to param slots
    for arg, slot in zip(callargs, callable.params):
        argval = evaluate(arg, env)
        slot.value = argval
    returnVal = executeStmts(callable.stmts, callable.env, **kwargs)
    assert returnVal, f"None returned from {callable}"
    return returnVal


def evalAssign(expr: lang.Assign, env: lang.Environment) -> lang.Assignable:
    """Handles assignment of a value to an Object attribute, Array
    index, or Frame name.
    """
    value = evaluate(expr.expr, env)
    if isinstance(expr.assignee, lang.GetName):
        frameMap = expr.assignee.frame
        name = str(expr.assignee.name)
        frameMap.setValue(name, value)
    elif isinstance(expr.assignee, lang.GetIndex):
        array = evaluate(expr.assignee.array, env)
        index = evalIndex(expr.assignee.index, env)
        array.setValue(index, value)
    elif isinstance(expr.assignee, lang.GetAttr):
        obj = evaluate(expr.assignee.object, env)
        name = str(expr.assignee.name)
        obj.setValue(name, value)
    else:
        raise builtin.RuntimeError("Invalid Input assignee",
                                   token=expr.assignee.token)
    return value


@singledispatch
def evaluate(expr, env, **kwargs):
    """Dispatcher for Expr evaluators."""
    raise TypeError(f"Unexpected expr {expr}")


@evaluate.register
def _(expr: lang.Literal, env: lang.Environment, **kw) -> lang.PyLiteral:
    return evalLiteral(expr, env)


@evaluate.register
def _(expr: lang.Unary, env: lang.Environment, **kw) -> lang.PyLiteral:
    return evalUnary(expr, env)


@evaluate.register
def _(expr: lang.Binary, env: lang.Environment, **kw) -> lang.PyLiteral:
    return evalBinary(expr, env)


@evaluate.register
def _(expr: lang.Assign, env: lang.Environment, **kw) -> lang.Assignable:
    return evalAssign(expr, env)


@evaluate.register
def _(
    expr: lang.GetName, env: lang.Environment, **kw
) -> Union[lang.Assignable, lang.Callable]:
    value = expr.frame.getValue(str(expr.name))
    # mypy can't type-check Non-Files
    if (isinstance(value, bool)
            or isinstance(value, int)
            or isinstance(value, float)
            or isinstance(value, str)
            or isinstance(value, lang.Container)
            or isinstance(value, lang.Callable)):
        return value
    raise RuntimeError(f"{value}: Unexpected File")


@evaluate.register
def _(expr: lang.GetIndex, env: lang.Environment,
      **kw) -> Union[lang.PyLiteral, lang.Object]:
    array = evaluate(expr.array, env)
    indexes = evalIndex(expr.index, env)
    return array.getValue(indexes)


@evaluate.register
def _(expr: lang.GetAttr, env: lang.Environment,
      **kw) -> lang.Assignable:
    obj = evaluate(expr.object, env)
    return obj.getValue(str(expr.name))


@evaluate.register
def _(expr: lang.Call, env: lang.Environment,
      **kw) -> Optional[lang.Assignable]:
    callable = evaluate(expr.callable, env)
    returnVal = evalCallable(callable, expr.args, callable.env)
    return returnVal


# Executors


def executeStmts(
        stmts: lang.Stmts, env: lang.Environment,
        **kwargs) -> Optional[lang.Assignable]:
    """Execute a list of statements."""
    for stmt in stmts:
        if isinstance(stmt, lang.Return):
            return execReturn(stmt, env, **kwargs)
        else:
            returnVal = execute(stmt, env, **kwargs)
            if returnVal:
                return returnVal
    return None


def execReturn(stmt: lang.Return, env: lang.Environment,
               **kwargs) -> lang.Assignable:
    """Return statements should be explicitly checked for and the
    return value passed back. They should not be dispatched through
    execute().
    """
    return evaluate(stmt.expr, env, **kwargs)


@singledispatch
def execute(stmt: lang.Stmt, env: lang.Environment, **kwargs):
    """Dispatcher for statement executors."""
    raise TypeError(f"Invalid Stmt {stmt}")


@execute.register
def _(stmt: lang.Return, env: lang.Environment, **kwargs) -> None:
    raise TypeError("Return Stmts should not be dispatched from execute()")


@execute.register
def _(stmt: lang.Output, env: lang.Environment, *, output: function,
      **kwargs) -> None:
    for expr in stmt.exprs:
        value = evaluate(expr, env)
        if type(value) is bool:
            value = str(value).upper()
        output(str(value), end='')
    output('')  # Add \n


@execute.register
def _(stmt: lang.Input, env: lang.Environment, **kwargs) -> None:
    if isinstance(stmt.key, lang.GetName):
        stmt.key.frame.setValue(str(stmt.key.name), input())
    elif isinstance(stmt.key, lang.GetIndex):
        array = evaluate(stmt.key.array, env)
        index = evalIndex(stmt.key.index, env)
        array.setValue(index, input())
    elif isinstance(stmt.key, lang.GetAttr):
        obj = evaluate(stmt.key.object, env)
        name = str(stmt.key.name)
        obj.setValue(name, input())
    raise builtin.RuntimeError("Invalid Input assignee",
                               token=stmt.key.token)


@execute.register
def _(stmt: lang.Conditional, env: lang.Environment,
      **kwargs) -> Optional[lang.Assignable]:
    condValue = evaluate(stmt.cond, env)
    for caseValue, stmts in stmt.cases.items():
        if evaluate(caseValue, env) == condValue:
            return executeStmts(stmts, env, **kwargs)
    else:  # for loop completed normally, i.e. no matching cases
        if stmt.fallback:
            return executeStmts(stmt.fallback, env, **kwargs)
    return None


@execute.register
def _(stmt: lang.While, env: lang.Environment,
      **kwargs) -> Optional[lang.Assignable]:
    if stmt.init:
        evaluate(stmt.init, env, **kwargs)
    while evaluate(stmt.cond, env) is True:
        returnVal = executeStmts(stmt.stmts, env, **kwargs)
        if returnVal:
            return returnVal
    return None


@execute.register
def _(stmt: lang.Repeat, env: lang.Environment,
      **kwargs) -> Optional[lang.Assignable]:
    executeStmts(stmt.stmts, env)
    while evaluate(stmt.cond, env) is False:
        returnVal = executeStmts(stmt.stmts, env)
        if returnVal:
            return returnVal
    return None


@execute.register
def _(stmt: lang.OpenFile, env: lang.Environment, **kwargs) -> None:
    filename = evaluate(stmt.filename, env)
    undeclaredElseError(env, filename, "File already opened",
                        token=stmt.filename.token)
    env.frame.declare(filename, env.types.cloneType('FILE'))
    env.frame.setValue(filename,
                       lang.File(filename,
                                 stmt.mode,
                                 open(filename, stmt.mode[0].lower())))


@execute.register
def _(stmt: lang.ReadFile, env: lang.Environment, **kwargs) -> None:
    filename = evaluate(stmt.filename, env)
    declaredElseError(env, filename, "File not open",
                      token=stmt.filename.token)
    file = env.frame.getValue(filename)
    assert isinstance(file, lang.File), f"Invalid file {file}"
    expectTypeElseError(env.frame.getType(filename), 'FILE',
                        token=stmt.filename.token)
    expectTypeElseError(file.mode, 'READ', token=stmt.filename.token)
    varname = evaluate(stmt.target, env)
    assert isinstance(varname, str), f"Expected str, got {varname!r}"
    declaredElseError(env, varname, token=stmt.target.token)
    # TODO: Catch and handle Python file io errors
    line = file.iohandler.readline().rstrip()
    # TODO: Type conversion
    env.frame.setValue(varname, line)


@execute.register
def _(stmt: lang.WriteFile, env: lang.Environment, **kwargs) -> None:
    filename = evaluate(stmt.filename, env)
    declaredElseError(env, filename, "File not open",
                      token=stmt.filename.token)
    file = env.frame.getValue(filename)
    assert isinstance(file, lang.File), f"Invalid file {file}"
    expectTypeElseError(env.frame.getType(filename), 'FILE',
                        token=stmt.filename.token)
    expectTypeElseError(file.mode, 'WRITE', 'APPEND',
                        token=stmt.filename.token)
    writedata = evaluate(stmt.data, env)
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
def _(stmt: lang.CloseFile, env: lang.Environment, **kwargs) -> None:
    filename = evaluate(stmt.filename, env)
    declaredElseError(env, filename, "File not open",
                      token=stmt.filename.token)
    file = env.frame.getValue(filename)
    assert isinstance(file, lang.File), f"Invalid file {file}"
    expectTypeElseError(env.frame.getType(filename), 'FILE',
                        token=stmt.filename.token)
    file.iohandler.close()
    env.frame.delete(filename)


@execute.register
def _(stmt: lang.CallStmt, env: lang.Environment, **kwargs) -> None:
    callable = evaluate(stmt.expr.callable, env)
    evalCallable(callable, stmt.expr.args, callable.env, **kwargs)


@execute.register
def _(stmt: lang.AssignStmt, env: lang.Environment, **kwargs) -> None:
    evaluate(stmt.expr, env, **kwargs)


@execute.register
def _(stmt: lang.DeclareStmt, env: lang.Environment, **kwargs) -> None:
    pass


@execute.register
def _(stmt: lang.TypeStmt, env: lang.Environment, **kwargs) -> None:
    pass


@execute.register
def _(stmt: lang.ProcedureStmt, env: lang.Environment, **kwargs) -> None:
    pass


@execute.register
def _(stmt: lang.FunctionStmt, env: lang.Environment, **kwargs) -> None:
    pass
