###############################################################################
"""resolver

verify(statements: list, frame: Frame) -> None
    Resolves expressions in statements, declares variables and types
    in the list of statements
"""

from typing import Optional, Union
from typing import Iterable, Iterator
from typing import Tuple
from functools import singledispatch
from dataclasses import dataclass
from itertools import product

from . import builtin, lang

# **********************************************************************

# Resolver helper functions


def expectTypeElseError(exprtype: lang.Type, *expected: lang.Type,
                        token: lang.Token) -> None:
    """Takes in a type, followed by one or more expected types.
    Raises an error if the given type is not in the expected types.
    """
    if exprtype not in expected:
        # Stringify expected types
        typesStr = f"({', '.join(expected)})"
        raise builtin.LogicError(f"Expected {typesStr}, is {exprtype}", token)


def rangeProduct(indexes: lang.IndexRanges) -> Iterator:
    """Takes an iterable of (start, end) tuple pairs.
    Returns an iterator for cartesian product of indexes.
    """
    ranges = [range(start, end + 1) for (start, end) in indexes]
    return product(*ranges)


def resolveName(unresolved: lang.UnresolvedName,
                frame: lang.Frame) -> lang.GetName:
    """Resolves GetName for the UnresolvedName."""
    exprFrame = frame.lookup(str(unresolved.name))
    if exprFrame is None:
        raise builtin.LogicError("Undeclared", unresolved.token)
    return lang.GetName(exprFrame, unresolved.name)


def resolveNamesInTarget(target: Union[lang.Expr, lang.Stmt],
                         frame: lang.Frame) -> None:
    """Checks the exprOrstmt's slots for UnresolvedName, and replaces
    them with GetNames.
    """
    for attr in target.__slots__:
        expr: lang.Expr = getattr(target, attr)
        if isinstance(expr, lang.UnresolvedName):
            setattr(target, attr, resolveName(expr, frame))


def resolveExprs(exprs: lang.Exprs,
                 frame: lang.Frame) -> Tuple[lang.Expr, ...]:
    """Resolve an iterable of Exprs.
    UnresolvedNames are resolved into GetNames.

    Return: Tuple[Expr, ...]
    """
    newexprs: Tuple[lang.Expr, ...] = tuple()
    for expr in exprs:
        if isinstance(expr, lang.UnresolvedName):
            expr = resolveName(expr, frame)
        resolve(expr, frame)
        newexprs += (expr, )
    return newexprs


def resolveArgsParams(callargs: lang.Args, params: lang.Params,
                      frame: lang.Frame, *, token: lang.Token) -> None:
    """resolveArgsParams() only type-checks the args and stmts of the
    call.
    It does not resolve the callable. This should be carried out first
    (e.g. in a wrapper function) before resolveArgsParams() is invoked.
    """
    if len(callargs) != len(params):
        raise builtin.LogicError(
            f"Expected {len(params)} args, got {len(callargs)}",
            token=token,
        )
    for arg, param in zip(callargs, params):
        # param is a TypedValue slot from either local or frame
        expectTypeElseError(resolve(arg, frame), param.type, token=arg.token)


@dataclass
class Resolver:
    """Resolves a list of statements with the given frame."""
    __slots__ = ('frame', 'statements')
    frame: lang.Frame
    statements: lang.Stmts

    def inspect(self) -> None:
        verifyStmts(self.statements, self.frame)


# Resolver helpers
def declareByref(declare: lang.Declare, frame: lang.Frame) -> None:
    """Declares BYREF variable in the given frame."""
    assert frame.outer, "Declared name in a frame with no outer"
    name: lang.NameKey = str(declare.name)
    expectTypeElseError(declare.type,
                        frame.outer.getType(name),
                        token=declare.token)
    # Reference frame vars in local
    frame.set(name, frame.outer.get(name))


def declareByval(declare: lang.Declare,
                 frame: Union[lang.Frame, lang.ObjectTemplate]) -> None:
    """Declares BYVALUE variable in the given frame."""
    if (isinstance(frame, lang.ObjectTemplate) and declare.type == 'ARRAY'):
        raise builtin.LogicError("ARRAY in TYPE not supported", declare.token)
    name: lang.NameKey = str(declare.name)
    frame.declare(name, declare.type)
    if declare.type == 'ARRAY':
        array = lang.Array(typesys=frame.types,
                           ranges=declare.metadata['size'],
                           type=declare.metadata['type'])
        assert isinstance(frame, lang.Frame), "Frame expected"
        frame.setValue(name, array)


