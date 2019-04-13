import astroid
from pylint.checkers import BaseChecker, utils
from pylint.interfaces import IAstroidChecker

BASE_ID = 59
MESSAGES = {
    'E%02d01' % BASE_ID: (
        'Field %r does not appear in the declared fields of protobuf-'
        'generated class %r and will raise AttributeError on access',
        'protobuf-undefined-attribute',
        'Used when an undefined field of a protobuf generated class is '
        'accessed'
    ),
}


def _slice(subscript):
    """
    slice ::
        (Subscript (Node value) (Node idx))
        -> Maybe[Node]
    """
    value, idx = subscript.value, subscript.slice
    indexable = next(value.infer())
    index = next(idx.infer())
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
        except AttributeError:
            mapping = {}  # unable to infer constant key values for lookup
    else:
        return None
    try:
        return mapping[i]
    except (TypeError, KeyError):
        return None


class TypeClass(object):
    __slots__ = ('t',)

    def __init__(self, t):
        self.t = t


def _instanceof(typeclass):
    """
    instanceof ::
        typeclass : TypeClass
        -> Type
    """
    if typeclass is None:
        return None
    assert isinstance(typeclass, TypeClass)
    return typeclass.t


class Module(object):
    __slots__ = ('original_name',)

    def __init__(self, original_name):
        self.original_name = original_name


def _typeof(scope, node):
    """
    typeof ::
        scope : Name -> Maybe[Type]
        node : Node
        -> Maybe[Type]
    """
    if isinstance(node, (astroid.Name, astroid.AssignName)):
        return scope.get(node.name)
    elif isinstance(node, astroid.Subscript):
        return _typeof(scope, _slice(node))
    elif isinstance(node, astroid.Call):
        return _instanceof(_typeof(scope, node.func))
    elif isinstance(node, astroid.Const):
        return None
        # NOTE: not returning type(node.value) anymore as it breaks assumptions
        # around _instanceof
    else:
        if node is None:
            return None  # node may be Uninferable
        return scope.get(node.as_string())


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


def _assignattr(scope, type_fields, node, _):
    """
    assignattr ::
        scope : Name -> Maybe[Type]
        type_fields : Type -> [str]
        node : AssignAttr
        rhs : Node
        -> [Warning]
    """
    assert isinstance(node, astroid.AssignAttr)
    expr, attr = node.expr, node.attrname
    expr_type = _typeof(scope, expr)
    if expr_type is None:
        return []  # not something we're tracking?
    fields = type_fields.get(expr_type)
    if fields is None:
        assert False, "type fields missing for {!r}".format(expr_type)
    if attr not in fields:
        return [('protobuf-undefined-attribute', (attr, expr_type), node)]
    return []


def visit_assign_node(scope, type_fields, node):
    assert isinstance(node, astroid.Assign)
    assert len(node.targets) == 1, "TODO: multiple assignment"
    target, value = node.targets[0], node.value
    if isinstance(target, astroid.AssignName):
        return _assign(scope, target, value), []
    if isinstance(target, astroid.AssignAttr):
        return scope, _assignattr(scope, type_fields, target, value)
    assert False, "unexpected case like Subscript, tuple-unpacking etc."


def visit_getattr(scope, type_fields, node):
    assert False, "TODO"


def _parse_fields(iterable):
    """
    Lift field names from keyword arguments to descriptor_pb2.FieldDescriptor.

    >>> _parse_fields([FieldDescriptor(name='a'), FieldDescriptor(name='b')])
    ['a', 'b']
    """
    fields = []
    for call in iterable:
        if not isinstance(call, astroid.Call):
            return None
        for kw in call.keywords:
            if kw.arg == 'name':
                value = getattr(kw.value, 'value', None)
                if value is not None:
                    fields.append(value)
    return fields


def _parse_descriptor(node):
    """
    Walk the nodes of a descriptor_pb2.Descriptor to find the fields keyword.
    """
    if node is None:
        return None
    node = node[0]
    assignment = node.parent
    if not isinstance(assignment, astroid.Assign):
        return None
    call = assignment.value
    if not isinstance(call, astroid.Call):
        return None
    for kw in call.keywords:
        if kw.arg == 'fields':
            return _parse_fields(kw.value.itered())
    return None


