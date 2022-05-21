from itertools import product

from . import builtin, lang



# Helper functions

def isProcedure(callable):
    return isinstance(callable, lang.Procedure)

def isFunction(callable):
    return type(callable) in (lang.Builtin, lang.Function)

def expectTypeElseError(exprtype, *expected, token=None):
    assert token, "Missing token"
    if exprtype not in expected:
        # Stringify expected types
        if len(expected) == 1:
            expected = expected[0]
        else:
            expected = f"({', '.join(expected)})"
        raise builtin.LogicError(f"Expected {expected}, is {exprtype}", token)

def declaredElseError(
    frame,
    name,
    errmsg="Undeclared",
    declaredType=None,
    *,
    token=None,
):
    if not frame.has(name):
        raise builtin.LogicError(errmsg, name, token)
    if declaredType:
        expectTypeElseError(
            frame.getType(name), declaredType, token=token
        )

def rangeProduct(indexes):
    ranges = [
        range(start, end + 1)
        for (start, end) in indexes
    ]
    return product(*ranges)



class Resolver:
    """
    Resolves a list of statements with the given frame.
    """
    def __init__(self, frame, statements):
        self.frame = frame
        self.statements = statements

    def inspect(self):
        verifyStmts(self.frame, self.statements)


    
# Resolvers

def resolveExprs(frame, exprs):
    for expr in exprs:
        resolve(frame, expr)

def evalLiteral(frame, expr):
    """Return the value of a Literal"""
    return expr.value
    
def resolveLiteral(frame, literal):
    return literal.type

def resolveDeclare(frame, expr, passby='BYVALUE'):
    """Declare variable in frame"""
    if passby == 'BYVALUE':
        frame.declare(expr.name, expr.type)
        if expr.type == 'ARRAY':
            array = lang.Array(typesys=frame.types)
            # Use n-element tuples to address arrays
            # itertools.product takes n iterables and returns
            # cartesian product of its combinations
            elemType = expr.metadata['type']
            for index in rangeProduct(expr.metadata['size']):
                array.declare(index, elemType)
            frame.setValue(expr.name, array)
        return expr.type
    assert passby == 'BYREF', f"Invalid passby {repr(passby)}"
    # BYREF
    expectTypeElseError(
        expr.type, frame.outer.getType(expr.name), token=expr.token()
    )
    # Reference frame vars in local
    frame.set(expr.name, frame.outer.get(expr.name))

def resolveUnary(frame, expr):
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

def resolveBinary(frame, expr):
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
                token=expr.oper.token(),
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

def resolveAssign(frame, expr):
    # assignee frame might be a Frame or Get(Object)
    assnType = resolveGet(frame, expr.assignee)
    exprType = resolve(frame, expr.expr)
    expectTypeElseError(
        exprType, assnType, token=expr.token()
    )

# Helper for resolving object+attribute types
def resolveObj(typesystem, objType, name, *, token):
    # Check objType existence in typesystem
    declaredElseError(
        typesystem, objType,
        errmsg="Undeclared type", token=token
    )
    # Check attribute existence in object template
    objTemplate = typesystem.getTemplate(objType).value
    declaredElseError(
        objTemplate, name,
        errmsg="Undeclared attribute", token=token
    )
    return objTemplate.getType(name)

def resolveArray(frame, expr):
    def intsElseError(frame, *indexes):
        for indexExpr in indexes:
            nameType = resolve(frame, indexExpr)
            expectTypeElseError(
                nameType, 'INTEGER', token=indexExpr.token()
            )
    # Array indexes must be integer
    intsElseError(frame, *expr.name)
    array = frame.getValue(expr.frame.name)
    return array.elementType
    
def resolveGet(frame, expr):
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
        while not frame.has(expr.name):
            frame = frame.lookup(expr.name)
            if not frame:
                raise builtin.LogicError("Undeclared", expr.token())
        expr.frame = frame
    # If frame is a Get Expr, resolve it recursively
    if isinstance(expr.frame, lang.Get):
        # Resolve Get frame
        objType = resolveGet(frame, expr.frame)
        if objType not in builtin.TYPES:
            # Check objType and attribute existence in types
            return resolveObj(
                frame.types, objType, expr.name, token=expr.token()
            )
        elif objType == 'ARRAY':
            return resolveArray(frame, expr)
        else:  # built-in, non-array
            pass
    return frame.getType(expr.name)