def resolveProcCall(expr: lang.Call, frame: lang.Frame) -> lang.Type:
    """Resolve a procedure call.
    Statement verification should be done in verifyProcedure, not here.
    """
    resolveNamesInTarget(expr, frame)
    assert isinstance(expr.callable, lang.GetName), \
        f"Callable {expr.callable} unresolved"
    callableType = resolve(expr.callable, frame)
    expectTypeElseError(callableType, 'NULL', token=expr.callable.token)
    callFrame = expr.callable.frame
    callable = callFrame.getValue(str(expr.callable.name))
    if not isinstance(callable, lang.Procedure):
        raise builtin.LogicError("Not PROCEDURE", token=expr.callable.token)
    expr.args = resolveExprs(expr.args, frame)
    resolveArgsParams(expr.args, callable.params, frame, token=expr.token)
    return callableType


@singledispatch
def resolve(expr, frame, **kw):
    """Dispatcher for Expr resolvers."""
    raise TypeError(f"No resolver found for {expr}")


@resolve.register
def _(expr: lang.Literal, frame: lang.Frame, **kw) -> lang.Type:
    return expr.type


@resolve.register
def _(expr: lang.Declare,
      frame: Union[lang.Frame, lang.ObjectTemplate],
      *,
      passby: lang.Passby = 'BYVALUE') -> lang.Type:
    """Declare variable in frame with dispatcher."""
    if passby == 'BYVALUE':
        declareByval(expr, frame)
    else:
        assert isinstance(frame, lang.Frame), \
            "Declared BYREF in invalid Frame"
        declareByref(expr, frame)
    return expr.type


@resolve.register
def _(expr: lang.Unary, frame: lang.Frame, **kw) -> lang.Type:
    resolveNamesInTarget(expr, frame)
    rType = resolve(expr.right, frame)
    if expr.oper is builtin.sub:
        expectTypeElseError(rType, *builtin.NUMERIC, token=expr.right.token)
        return rType
    if expr.oper is builtin.NOT:
        expectTypeElseError(rType, 'BOOLEAN', token=expr.right.token)
        return 'BOOLEAN'
    raise ValueError(f"Unexpected oper {expr.oper}")


@resolve.register
def _(expr: lang.Binary, frame: lang.Frame, **kw) -> lang.Type:
    resolveNamesInTarget(expr, frame)
    lType = resolve(expr.left, frame)
    rType = resolve(expr.right, frame)
    if expr.oper in (builtin.AND, builtin.OR):
        expectTypeElseError(lType, 'BOOLEAN', token=expr.left.token)
        expectTypeElseError(rType, 'BOOLEAN', token=expr.right.token)
        return 'BOOLEAN'
    if expr.oper in (builtin.ne, builtin.eq):
        expectTypeElseError(lType, *builtin.EQUATABLE, token=expr.left.token)
        expectTypeElseError(rType, *builtin.EQUATABLE, token=expr.right.token)
        if not ((lType == 'BOOLEAN' and rType == 'BOOLEAN') or
                (lType in builtin.NUMERIC and rType in builtin.NUMERIC)):
            raise builtin.LogicError(
                f"Illegal comparison of {lType} and {rType}",
                token=expr.token,
            )
        return 'BOOLEAN'
    if expr.oper in (builtin.gt, builtin.gte, builtin.lt, builtin.lte):
        expectTypeElseError(lType, *builtin.NUMERIC, token=expr.left.token)
        expectTypeElseError(rType, *builtin.NUMERIC, token=expr.right.token)
        return 'BOOLEAN'
    if expr.oper in (builtin.add, builtin.sub, builtin.mul, builtin.div):
        expectTypeElseError(lType, *builtin.NUMERIC, token=expr.left.token)
        expectTypeElseError(rType, *builtin.NUMERIC, token=expr.right.token)
        if ((expr.oper is not builtin.div) and (lType == rType == 'INTEGER')):
            return 'INTEGER'
        return 'REAL'
    if expr.oper in (builtin.concat, ):
        expectTypeElseError(lType, 'STRING', token=expr.left.token)
        expectTypeElseError(rType, 'STRING', token=expr.right.token)
        return 'STRING'
    raise ValueError("No return for Binary")


@resolve.register
def _(expr: lang.Assign, frame: lang.Frame, **kw) -> lang.Type:
    resolveNamesInTarget(expr, frame)
    assnType = resolve(expr.assignee, frame)
    exprType = resolve(expr.expr, frame)
    expectTypeElseError(exprType, assnType, token=expr.token)
    return assnType