def _extract_fields(node, module_globals=None):
    """
    Given a "name = type(...)"-style assignment, look up the variable
    corresponding to the protobuf-generated descriptor in the module and parse
    out the names of its fields.

    ```
    Person = _reflection.GeneratedProtocolMessageType(
        'Person', (_message.Message,), dict(
            DESCRIPTOR = _PERSON,  # parse AST of _PERSON for field names
            __module__ = 'person_pb2'
        )
    )
    ```
    """
    if module_globals is None:
        module_globals = {}

    def parse_name(var):
        if not isinstance(var, astroid.Name):
            return None
        return _parse_descriptor(module_globals.get(var.name))
    if not isinstance(node, astroid.AssignName):
        return None
    call = node.parent.value
    if not isinstance(call, astroid.Call) or len(call.args) < 3:
        return None
    type_dict = call.args[2]
    if isinstance(type_dict, astroid.Call):
        for kw in type_dict.keywords:
            if kw.arg == 'DESCRIPTOR':
                var = kw.value
                return parse_name(var)
    elif isinstance(type_dict, astroid.Dict):
        for key, var in type_dict.items:
            if getattr(key, 'value', None) == 'DESCRIPTOR':
                return parse_name(var)
    return None


def _do_import(node, module_name, scope, type_fields):
    assert isinstance(node, (astroid.Import, astroid.ImportFrom))
    new_scope = scope.copy()
    new_fields = type_fields.copy()
    del type_fields, scope
    try:
        mod = node.do_import_module(module_name)
    except astroid.TooManyLevelsError:
        return
    except astroid.AstroidBuildingException:
        return  # TODO: warn about not being able to import?

    imported_names = None  # ignore aliases of modules
    if isinstance(node, astroid.ImportFrom):
        imported_names = node.names
    aliases = {
        name: alias
        for name, alias in (imported_names or [])
        if alias is not None
    }

    def likely_name(n):
        if imported_names is not None:
            # NOTE: only map aliases when mapping names to fields, not when
            # checking mod.globals (since they haven't been renamed yet).
            return any(n == name for name, _ in imported_names)
        return not n.startswith('_') and n not in ('sys', 'DESCRIPTOR')

    def qualified_name(n):
        if isinstance(node, astroid.Import):
            return '{}.{}'.format(module_name, n)
        return aliases.get(n, n)

    for original_name, nodes in mod.globals.items():
        if likely_name(original_name):
            # FIXME: multiple nodes, renamings?
            fields = _extract_fields(nodes[0], mod.globals)
            if fields is not None:
                imported_name = qualified_name(original_name)
                new_fields[imported_name] = fields
                new_scope[imported_name] = TypeClass(imported_name)
    new_scope[module_name] = Module(module_name)
    return new_scope, new_fields


def import_(node, modname, scope, type_fields):
    """
    import ::
        scope : Name -> Maybe[Type]
        type_fields : Type -> [str]
        node : Import | ImportFrom
        -> (scope' : Name -> Maybe[Type], type_fields': Type -> [str])
    """
    new_scope, new_fields = _do_import(node, modname, scope, type_fields)
    return new_scope, new_fields


def _try_infer_subscript(node):
    """
    Assumed structure is now:
    <target> = <exp>[<index>]()
               ^ .value
                     ^ .slice
               \____________/ <- .call.func

    Here, :param:`node` equals the .func of Call
    """
    value, idx = node.value, node.slice
    indexable = next(value.infer())
    index = next(idx.infer())
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
        except AttributeError:
            mapping = {}  # unable to infer constant key values for lookup
    else:
        return None
    try:
        name = mapping[i]
    except (TypeError, KeyError):
        # no such luck
        return None
    else:
        # Hopefully `name` refers to eithar a ClassDef or an imported Name from
        # a protobuf-generated module which we can match up with `well_known`
        # names
        if not isinstance(name, astroid.Name):
            return None
        return name.name


def issubset(left, right):
    """A subset relation for dictionaries"""
    return set(left.keys()) <= set(right.keys())


