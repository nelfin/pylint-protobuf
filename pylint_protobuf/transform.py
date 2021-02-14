from functools import lru_cache
from typing import Any, List, Tuple, Set, Dict, Union, MutableMapping
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


class SimpleDescriptor(object):
    def __init__(self, desc):
        # type: (Union[EnumDescriptor, Descriptor]) -> None
        if isinstance(desc, EnumDescriptor):  # do something about this variance
            self._is_protobuf_enum = True
            self._enum_desc = desc
        else:
            self._is_protobuf_enum = False
            self._desc = desc
        self._cls_hash = str(id(self))  # err...

    @property
    def identifier(self):
        # type: () -> str
        return self._cls_hash

    @property
    def name(self):
        # type: () -> str
        if self._is_protobuf_enum:
            return self._enum_desc.name
        else:
            return self._desc.name

    @property
    def options(self):
        if self._desc.has_options:
            return self._desc.GetOptions()
        else:
            class FalseyAttributes(object):
                def __getattr__(self, item):
                    return None
            return FalseyAttributes()

    @property
    def field_names(self):
        # type: () -> Set[str]
        if self._is_protobuf_enum:
            return set(self._enum_desc.values_by_name) | set(PROTOBUF_ENUM_IMPLICIT_ATTRS)
        else:
            desc = self._desc  # type: Descriptor
            return set(desc.fields_by_name) | \
                   set(desc.enum_values_by_name) | \
                   set(desc.enum_types_by_name) | \
                   set(desc.nested_types_by_name) | \
                   set(PROTOBUF_IMPLICIT_ATTRS)

    @property
    def fields_by_name(self):
        # type: () -> Dict[str, FieldDescriptor]
        return self._desc.fields_by_name

    @property
    def values_by_name(self):
        # type: () -> List[Tuple[str, int]]
        assert self._is_protobuf_enum, "Only makes sense for enum descriptors"
        return [(n, v.number) for n, v in self._enum_desc.values_by_name.items()]

    @property
    def message_fields(self):
        # type: () -> List[FieldDescriptor]
        assert not self._is_protobuf_enum, "Only makes sense for message descriptors"
        return [f for f in self._desc.fields if f.type == FieldDescriptor.TYPE_MESSAGE]

    @property
    def enum_types(self):
        return self._desc.enum_types

    @property
    def nested_types(self):
        return self._desc.nested_types

    @property
    def inner_fields(self):
        # type: () -> List[Tuple[str, str]]
        return [
            (f.name, f.message_type.name) for f in self.message_fields
            if f.message_type.containing_type is self._desc
        ]

    @property
    def external_fields(self):
        # type: () -> List[Tuple[str, str]]
        return [
            (f.name, f.message_type.name) for f in self.message_fields
            if f.message_type.containing_type is not self._desc
        ]

    @property
    def repeated_fields(self):
        # type: () -> Set[str]
        return set(
            f.name for f in self._desc.fields
            if f.label == FieldDescriptor.LABEL_REPEATED
            and (f.type != FieldDescriptor.TYPE_MESSAGE)
        )

DescriptorRegistry = MutableMapping[str, SimpleDescriptor]


def _template_enum(desc, descriptor_registry):
    # type: (EnumDescriptor, DescriptorRegistry) -> str
    desc = SimpleDescriptor(desc)
    descriptor_registry[desc.identifier] = desc

    body = ''.join(
        '{} = {}\n'.format(name, value) for name, value in desc.values_by_name
    )
    return (
        'class {name}(object):\n'
        '    {docstring!r}\n'
        '    __slots__ = {slots}\n'
        '{body}\n'
    ).format(
        name=desc.name,
        docstring="descriptor={}".format(desc.identifier),
        slots=repr(tuple(desc.field_names)),
        body=textwrap.indent(body, '    '),
    )


