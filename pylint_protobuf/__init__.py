from typing import Union

import astroid
from pylint.checkers import BaseChecker, utils
from pylint.interfaces import IAstroidChecker


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
PROTOBUF_ENUM_IMPLICIT_ATTRS = [
    'Name',
    'Value',
    'keys',
    'values',
    'items',
]  # See google.protobuf.internal.enum_type_wrapper
WELLKNOWNTYPE_MODULES = [
    'any_pb2',
    'descriptor_pb2',
    'duration_pb2',
    'empty_pb2',
    'field_mask_pb2',
    'struct_pb2',
    'timestamp_pb2',
    'type_pb2',
    'wrappers_pb2',
]


def wellknowntype(modname):
    return (modname in WELLKNOWNTYPE_MODULES) or \
           (modname.startswith('google.protobuf') and modname.endswith('_pb2'))


class ProtobufDescriptorChecker(BaseChecker):
    __implements__ = IAstroidChecker
    msgs = MESSAGES
    name = 'protobuf-descriptor-checker'
    priority = 0  # need to be higher than builtin typecheck lint

    def __init__(self, linter):
        self.linter = linter

    def visit_import(self, node):
        # type: (astroid.Import) -> None
        for modname, _ in node.names:
            self._check_import(node, modname)

    def visit_importfrom(self, node):
        # type: (astroid.ImportFrom) -> None
        self._check_import(node, node.modname)

    def _check_import(self, node, modname):
        # type: (Union[astroid.Import, astroid.ImportFrom], str) -> None
        if not _MISSING_IMPORT_IS_ERROR or not modname.endswith('_pb2'):
            return  # only relevant when testing
        try:
            node.do_import_module(modname)
        except astroid.AstroidBuildingError:
            assert not _MISSING_IMPORT_IS_ERROR, 'expected to import module "{}"'.format(modname)

    @utils.check_messages('protobuf-undefined-attribute')
    def visit_assignattr(self, node):
        # type: (astroid.AssignAttr) -> None
        self._assignattr(node)

    @utils.check_messages('protobuf-undefined-attribute')
    def visit_attribute(self, node):
        # type: (astroid.Attribute) -> None
        self._assignattr(node)

    def _assignattr(self, node):
        # type: (Union[astroid.Attribute, astroid.AssignAttr]) -> None
        try:
            vals = node.expr.inferred()
        except astroid.InferenceError:
            return  # TODO: warn or redo
        # Look for any version of the inferred type to be a Protobuf class
        for val in vals:
            cls_def = None
            if hasattr(val, '_proxied'):
                cls_def = val._proxied  # type: astroid.ClassDef
            elif isinstance(val, astroid.Module):
                return self._check_module(val, node)  # FIXME: move
            elif isinstance(val, astroid.ClassDef):
                cls_def = val
            if cls_def and getattr(cls_def, '_is_protobuf_class', False):
                break
        else:
            # couldn't find cls_def
            return
        self._disable('no-member', node.lineno)  # Should always be checked by us instead
        if node.attrname not in cls_def._protobuf_fields:
            if node.attrname in PROTOBUF_IMPLICIT_ATTRS + PROTOBUF_ENUM_IMPLICIT_ATTRS:  # FIXME: move to definition
                return
            self.add_message('protobuf-undefined-attribute', args=(node.attrname, cls_def.name), node=node)
            self._disable('assigning-non-slot', node.lineno)

    def _check_module(self, mod, node):
        # type: (astroid.Module, astroid.Attribute) -> None
        if not is_some_protobuf_module(mod):
            return
        if node.attrname not in mod.locals:
            self.add_message('protobuf-undefined-attribute', args=(node.attrname, mod.name), node=node)

    def _disable(self, msgid, line, scope='module'):
        try:
            self.linter.disable(msgid, scope=scope, line=line)
        except AttributeError:
            pass  # might be UnittestLinter


def register(linter):
    linter.register_checker(ProtobufDescriptorChecker(linter))

from astroid import MANAGER
from pylint_protobuf.transform import transform_module, is_some_protobuf_module
MANAGER.register_transform(astroid.Module, transform_module, is_some_protobuf_module)
