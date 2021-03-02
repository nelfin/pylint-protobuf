from functools import lru_cache
from typing import Any, List, Tuple, Set, Dict, Union, MutableMapping, Iterator
import textwrap

import astroid

try:
    from google.protobuf.pyext._message import (
        Descriptor,
        EnumDescriptor,
        FieldDescriptor,
    )
except ImportError:  # pragma: nocover
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
except ImportError:  # pragma: nocover
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


def is_repeated(fd):
    # type: (FieldDescriptor) -> bool
    return fd.label == FieldDescriptor.LABEL_REPEATED

def is_composite(fd):
    # type: (FieldDescriptor) -> bool
    return fd.type == FieldDescriptor.TYPE_MESSAGE

def is_map_field(fd):  # FIXME: too many selectors
    # type: (FieldDescriptor) -> bool
    return is_composite(fd) and fd.message_type.has_options and fd.message_type.GetOptions().map_entry


class TODO(object):
    pass  # These fields are not assignable


FIELD_TYPES = {
    FieldDescriptor.TYPE_BOOL: bool,
    FieldDescriptor.TYPE_BYTES: str,
    FieldDescriptor.TYPE_DOUBLE: float,
    FieldDescriptor.TYPE_ENUM: int,
    FieldDescriptor.TYPE_FIXED32: float,
    FieldDescriptor.TYPE_FIXED64: float,
    FieldDescriptor.TYPE_FLOAT: float,
    FieldDescriptor.TYPE_GROUP: TODO,
    FieldDescriptor.TYPE_INT32: int,
    FieldDescriptor.TYPE_INT64: int,
    FieldDescriptor.TYPE_MESSAGE: TODO,
    FieldDescriptor.TYPE_SFIXED32: float,
    FieldDescriptor.TYPE_SFIXED64: float,
    FieldDescriptor.TYPE_SINT32: int,
    FieldDescriptor.TYPE_SINT64: int,
    FieldDescriptor.TYPE_STRING: str,
    FieldDescriptor.TYPE_UINT32: int,
    FieldDescriptor.TYPE_UINT64: int,
}

def to_pytype(fd):
    # type: (FieldDescriptor) -> type
    if is_composite(fd):
        return type(fd.message_type.name, (TODO,), {})  # XXX: such a hack!
    return FIELD_TYPES[fd.type]

def field_type_path(fd):
    # type: (FieldDescriptor) -> Iterator[str]
    if fd.containing_type is not None:
        yield from field_type_path(fd.containing_type)
    yield fd.name

