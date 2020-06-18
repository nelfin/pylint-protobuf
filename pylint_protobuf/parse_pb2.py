from collections import defaultdict

import astroid


class TypeTags(object):
    NONE = -1
    OBJECT = 11


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

    @property
    def fields(self):
        return self.t.fields

    @property
    def qualname(self):
        return self.t.qualname

    def instance(self):
        # TODO: clarify/unify this and ClassDef
        return self.t


class Module(object):
    __slots__ = ('original_name', 'module_globals')

    def __init__(self, original_name, module_globals):
        self.original_name = original_name
        self.module_globals = module_globals

    def getattr(self, var):
        qualified_name = '{}.{}'.format(self.original_name, var)
        return self.module_globals.get(qualified_name)

    @property
    def fields(self):
        return [self.unqualified_name(k) for k in self.module_globals]

    @property
    def qualname(self):
        return self.original_name

    def unqualified_name(self, n):
        return n[len(self.original_name)+1:]  # +1 = include dot

    def __repr__(self):
        return "Module({}, {})".format(self.original_name, self.module_globals)


def build_field(call):
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


def parse_fields(iterable, inner_fields, qualname):
    # XXX pass whole field lookup for arbitrary nesting
    """
    Lift field names from keyword arguments to descriptor_pb2.FieldDescriptor.

    >>> parse_fields([FieldDescriptor(name='a'), FieldDescriptor(name='b')])
    ['a', 'b']
    """
    fields = {}
    for call in iterable:
        if not isinstance(call, astroid.Call):
            return None
        name, type_ = build_field(call)
        if type_ == TypeTags.OBJECT:
            # XXX: guard against mutually recursive types
            try:
                desc = parse_descriptor([inner_fields[name]], inner_fields, qualname)
            except KeyError:
                continue
            fully_qualified_name = '{}.{}'.format(qualname, name)
            fields[name] = ClassDef(desc, fully_qualified_name)
        elif type_ == TypeTags.NONE:  # EnumValueDescriptor?
            fields[name] = SimpleField(name)
        else:
            fields[name] = SimpleField(name)  # FIXME
    return fields


def parse_descriptor(node, candidates, qualname):
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
            return parse_fields(kw.value.itered(), candidates, qualname)
    return None


def parse_field_name(arg, parse_name_func):
    if isinstance(arg, astroid.Call):
        for kw in arg.keywords:
            if kw.arg == 'DESCRIPTOR':
                var = kw.value
                return parse_name_func(var)
    elif isinstance(arg, astroid.Dict):
        for key, var in arg.items:
            if getattr(key, 'value', None) == 'DESCRIPTOR':
                return parse_name_func(var)
    return None


def parse_generated_protocol_message(call, module_globals, inner_fields, qualname):
    def parse_name(var):
        if not isinstance(var, astroid.Name):
            return None
        outer_node = module_globals.get(var.name)
        filtered_fields = inner_fields.get(var.name, {})
        return parse_descriptor(outer_node, filtered_fields, qualname)
    if not isinstance(call, astroid.Call) or len(call.args) < 3:
        return None
    type_dict = call.args[2]
    return parse_field_name(type_dict, parse_name)


def parse_enum_descriptor(node, candidates, qualname):
    # TODO: docstring, unify with above
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
        if kw.arg == 'values':
            fields = parse_fields(kw.value.itered(), candidates, qualname)
            fields['Value'] = SimpleField('Value')  # implicit
            return fields
    return None


def parse_enum_type_wrapper(rhs, module_globals, qualname):
    def parse_name(var):
        if not isinstance(var, astroid.Name):
            return None
        outer_node = module_globals.get(var.name)
        filtered_fields = {}  # FIXME
        return parse_enum_descriptor(outer_node, filtered_fields, qualname)
    enum_descriptor = rhs.args[0]
    return parse_name(enum_descriptor)


def add_inner_types(rhs, contained_types, additions):
    retval = additions.copy()
    del additions
    for arg in rhs.args:
        if type(arg) is not astroid.Call and type(arg) is not astroid.Dict:
            continue
        name = parse_field_name(arg, lambda a: a.name)
        if name in contained_types:
            field_name, _ = build_field(contained_types[name])
            retval[field_name] = SimpleField(field_name)  # FIXME: inner fields
    return retval


def parse_enum_value(node, value):
    return {node.name: TypeClass(value.pytype())}


def extract_fields(node, module_globals, inner_fields, qualname, contained_types=None):
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

    if not isinstance(node, astroid.AssignName):
        return None
    rhs = node.parent.value
    if isinstance(rhs, astroid.Const):
        return parse_enum_value(node, rhs)
    try:
        attr_name = rhs.func.attrname
    except AttributeError:
        return None
    if attr_name == "GeneratedProtocolMessageType":
        retval = parse_generated_protocol_message(rhs, module_globals, inner_fields, qualname)
        retval = add_inner_types(rhs, contained_types, retval)
        return retval
    if attr_name == "EnumTypeWrapper":
        return parse_enum_type_wrapper(rhs, module_globals, qualname)
    return None


###


def parse_message_type(node):
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
            message_type = parse_message_type(c)
            if message_type is None:
                continue
            outer, field, inner = message_type
            candidates[outer][field] = mod_node.getattr(inner)[0]
    return candidates


def find_message_types_by_name(mod_node):
    pass


def parse_containing_type(node):
    try:
        parent = node.parent.value.name
        child = node.expr.name
    except AttributeError:
        return None
    else:
        return parent, child


def find_containing_types(mod_node):
    candidates = defaultdict(dict)
    for c in mod_node.nodes_of_class(astroid.AssignAttr):
        if c.attrname == 'containing_type':
            message_type = parse_containing_type(c)
            if message_type is None:
                continue
            parent, child = message_type
            candidates[parent] = mod_node.getattr(child)[0].parent.value
    return candidates


###


def import_module(mod, module_name, scope, imported_names):
    new_scope = scope.copy()
    del scope
    inner_fields = find_fields_by_name(mod)
    find_message_types_by_name(mod)
    contained_types = find_containing_types(mod)

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

    def unqualified_name(n):
        return n[len(module_name)+1:]  # +1 = include dot

    new_names = {}
    for original_name, nodes in mod.globals.items():
        if likely_name(original_name):
            # FIXME: multiple nodes, renamings?
            imported_name = qualified_name(original_name)
            fields = extract_fields(nodes[0], mod.globals, inner_fields,
                                    imported_name, contained_types)
            if fields is not None:
                cls = ClassDef(fields, imported_name)
                new_names[imported_name] = TypeClass(cls)

    new_scope[module_name] = Module(module_name, new_names)
    for name, alias in imported_names:  # check aliasing for ImportFrom
        if name == '*':
            for qualname in new_names:
                new_scope[unqualified_name(qualname)] = new_names[qualname]
            break  # it's a SyntaxError to have other clauses with a *-import
        if alias is None:
            alias = name
        new_scope[alias] = new_names[qualified_name(name)]
    return new_scope
