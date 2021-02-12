from functools import lru_cache
from typing import Any, List, Tuple, Union
import textwrap

import astroid

try:
    from google.protobuf.pyext._message import (
        Descriptor,
        EnumDescriptor,
        FieldDescriptor,
    )
except ImportError:
    import sys
    import warnings
    if sys.version_info >= (3, 9):
        warnings.warn(
            "google.protobuf (earlier than 3.15.x) does not support Python 3.9"
            " (see https://github.com/protocolbuffers/protobuf/issues/7978)"
        )
    class Descriptor:
        pass
    class EnumDescriptor:
        pass
    class FieldDescriptor:
        pass

try:
    from google.protobuf.internal.containers import ScalarMap, MessageMap
except ImportError:
    class MessageMap:
        pass
    class ScalarMap:
        pass

def _template_enum(desc):
    # type: (EnumDescriptor) -> str
    body = ''.join(
        '{} = {}\n'.format(name, value.number)
        for name, value in desc.values_by_name.items()
    )
    return 'class {name}(object):\n    __slots__ = {slots}\n{body}'.format(
        name=desc.name,
        slots=repr(tuple(desc.values_by_name)),
        body=textwrap.indent(body, '    '),
    )

def transform_enum(desc):
    # type: (EnumDescriptor) -> List[Tuple[str, Union[astroid.ClassDef, astroid.Assign]]]
    cls_def = astroid.extract_node(_template_enum(desc))  # type: astroid.ClassDef
    cls_def._is_protobuf_class = True
    cls_def._is_protobuf_enum = True
    cls_def._protobuf_fields = set(desc.values_by_name)
    names = []  # type: List[Tuple[str, astroid.Assign]]
    for type_wrapper in desc.values:
        name, number = type_wrapper.name, type_wrapper.number
        names.append((name, astroid.extract_node('{} = {}'.format(name, number))))
    return [(cls_def.name, cls_def)] + names

def inner_types(desc):
    # type: (Descriptor) -> str
    fragments = []
    for enum_desc in desc.enum_types:
        fragments.append(_template_enum(enum_desc))
    for inner_desc in desc.nested_types:
        fragments.append(_template_message(inner_desc))
    return textwrap.indent('\n'.join(fragments), '    ')

def mark_as_protobuf(cls_def):
    # type: (astroid.ClassDef) -> None
    cls_def._is_protobuf_class = True
    cls_def._protobuf_fields = set(s.value for s in cls_def.slots())  # FIXME: descriptors?, duplication?
    for name, val in cls_def.locals.items():
        val = val[0]  # assert len(val) == 1?
        if isinstance(val, astroid.ClassDef):
            mark_as_protobuf(val)

def _names(desc):
    # type: (Descriptor) -> Tuple[str]
    return tuple(desc.fields_by_name) + tuple(desc.enum_values_by_name) + tuple(desc.enum_types_by_name) + tuple(desc.nested_types_by_name)


def partition_message_fields(desc):
    # type: (Descriptor) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]
    message_fields = [f for f in desc.fields if f.type == FieldDescriptor.TYPE_MESSAGE]  # type: List[FieldDescriptor]
    inner_fields = [
        (f.name, f.message_type.name) for f in message_fields
        if f.message_type.containing_type is desc
    ]
    external_fields = [
        (f.name, f.message_type.name) for f in message_fields
        if f.message_type.containing_type is not desc
    ]
    return inner_fields, external_fields

def _template_message(desc):
    # type: (Descriptor) -> str
    name = desc.name
    inner_fragments = inner_types(desc)
    slots = _names(desc)
    inner_fields, external_fields = partition_message_fields(desc)
    args = list(slots) + [name for name, _ in inner_fields] + [name for name, _ in external_fields]
    args = ['self'] + ['{}=None'.format(arg) for arg in args]
    # NOTE: the "pass" statement is a hack to provide a body when struct_fields is empty
    init_str = 'def __init__({}):\n    pass\n'.format(', '.join(args)) + ''.join(
        '    self.{} = self.{}()\n'.format(field_name, field_type)
        for field_name, field_type in inner_fields
    ) + ''.join(
        '    self.{} = {}()\n'.format(field_name, field_type)
        for field_name, field_type in external_fields
    )
    helpers = ""
    if desc.has_options and desc.GetOptions().map_entry:
        # for map <key, value> fields
        # This mirrors the _IsMessageMapField check
        value_type = desc.fields_by_name['value']
        if value_type.cpp_type == FieldDescriptor.CPPTYPE_MESSAGE:
            base_class = MessageMap
        else:
            base_class = ScalarMap
        # Rather than (key, value), use the attributes of the correct
        # MutableMapping type as the "slots"
        slots = tuple(m for m in dir(base_class) if not m.startswith("_"))
        helpers = 'def __getitem__(self, idx):\n    pass\n'
        helpers += 'def __delitem__(self, idx):\n    pass\n'
    cls_str = 'class {name}(object):\n    __slots__ = {slots}\n{helpers}{body}{init}'.format(
        name=name,
        slots=slots,
        body=inner_fragments,
        helpers=textwrap.indent(helpers, '    '),
        init=textwrap.indent(init_str, '    '),
    )
    return cls_str

def transform_message(desc):
    # type: (Any) -> List[Tuple[str, astroid.ClassDef]]
    cls_str = _template_message(desc)
    cls = astroid.extract_node(cls_str)  # type: astroid.ClassDef
    mark_as_protobuf(cls)
    return [(cls.name, cls)]

def transform_descriptor_to_class(cls):
    # type: (Any) -> List[Tuple[str, Union[astroid.ClassDef, astroid.Name]]]
    desc = cls.DESCRIPTOR
    if isinstance(desc, EnumDescriptor):
        return transform_enum(desc)
    elif isinstance(desc, Descriptor):
        return transform_message(desc)
    else:
        raise NotImplementedError()


@lru_cache()
def _exec_module(mod):
    # type: (astroid.Module) -> dict
    l = {}
    exec(mod.as_string(), {}, l)
    return l


def mod_node_to_class(mod, name):
    # type: (astroid.Module, str) -> Any
    ns = _exec_module(mod)
    return ns[name]


def transform_import(node):
    # have to transform imports into class definitions
    # or is there a way to modify the inferred value of the names when doing a function call?

    # turn an import into a series of class definitions assigned to some object, or inner class definitions?
    # a la:
    # class person_pb2:
    #     class Person:
    #          __slots__ = ('name', )
    raise NotImplementedError()


def transform_module(mod):
    # type: (astroid.Module) -> astroid.Module

    for name in mod.wildcard_import_names():
        cls = mod_node_to_class(mod, name)
        try:
            for local_name, node in transform_descriptor_to_class(cls):
                mod.locals[local_name] = [node]
        except (NotImplementedError, AttributeError):
            pass

    return mod


def is_some_protobuf_module(node):
    # type: (astroid.Module) -> bool
    modname = node.name
    return modname.endswith('_pb2') and not modname.startswith('google.')
