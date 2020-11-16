import astroid

from .parse_pb2 import ClassDef, TypeClass


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