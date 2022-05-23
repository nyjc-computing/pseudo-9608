from typing import Any, Optional, Union, Literal, Iterable, Iterator
from itertools import product

from . import builtin, lang



# Helper functions

def isProcedure(callable: Any) -> bool:
    return isinstance(callable, lang.Procedure)

def isFunction(callable: Any) -> bool:
    return type(callable) in (lang.Builtin, lang.Function)

def expectTypeElseError(
    exprtype: lang.Type,
    *expected: lang.Type,
    token: lang.Token,
) -> None:
    if exprtype not in expected:
        # Stringify expected types
        typesStr = f"({', '.join(expected)})"
        raise builtin.LogicError(f"Expected {typesStr}, is {exprtype}", token)

def declaredElseError(
    frame: Union[lang.Object, lang.TypeSystem],
    name: lang.Name,
    errmsg: str="Undeclared",
    declaredType: lang.Type=None,
    *,
    token: lang.Token,
) -> None:
    nameStr = str(name)
    if not frame.has(nameStr):
        raise builtin.LogicError(errmsg, nameStr, token)
    if declaredType:
        expectTypeElseError(
            frame.getType(nameStr), declaredType, token=token
        )

def lookupElseError(
    frame: lang.Frame,
    name: lang.Key,
    errmsg: str="Undeclared",
    *,
    token: lang.Token,
) -> lang.Frame:
    if frame.has(name):
        return frame
    if isinstance(frame, lang.Frame):
        frame: Optional[lang.Frame] = frame.lookup(name)
        if frame:
            return frame
    raise builtin.LogicError(errmsg, name, token)

def rangeProduct(indexes: Iterable[tuple]) -> Iterator:
    ranges = [
        range(start, end + 1)
        for (start, end) in indexes
    ]
    return product(*ranges)



class Resolver:
    """
    Resolves a list of statements with the given frame.
    """
    def __init__(
        self,
        frame: lang.Frame,
        statements: Iterable[lang.Stmt],
    ) -> None:
        self.frame = frame
        self.statements = statements

    def inspect(self) -> None:
        verifyStmts(self.frame, self.statements)


    
# Resolvers

def resolveExprs(
    frame: lang.Frame,
    exprs: Iterable[lang.Expr],
) -> None:
    for expr in exprs:
        resolve(frame, expr)

def evalLiteral(
    frame: lang.Frame,
    expr: lang.Literal,
) -> lang.PyLiteral:
    """Return the value of a Literal"""
    return expr.value
    
def resolveLiteral(
    frame: lang.Frame,
    literal: lang.Literal,
) -> lang.Type:
    return literal.type

def resolveDeclare(
    frame: lang.Frame,
    expr: lang.Declare,
    passby: str='BYVALUE',
) -> lang.Type:
    """Declare variable in frame"""
    if passby == 'BYVALUE':
        frame.declare(expr.name, expr.type)
        if expr.type == 'ARRAY':
            array = lang.Array(typesys=frame.types)
            elemType = expr.metadata['type']
            for index in rangeProduct(expr.metadata['size']):
                array.declare(index, elemType)
            frame.setValue(expr.name, array)
        return expr.type
    assert passby == 'BYREF', f"Invalid passby {repr(passby)}"
    # BYREF -- TODO: resolveByref() as a separate function
    expectTypeElseError(
        expr.type, frame.outer.getType(expr.name), token=expr.token()
    )
    # Reference frame vars in local
    frame.set(expr.name, frame.outer.get(expr.name))
    return expr.type

def resolveUnary(
    frame: lang.Frame,
    expr: lang.Unary,
) -> lang.Type:
    rType = resolve(frame, expr.right)
    if expr.oper is builtin.sub:
        expectTypeElseError(rType, *builtin.NUMERIC, token=expr.right.token())
        return rType
    if expr.oper is builtin.NOT:
        expectTypeElseError(
            rType, 'BOOLEAN', token=expr.right.token()
        )
        return 'BOOLEAN'
    raise ValueError(f"Unexpected oper {expr.oper}")

