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


def _extract_fields(node):
    return ['name', 'id', 'email']  # TODO


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
        if not isinstance(assignment, astroid.Assign):
            return
        if len(assignment.targets) > 1:
            # not going to bother with this case
            return
        target = assignment.targets[0]
        if not isinstance(target, astroid.AssignName):
            return
        func = node.func
        if isinstance(func, astroid.Attribute):
            name = func.attrname
        else:
            name = func.name
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
            if attr.attrname not in cls_fields:
                self.add_message('protobuf-undefined-attribute',
                                 args=(attr.attrname, cls_name), node=attr)

    def _load_known_classes(self, importnode, modname):
        try:
            mod = importnode.do_import_module(modname)
        except astroid.TooManyLevelsError as ex:
            raise  # TODO
        except astroid.AstroidBuildingException as ex:
            raise  # TODO
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
                self._known_classes[imported_name] = _extract_fields(node)


# just need to fill out typecheck.py / generated-members it looks like?
#
# not really, we actually want to throw a lint on attribute assignment (which
# pylint doesn't do except with +=/augmented-assignment, since it assumes the
# default Python behaviour of setting the attribute before "access" is always
# fine).
#
# e.g. regular Python class:
# >>> class Foo(): pass
# >>> foo = Foo()
# >>> foo.bar = 123  # fine
#
# Protobuf-specified class:
# >>> from test_pb2 import Bar  # only defines 'id' field
# >>> bar = Bar()
# >>> bar.baz = 123  # AttributeError

def register(linter):
    linter.register_checker(ProtobufDescriptorChecker(linter))