def full_name(fd):
    # type: (FieldDescriptor) -> str
    return '.'.join(field_type_path(fd))


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

    def is_nested(self, fd):
        # type: (FieldDescriptor) -> bool
        return fd.message_type.containing_type is self._desc

    def is_typeof_field(self, fd):
        # type: (FieldDescriptor) -> bool
        return fd.message_type is self._desc

    @property
    def identifier(self):
        # type: () -> str
        return self._cls_hash

    @property
    def is_enum(self):
        return self._is_protobuf_enum

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
    def fields(self):
        # type: () -> List[FieldDescriptor]
        return self._desc.fields

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
    def values(self):
        # type: () -> Dict[str, int]
        assert self._is_protobuf_enum, "Only makes sense for enum descriptors"
        return {n: v.number for n, v in self._enum_desc.values_by_name.items()}

    @property
    def names(self):
        # type: () -> Dict[int, str]
        assert self._is_protobuf_enum, "Only makes sense for enum descriptors"
        return {v.number: n for n, v in self._enum_desc.values_by_name.items()}

    @property
    def values_by_name(self):
        # type: () -> List[Tuple[str, int]]
        assert self._is_protobuf_enum, "Only makes sense for enum descriptors"
        return [(n, v.number) for n, v in self._enum_desc.values_by_name.items()]

    @property
    def message_fields(self):
        # type: () -> List[FieldDescriptor]
        assert not self._is_protobuf_enum, "Only makes sense for message descriptors"
        return [f for f in self.fields if is_composite(f)]

    @property
    def enum_types(self):
        return self._desc.enum_types

    @property
    def nested_types(self):
        return self._desc.nested_types

    @property
    def inner_nonrepeated_fields(self):
        # type: () -> List[Tuple[str, str]]
        return [
            (f.name, f.message_type.name) for f in self.message_fields
            if self.is_nested(f) and not is_repeated(f)
        ]

    @property
    def external_fields(self):
        # type: () -> List[Tuple[str, str]]
        return [
            (f.name, full_name(f.message_type)) for f in self.message_fields
            if not self.is_nested(f)
        ]

    @property
    def repeated_fields(self):
        # type: () -> Set[str]
        return set(
            f.name for f in self.fields
            if is_repeated(f) and not is_composite(f)
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


def _template_composite_field(parent_name, name, field_type, is_nested=False):
    # TODO: add some marker for it being a producer of repeated fields?
    # it's tricky to work with inferred results
    # as it stands the result of the call (or explicitly infer_call_result on the BoundMethod)
    # seems to always return Uninferable
    # maybe it'd work

    # NOTE: this took some rejigging to make it work, specifically, astroid.inference didn't
    # like the use of self for the local class definition (even if the method used some other
    # argument so as to not shadow __init__.self. Some manual testing found parent class
    # name to work

    # also I'm not sure we need to subclass/return list, just return the appropriate type?

    # looks like <Entry>CompositeContainer should be defined outside of __init__ if the type
    # is not nested
    qualifier = parent_name+'.' if is_nested else ''
    return textwrap.dedent("""
    class {field_type}CompositeContainer(list):
        def add(self, **kwargs):
            return {qualifier}{field_type}()
    self.{name} = {field_type}CompositeContainer()  # repeated composite_fields
    """.format(name=name, field_type=field_type, qualifier=qualifier))


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
        'self.{} = self.{}()  # inner_nonrepeated_fields'.format(field_name, field_type)
        for field_name, field_type in desc.inner_nonrepeated_fields
    ]


    repeated_scalar_fields = [fd.name for fd in desc.fields if is_repeated(fd) and not is_composite(fd)]
    initialisers += [
        'self.{} = []  # repeated_fields'.format(field_name)
        for field_name in repeated_scalar_fields
    ]

    rcfields = {
        fd for fd in desc.fields
        if is_repeated(fd) and is_composite(fd) and not is_map_field(fd)
    }
    repeated_composite_fields = [
        (fd.name, fd.message_type.name, desc.is_nested(fd))
        for fd in rcfields
    ]
    initialisers += [
        _template_composite_field(desc.name, field_name, field_type, is_nested)
        for field_name, field_type, is_nested in repeated_composite_fields
    ]

    # TODO: refactor this
    external_fields = [
        (f.name, full_name(f.message_type)) for f in desc.message_fields
        if not desc.is_nested(f)
        if f not in rcfields  # don't want to double up above
    ]
    initialisers += [
        'self.{} = {}()  # external_fields'.format(field_name, field_type)
        for field_name, field_type in external_fields

    ]

    args = ['self'] + ['{}=None'.format(f) for f in slots]
    init_str = 'def __init__({argspec}):\n{initialisers}\n'.format(
        argspec=', '.join(args),
        initialisers=textwrap.indent('\n'.join(initialisers), '    '),
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
        try:
            simple_desc = desc_registry[cls_def.doc.split('=')[-1]]
        except (AttributeError, KeyError):
            pass # probably a helper class like CompositeContainer
        else:
            cls_def._is_protobuf_class = True
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
                node.parent = mod
                mod.locals[local_name] = [node]
        except NotImplementedError:
            pass
    return mod


def is_some_protobuf_module(node):
    # type: (astroid.Module) -> bool
    modname = node.name
    return modname.endswith('_pb2') and not modname.startswith('google.')
