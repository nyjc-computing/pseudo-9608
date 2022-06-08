"""resolver

verify(frame: Frame, statements: list) -> None
    Resolves expressions in statements, declares variables and types
    in the list of statements
"""

from typing import Optional, Union, Literal
from typing import Iterable, Iterator, Mapping, Collection
from typing import Tuple
from functools import singledispatch
from dataclasses import dataclass
from itertools import product

from . import builtin, lang



# **********************************************************************

# Resolver helper functions

def expectTypeElseError(
    exprtype: lang.Type,
    *expected: lang.Type,
    token: lang.Token,
) -> None:
    """Takes in a type, followed by one or more expected types.
    Raises an error if the given type is not in the expected types.
    """
    if exprtype not in expected:
        # Stringify expected types
        typesStr = f"({', '.join(expected)})"
        raise builtin.LogicError(
            f"Expected {typesStr}, is {exprtype}", token
        )

def rangeProduct(indexes: Iterable[tuple]) -> Iterator:
    """Takes an iterable of (start, end) tuple pairs.
    Returns an iterator for cartesian product of indexes.
    """
    ranges = [
        range(start, end + 1)
        for (start, end) in indexes
    ]
    return product(*ranges)

def resolveName(
    exprOrStmt: Union[lang.Expr, lang.Stmt],
    frame: lang.Frame,
    attr: Optional[str]=None,
) -> lang.GetName:
    """Takes in an UnresolvedName, and returns a GetName with an
    appropriate frame.
    """
    if isinstance(exprOrStmt, lang.Stmt) and not attr:
        raise TypeError("attr required for Stmt argument")
    expr: lang.Expr = getattr(exprOrStmt, attr) if attr else exprOrStmt
    if not isinstance(expr, lang.UnresolvedName):
        raise TypeError('Attempted to resolve invalid UnresolvedName')
    unresolved: lang.UnresolvedName = expr
    exprFrame = frame.lookup(str(unresolved.name))
    if exprFrame is None:
        raise builtin.LogicError("Undeclared", unresolved.token)
    getNameExpr = lang.GetName(exprFrame, unresolved.name)
    if attr:
        setattr(exprOrStmt, attr, getNameExpr)
    # Return value needed by resolveExprs()
    return getNameExpr

def resolveNamesInExpr(
    exprOrStmt: Union[lang.Expr, lang.Stmt],
    frame: lang.Frame,
) -> None:
    """Checks the exprOrstmt's slots for UnresolvedName, and replaces
    them with GetNames.
    """
    for attr in exprOrStmt.__slots__:
        if isinstance(getattr(exprOrStmt, attr), lang.UnresolvedName):
            resolveName(exprOrStmt, frame, attr)

def resolveExprs(
    exprs: Iterable[lang.Expr],
    frame: lang.Frame,
) -> Tuple[lang.Expr, ...]:
    """Resolve an iterable of Exprs.
    UnresolvedNames are resolved into GetNames.

    Return
    ------
    Tuple[Expr, ...]
        A tuple of Exprs
    """
    newexprs: Tuple[lang.Expr, ...] = tuple()
    for expr in exprs:
        if isinstance(expr, lang.UnresolvedName):
            expr = resolveName(expr, frame)
        resolve(expr, frame)
        newexprs += (expr,)
    return newexprs

def resolveArgsParams(
    args: lang.Args,
    params: Collection[lang.Param],
    frame: lang.Frame,
    *,
    token: lang.Token,
) -> None:
    """resolveArgsParams() only type-checks the args and stmts of the
    call.
    It does not resolve the callable. This should be carried out first
    (e.g. in a wrapper function) before resolveArgsParams() is invoked.
    """
    if len(args) != len(params):
        raise builtin.LogicError(
            f"Expected {len(params)} args, got {len(args)}",
            token=token,
        )
    for arg, param in zip(args, params):
        # param is a TypedValue slot from either local or frame
        expectTypeElseError(
            resolve(arg, frame), param.type, token=arg.token
        )