def resolveBinary(
    frame: lang.Frame,
    expr: lang.Binary,
) -> lang.Type:
    lType = resolve(frame, expr.left)
    rType = resolve(frame, expr.right)
    if expr.oper in (builtin.AND, builtin.OR):
        expectTypeElseError(lType, 'BOOLEAN', token=expr.left.token())
        expectTypeElseError(rType, 'BOOLEAN', token=expr.right.token())
        return 'BOOLEAN'
    if expr.oper in (builtin.ne, builtin.eq):
        expectTypeElseError(lType, *builtin.EQUATABLE, token=expr.left.token())
        expectTypeElseError(rType, *builtin.EQUATABLE, token=expr.right.token())
        if not (
            (lType == 'BOOLEAN' and rType == 'BOOLEAN')
            or (lType in builtin.NUMERIC and rType in builtin.NUMERIC)
        ):
            raise builtin.LogicError(
                f"Illegal comparison of {lType} and {rType}",
                token=expr.token(),
            )
        return 'BOOLEAN'
    if expr.oper in (builtin.gt, builtin.gte, builtin.lt, builtin.lte):
        expectTypeElseError(lType, *builtin.NUMERIC, token=expr.left.token())
        expectTypeElseError(rType, *builtin.NUMERIC, token=expr.left.token())
        return 'BOOLEAN'
    if expr.oper in (builtin.add, builtin.sub, builtin.mul, builtin.div):
        expectTypeElseError(lType, *builtin.NUMERIC, token=expr.left.token())
        expectTypeElseError(rType, *builtin.NUMERIC, token=expr.left.token())
        if (expr.oper is not builtin.div) and (lType == rType == 'INTEGER'):
            return 'INTEGER'
        return 'REAL'

def resolveAssign(
    frame: lang.Frame,
    expr: lang.Assign,
) -> lang.Type:
    # assignee frame might be a Frame or Get(Object)
    assnType = resolveGet(frame, expr.assignee)
    exprType = resolve(frame, expr.expr)
    expectTypeElseError(
        exprType, assnType, token=expr.token()
    )

# Helper for resolving attribute types
def resolveAttr(
    typesystem: lang.TypeSystem,
    objType: lang.Type,
    name: lang.Name,
    *,
    token: lang.Token,
) -> lang.Type:
    # Check objType existence in typesystem
    declaredElseError(
        typesystem, objType,
        errmsg="Undeclared type", token=token
    )
    # Check attribute existence in object template
    objTemplate = typesystem.clone(objType)
    declaredElseError(
        objTemplate, name,
        errmsg="Undeclared attribute", token=token
    )
    return objTemplate.getType(name)

def resolveArray(
    frame: lang.Frame,
    expr: lang.Get,
) -> lang.Type:
    def intsElseError(frame, *indexes):
        for indexExpr in indexes:
            nameType = resolve(frame, indexExpr)
            expectTypeElseError(
                nameType, 'INTEGER', token=indexExpr.token()
            )
    # Array indexes must be integer
    intsElseError(frame, *expr.name)
    array: lang.Array = frame.getValue(expr.frame.name)
    return array.elementType
    
def resolveGet(
    frame: lang.Frame,
    expr: lang.Get,
) -> lang.Type:
    """Insert frame into Get expr"""
    assert isinstance(expr, lang.Get), "Not a Get Expr"
    # frame can be:
    # 1. NULL
    #    - insert frame
    # 2. A Get Expr (for an Object)
    #    - check type existence
    #    - custom types: check attribute existence in template
    #    - arrays: check element type in frame
    if expr.frame is builtin.NULL:
        target: Optional[lang.Frame] = frame
        while not target.has(expr.name):
            target = target.lookup(expr.name)
            if not target:
                raise builtin.LogicError("Undeclared", expr.token())
        expr.frame: lang.Frame = target
    # If frame is a Get Expr, resolve it recursively
    if isinstance(expr.frame, lang.Get):
        # Resolve Get frame
        objType = resolveGet(frame, expr.frame)
        if objType not in builtin.TYPES:
            # Check objType and attribute existence in types
            return resolveAttr(
                frame.types, objType, expr.name, token=expr.token()
            )
        elif objType == 'ARRAY':
            return resolveArray(frame, expr)
        else:  # built-in, non-array
            pass
    return frame.getType(expr.name)

