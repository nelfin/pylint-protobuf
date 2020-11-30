try:
    from functools import lru_cache
except ImportError:
    def lru_cache(*args):
        def wrapped(func):
            return func
        return wrapped
try:
    from typing import Any, List, Tuple, Union
except ImportError:
    pass

import textwrap

import astroid

from google.protobuf.pyext._message import Descriptor
from google.protobuf.pyext._message import EnumDescriptor


def _template_enum(desc, depth=0):
    # type: (EnumDescriptor, int) -> str
    body = '; '.join(
        '{} = {}'.format(name, value.number)
        for name, value in desc.values_by_name.items()
    )
    enum_str = 'class {name}(object):\n    __slots__ = {slots}\n    {body}'.format(
        name=desc.name, slots=repr(tuple(desc.values_by_name)), body=body
    )
    return textwrap.indent(enum_str, '    '*depth)

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
        fragments.append(_template_enum(enum_desc, depth=1))
    return '\n'.join(fragments)

def mark_as_protobuf(cls_def):
    # type: (astroid.ClassDef) -> None
    cls_def._is_protobuf_class = True
    cls_def._protobuf_fields = set(s.value for s in cls_def.slots())  # FIXME: descriptors?, duplication?
    for name, val in cls_def.locals.items():
        val = val[0]  # assert len(val) == 1?
        if isinstance(val, astroid.ClassDef):
            mark_as_protobuf(val)

def transform_message(desc, name):
    # type: (Any, str) -> List[Tuple[str, astroid.ClassDef]]
    if name is None:
        name = desc.name
    inner_fragments = inner_types(desc)
    slots = tuple(desc.fields_by_name) + tuple(desc.enum_values_by_name) + tuple(desc.enum_types_by_name)
    cls_str = 'class {name}(object):\n    __slots__ = {slots}\n{body}'.format(
        name=name,
        slots=slots,
        body=inner_fragments,
    )
    cls = astroid.extract_node(cls_str)  # type: astroid.ClassDef
    mark_as_protobuf(cls)
    return [(cls.name, cls)]



def transform_descriptor_to_class(cls, alias=None):
    # type: (Any, str) -> List[Tuple[str, Union[astroid.ClassDef, astroid.Name]]]
    desc = cls.DESCRIPTOR
    if isinstance(desc, EnumDescriptor):
        return transform_enum(desc)
    elif isinstance(desc, Descriptor):
        return transform_message(desc, alias)
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