@dataclass
class Resolver:
    """Resolves a list of statements with the given frame."""
    __slots__ = ('frame', 'statements')
    frame: lang.Frame
    statements: Iterable[lang.Stmt]

    def inspect(self) -> None:
        verifyStmts(self.frame, self.statements)


    
# Resolvers

def resolveLiteral(
    literal: lang.Literal,
    frame: lang.Frame,
) -> lang.Type:
    return literal.type

def declareByref(
    declare: lang.Declare,
    frame: lang.Frame,
) -> None:
    """Declares BYREF variable in the given frame."""
    assert frame.outer, "Declared name in a frame with no outer"
    name: lang.NameKey = str(declare.name)
    expectTypeElseError(
        declare.type, frame.outer.getType(name),
        token=declare.token
    )
    # Reference frame vars in local
    frame.set(name, frame.outer.get(name))

def declareByval(
    declare: lang.Declare,
    frame: Union[lang.Frame, lang.ObjectTemplate],
) -> None:
    """Declares BYVALUE variable in the given frame."""
    if (
        isinstance(frame, lang.ObjectTemplate)
        and declare.type == 'ARRAY'
    ):
        raise builtin.LogicError(
            "ARRAY in TYPE not supported", declare.token
        )
    name: lang.NameKey = str(declare.name)
    frame.declare(name, declare.type)
    if declare.type == 'ARRAY':
        array = lang.Array(
            typesys=frame.types,
            ranges=declare.metadata['size'],
            type=declare.metadata['type'],
        )
        assert isinstance(frame, lang.Frame), "Frame expected"
        frame.setValue(name, array)

def resolveDeclare(
    declare: lang.Declare,
    frame: Union[lang.Frame, lang.ObjectTemplate],
    passby: Literal['BYVALUE', 'BYREF']='BYVALUE',
) -> lang.Type:
    """Declare variable in frame with dispatcher."""
    if passby == 'BYVALUE':
        declareByval(declare, frame)
    else:
        assert isinstance(frame, lang.Frame), \
            "Declared BYREF in invalid Frame"
        declareByref(declare, frame)
    return declare.type

def resolveUnary(
    expr: lang.Unary,
    frame: lang.Frame,
) -> lang.Type:
    resolveNamesInExpr(expr, frame)
    rType = resolve(expr.right, frame)
    if expr.oper is builtin.sub:
        expectTypeElseError(
            rType, *builtin.NUMERIC, token=expr.right.token
        )
        return rType
    if expr.oper is builtin.NOT:
        expectTypeElseError(
            rType, 'BOOLEAN', token=expr.right.token
        )
        return 'BOOLEAN'
    raise ValueError(f"Unexpected oper {expr.oper}")

def resolveBinary(
    expr: lang.Binary,
    frame: lang.Frame,
) -> lang.Type:
    resolveNamesInExpr(expr, frame)
    lType = resolve(expr.left, frame)
    rType = resolve(expr.right, frame)
    if expr.oper in (builtin.AND, builtin.OR):
        expectTypeElseError(lType, 'BOOLEAN', token=expr.left.token)
        expectTypeElseError(rType, 'BOOLEAN', token=expr.right.token)
        return 'BOOLEAN'
    if expr.oper in (builtin.ne, builtin.eq):
        expectTypeElseError(
            lType, *builtin.EQUATABLE, token=expr.left.token
        )
        expectTypeElseError(
            rType, *builtin.EQUATABLE, token=expr.right.token
        )
        if not (
            (lType == 'BOOLEAN' and rType == 'BOOLEAN')
            or (lType in builtin.NUMERIC and rType in builtin.NUMERIC)
        ):
            raise builtin.LogicError(
                f"Illegal comparison of {lType} and {rType}",
                token=expr.token,
            )
        return 'BOOLEAN'
    if expr.oper in (builtin.gt, builtin.gte, builtin.lt, builtin.lte):
        expectTypeElseError(
            lType, *builtin.NUMERIC, token=expr.left.token
        )
        expectTypeElseError(
            rType, *builtin.NUMERIC, token=expr.right.token
        )
        return 'BOOLEAN'
    if expr.oper in (
        builtin.add, builtin.sub, builtin.mul, builtin.div
    ):
        expectTypeElseError(
            lType, *builtin.NUMERIC, token=expr.left.token
        )
        expectTypeElseError(
            rType, *builtin.NUMERIC, token=expr.right.token
        )
        if (
            (expr.oper is not builtin.div)
            and (lType == rType == 'INTEGER')
        ):
            return 'INTEGER'
        return 'REAL'
    raise ValueError("No return for Binary")