class ProtobufDescriptorChecker(BaseChecker):
    __implements__ = IAstroidChecker
    msgs = MESSAGES
    name = 'protobuf-descriptor-checker'

    def __init__(self, linter):
        self.linter = linter
        self._seen_imports = None
        self._known_classes = None
        self._known_variables = None
        self._scope = None
        self._type_fields = None

    def visit_module(self, _):
        self._seen_imports = []
        self._known_classes = {}
        self._known_variables = {}
        self._scope = {}
        self._type_fields = {}

    def leave_module(self, _):
        self._seen_imports = []
        self._known_classes = {}
        self._known_variables = {}
        self._scope = {}
        self._type_fields = {}

    def visit_import(self, node):
        for modname, alias in node.names:
            self._import_node(node, modname, alias)

    def visit_importfrom(self, node):
        self._import_node(node, node.modname)

    def _import_node(self, node, modname, alias=None):
        if not modname.endswith('_pb2'):
            return
        new_scope, new_fields = import_(node, modname, self._scope, self._type_fields)
        assert issubset(self._scope, new_scope)
        assert issubset(self._type_fields, new_fields)
        if alias is not None:
            diff = new_scope[modname]
            del new_scope[modname]
            new_scope[alias] = diff
        self._scope = new_scope
        self._type_fields = new_fields

    @utils.check_messages('protobuf-undefined-attribute')
    def visit_assign(self, node):
        new_scope, messages = visit_assign_node(self._scope, self._type_fields, node)
        assert issubset(self._scope, new_scope)
        self._scope = new_scope
        if messages:
            assert len(messages) == 1, "unexpected"
        for code, args, target in messages:
            self.add_message(code, args=args, node=target)

    def visit_assignattr(self, node):
        pass

    def visit_delattr(self, node):
        self.visit_attribute(node)

    @utils.check_messages('protobuf-undefined-attribute')
    def visit_attribute(self, node):
        obj = node.expr
        if not isinstance(obj, astroid.Name):
            return
        attr = node
        if obj.name in self._seen_imports:
            if attr.attrname in self._type_fields:
                self.visit_call(attr.parent)
        elif obj.name in self._known_variables:
            cls_name = self._known_variables[obj.name]
            cls_fields = self._type_fields[cls_name]
            if attr.attrname not in cls_fields and attr.attrname not in [
                "ByteSize",
                "Clear",
                "ClearExtension",
                "ClearField",
                "CopyFrom",
                "DESCRIPTOR",
                "DiscardUnknownFields",
                "HasExtension",
                "HasField",
                "IsInitialized",
                "ListFields",
                "MergeFrom",
                "MergeFromString",
                "ParseFromString",
                "SerializePartialToString",
                "SerializeToString",
                "SetInParent",
                "WhichOneof"
            ]:
                self.add_message('protobuf-undefined-attribute',
                                 args=(attr.attrname, cls_name), node=attr)

    def _load_known_classes(self, importnode, modname):
        try:
            mod = importnode.do_import_module(modname)
        except astroid.TooManyLevelsError:
            pass
        except astroid.AstroidBuildingException as ex:
            pass  # TODO: warn about not being able to import?
        else:
            imported_names = None  # ignore aliases of modules
            if isinstance(importnode, astroid.ImportFrom):
                imported_names = importnode.names
            self._walk_protobuf_generated_module(mod, imported_names)

    def _walk_protobuf_generated_module(self, mod, imported_names):
        # type: (str, int) -> None
        #Optional[List[Tuple[str, Optional[str]]]]) -> None
        def likely_name(n):
            if imported_names is not None:
                # NOTE: only map aliases when mapping names to fields, not when
                # checking mod.globals (since they haven't been renamed yet).
                return any(n == name for name, _ in imported_names)
            return not n.startswith('_') and n not in ('sys', 'DESCRIPTOR')
        aliases = {
            name: alias
            for name, alias in (imported_names or [])
            if alias is not None
        }
        for original_name, node in mod.globals.items():
            if likely_name(original_name):
                imported_name = aliases.get(original_name, original_name)
                fields = _extract_fields(node[0], mod.globals)
                if fields is not None:
                    self._known_classes[imported_name] = fields


def register(linter):
    linter.register_checker(ProtobufDescriptorChecker(linter))