def resolveProcCall(frame, expr):
    resolveGet(frame, expr.callable)
    # Resolve global frame where procedure is declared
    callFrame = expr.callable.frame
    callable = callFrame.getValue(expr.callable.name)
    if not isProcedure(callable):
        raise builtin.LogicError("Not PROCEDURE", token=expr.callable.token())
    resolveCall(frame, expr)

def resolveFuncCall(frame, expr):
    resolveGet(frame, expr.callable)
    # Resolve global frame where function is declared
    callFrame = expr.callable.frame
    callable = callFrame.getValue(expr.callable.name)
    if not isFunction(callable):
        raise builtin.LogicError("Not FUNCTION", token=expr.callable.token())
    resolveCall(frame, expr)
    
def resolveCall(frame, expr):
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
            token=expr.callable.token(),
        )
    # Type-check arguments
    for arg, param in zip(expr.args, callable.params):
        # param is a slot from either local or frame
        argtype = resolve(frame, arg)
        expectTypeElseError(argtype, param.type, token=arg.token())

def resolve(frame, expr):
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

def verifyStmts(frame, stmts):
    for stmt in stmts:
        stmtType = verify(frame, stmt)
        # For Return statements
        if stmt.rule == 'return':
            expectTypeElseError(
                stmtType, stmt.returnType, token=stmt.name.token()
            )

def verifyOutput(frame, stmt):
    resolveExprs(frame, stmt.exprs)

def verifyInput(frame, stmt):
    declaredElseError(frame, stmt.name)

def verifyCase(frame, stmt):
    resolve(frame, stmt.cond)
    verifyStmts(frame, stmt.stmtMap.values())
    if stmt.fallback:
        verify(frame, stmt.fallback)

def verifyIf(frame, stmt):
    condType = resolve(frame, stmt.cond)
    expectTypeElseError(condType, 'BOOLEAN', token=stmt.cond.token())
    verifyStmts(frame, stmt.stmtMap[True])
    if stmt.fallback:
        verifyStmts(frame, stmt.fallback)

def verifyLoop(frame, stmt):
    if stmt.init:
        resolve(frame, stmt.init)
    condType = resolve(frame, stmt.cond)
    expectTypeElseError(condType, 'BOOLEAN', token=stmt.cond.token())
    verifyStmts(frame, stmt.stmts)

def verifyParams(frame, params, passby):
    for i, expr in enumerate(params):
        resolveDeclare(frame, expr, passby=passby)
        # params: replace Declare Expr with slot
        params[i] = frame.get(expr.name)

def verifyProcedure(frame, stmt):
    # Set up local frame
    local = lang.Frame(outer=frame)
    # Assign procedure in frame first, to make recursive calls work
    frame.declare(stmt.name, 'NULL')
    frame.setValue(stmt.name, lang.Procedure(
        local, stmt.params, stmt.stmts
    ))
    verifyParams(local, stmt.params, stmt.passby)
    # Resolve procedure statements using local
    verifyStmts(local, stmt.stmts)

def verifyFunction(frame, stmt):
    # Set up local frame
    local = lang.Frame(outer=frame)
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

def verifyFile(frame, stmt):
    evalLiteral(frame, stmt.name)
    if stmt.action == 'open':
        pass
    elif stmt.action in ('read', 'write'):
        resolve(frame, stmt.data)
    elif stmt.action == 'close':
        pass

def verifyDeclareType(frame, stmt):
    frame.types.declare(stmt.name)
    obj = lang.Object(typesys=frame.types)
    for expr in stmt.exprs:
        resolveDeclare(obj, expr)
    frame.types.setTemplate(stmt.name, obj)
    


def verify(frame, stmt):
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
    elif stmt.rule in ('assign', 'declare', 'return'):
        return resolve(frame, stmt.expr)
    elif stmt.rule == 'call':
        resolveProcCall(frame, stmt.expr)