def resolveAssign(
    expr: lang.Assign,
    frame: lang.Frame,
) -> lang.Type:
    resolveNamesInExpr(expr, frame)
    assnType = resolve(expr.assignee, frame)
    exprType = resolve(expr.expr, frame)
    expectTypeElseError(
        exprType, assnType, token=expr.token
    )
    # Return statement for resolve()
    return assnType

def resolveAttr(
    expr: lang.GetAttr,
    frame: lang.Frame,
) -> lang.Type:
    """Resolves a GetAttr Expr to return an attribute's type"""
    resolveNamesInExpr(expr, frame)
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

def resolveIndex(
    expr: lang.GetIndex,
    frame: lang.Frame,
) -> lang.Type:
    """Resolves a GetIndex Expr to return an array element's type"""
    def intsElseError(frame, *indexes):
        for indexExpr in indexes:
            nameType = resolve(indexExpr, frame)
            expectTypeElseError(
                nameType, 'INTEGER', token=indexExpr.token
            )
    expr.index = resolveExprs(expr.index, frame)
    # Array indexes must be integer
    intsElseError(frame, *expr.index)
    # Arrays in Objects not yet supported; assume frame
    resolveNamesInExpr(expr, frame)
    assert isinstance(expr.array, lang.GetName), "Array unresolved"
    expectTypeElseError(
        ## Expect array
        resolve(expr.array, frame), 'ARRAY', token=expr.token
    )
    array = expr.array.frame.getValue(str(expr.array.name))
    # For mypy type-checking
    assert (isinstance(array, lang.Array)), "Invalid ARRAY"
    return array.elementType

def resolveGetName(
    expr: lang.GetName,
    frame: lang.Frame,
) -> lang.Type:
    """Returns the type of value that name is mapped to in frame."""
    return expr.frame.getType(str(expr.name))

def resolveProcCall(
    expr: lang.Call,
    frame: lang.Frame,
) -> lang.Type:
    """Resolve a procedure call.
    Statement verification should be done in verifyProcedure, not here.
    """
    resolveNamesInExpr(expr, frame)
    assert isinstance(expr.callable, lang.GetName), \
        f"Callable {expr.callable} unresolved"
    callableType = resolveGetName(expr.callable, frame)
    expectTypeElseError(
        callableType, 'NULL', token=expr.callable.token
    )
    callFrame = expr.callable.frame
    callable = callFrame.getValue(str(expr.callable.name))
    if not isinstance(callable, lang.Procedure):
        raise builtin.LogicError(
            "Not PROCEDURE", token=expr.callable.token
        )
    expr.args = resolveExprs(expr.args, frame)
    resolveArgsParams(
        expr.args, callable.params, frame,
        token=expr.token
    )
    return callableType

def resolveFuncCall(
    expr: lang.Call,
    frame: lang.Frame,
) -> lang.Type:
    """Resolve a function call.
    Statement verification should be done in verifyFunction, not here.
    """
    resolveNamesInExpr(expr, frame)
    assert isinstance(expr.callable, lang.GetName), \
        "Callable unresolved"
    callableType = resolveGetName(expr.callable, frame)
    callFrame = expr.callable.frame
    callable = callFrame.getValue(str(expr.callable.name))
    if not (
        isinstance(callable, lang.Function)
        or isinstance(callable, lang.Builtin)
    ):
        raise builtin.LogicError(
            "Not FUNCTION", token=expr.callable.token
        )
    expr.args = resolveExprs(expr.args, frame)
    resolveArgsParams(
        expr.args, callable.params, frame,
        token=expr.token
    )
    return callableType