def resolveProcCall(
    frame: lang.Frame,
    expr: lang.Call,
) -> Literal['NULL']:
    # Resolve global frame where procedure is declared
    callableType = resolveGet(frame, expr.callable)
    callFrame = expr.callable.frame
    callable = callFrame.getValue(expr.callable.name)
    if not isProcedure(callable):
        raise builtin.LogicError("Not PROCEDURE", token=expr.callable.token())
    resolveCall(frame, callable, callableType, token=expr.callable.token())
    return callableType

def resolveFuncCall(
    frame: lang.Frame,
    expr: lang.Call,
) -> lang.Type:
    # Resolve global frame where function is declared
    callableType = resolveGet(frame, expr.callable)
    callFrame = expr.callable.frame
    callable = callFrame.getValue(expr.callable.name)
    if not isFunction(callable):
        raise builtin.LogicError("Not FUNCTION", token=expr.callable.token())
    resolveCall(frame, callable, callableType, token=expr.callable.token())
    return callableType
    
def resolveCall(
    frame: lang.Frame,
    expr: lang.Call,
    callableType: Union[Literal['NULL'], lang.Type],
    *,
    token: lang.Token,
) -> None:
    """
    resolveCall() does not carry out any frame insertion or
    type-checking. These should be carried out first (e.g. in a wrapper
    function) before resolveCall() is invoked.
    """
    callable = expr.callable.frame.getValue(expr.callable.name)
    numArgs, numParams = len(expr.args), len(callable.params)
    if numArgs != numParams:
        raise builtin.LogicError(
            f"Expected {numParams} args, got {numArgs}",
            token=token,
        )
    # Type-check arguments
    for arg, param in zip(expr.args, callable.params):
        # param is a slot from either local or frame
        argtype = resolve(frame, arg)
        expectTypeElseError(argtype, param.type, token=arg.token())
    for stmt in callable.stmts:
        if isProcedure(callable) and stmt.rule == 'return':
            raise builtin.LogicError("Unexpected RETURN", token)
        returnType = verify(frame, stmt)
        if isFunction(callable) and stmt.rule == 'return':
            expectTypeElseError(returnType, callableType, token=token)

def resolve(
    frame: lang.Frame,
    expr: lang.Expr,
) -> lang.Type:
    if isinstance(expr, lang.Literal):
        return resolveLiteral(frame, expr)
    if isinstance(expr, lang.Declare):
        return resolveDeclare(frame, expr)
    elif isinstance(expr, lang.Unary):
        return resolveUnary(frame, expr)
    elif isinstance(expr, lang.Binary):
        return resolveBinary(frame, expr)
    elif isinstance(expr, lang.Assign):
        return resolveAssign(frame, expr)
    elif isinstance(expr, lang.Get):
        return resolveGet(frame, expr)
    elif isinstance(expr, lang.Call):
        return resolveFuncCall(frame, expr)


        
# Verifiers

def verifyStmts(frame: lang.Frame, stmts: Iterable[lang.Stmt]) -> None:
    for stmt in stmts:
        stmtType = verify(frame, stmt)
        # For Return statements
        if stmt.rule == 'return':
            expectTypeElseError(
                stmtType, stmt.returnType, token=stmt.name.token()
            )

def verifyOutput(frame: lang.Frame, stmt: lang.Output) -> None:
    resolveExprs(frame, stmt.exprs)

def verifyInput(frame: lang.Frame, stmt: lang.Input) -> None:
    declaredElseError(frame, stmt.name, token=stmt.name.token())

def verifyCase(frame: lang.Frame, stmt: lang.Conditional) -> None:
    resolve(frame, stmt.cond)
    for statements in stmt.stmtMap.values():
        verifyStmts(frame, statements)
    if stmt.fallback:
        verifyStmts(frame, stmt.fallback)

