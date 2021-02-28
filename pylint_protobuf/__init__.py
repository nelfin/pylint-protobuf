from typing import Union, Optional, List

import astroid
from pylint.checkers import BaseChecker, utils
from pylint.interfaces import IAstroidChecker

from .transform import transform_module, is_some_protobuf_module, to_pytype, is_composite, is_repeated
from .transform import SimpleDescriptor, PROTOBUF_IMPLICIT_ATTRS, PROTOBUF_ENUM_IMPLICIT_ATTRS

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
    'E%02d03' % BASE_ID: (
        'Field "%s.%s" is of type %r and value %r will raise TypeError '
        'at runtime',
        'protobuf-type-error',
        'Used when a scalar field is written to by a bad value'
    ),
    'E%02d04' % BASE_ID: (
        'Positional arguments are not allowed in message constructors and '
        'will raise TypeError',
        'protobuf-no-posargs',
        'Used when a message class is initialised with positional '
        'arguments instead of keyword arguments'
    ),
    'E%02d05' % BASE_ID: (
        'Field "%s.%s" does not support assignment',
        'protobuf-no-assignment',
        'Used when a value is written to a read-only field such as a '
        'composite or repeated field'
    ),
}
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
Node = astroid.node_classes.NodeNG


def wellknowntype(node):
    # type: (astroid.Instance) -> bool
    modname, type_ = node.pytype().rsplit('.', 1)
    return (modname in WELLKNOWNTYPE_MODULES) or \
           (modname.startswith('google.protobuf') and modname.endswith('_pb2'))


def _get_inferred_values(node):
    # type: (Node) -> List[Node]
    try:
        vals = node.inferred()
    except astroid.InferenceError:
        return []
    return [v for v in vals if v is not astroid.Uninferable]