resolver: Mapping = {
    lang.Literal: resolveLiteral,
    lang.Declare: resolveDeclare,
    lang.Unary: resolveUnary,
    lang.Binary: resolveBinary,
    lang.Assign: resolveAssign,
    lang.Call: resolveFuncCall,
    lang.GetIndex: resolveIndex,
    lang.GetAttr: resolveAttr,
    lang.GetName: resolveGetName,
}

def resolve(expr, frame):
    """Dispatcher for Expr resolvers."""
    exprtype = type(expr)
    if exprtype not in resolver:
        raise TypeError(f"Encountered {expr} in resolve()")
    return resolver[exprtype](expr, frame)



# Verifiers

def verifyStmts(
    frame: lang.Frame,
    stmts: Iterable[lang.Stmt],
    returnType: Optional[lang.Type]=None,
) -> None:
    """Verify a list of statements."""
    for stmt in stmts:
        verify(frame, stmt)
        if returnType and isinstance(stmt, lang.Return):
            expectTypeElseError(
                resolve(stmt.expr, frame), returnType,
                token=stmt.expr.token
            )

def verifyOutput(frame: lang.Frame, stmt: lang.Output) -> None:
    stmt.exprs = resolveExprs(stmt.exprs, frame)

def verifyInput(frame: lang.Frame, stmt: lang.Input) -> None:
    resolveNamesInExpr(stmt, frame)
    resolve(stmt.key, frame)

def verifyCase(frame: lang.Frame, stmt: lang.Conditional) -> None:
    resolveNamesInExpr(stmt, frame)
    resolve(stmt.cond, frame)
    for statements in stmt.stmtMap.values():
        verifyStmts(frame, statements)
    if stmt.fallback:
        verifyStmts(frame, stmt.fallback)

def verifyIf(frame: lang.Frame, stmt: lang.Conditional) -> None:
    resolveNamesInExpr(stmt, frame)
    condType = resolve(stmt.cond, frame)
    expectTypeElseError(condType, 'BOOLEAN', token=stmt.cond.token)
    for statements in stmt.stmtMap.values():
        verifyStmts(frame, statements)
    if stmt.fallback:
        verifyStmts(frame, stmt.fallback)

def verifyLoop(frame: lang.Frame, stmt: lang.Loop) -> None:
    resolveNamesInExpr(stmt, frame)
    if stmt.init:
        verify(frame, stmt.init)
    condType = resolve(stmt.cond, frame)
    expectTypeElseError(condType, 'BOOLEAN', token=stmt.cond.token)
    verifyStmts(frame, stmt.stmts)

def transformDeclares(
    frame: lang.Frame,
    declares: Iterable[lang.Declare],
    passby: lang.Passby,
) -> Tuple[lang.TypedValue, ...]:
    """Takes in a list of Declares. Returns a list of TypedValues.
    Used to declare names in a frame/object.
    """
    params: Tuple[lang.TypedValue, ...] = tuple()
    for declaration in declares:
        resolveDeclare(declaration, frame, passby=passby)
        params += (frame.get(str(declaration.name)),)
    return params

def verifyProcedure(frame: lang.Frame, stmt: lang.ProcFunc) -> None:
    """Declare a Procedure in the given frame."""
    resolveNamesInExpr(stmt, frame)
    local = lang.Frame(typesys=frame.types, outer=frame)
    params = transformDeclares(local, stmt.params, stmt.passby)
    # Assign procedure in frame first, to make recursive calls work
    frame.declare(str(stmt.name), 'NULL')
    frame.setValue(str(stmt.name), lang.Procedure(
        local, params, stmt.stmts
    ))
    for procstmt in stmt.stmts:
        if isinstance(procstmt, lang.Return):
            raise builtin.LogicError(
                "Unexpected RETURN in PROCEDURE",
                procstmt.expr.token
            )
    verifyStmts(local, stmt.stmts)

