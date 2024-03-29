###############################################################################
"""resolver

verify(statements: list, frame: Frame) -> None
    Resolves expressions in statements, declares variables and types
    in the list of statements
"""

from dataclasses import dataclass
from functools import singledispatch
from itertools import product
from typing import (
    Iterable,
    Iterator,
    Optional,
    Tuple,
    Union,
)

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
        raise builtin.LogicError(f"Expected {typesStr}, is {exprtype}",
                                 token)


def rangeProduct(indexes: lang.IndexRanges) -> Iterator:
    """Takes an iterable of (start, end) tuple pairs.
    Returns an iterator for cartesian product of indexes.
    """
    ranges = [range(start, end + 1) for (start, end) in indexes]
    return product(*ranges)


def resolveName(unresolved: lang.UnresolvedName,
                env: lang.Environment) -> lang.GetName:
    """Resolves GetName for the UnresolvedName."""
    exprFrame = env.frame.lookup(str(unresolved.name))
    if exprFrame is None:
        raise builtin.LogicError("Undeclared", unresolved.token)
    return lang.GetName(exprFrame, unresolved.name)


def resolveNamesInTarget(target: Union[lang.Expr, lang.Stmt],
                         env: lang.Environment) -> None:
    """Checks the exprOrstmt's slots for UnresolvedName, and replaces
    them with GetNames.
    """
    for attr in target.__slots__:
        expr: lang.Expr = getattr(target, attr)
        if isinstance(expr, lang.UnresolvedName):
            setattr(target, attr, resolveName(expr, env))


def resolveExprs(exprs: lang.Exprs,
                 env: lang.Environment) -> Tuple[lang.Expr, ...]:
    """Resolve an iterable of Exprs.
    UnresolvedNames are resolved into GetNames.

    Return: Tuple[Expr, ...]
    """
    newexprs: Tuple[lang.Expr, ...] = tuple()
    for expr in exprs:
        if isinstance(expr, lang.UnresolvedName):
            expr = resolveName(expr, env)
        resolve(expr, env)
        newexprs += (expr, )
    return newexprs


def resolveArgsParams(callargs: lang.Args, params: lang.Params,
                      env: lang.Environment, *, token: lang.Token) -> None:
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
        # param is a TypedValue slot from either local or global frame
        expectTypeElseError(resolve(arg, env), param.type, token=arg.token)


@dataclass
class Resolver:
    """Resolves a list of statements with the given environment."""
    env: lang.Environment
    statements: lang.Stmts

    def inspect(self) -> None:
        verifyStmts(self.statements, self.env)


# Resolver helpers
def declareByref(declare: lang.Declare, env: lang.Environment) -> None:
    """Declares BYREF variable in the given environment."""
    assert env.frame.outer, "Declared name in a frame with no outer"
    name: lang.NameKey = str(declare.name)
    expectTypeElseError(declare.type,
                        env.frame.outer.getType(name),
                        token=declare.token)
    # Reference global vars in local frame
    env.frame.set(name, env.frame.outer.get(name))


def declareByval(declare: lang.Declare, env: lang.Environment) -> None:
    """Declares BYVALUE variable in the given environment's frame."""
    if (isinstance(env.frame, lang.ObjectTemplate) and declare.type == 'ARRAY'):
        raise builtin.LogicError("ARRAY in TYPE not supported", declare.token)
    name: lang.NameKey = str(declare.name)
    env.frame.declare(name, env.types.cloneType(declare.type))
    if declare.type == 'ARRAY':
        array = lang.Array(ranges=declare.metadata['size'],
                           type=declare.metadata['type'])
        for index in array.rangeProduct(declare.metadata['size']):
            array.declare(index, env.types.cloneType(declare.metadata['type']))

        assert isinstance(env.frame, lang.Frame), "Frame expected"
        env.frame.setValue(name, array)


def resolveProcCall(expr: lang.Call, env: lang.Environment) -> lang.Type:
    """Resolve a procedure call.
    Statement verification should be done in verifyProcedure, not here.
    """
    resolveNamesInTarget(expr, env)
    assert isinstance(expr.callable, lang.GetName), \
        f"Callable {expr.callable} unresolved"
    callableType = resolve(expr.callable, env)
    expectTypeElseError(callableType, 'NULL', token=expr.callable.token)
    callFrame = expr.callable.frame
    callable = callFrame.getValue(str(expr.callable.name))
    if not isinstance(callable, lang.Procedure):
        raise builtin.LogicError("Not PROCEDURE", token=expr.callable.token)
    expr.args = resolveExprs(expr.args, env)
    resolveArgsParams(expr.args, callable.params, env, token=expr.token)
    return callableType