def _get_protobuf_descriptor(node):
    # type: (Node) -> Optional[SimpleDescriptor]
    # Look for any version of the inferred type to be a Protobuf class
    for val in _get_inferred_values(node):
        cls_def = None
        if hasattr(val, '_proxied'):
            # if wellknowntype(val):  # where to put this side-effect?
            #     self._disable('no-member', node.lineno)
            #     return
            cls_def = val._proxied  # type: astroid.ClassDef
        # elif isinstance(val, astroid.Module):
        #     return self._check_module(val, node)  # FIXME: move
        elif isinstance(val, astroid.ClassDef):
            cls_def = val
        if cls_def and getattr(cls_def, '_is_protobuf_class', False):
            break  # getattr guards against Uninferable (always returns self)
    else:
        return # couldn't find cls_def
    return cls_def._protobuf_descriptor  # type: SimpleDescriptor


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

    def visit_call(self, node):
        self._check_enum_values(node)
        self._check_init_posargs(node)
        self._check_init_kwargs(node)
        self._check_repeated_scalar(node)

    @utils.check_messages('protobuf-enum-value')
    def _check_enum_values(self, node):
        if len(node.args) != 1:
            return  # protobuf enum .Value() is only called with one argument
        value_node = node.args[0]
        func = node.func
        if not isinstance(func, astroid.Attribute):
            # NOTE: inference fails on this case
            #   f = Enum.Value  # <-
            #   f('some_value')
            return
        if func.attrname not in ('Value', 'Name'):
            return
        desc = _get_protobuf_descriptor(func.expr)
        if desc is None or not desc.is_enum:
            return
        expected = desc.values if func.attrname == 'Value' else desc.names
        for val_const in _get_inferred_values(value_node):
            if not hasattr(val_const, 'value'):
                continue
            val = val_const.value
            if val not in expected:
                self.add_message('protobuf-enum-value', args=(val, desc.name), node=node)
                break  # should we continue to check?

    @utils.check_messages('protobuf-no-posargs')
    def _check_init_posargs(self, node):
        # type: (astroid.Call) -> None
        desc = _get_protobuf_descriptor(node.func)
        if desc is not None and len(node.args) > 0:
            self.add_message('protobuf-no-posargs', node=node)

    @utils.check_messages('protobuf-type-error')
    def _check_init_kwargs(self, node):
        # type: (astroid.Call) -> None
        desc = _get_protobuf_descriptor(node.func)
        keywords = node.keywords or []
        for kw in keywords:
            arg_name, val_node = kw.arg, kw.value
            if arg_name not in desc.fields_by_name:
                continue  # should raise "unexpected-keyword-arg"
            fd = desc.fields_by_name[arg_name]
            arg_type = to_pytype(fd)
            if is_composite(fd):
                # messages
                for val in _get_inferred_values(val_node):
                    if isinstance(val, astroid.Const):
                        self.add_message('protobuf-type-error', node=node,
                                         args=(desc.name, arg_name, arg_type.__name__, val.value))
                        break
                    val_desc = _get_protobuf_descriptor(val)
                    if val_desc is None:
                        continue  # XXX: ignore?
                    if not val_desc.is_typeof_field(fd):
                        val = '{}()'.format(val_desc.name)
                        self.add_message('protobuf-type-error', node=node,
                                         args=(desc.name, arg_name, arg_type.__name__, val))
            else:
                for val_const in _get_inferred_values(val_node):
                    if not hasattr(val_const, 'value'):
                        try:
                            val = '{}()'.format(val_const.name)
                        except AttributeError:
                            continue
                        self.add_message('protobuf-type-error', node=node,
                                         args=(desc.name, arg_name, arg_type.__name__, val))
                        break
                    val = val_const.value
                    if not isinstance(val, arg_type):
                        self.add_message('protobuf-type-error', node=node,
                                         args=(desc.name, arg_name, arg_type.__name__, val))
                        break

    @utils.check_messages('protobuf-type-error')
    def _check_repeated_scalar(self, node):
        # type: (astroid.Call) -> None
        if len(node.args) != 1:
            return  # append and extend take one argument
        arg_node = node.args[0]
        func = node.func
        if not isinstance(func, astroid.Attribute):
            # NOTE: inference fails on this case
            #   f = Enum.Value  # <-
            #   f('some_value')
            return  # FIXME: check
        if func.attrname not in ('append', 'extend'):
            return

        arg_infer = _get_inferred_values(arg_node)
        if len(arg_infer) != 1:
            return  # no point warning on ambiguous types
        arg = arg_infer[0]

        if func.attrname == 'append':
            if not hasattr(arg, 'value'):
                return
            vals = [arg.value]
        else:  # 'extend'
            if not hasattr(arg, 'elts'):
                return  # FIXME: check how to deal with arbitrary iterables
            vals = []
            for elem in arg.elts:
                c = _get_inferred_values(elem)
                if c is None:
                    continue
                c = c[0]
                if not hasattr(c, 'value'):
                    continue
                vals.append(c.value)

        expr = func.expr
        try:
            desc = _get_protobuf_descriptor(expr.expr)
            arg_name = expr.attrname
        except AttributeError:
            return  # only checking <...>.repeated_field.append()
        try:
            arg_type = to_pytype(desc.fields_by_name[arg_name])
        except KeyError:
            return  # warn?

        def check_arg(val):
            if not isinstance(val, arg_type):
                self.add_message('protobuf-type-error', node=node,
                                 args=(desc.name, arg_name, arg_type.__name__, val))
        for val in vals:
            check_arg(val)

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
            if val is astroid.Uninferable:
                continue
            if hasattr(val, '_proxied'):
                if wellknowntype(val):
                    self._disable('no-member', node.lineno)
                    return
                cls_def = val._proxied  # type: astroid.ClassDef
            elif isinstance(val, astroid.Module):
                return self._check_module(val, node)  # FIXME: move
            elif isinstance(val, astroid.ClassDef):
                cls_def = val
            if cls_def and getattr(cls_def, '_is_protobuf_class', False):
                break  # getattr guards against Uninferable (always returns self)
        else:
            # couldn't find cls_def
            return
        desc = cls_def._protobuf_descriptor  # type: SimpleDescriptor
        self._disable('no-member', node.lineno)  # Should always be checked by us instead
        if node.attrname not in desc.field_names:
            self.add_message('protobuf-undefined-attribute', args=(node.attrname, cls_def.name), node=node)
            self._disable('assigning-non-slot', node.lineno)
        else:
            self._check_type_error(node, desc)
            self._check_no_assign(node, desc)

    @utils.check_messages('protobuf-type-error')
    def _check_type_error(self, node, desc):
        # type: (Node, SimpleDescriptor) -> None
        if not isinstance(node, astroid.AssignAttr):
            return
        attr = node.attrname
        value_node = node.assign_type().value  # type: Node
        fd = desc.fields_by_name[attr]  # this should always pass given the check in _assignattr
        if is_composite(fd) or is_repeated(fd):
            return  # skip this check and resolve in _check_no_assign
        type_ = to_pytype(fd)
        for val_const in _get_inferred_values(value_node):
            if not hasattr(val_const, 'value'):
                continue
            val = val_const.value
            if not isinstance(val, type_):
                self.add_message('protobuf-type-error', node=node, args=(desc.name, attr, type_.__name__, val))
                break

    @utils.check_messages('protobuf-no-assignment')
    def _check_no_assign(self, node, desc):
        # type: (Node, SimpleDescriptor) -> None
        if not isinstance(node, astroid.AssignAttr):
            return
        attr = node.attrname
        fd = desc.fields_by_name[attr]
        if is_composite(fd) or is_repeated(fd):
            self.add_message('protobuf-no-assignment', node=node, args=(desc.name, attr))

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

astroid.MANAGER.register_transform(astroid.Module, transform_module, is_some_protobuf_module)