def verifyIf(frame: lang.Frame, stmt: lang.Conditional) -> None:
    condType = resolve(frame, stmt.cond)
    expectTypeElseError(condType, 'BOOLEAN', token=stmt.cond.token())
    for statements in stmt.stmtMap.values():
        verifyStmts(frame, statements)
    if stmt.fallback:
        verifyStmts(frame, stmt.fallback)

def verifyLoop(frame: lang.Frame, stmt: lang.Loop) -> None:
    if stmt.init:
        verify(frame, stmt.init)
    condType = resolve(frame, stmt.cond)
    expectTypeElseError(condType, 'BOOLEAN', token=stmt.cond.token())
    verifyStmts(frame, stmt.stmts)

def verifyParams(frame: lang.Frame, params: Iterable[lang.Param], passby: str) -> None:
    for i, expr in enumerate(params):
        resolveDeclare(frame, expr, passby=passby)
        # params: replace Declare Expr with slot
        params[i] = frame.get(expr.name)

def verifyProcedure(frame: lang.Frame, stmt: lang.ProcFunc) -> None:
    # Set up local frame
    local = lang.Frame(typesys=frame.types, outer=frame)
    # Assign procedure in frame first, to make recursive calls work
    frame.declare(stmt.name, 'NULL')
    frame.setValue(stmt.name, lang.Procedure(
        local, stmt.params, stmt.stmts
    ))
    verifyParams(local, stmt.params, stmt.passby)
    # Resolve procedure statements using local
    verifyStmts(local, stmt.stmts)

def verifyFunction(frame: lang.Frame, stmt: lang.ProcFunc) -> None:
    # Set up local frame
    local = lang.Frame(typesys=frame.types, outer=frame)
    # Assign function in frame first, to make recursive calls work
    frame.declare(stmt.name, stmt.returnType)
    frame.setValue(stmt.name, lang.Function(
        local, stmt.params, stmt.stmts
    ))
    verifyParams(local, stmt.params, stmt.passby)
    # Check for return statements
    if not any([stmt.rule == 'return' for stmt in stmt.stmts]):
        raise builtin.LogicError("No RETURN in function", stmt.name.token())
    # Resolve procedure statements using local
    verifyStmts(local, stmt.stmts)

def verifyFile(frame: lang.Frame, stmt: lang.FileAction) -> None:
    resolve(frame, stmt.name)
    if stmt.action == 'open':
        pass
    if isinstance(stmt.data, lang.Expr):
        resolve(frame, stmt.data)

def verifyDeclareType(frame: lang.Frame, stmt: lang.TypeStmt) -> None:
    frame.types.declare(stmt.name)
    obj = lang.Object(typesys=frame.types)
    for expr in stmt.exprs:
        resolve(obj, expr)
    frame.types.setTemplate(stmt.name, obj)

def verifyExprStmt(frame: lang.Frame, stmt: lang.ExprStmt) -> Optional[lang.Value]:
    if stmt.rule == 'call':
        return resolveProcCall(frame, stmt.expr)
    return resolve(frame, stmt.expr)



def verify(frame: lang.Frame, stmt: lang.Stmt) -> Optional[lang.Type]:
    if stmt.rule == 'output':
        verifyOutput(frame, stmt)
    if stmt.rule == 'input':
        verifyInput(frame, stmt)
    elif stmt.rule == 'case':
        verifyCase(frame, stmt)
    elif stmt.rule == 'if':
        verifyIf(frame, stmt)
    elif stmt.rule in ('while', 'repeat', 'for'):
        verifyLoop(frame, stmt)
    elif stmt.rule == 'procedure':
        verifyProcedure(frame, stmt)
    elif stmt.rule == 'function':
        verifyFunction(frame, stmt)
    elif stmt.rule == 'file':
        verifyFile(frame, stmt)
    elif stmt.rule == 'declaretype':
        verifyDeclareType(frame, stmt)
    elif stmt.rule in ('assign', 'declare', 'return', 'call'):
        verifyExprStmt(frame, stmt)