@singledispatch
def resolve(expr, env, **kw):
    """Dispatcher for Expr resolvers."""
    raise TypeError(f"No resolver found for {expr}")


@resolve.register
def _(expr: lang.Literal, env: lang.Environment, **kw) -> lang.Type:
    return expr.type


@resolve.register
def _(expr: lang.Declare, env: lang.Environment,
      *,
      passby: lang.Passby = 'BYVALUE') -> lang.Type:
    """Declare variable in environment's frame with dispatcher."""
    if passby == 'BYVALUE':
        declareByval(expr, env)
    else:
        assert isinstance(env.frame, lang.Frame), \
            "Declared BYREF in invalid Frame"
        declareByref(expr, env)
    return expr.type


@resolve.register
def _(expr: lang.Unary, env: lang.Environment, **kw) -> lang.Type:
    resolveNamesInTarget(expr, env)
    rType = resolve(expr.right, env)
    if expr.oper is builtin.sub:
        expectTypeElseError(rType, *builtin.NUMERIC, token=expr.right.token)
        return rType
    if expr.oper is builtin.NOT:
        expectTypeElseError(rType, 'BOOLEAN', token=expr.right.token)
        return 'BOOLEAN'
    raise ValueError(f"Unexpected oper {expr.oper}")


@resolve.register
def _(expr: lang.Binary, env: lang.Environment, **kw) -> lang.Type:
    resolveNamesInTarget(expr, env)
    lType = resolve(expr.left, env)
    rType = resolve(expr.right, env)
    if expr.oper in (builtin.AND, builtin.OR):
        expectTypeElseError(lType, 'BOOLEAN', token=expr.left.token)
        expectTypeElseError(rType, 'BOOLEAN', token=expr.right.token)
        return 'BOOLEAN'
    if expr.oper in (builtin.ne, builtin.eq):
        expectTypeElseError(lType, *builtin.EQUATABLE, token=expr.left.token)
        expectTypeElseError(rType, *builtin.EQUATABLE, token=expr.right.token)
        if not ((lType == 'BOOLEAN' and rType == 'BOOLEAN')
                or (lType in builtin.NUMERIC and rType in builtin.NUMERIC)):
            raise builtin.LogicError(
                f"Illegal comparison of {lType} and {rType}",
                token=expr.token,
            )
        return 'BOOLEAN'
    if expr.oper in (builtin.gt, builtin.gte, builtin.lt, builtin.lte):
        expectTypeElseError(lType, *builtin.NUMERIC,
                            token=expr.left.token)
        expectTypeElseError(rType, *builtin.NUMERIC,
                            token=expr.right.token)
        return 'BOOLEAN'
    if expr.oper in (builtin.add, builtin.sub, builtin.mul, builtin.div):
        expectTypeElseError(lType, *builtin.NUMERIC,
                            token=expr.left.token)
        expectTypeElseError(rType, *builtin.NUMERIC,
                            token=expr.right.token)
        if ((expr.oper is not builtin.div)
                and (lType == rType == 'INTEGER')):
            return 'INTEGER'
        return 'REAL'
    if expr.oper in (builtin.concat, ):
        expectTypeElseError(lType, 'STRING', token=expr.left.token)
        expectTypeElseError(rType, 'STRING', token=expr.right.token)
        return 'STRING'
    raise ValueError("No return for Binary")


@resolve.register
def _(expr: lang.Assign, env: lang.Environment, **kw) -> lang.Type:
    resolveNamesInTarget(expr, env)
    assnType = resolve(expr.assignee, env)
    exprType = resolve(expr.expr, env)
    expectTypeElseError(exprType, assnType, token=expr.token)
    return assnType


@resolve.register
def _(expr: lang.Call, env: lang.Environment, **kw) -> lang.Type:
    """Resolve a function call.
    Statement verification should be done in verifyFunction, not here.
    """
    resolveNamesInTarget(expr, env)
    assert isinstance(expr.callable, lang.GetName), \
        "Unresolved Callable"
    callableType = resolve(expr.callable, env)
    callFrame = expr.callable.frame
    callable = callFrame.getValue(str(expr.callable.name))
    if not (isinstance(callable, lang.Function)
            or isinstance(callable, lang.Builtin)):
        raise builtin.LogicError("Not FUNCTION", token=expr.callable.token)
    expr.args = resolveExprs(expr.args, env)
    resolveArgsParams(expr.args, callable.params, env, token=expr.token)
    return callableType


