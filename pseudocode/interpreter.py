from typing import Optional, Iterable, Tuple, Callable as function

from . import builtin, lang, system



# Helper functions

def expectTypeElseError(
    exprmode: str,
    expected: str,
    errmsg: str="Expected",
    token: lang.Token=None,
) -> None:
    if type(expected) is str:
        expected = (expected,)
    if not exprmode in expected:
        if not token: token = exprmode
        raise builtin.RuntimeError(f"{errmsg} {expected}", token)

def declaredElseError(
    frame: lang.Frame,
    name: lang.Varname,
    errmsg: str="Undeclared",
    token: lang.Token=None,
) -> None:
    if not frame.has(name):
        raise builtin.RuntimeError(errmsg, token)

def undeclaredElseError(
    frame: lang.Frame,
    name: lang.Varname,
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
        self.outputHandler = handler

    def interpret(self) -> None:
        executeStmts(
            self.frame,
            self.statements,
            output=self.outputHandler,
        )



# Evaluators

def evalIndex(
    frame: lang.Frame,
    indexes: Iterable[tuple],
) -> Tuple[int]:
    return tuple((
        evaluate(frame, expr) for expr in indexes
    ))

def evalLiteral(
    frame: lang.Frame,
    literal: lang.Literal,
) -> lang.Lit:
    return literal.value

def evalUnary(frame: lang.Frame, expr: lang.Unary) -> lang.Lit:
    rightval = evaluate(frame, expr.right)
    return expr.oper(rightval)

def evalBinary(frame: lang.Frame, expr: lang.Binary) -> lang.Lit:
    leftval = evaluate(frame, expr.left)
    rightval = evaluate(frame, expr.right)
    return expr.oper(leftval, rightval)

def evalGet(frame: lang.Frame, expr: lang.Get) -> lang.Val:
    # Frame should have been inserted in resolver
    # So ignore the frame that is passed here
    obj = expr.frame
    # evaluate obj until object is retrieved
    if isinstance(obj, lang.Expr):
        obj = evaluate(frame, obj)
    if not isinstance(obj, lang.Object):
        raise builtin.RuntimeError("Invalid object", expr.frame.token())
    name = expr.name
    if isinstance(obj, lang.Array):
        name = evalIndex(frame, expr.name)
    return obj.getValue(name)

def evalCall(frame: lang.Frame, expr: lang.Call, **kwargs) -> lang.Val:
    callable = evalGet(frame, expr.callable)
    if isinstance(callable, lang.Builtin):
        if callable.func is system.EOF:
            name = evaluate(frame, expr.args[0])
            file = frame.getValue(name)
            return callable.func(file.iohandler)
        argvals = [evaluate(frame, arg) for arg in expr.args]
        return callable.func(*argvals)
    elif isinstance(callable, lang.Callable):
        # Assign args to param slots
        for arg, slot in zip(expr.args, callable.params):
            argval = evaluate(frame, arg)
            slot.value = argval
        for stmt in callable.stmts:
            returnval = execute(callable.frame, stmt, **kwargs)
            if returnval is not None:
                return returnval

def evalAssign(frame: lang.Frame, expr: lang.Assign) -> None:
    value = evaluate(frame, expr.expr)
    obj = expr.assignee.frame
    if type(obj) in (lang.Get, lang.Call):
        obj = evaluate(frame, obj)
    name = expr.name
    if type(obj) in (lang.Array,):
        name = evalIndex(frame, expr.name)
    obj.setValue(name, value)

def evaluate(
    frame: lang.Frame,
    expr: lang.Expr,
    **kwargs,
) -> Optional[lang.Val]:
    if isinstance(expr, lang.Literal):
        return evalLiteral(frame, expr)
    if isinstance(expr, lang.Unary):
        return evalUnary(frame, expr)
    if isinstance(expr, lang.Binary):
        return evalBinary(frame, expr)
    if isinstance(expr, lang.Assign):
        return evalAssign(frame, expr)
    if isinstance(expr, lang.Get):
        return evalGet(frame, expr)
    if isinstance(expr, lang.Call):
        return evalCall(frame, expr)
    else:
        raise TypeError(f"Unexpected expr {expr}")

# Executors

def executeStmts(
    frame: lang.Frame,
    stmts: Iterable[lang.Stmt],
    *args,
    **kwargs,
) -> Optional[lang.Val]:
    for stmt in stmts:
        returnval = execute(frame, stmt, *args, **kwargs)
        if returnval is not None:
            return returnval

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
    name = stmt.name
    frame.setValue(name, input())

def execCase(
    frame: lang.Frame,
    stmt: lang.Conditional,
    **kwargs,
) -> None:
    cond = evaluate(frame, stmt.cond)
    if cond in stmt.stmtMap:
        execute(frame, stmt.stmtMap[cond], **kwargs)
    elif stmt.fallback:
        execute(frame, stmt.fallback, **kwargs)

def execIf(
    frame: lang.Frame,
    stmt: lang.Conditional,
    **kwargs,
) -> None:
    if evaluate(frame, stmt.cond):
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
    while evaluate(frame, stmt) is False:
        executeStmts(frame, stmt.stmts)

def execFile(
    frame: lang.Frame,
    stmt: lang.FileAction,
    **kwargs,
) -> None:
    name = evalLiteral(frame, stmt.name)
    if stmt.action == 'open':
        undeclaredElseError(
            frame, name, "File already opened", stmt.name.token()
        )
        frame.declare(name, 'FILE')
        file = lang.File(name, stmt.mode, open(name, stmt.mode[0].lower()))
        frame.setValue(name, file)
    elif stmt.action == 'read':
        declaredElseError(
            frame, name, "File not open", stmt.name.token()
        )
        file = frame.getValue(name)
        expectTypeElseError(
            frame.getType(name), 'FILE', stmt.name.token()
        )
        expectTypeElseError(file.mode, 'READ', stmt.name.token())
        varname = evaluate(frame, stmt.data)
        declaredElseError(frame, varname, stmt.data.token())
        # TODO: Catch and handle Python file io errors
        line = file.iohandler.readline().rstrip()
        # TODO: Type conversion
        frame.setValue(varname, line)
    elif stmt.action == 'write':
        declaredElseError(
            frame, name, "File not open", stmt.name.token()
        )
        file = frame.getValue(name)
        expectTypeElseError(
            frame.getType(name), 'FILE', stmt.name.token()
        )
        expectTypeElseError(
            file.mode, ('WRITE', 'APPEND'), stmt.name.token()
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
    elif stmt.action == 'close':
        declaredElseError(
            frame, name, "File not open", stmt.name.token()
        )
        file = frame.getValue(name)
        expectTypeElseError(
            frame.getType(name), 'FILE', stmt.name.token()
        )
        file.iohandler.close()
        frame.delete(name)

def execCall(
    frame: lang.Frame,
    stmt: lang.ExprStmt,
    **kwargs,
) -> None:
    evaluate(frame, stmt.expr, **kwargs)

def execAssign(
    frame: lang.Frame,
    stmt: lang.ExprStmt,
    **kwargs,
) -> None:
    evaluate(frame, stmt.expr, **kwargs)

def execReturn(
    frame: lang.Frame,
    stmt: lang.ExprStmt,
    **kwargs,
) -> None:
    return evaluate(frame, stmt.expr, **kwargs)



def execute(
    frame: lang.Frame,
    stmt: lang.Stmt,
    *args,
    **kwargs,
) -> Optional[lang.Val]:
    if stmt.rule == 'output':
        execOutput(frame, stmt, **kwargs)
    if stmt.rule == 'input':
        execInput(frame, stmt, **kwargs)
    if stmt.rule == 'case':
        execCase(frame, stmt, **kwargs)
    if stmt.rule == 'if':
        execIf(frame, stmt, **kwargs)
    if stmt.rule == 'while':
        execWhile(frame, stmt, **kwargs)
    if stmt.rule == 'repeat':
        execRepeat(frame, stmt, **kwargs)
    if stmt.rule == 'file':
        execFile(frame, stmt, **kwargs)
    if stmt.rule == 'call':
        execCall(frame, stmt, **kwargs)
    if stmt.rule == 'assign':
        execAssign(frame, stmt, **kwargs)
    if stmt.rule == 'return':
        return execReturn(frame, stmt, **kwargs)
    if stmt.rule in ('declare', 'procedure', 'function'):
        pass