def verifyFunction(frame: lang.Frame, stmt: lang.ProcFunc) -> None:
    """Declare a Function in the given frame."""
    resolveNamesInExpr(stmt, frame)
    local = lang.Frame(typesys=frame.types, outer=frame)
    params = transformDeclares(local, stmt.params, stmt.passby)
    # Assign function in frame first, to make recursive calls work
    frame.declare(str(stmt.name), stmt.returnType)
    frame.setValue(str(stmt.name), lang.Function(
        local, params, stmt.stmts
    ))
    # Check for return statements
    if not any([
        isinstance(stmt, lang.Return)
        for stmt in stmt.stmts
    ]):
        raise builtin.LogicError(
            "No RETURN in function", stmt.name.token
        )
    verifyStmts(local, stmt.stmts, stmt.returnType)

def verifyDeclareType(
    frame: lang.Frame,
    stmt: lang.TypeStmt,
) -> None:
    """Declare a custom Type in the given frame's TypeSystem."""
    frame.types.declare(str(stmt.name))
    objTemplate = lang.ObjectTemplate(typesys=frame.types)
    for expr in stmt.exprs:
        resolveDeclare(expr, objTemplate)
    frame.types.setTemplate(str(stmt.name), objTemplate)

def verify(frame: lang.Frame, stmt: lang.Stmt) -> None:
    """Dispatcher for Stmt verifiers."""
    if isinstance(stmt, lang.Output):
        verifyOutput(frame, stmt)
    elif isinstance(stmt, lang.Input):
        verifyInput(frame, stmt)
    elif isinstance(stmt, lang.Case):
        verifyCase(frame, stmt)
    elif isinstance(stmt, lang.If):
        verifyIf(frame, stmt)
    elif isinstance(stmt, lang.Loop):
        verifyLoop(frame, stmt)
    elif isinstance(stmt, lang.ProcedureStmt):
        verifyProcedure(frame, stmt)
    elif isinstance(stmt, lang.FunctionStmt):
        verifyFunction(frame, stmt)
    elif isinstance(stmt, lang.OpenFile):
        resolveNamesInExpr(stmt, frame)
        expectTypeElseError(
            resolve(stmt.filename, frame), 'STRING',
            token=stmt.filename.token
        )
    elif isinstance(stmt, lang.ReadFile):
        resolveNamesInExpr(stmt, frame)
        expectTypeElseError(
            resolve(stmt.filename, frame), 'STRING',
            token=stmt.filename.token
        )
    elif isinstance(stmt, lang.WriteFile):
        resolveNamesInExpr(stmt, frame)
        expectTypeElseError(
            resolve(stmt.filename, frame), 'STRING',
            token=stmt.filename.token
        )
    elif isinstance(stmt, lang.CloseFile):
        resolveNamesInExpr(stmt, frame)
        expectTypeElseError(
            resolve(stmt.filename, frame), 'STRING',
            token=stmt.filename.token
        )
    elif isinstance(stmt, lang.TypeStmt):
        verifyDeclareType(frame, stmt)
    elif isinstance(stmt, lang.CallStmt):
        assert isinstance(stmt.expr, lang.Call), "Invalid Call"
        resolveProcCall(stmt.expr, frame)
    elif isinstance(stmt, lang.AssignStmt):
        assert isinstance(stmt.expr, lang.Assign), "Invalid Assign"
        resolveAssign(stmt.expr, frame)
    elif isinstance(stmt, lang.DeclareStmt):
        assert isinstance(stmt.expr, lang.Declare), "Invalid Declare"
        resolveDeclare(stmt.expr, frame)
    assert not isinstance(stmt, lang.Return), \
        "Unhandled Return in verify()"