def transform_enum(desc, descriptor_registry):
    # type: (EnumDescriptor, DescriptorRegistry) -> List[Tuple[str, Union[astroid.ClassDef, astroid.Assign]]]

    # NOTE: Only called on top-level enum definitions, so we don't need to
    # recurse like with transform_message
    cls_def = astroid.extract_node(_template_enum(desc, descriptor_registry))  # type: astroid.ClassDef

    cls_def._is_protobuf_class = True
    simple_desc = descriptor_registry[cls_def.doc.split('=')[-1]]  # FIXME: guard?
    cls_def._protobuf_descriptor = simple_desc

    names = []  # type: List[Tuple[str, astroid.Assign]]
    for type_wrapper in desc.values:
        name, number = type_wrapper.name, type_wrapper.number
        names.append((name, astroid.extract_node('{} = {}'.format(name, number))))
    return [(cls_def.name, cls_def)] + names


def _template_message(desc, descriptor_registry):
    # type: (Descriptor, DescriptorRegistry) -> str
    """
    Returns cls_def string, list of fields, list of repeated fields
    """
    desc = SimpleDescriptor(desc)
    descriptor_registry[desc.identifier] = desc

    slots = desc.field_names

    # NOTE: the "pass" statement is a hack to provide a body when args is empty
    initialisers = ['pass']
    initialisers += [
        'self.{} = self.{}()'.format(field_name, field_type)
        for field_name, field_type in (desc.inner_fields)
    ]
    initialisers += [
        'self.{} = {}()'.format(field_name, field_type)
        for field_name, field_type in (desc.external_fields)
    ]
    initialisers += [
        'self.{} = []'.format(field_name)
        for field_name in desc.repeated_fields
    ]

    args = ['self'] + ['{}=None'.format(f) for f in slots]
    init_str = 'def __init__({argspec}):\n{initialisers}\n'.format(
        argspec=', '.join(args),
        initialisers=textwrap.indent('\n'.join(initialisers), '   '),
    )

    helpers = ""
    if desc.options.map_entry:
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

    body = ''.join([
        _template_enum(d, descriptor_registry) for d in desc.enum_types
    ] + [
        _template_message(d, descriptor_registry) for d in desc.nested_types
    ])

    cls_str = (
        'class {name}(object):\n'
        '    {docstring!r}\n'
        '    __slots__ = {slots}\n'
        '{helpers}{body}{init}\n'
    ).format(
        name=desc.name,
        docstring="descriptor={}".format(desc.identifier),
        slots=slots,
        body=textwrap.indent(body, '    '),
        helpers=textwrap.indent(helpers, '    '),
        init=textwrap.indent(init_str, '    '),
    )

    return cls_str


def transform_message(desc, desc_registry):
    # type: (Any, DescriptorRegistry) -> List[Tuple[str, astroid.ClassDef]]
    cls_str = _template_message(desc, desc_registry)

    def visit_classdef(cls_def):
        # type: (astroid.ClassDef) -> astroid.ClassDef
        cls_def._is_protobuf_class = True
        simple_desc = desc_registry[cls_def.doc.split('=')[-1]]  # FIXME: guard?
        cls_def._protobuf_descriptor = simple_desc
        return cls_def

    # Now we can do stuff bottom-up instead of top-down...
    astroid.MANAGER.register_transform(astroid.ClassDef, visit_classdef)
    cls = astroid.extract_node(cls_str)  # type: astroid.ClassDef
    astroid.MANAGER.unregister_transform(astroid.ClassDef, visit_classdef)

    return [(cls.name, cls)]


def transform_descriptor_to_class(cls):
    # type: (Any) -> List[Tuple[str, Union[astroid.ClassDef, astroid.Name]]]
    try:
        desc = cls.DESCRIPTOR
    except AttributeError:
        raise NotImplementedError()
    desc_registry = {}  # type: DescriptorRegistry
    if isinstance(desc, EnumDescriptor):
        return transform_enum(desc, desc_registry)
    elif isinstance(desc, Descriptor):
        return transform_message(desc, desc_registry)
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


def transform_module(mod):
    # type: (astroid.Module) -> astroid.Module
    for name in mod.wildcard_import_names():
        cls = mod_node_to_class(mod, name)
        try:
            for local_name, node in transform_descriptor_to_class(cls):
                mod.locals[local_name] = [node]
        except NotImplementedError:
            pass
    return mod


def is_some_protobuf_module(node):
    # type: (astroid.Module) -> bool
    modname = node.name
    return modname.endswith('_pb2') and not modname.startswith('google.')
