from __future__ import absolute_import

import astroid
from pylint.checkers import BaseChecker, utils
from pylint.interfaces import IAstroidChecker

from .parse_pb2 import ClassDef, TypeClass, import_module as import_module_
from .evaluation import resolve as _typeof, slice as _slice


_MISSING_IMPORT_IS_ERROR = False
BASE_ID = 59
MESSAGES = {
    'E%02d01' % BASE_ID: (
        'Field %r does not appear in the declared fields of protobuf-'
        'generated class %r and will raise AttributeError on access',
        'protobuf-undefined-attribute',
        'Used when an undefined field of a protobuf generated class is '
        'accessed'
    ),
    'E%02d02' % BASE_ID: (
        'Value %r does not appear in the declared values of protobuf-'
        'generated enum %r and will raise ValueError at runtime',
        'protobuf-enum-value',
        'Used when an undefined enum value of a protobuf generated enum '
        'is built'
    ),
}
PROTOBUF_IMPLICIT_ATTRS = [
    'ByteSize',
    'Clear',
    'ClearExtension',
    'ClearField',
    'CopyFrom',
    'DESCRIPTOR',
    'DiscardUnknownFields',
    'HasExtension',
    'HasField',
    'IsInitialized',
    'ListFields',
    'MergeFrom',
    'MergeFromString',
    'ParseFromString',
    'SerializePartialToString',
    'SerializeToString',
    'SetInParent',
    'WhichOneof',
]
WELLKNOWNTYPE_MODULES = [
    'any_pb2',
    'timestamp_pb2',
    'duration_pb2',
    'fieldmask_pb2',
    'struct_pb2',
    'listvalue_pb2',
]


def wellknowntype(modname):
    return (modname in WELLKNOWNTYPE_MODULES) or \
           (modname.startswith('google.protobuf') and modname.endswith('_pb2'))


def _instanceof(typeclass):
    """
    instanceof ::
        typeclass : TypeClass
        -> Type
    """
    if typeclass is None:
        return None
    assert isinstance(typeclass, TypeClass)
    return typeclass.instance()


def _assign(scope, target, rhs):
    """
    assign ::
        scope : Name -> Maybe[Type]
        target : Name
        rhs : Node
        -> scope' : (Name -> Maybe[Type])
    """
    assert isinstance(target, astroid.AssignName)
    new_scope = scope.copy()
    del scope
    new_type = _typeof(new_scope, rhs)
    new_scope[target.name] = new_type
    return new_scope


def _assignattr(scope, node):
    """
    assignattr ::
        scope : Name -> Maybe[Type]
        node : AssignAttr
        -> Bool, [Warning]
    """
    assert isinstance(node, (astroid.Attribute, astroid.AssignAttr))
    expr, attr = node.expr, node.attrname
    expr_type = _typeof(scope, expr)
    if expr_type is None:
        return True, []  # not something we're tracking?
    try:  # ClassDef, Module, TypeClass
        fields, qualname = expr_type.fields, expr_type.qualname
    except AttributeError:
        return True, []  # unknown expression type
    if fields is None:
        # assert False, "type fields missing for {!r}".format(expr_type)
        return False, []
    if attr not in fields and attr not in PROTOBUF_IMPLICIT_ATTRS:
        msg = ('protobuf-undefined-attribute', (attr, qualname), node)
        return False, [msg]
    return False, []


def visit_assign_node(scope, node):
    assert isinstance(node, (astroid.Assign, astroid.AnnAssign))
    new_scope, old_scope = scope.copy(), scope.copy()
    del scope
    value, messages = node.value, []
    if isinstance(node, astroid.AnnAssign):
        targets = [node.target]
    else:
        targets = node.targets
    for target in targets:
        if isinstance(target, astroid.AssignName):
            # NOTE: we still use old_scope here for every target here since
            # locals is not updated until the end of the assignment, i.e.
            # foo.ref = foo = Foo() will trigger a NameError if foo is not
            # already in scope
            new_scope.update(_assign(old_scope, target, value))
        elif isinstance(target, astroid.AssignAttr):
            skip, m = _assignattr(old_scope, target)
            if not skip:
                messages.extend(m)
        else:
            # assert False, "unexpected case like Subscript, tuple-unpacking etc."
            return old_scope, []  # TODO
    return new_scope, messages