@resolve.register
def _(expr: lang.Call, frame: lang.Frame, **kw) -> lang.Type:
    """Resolve a function call.
    Statement verification should be done in verifyFunction, not here.
    """
    resolveNamesInTarget(expr, frame)
    assert isinstance(expr.callable, lang.GetName), \
        "Unresolved Callable"
    callableType = resolve(expr.callable, frame)
    callFrame = expr.callable.frame
    callable = callFrame.getValue(str(expr.callable.name))
    if not (isinstance(callable, lang.Function)
            or isinstance(callable, lang.Builtin)):
        raise builtin.LogicError("Not FUNCTION", token=expr.callable.token)
    expr.args = resolveExprs(expr.args, frame)
    resolveArgsParams(expr.args, callable.params, frame, token=expr.token)
    return callableType


@resolve.register
def _(expr: lang.GetIndex, frame: lang.Frame, **kw) -> lang.Type:
    """Resolves a GetIndex Expr to return an array element's type"""
    def intsElseError(frame, *indexes):
        for indexExpr in indexes:
            nameType = resolve(indexExpr, frame)
            expectTypeElseError(nameType, 'INTEGER', token=indexExpr.token)

    expr.index = resolveExprs(expr.index, frame)
    # Array indexes must be integer
    intsElseError(frame, *expr.index)
    # Arrays in Objects not yet supported; assume frame
    resolveNamesInTarget(expr, frame)
    assert isinstance(expr.array, lang.GetName), "Array unresolved"
    ## Expect array
    expectTypeElseError(resolve(expr.array, frame), 'ARRAY', token=expr.token)
    array = expr.array.frame.getValue(str(expr.array.name))
    assert (isinstance(array, lang.Array)), "Invalid ARRAY"
    return array.elementType


@resolve.register
def _(expr: lang.GetAttr, frame: lang.Frame, **kw) -> lang.Type:
    """Resolves a GetAttr Expr to return an attribute's type"""
    resolveNamesInTarget(expr, frame)
    assert not isinstance(expr.object, lang.UnresolvedName), \
        "Object unresolved"
    objType = resolve(expr.object, frame)
    # Check objType existence in typesystem
    if not frame.types.has(objType):
        raise builtin.LogicError("Undeclared type", expr.token)
    # Check attribute existence in object template
    obj = frame.types.cloneType(objType).value
    assert isinstance(obj, lang.Object), "Invalid Object"
    if not obj.has(str(expr.name)):
        raise builtin.LogicError("Undeclared attribute", expr.token)
    return obj.getType(str(expr.name))


@resolve.register
def _(expr: lang.GetName, frame: lang.Frame, **kw) -> lang.Type:
    """Returns the type of value that name is mapped to in frame."""
    return expr.frame.getType(str(expr.name))


# Verifier helpers


def transformDeclares(declares: Iterable[lang.Declare], passby: lang.Passby,
                      frame: lang.Frame) -> Tuple[lang.TypedValue, ...]:
    """Takes in a list of Declares. Returns a tuple of TypedValues.
    Used to declare names in a frame/object.
    """
    params: Tuple[lang.TypedValue, ...] = tuple()
    for declaration in declares:
        resolve(declaration, frame, passby=passby)
        params += (frame.get(str(declaration.name)), )
    return params


@singledispatch
def willReturn(stmt) -> bool:
    """Checks if statement is a Return statement, or is guaranteed to return
    a value.

    Returns True if yes, otherwise returns False.
    """
    return False


@willReturn.register
def _(stmt: lang.Conditional) -> bool:
    # If & CASE: If any case statements do not have a return, the statement is
    # not guaranteed to return.
    for stmts in stmt.stmtMap.values():
        if not any(map(willReturn, stmts)):
            return False
    if (not stmt.fallback) or not any(map(willReturn, stmt.fallback)):
        return False
    return True


@willReturn.register
def _(stmt: lang.Loop) -> bool:
    stmtsWillReturn: bool = any(map(willReturn, stmt.stmts))
    return stmtsWillReturn


@willReturn.register
def _(stmt: lang.Return) -> bool:
    return True


# Verifiers


def verifyStmts(stmts: lang.Stmts,
                frame: lang.Frame,
                returnType: Optional[lang.Type] = None) -> None:
    """Verify a list of statements."""
    for stmt in stmts:
        if isinstance(stmt, lang.Return):
            if not returnType:
                raise builtin.LogicError("Unexpected RETURN statement",
                                         token=stmt.expr.token)
            expectTypeElseError(resolve(stmt.expr, frame),
                                returnType,
                                token=stmt.expr.token)
        else:
            verify(stmt, frame, returnType)


@singledispatch
def verify(stmt, frame, returnType):
    """Dispatcher for Stmt verifiers."""
    raise builtin.LogicError("Unexpected statement")


@verify.register
def _(stmt: lang.Output,
      frame: lang.Frame,
      returnType: Optional[lang.Type] = None) -> None:
    stmt.exprs = resolveExprs(stmt.exprs, frame)