@resolve.register
def _(expr: lang.GetIndex, env: lang.Environment, **kw) -> lang.Type:
    """Resolves a GetIndex Expr to return an array element's type"""
    def intsElseError(env: lang.Environment, *indexes):
        for indexExpr in indexes:
            nameType = resolve(indexExpr, env)
            expectTypeElseError(nameType, 'INTEGER', token=indexExpr.token)

    expr.index = resolveExprs(expr.index, env)
    # Array indexes must be integer
    intsElseError(env, *expr.index)
    # Arrays in Objects not yet supported; assume frame
    resolveNamesInTarget(expr, env)
    assert isinstance(expr.array, lang.GetName), "Array unresolved"
    ## Expect array
    expectTypeElseError(resolve(expr.array, env), 'ARRAY', token=expr.token)
    array = expr.array.frame.getValue(str(expr.array.name))
    assert (isinstance(array, lang.Array)), "Invalid ARRAY"
    return array.elementType


@resolve.register
def _(expr: lang.GetAttr, env: lang.Environment, **kw) -> lang.Type:
    """Resolves a GetAttr Expr to return an attribute's type"""
    resolveNamesInTarget(expr, env)
    assert not isinstance(expr.object, lang.UnresolvedName), \
        "Object unresolved"
    objType = resolve(expr.object, env)
    # Check objType existence in typesystem
    if not env.types.has(objType):
        raise builtin.LogicError("Undeclared type", expr.token)
    # Check attribute existence in object template
    obj = env.types.cloneType(objType).value
    assert isinstance(obj, lang.Object), "Invalid Object"
    if not obj.has(str(expr.name)):
        raise builtin.LogicError("Undeclared attribute", expr.token)
    return obj.getType(str(expr.name))


@resolve.register
def _(expr: lang.GetName, env: lang.Environment, **kw) -> lang.Type:
    """Returns the type of value that name is mapped to in
    environment's frame.
    """
    return expr.frame.getType(str(expr.name))


# Verifier helpers


def transformDeclares(declares: Iterable[lang.Declare], passby: lang.Passby,
                      env: lang.Environment) -> Tuple[lang.TypedValue, ...]:
    """Takes in a list of Declares. Returns a tuple of TypedValues.
    Used to declare names in an environment's frame/object.
    """
    params: Tuple[lang.TypedValue, ...] = tuple()
    for declaration in declares:
        resolve(declaration, env, passby=passby)
        params += (env.frame.get(str(declaration.name)), )
    return params


@singledispatch
def willReturn(stmt) -> bool:
    """Checks if statement is a Return statement, or is guaranteed to
    return a value.

    Returns True if yes, otherwise returns False.
    """
    return False


@willReturn.register
def _(stmt: lang.Conditional) -> bool:
    # If & CASE: If any case statements do not have a return, the statement is
    # not guaranteed to return.
    for stmts in stmt.cases.values():
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


def verifyStmts(stmts: lang.Stmts, env: lang.Environment,
                returnType: Optional[lang.Type] = None) -> None:
    """Verify a list of statements."""
    for stmt in stmts:
        if isinstance(stmt, lang.Return):
            if not returnType:
                raise builtin.LogicError("Unexpected RETURN statement",
                                         token=stmt.expr.token)
            expectTypeElseError(resolve(stmt.expr, env), returnType,
                                token=stmt.expr.token)
        else:
            verify(stmt, env, returnType)


@singledispatch
def verify(stmt, env, returnType):
    """Dispatcher for Stmt verifiers."""
    raise builtin.LogicError("Unexpected statement")


@verify.register
def _(stmt: lang.Output, env: lang.Environment,
      returnType: Optional[lang.Type] = None) -> None:
    stmt.exprs = resolveExprs(stmt.exprs, env)


@verify.register
def _(stmt: lang.Input, env: lang.Environment,
      returnType: Optional[lang.Type] = None) -> None:
    resolveNamesInTarget(stmt, env)
    resolve(stmt.key, env)


