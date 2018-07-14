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


class ProtobufDescriptorChecker(BaseChecker):
    __implements__ = IAstroidChecker
    msgs = messages
    name = 'protobuf-descriptor-checker'
    _known_classes = {  # TODO
        'Person': ['name', 'id', 'email'],
    }

    def __init__(self, linter):
        self.linter = linter
        self._seen_imports = None
        #self._known_classes = None
        self._known_variables = None

    def visit_module(self, node):
        self._seen_imports = []
        #self._known_classes = {}
        self._known_variables = {}

    def leave_module(self, node):
        self._seen_imports = []
        #self._known_classes = {}
        self._known_variables = {}

    def visit_import(self, node):
        modnode = node.root()
        for name, alias in node.names:
            if name.endswith('_pb2'):
                self._seen_imports.append(alias)

    def visit_importfrom(self, node):
        if node.modname.endswith('_pb2'):
            self._seen_imports.append(node.modname)  # TODO

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
                # look up assignment and add to names to check
                call = attr.parent
                if not isinstance(call, astroid.Call):
                    return
                assignment = call.parent
                if not isinstance(assignment, astroid.Assign):
                    return
                if len(assignment.targets) > 1:
                    # not going to bother with this case
                    return
                target = assignment.targets[0]
                if not isinstance(target, astroid.AssignName):
                    return
                self._known_variables[target.name] = attr.attrname
        elif obj.name in self._known_variables:
            cls_name = self._known_variables[obj.name]
            cls_fields = self._known_classes[cls_name]
            if attr.attrname not in cls_fields:
                self.add_message('protobuf-undefined-attribute',
                                 args=(attr.attrname, cls_name), node=attr)


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