def visit_attribute(scope, node):
    assert isinstance(node, astroid.Attribute)
    skip, messages = _assignattr(scope, node)
    if skip:
        return [], []
    suppressions = []
    if not messages:
        suppressions.append(node)
    return messages, suppressions


def import_(node, module_name, scope):
    """
    import ::
        scope : Name -> Maybe[Type]
        node : Import | ImportFrom
        -> (scope' : Name -> Maybe[Type])
    """
    assert isinstance(node, (astroid.Import, astroid.ImportFrom))
    old_scope, new_scope = scope.copy(), scope.copy()
    del scope
    try:
        mod = node.do_import_module(module_name)
    except (astroid.TooManyLevelsError, astroid.AstroidBuildingException):
        assert not _MISSING_IMPORT_IS_ERROR, 'expected to import module "{}"'.format(module_name)
        return new_scope
    imported_names = []
    if isinstance(node, astroid.ImportFrom):
        imported_names = node.names
    if mod.package:
        for name, alias in imported_names:
            mod2 = mod.import_module(name, relative_only=True)
            new_scope = import_module_(mod2, name, new_scope, [])
            if alias is not None and name in new_scope:
                # modname not in new_scope implies that the module was not
                # successfully imported
                diff = new_scope[name]
                del new_scope[name]
                new_scope[alias] = diff
                if name in old_scope:  # undo overwrite iff name was present
                    new_scope[name] = old_scope[name]
        return new_scope
    else:
        return import_module_(mod, module_name, new_scope, imported_names)


def issubset(left, right):
    """A subset relation for dictionaries"""
    return set(left.keys()) <= set(right.keys())


class ProtobufDescriptorChecker(BaseChecker):
    __implements__ = IAstroidChecker
    msgs = MESSAGES
    name = 'protobuf-descriptor-checker'
    priority = 0  # need to be higher than builtin typecheck lint

    def __init__(self, linter):
        self.linter = linter
        self._scope = None

    def visit_module(self, _):
        self._scope = {}

    def leave_module(self, _):
        self._scope = {}

    def visit_import(self, node):
        for modname, alias in node.names:
            if wellknowntype(modname):
                continue
            if not modname.endswith('_pb2'):
                continue
            self._import_node(node, modname, alias)

    def visit_importfrom(self, node):
        if wellknowntype(node.modname):
            return
        if not node.modname.endswith('_pb2'):
            for name, _ in node.names:
                if wellknowntype(name):
                    continue
                # NOTE: aliasing of module imports is handled in import_
                if name.endswith('_pb2'):
                    self._import_node(node, node.modname)
        else:
            self._import_node(node, node.modname)

    def _import_node(self, node, modname, alias=None):
        old_scope = self._scope.copy()
        new_scope = import_(node, modname, self._scope)
        assert issubset(self._scope, new_scope)
        if alias is not None and modname in new_scope:
            # modname not in new_scope implies that the module was not
            # successfully imported
            diff = new_scope[modname]
            del new_scope[modname]
            new_scope[alias] = diff
            if modname in old_scope:
                new_scope[modname] = old_scope[modname]
        self._scope = new_scope

    @utils.check_messages('protobuf-undefined-attribute')
    def visit_annassign(self, node):
        self._visit_assign(node)

    @utils.check_messages('protobuf-undefined-attribute')
    def visit_assign(self, node):
        self._visit_assign(node)

    def _visit_assign(self, node):
        new_scope, messages = visit_assign_node(self._scope, node)
        assert issubset(self._scope, new_scope)
        self._scope = new_scope
        for code, args, target in messages:
            self.add_message(code, args=args, node=target)

    def visit_assignattr(self, node):
        pass

    def visit_delattr(self, node):
        pass

    @utils.check_messages('protobuf-undefined-attribute')
    def visit_attribute(self, node):
        messages, suppressions = visit_attribute(self._scope, node)
        for code, args, target in messages:
            self.add_message(code, args=args, node=target)
            self._disable('no-member', target.lineno)
        for target in suppressions:
            self._disable('no-member', target.lineno)

    def _disable(self, msgid, line, scope='module'):
        try:
            self.linter.disable(msgid, scope=scope, line=line)
        except AttributeError:
            pass  # might be UnittestLinter


def register(linter):
    linter.register_checker(ProtobufDescriptorChecker(linter))