@verify.register
def _(stmt: lang.Input,
      frame: lang.Frame,
      returnType: Optional[lang.Type] = None) -> None:
    resolveNamesInTarget(stmt, frame)
    resolve(stmt.key, frame)


@verify.register
def _(stmt: lang.Case,
      frame: lang.Frame,
      returnType: Optional[lang.Type] = None) -> None:
    resolveNamesInTarget(stmt, frame)
    condType = resolve(stmt.cond, frame)
    for caseValue, statements in stmt.stmtMap.items():
        caseType = resolve(caseValue, frame)
        expectTypeElseError(caseType, condType, token=caseValue.token)
        verifyStmts(statements, frame, returnType)
    if stmt.fallback:
        verifyStmts(stmt.fallback, frame, returnType)


@verify.register
def _(stmt: lang.If,
      frame: lang.Frame,
      returnType: Optional[lang.Type] = None) -> None:
    resolveNamesInTarget(stmt, frame)
    condType = resolve(stmt.cond, frame)
    expectTypeElseError(condType, 'BOOLEAN', token=stmt.cond.token)
    for statements in stmt.stmtMap.values():
        verifyStmts(statements, frame, returnType)
    if stmt.fallback:
        verifyStmts(stmt.fallback, frame, returnType)


@verify.register
def _(stmt: lang.Loop,
      frame: lang.Frame,
      returnType: Optional[lang.Type] = None) -> None:
    resolveNamesInTarget(stmt, frame)
    if stmt.init:
        resolve(stmt.init, frame)
    condType = resolve(stmt.cond, frame)
    expectTypeElseError(condType, 'BOOLEAN', token=stmt.cond.token)
    verifyStmts(stmt.stmts, frame, returnType)


@verify.register
def _(stmt: lang.ProcedureStmt,
      frame: lang.Frame,
      returnType: Optional[lang.Type] = None) -> None:
    """Declare a Procedure in the given frame."""
    # Assign procedure in frame first, to make recursive calls work
    frame.declare(str(stmt.name), 'NULL')
    # No UnresolvedNames to resolve

    # Declare parameters
    local = lang.Frame(typesys=frame.types, outer=frame)
    params = transformDeclares(stmt.params, stmt.passby, local)

    # Add procedure definition
    proc = lang.Procedure(local, params, stmt.stmts)
    frame.setValue(str(stmt.name), proc)

    verifyStmts(stmt.stmts, local)


@verify.register
def _(stmt: lang.FunctionStmt,
      frame: lang.Frame,
      returnType: Optional[lang.Type] = None) -> None:
    """Declare a Function in the given frame."""
    # Assign function in frame first, to make recursive calls work
    frame.declare(str(stmt.name), stmt.returnType)
    # No UnresolvedNames to resolve

    # Declare parameters
    local = lang.Frame(typesys=frame.types, outer=frame)
    params = transformDeclares(stmt.params, stmt.passby, local)

    # Add procedure definition
    func = lang.Function(local, params, stmt.stmts)
    frame.setValue(str(stmt.name), func)

    # Check for return statements
    if not any(map(willReturn, stmt.stmts)):
        raise builtin.LogicError("Function does not guarantee a return value",
                                 stmt.name.token)
    verifyStmts(stmt.stmts, local, stmt.returnType)


@verify.register
def _(stmt: lang.FileStmt,
      frame: lang.Frame,
      returnType: Optional[lang.Type] = None) -> None:
    resolveNamesInTarget(stmt, frame)
    expectTypeElseError(resolve(stmt.filename, frame),
                        'STRING',
                        token=stmt.filename.token)


@verify.register
def _(stmt: lang.TypeStmt,
      frame: lang.Frame,
      returnType: Optional[lang.Type] = None) -> None:
    """Declare a custom Type in the given frame's TypeSystem."""
    frame.types.declare(str(stmt.name))
    objTemplate = lang.ObjectTemplate(typesys=frame.types)
    for expr in stmt.exprs:
        resolve(expr, objTemplate)
    frame.types.setTemplate(str(stmt.name), objTemplate)


@verify.register
def _(stmt: lang.CallStmt,
      frame: lang.Frame,
      returnType: Optional[lang.Type] = None) -> None:
    resolveProcCall(stmt.expr, frame)


@verify.register
def _(stmt: lang.AssignStmt,
      frame: lang.Frame,
      returnType: Optional[lang.Type] = None) -> None:
    resolve(stmt.expr, frame)


@verify.register
def _(stmt: lang.DeclareStmt,
      frame: lang.Frame,
      returnType: Optional[lang.Type] = None) -> None:
    resolve(stmt.expr, frame)