@verify.register
def _(stmt: lang.Case, env: lang.Environment,
      returnType: Optional[lang.Type] = None) -> None:
    resolveNamesInTarget(stmt, env)
    condType = resolve(stmt.cond, env)
    for caseValue, statements in stmt.cases.items():
        caseType = resolve(caseValue, env)
        expectTypeElseError(caseType, condType, token=caseValue.token)
        verifyStmts(statements, env, returnType)
    if stmt.fallback:
        verifyStmts(stmt.fallback, env, returnType)


@verify.register
def _(stmt: lang.If, env: lang.Environment,
      returnType: Optional[lang.Type] = None) -> None:
    resolveNamesInTarget(stmt, env)
    condType = resolve(stmt.cond, env)
    expectTypeElseError(condType, 'BOOLEAN', token=stmt.cond.token)
    for statements in stmt.cases.values():
        verifyStmts(statements, env, returnType)
    if stmt.fallback:
        verifyStmts(stmt.fallback, env, returnType)


@verify.register
def _(stmt: lang.Loop, env: lang.Environment,
      returnType: Optional[lang.Type] = None) -> None:
    resolveNamesInTarget(stmt, env)
    if stmt.init:
        resolve(stmt.init, env)
    condType = resolve(stmt.cond, env)
    expectTypeElseError(condType, 'BOOLEAN', token=stmt.cond.token)
    verifyStmts(stmt.stmts, env, returnType)


@verify.register
def _(stmt: lang.ProcedureStmt, env: lang.Environment,
      returnType: Optional[lang.Type] = None) -> None:
    """Declare a Procedure in the given environment's frame."""
    # Assign procedure in frame first, to make recursive calls work
    env.frame.declare(str(stmt.name), env.types.cloneType('NULL'))
    # No UnresolvedNames to resolve

    # Declare parameters
    local = lang.Frame(outer=env.frame)
    localenv = env.with_frame(local)
    params = transformDeclares(stmt.params, stmt.passby, localenv)

    # Add procedure definition
    proc = lang.Procedure(localenv, params, stmt.stmts)
    env.frame.setValue(str(stmt.name), proc)

    verifyStmts(stmt.stmts, localenv)


@verify.register
def _(stmt: lang.FunctionStmt, env: lang.Environment,
      returnType: Optional[lang.Type] = None) -> None:
    """Declare a Function in the given environment's frame."""
    # Assign function in frame first, to make recursive calls work
    env.frame.declare(str(stmt.name), env.types.cloneType(stmt.returnType))
    # No UnresolvedNames to resolve

    # Declare parameters
    local = lang.Frame(outer=env.frame)
    localenv = env.with_frame(local)
    params = transformDeclares(stmt.params, stmt.passby, localenv)

    # Add procedure definition
    func = lang.Function(localenv, params, stmt.stmts)
    env.frame.setValue(str(stmt.name), func)

    # Check for return statements
    if not any(map(willReturn, stmt.stmts)):
        raise builtin.LogicError(
            "Function does not guarantee a return value",
            stmt.name.token
        )
    verifyStmts(stmt.stmts, localenv, stmt.returnType)


@verify.register
def _(stmt: lang.FileStmt, env: lang.Environment,
      returnType: Optional[lang.Type] = None) -> None:
    resolveNamesInTarget(stmt, env)
    expectTypeElseError(resolve(stmt.filename, env),
                        'STRING',
                        token=stmt.filename.token)


@verify.register
def _(stmt: lang.TypeStmt, env: lang.Environment,
      returnType: Optional[lang.Type] = None) -> None:
    """Declare a custom Type in the given environment's TypeSystem."""
    env.types.declare(str(stmt.name))
    objTemplate = lang.ObjectTemplate(typesys=env.types)
    objenv = env.with_frame(objTemplate)
    for expr in stmt.exprs:
        resolve(expr, objenv)
    env.types.setTemplate(str(stmt.name), objTemplate)


@verify.register
def _(stmt: lang.CallStmt, env: lang.Environment,
      returnType: Optional[lang.Type] = None) -> None:
    resolveProcCall(stmt.expr, env)


@verify.register
def _(stmt: lang.AssignStmt, env: lang.Environment,
      returnType: Optional[lang.Type] = None) -> None:
    resolve(stmt.expr, env)


@verify.register
def _(stmt: lang.DeclareStmt,
      env: lang.Environment,
      returnType: Optional[lang.Type] = None) -> None:
    resolve(stmt.expr, env)
