from collections import defaultdict

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


class TypeTags(object):
    OBJECT = 11


def _slice(subscript):
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


class SimpleField(object):
    __slots__ = ('name',)

    def __init__(self, name):
        self.name = name


class ClassDef(object):  # XXX
    def __init__(self, fields, qualname):
        self.fields = fields
        self.qualname = qualname

    def getattr(self, key):
        return self.fields.get(key)


class TypeClass(object):
    __slots__ = ('t',)

    def __init__(self, t):
        self.t = t

    def instance(self):
        # TODO: clarify/unify this and ClassDef
        return self.t


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


class Module(object):
    __slots__ = ('original_name', 'module_globals')

    def __init__(self, original_name, module_globals):
        self.original_name = original_name
        self.module_globals = module_globals

    def getattr(self, var):
        qualified_name = '{}.{}'.format(self.original_name, var)
        return self.module_globals.get(qualified_name)

    def __repr__(self):
        return "Module({}, {})".format(self.original_name, self.module_globals)


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
    elif isinstance(node, astroid.Attribute):
        try:
            namespace = scope.get(node.expr.name)
        except AttributeError:
            return None
        # namespace is something like a module or ClassDef that supports
        # getattr
        try:
            attr = namespace.getattr(node.attrname)
        except AttributeError:
            return None
        else:
            return _typeof(scope, attr)
    elif isinstance(node, (TypeClass, ClassDef)):
        return node
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
    if expr_type is None or isinstance(expr_type, Module):
        return True, []  # not something we're tracking?
    fields = expr_type.fields  # ClassDef
    if fields is None:
        # assert False, "type fields missing for {!r}".format(expr_type)
        return False, []
    if attr not in fields and attr not in PROTOBUF_IMPLICIT_ATTRS:
        msg = ('protobuf-undefined-attribute', (attr, expr_type.qualname), node)
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


def _build_field(call):
    name = ''
    type_ = -1
    for kw in call.keywords:
        if kw.arg == 'name':
            value = getattr(kw.value, 'value', None)
            if value is not None:
                name = value
        if kw.arg == 'type':
            value = getattr(kw.value, 'value', None)
            if value is not None:
                type_ = value
    return name, type_


def _parse_fields(iterable, inner_fields, qualname):
    # XXX pass whole field lookup for arbitrary nesting
    """
    Lift field names from keyword arguments to descriptor_pb2.FieldDescriptor.

    >>> _parse_fields([FieldDescriptor(name='a'), FieldDescriptor(name='b')])
    ['a', 'b']
    """
    fields = {}
    for call in iterable:
        if not isinstance(call, astroid.Call):
            return None
        name, type_ = _build_field(call)
        if type_ == TypeTags.OBJECT:
            # XXX: guard against mutually recursive types
            try:
                desc = _parse_descriptor([inner_fields[name]], inner_fields, qualname)
            except KeyError:
                continue
            fully_qualified_name = '{}.{}'.format(qualname, name)
            fields[name] = ClassDef(desc, fully_qualified_name)
        else:
            fields[name] = SimpleField(name)  # FIXME
    return fields


def _parse_descriptor(node, candidates, qualname):
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
            return _parse_fields(kw.value.itered(), candidates, qualname)
    return None


def _extract_fields(node, module_globals, inner_fields, qualname):
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
    if inner_fields is None:
        inner_fields = {}

    def parse_name(var):
        if not isinstance(var, astroid.Name):
            return None
        outer_node = module_globals.get(var.name)
        filtered_fields = inner_fields.get(var.name, {})
        return _parse_descriptor(outer_node, filtered_fields, qualname)
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


def _parse_message_type(node):
    try:
        outer = node.expr.value.expr.name
        field = node.expr.slice.value.value
    except AttributeError:
        return None
    try:
        inner = node.parent.value.name
    except AttributeError:
        try:
            inner = node.parent.value.expr.name
        except AttributeError:
            return None
    else:
        return outer, field, inner


def find_fields_by_name(mod_node):
    """
    _SOME_TYPE.fields_by_name['some_field'].message_type = _INNER
    """
    candidates = defaultdict(dict)
    for c in mod_node.nodes_of_class(astroid.AssignAttr):
        if c.attrname == 'message_type':
            message_type = _parse_message_type(c)
            if message_type is None:
                continue
            outer, field, inner = message_type
            candidates[outer][field] = mod_node.getattr(inner)[0]
    return candidates


def find_message_types_by_name(mod_node):
    pass


def import_(node, module_name, scope):
    """
    import ::
        scope : Name -> Maybe[Type]
        node : Import | ImportFrom
        -> (scope' : Name -> Maybe[Type])
    """
    assert isinstance(node, (astroid.Import, astroid.ImportFrom))
    new_scope = scope.copy()
    del scope
    try:
        mod = node.do_import_module(module_name)
    except (astroid.TooManyLevelsError, astroid.AstroidBuildingException):
        return new_scope  # TODO: warn about not being able to import?

    inner_fields = find_fields_by_name(mod)
    find_message_types_by_name(mod)

    imported_names = []
    if isinstance(node, astroid.ImportFrom):
        imported_names = node.names

    def likely_name(n):
        # XXX: parse all fields for nested classes
        #
        # if imported_names:
        #     # NOTE: only map aliases when mapping names to fields, not when
        #     # checking mod.globals (since they haven't been renamed yet).
        #     return any(n == name for name, _ in imported_names)
        return not n.startswith('_') and n not in ('sys', 'DESCRIPTOR')

    def qualified_name(n):
        return '{}.{}'.format(module_name, n)

    new_names = {}
    for original_name, nodes in mod.globals.items():
        if likely_name(original_name):
            # FIXME: multiple nodes, renamings?
            imported_name = qualified_name(original_name)
            fields = _extract_fields(nodes[0], mod.globals, inner_fields, imported_name)
            if fields is not None:
                cls = ClassDef(fields, imported_name)
                new_names[imported_name] = TypeClass(cls)

    new_scope[module_name] = Module(module_name, new_names)
    for name, alias in imported_names:  # check aliasing for ImportFrom
        if alias is None:
            alias = name
        new_scope[alias] = new_names[qualified_name(name)]
    return new_scope


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
            self._import_node(node, modname, alias)

    def visit_importfrom(self, node):
        self._import_node(node, node.modname)

    def _import_node(self, node, modname, alias=None):
        if not modname.endswith('_pb2'):
            return
        new_scope = import_(node, modname, self._scope)
        assert issubset(self._scope, new_scope)
        if alias is not None and modname in new_scope:
            # modname not in new_scope implies that the module was not
            # successfully imported
            diff = new_scope[modname]
            del new_scope[modname]
            new_scope[alias] = diff
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
