from typing import Any, Optional

import astroid

from .parse_pb2 import ClassDef, TypeClass

class Scope(object):
    __slots__ = ('_scope',)

    def __init__(self, initial_scope=None):
        if initial_scope is None:
            initial_scope = {}
        self._scope = [initial_scope]

    @property
    def current(self):
        # type: () -> dict
        return self._scope[-1]

    def __getitem__(self, item):
        # type: (str) -> Any
        for frame in self._scope[::-1]:
            try:
                return frame[item]
            except KeyError:
                pass
        raise KeyError(item)

    def assign(self, lhs, rhs):
        # type: (str, Any) -> None
        self.current[lhs] = rhs

    def push(self, d=None):
        # type: (Optional[dict]) -> Scope
        if d is None:
            d = {}
        assert isinstance(d, dict)
        self._scope.append(d)
        return self

    def pop(self):
        # type: () -> dict
        return self._scope.pop()

    def __repr__(self):
        return 'Scope({})'.format(self._scope)

def resolve_name(scope, lhs):
    # type: (Scope, astroid.Name) -> Any
    return scope[lhs.name]

def resolve_constant(lhs):
    # type: (astroid.Const) -> Any
    return next(lhs.infer()).value

def resolve_attribute(scope, expr):
    # type: (Scope, astroid.Attribute) -> Any
    lhs = evaluate(scope, expr.expr)
    return getattr(lhs, expr.attrname)

def evaluate(scope, expr):
    # type: (Scope, astroid.node_classes.NodeNG) -> Any
    if isinstance(expr, astroid.Name):
        return resolve_name(scope, expr)
    elif isinstance(expr, astroid.Const):
        return resolve_constant(expr)
    elif isinstance(expr, astroid.Attribute):
        return resolve_attribute(scope, expr)
    else:
        raise NotImplementedError()

def resolve(scope, node):
    """
    typeof ::
        scope : Name -> Maybe[Type]
        node : Node
        -> Maybe[Type]
    """
    if isinstance(node, (astroid.Name, astroid.AssignName)):
        return scope.get(node.name)
    elif isinstance(node, astroid.Subscript):
        return resolve(scope, slice(node))
    elif isinstance(node, astroid.Call):
        # XXX: return _instanceof(resolve(scope, node.func))
        return resolve(scope, node.func)
    elif isinstance(node, astroid.Const):
        return None
        # NOTE: not returning type(node.value) anymore as it breaks assumptions
        # around _instanceof
    elif isinstance(node, astroid.Attribute):
        try:
            namespace = scope.get(node.expr.name)
        except AttributeError:
            return None
        # namespace is something like a module or ClassDef that supports
        # getattr
        try:
            return namespace.getattr(node.attrname)  # XXX: changed
        except AttributeError:
            return None
        # else:
        #     return resolve(scope, attr)
    elif isinstance(node, (TypeClass, ClassDef)):
        return node
    else:
        if node is None:
            return None  # node may be Uninferable
        try:
            return scope.get(node.as_string())
        except AttributeError:
            return None


def slice(subscript):
    """
    slice ::
        (Subscript (Node value) (Node idx))
        -> Maybe[Node]
    """
    value, idx = subscript.value, subscript.slice
    try:
        indexable = next(value.infer())
        index = next(idx.infer())
    except astroid.exceptions.InferenceError:
        return None
    if indexable is astroid.Uninferable or index is astroid.Uninferable:
        return None
    if not isinstance(index, astroid.Const):
        return None
    i = index.value
    if hasattr(indexable, 'elts'):  # looks like astroid.List
        mapping = indexable.elts
    elif hasattr(indexable, 'items'):  # looks like astroid.Dict
        try:
            mapping = {
                next(k.infer()).value: v for k, v in indexable.items
            }
        except (AttributeError, TypeError):
            mapping = {}  # unable to infer constant key values for lookup
    else:
        return None
    try:
        return mapping[i]
    except (TypeError, KeyError, IndexError):
        return None