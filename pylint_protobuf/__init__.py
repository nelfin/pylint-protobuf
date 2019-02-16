import astroid
from pylint.checkers import BaseChecker, utils
from pylint.interfaces import IAstroidChecker

BASE_ID = 59

messages = {
    'E%02d01' % BASE_ID: (
        'Field %r does not appear in the declared fields of protobuf-'
        'generated class %r and will raise AttributeError on access',
        'protobuf-undefined-attribute',
        'Used when an undefined field of a protobuf generated class is '
        'accessed'
    ),
}


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


def _extract_fields(node, module_globals={}):
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


class ProtobufDescriptorChecker(BaseChecker):
    __implements__ = IAstroidChecker
    msgs = messages
    name = 'protobuf-descriptor-checker'

    def __init__(self, linter):
        self.linter = linter
        self._seen_imports = None
        self._known_classes = None
        self._known_variables = None

    def visit_module(self, node):
        self._seen_imports = []
        self._known_classes = {}
        self._known_variables = {}

    def leave_module(self, node):
        self._seen_imports = []
        self._known_classes = {}
        self._known_variables = {}

    def visit_import(self, node):
        modnode = node.root()
        for name, alias in node.names:
            if name.endswith('_pb2'):
                self._seen_imports.append(alias)
                self._load_known_classes(node, name)

    def visit_importfrom(self, node):
        if node.modname.endswith('_pb2'):
            self._seen_imports.append(node.modname)  # TODO
            self._load_known_classes(node, node.modname)

    def visit_call(self, node):
        if not isinstance(node, astroid.Call):
            return  # NOTE: potentially from visit_attribute
        assignment = node.parent
        if isinstance(assignment, astroid.Assign):
            if len(assignment.targets) > 1:
                # not going to bother with this case
                return
            target = assignment.targets[0]
        elif isinstance(assignment, astroid.AnnAssign):
            target = assignment.target
        else:
            return

        if not isinstance(target, astroid.AssignName):
            return
        func = node.func
        if isinstance(func, astroid.Attribute):
            name = func.attrname
        elif hasattr(func, 'name'):
            name = func.name
        else:
            # TODO: derive name
            name = None
        if name in self._known_classes:
            self._known_variables[target.name] = name

    def visit_assignattr(self, node):
        self.visit_attribute(node)

    def visit_delattr(self, node):
        self.visit_attribute(node)

    @utils.check_messages('protobuf-undefined-attribute')
    def visit_attribute(self, node):
        obj = node.expr
        if not isinstance(obj, astroid.Name):
            return
        attr = node
        if obj.name in self._seen_imports:
            if attr.attrname in self._known_classes:
                self.visit_call(attr.parent)
        elif obj.name in self._known_variables:
            cls_name = self._known_variables[obj.name]
            cls_fields = self._known_classes[cls_name]
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

    # type: imported_names: Optional[List[Tuple[str, Optional[str]]]]
    def _walk_protobuf_generated_module(self, mod, imported_names):
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
