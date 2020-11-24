from functools import lru_cache
from typing import Any

import astroid
from astroid import MANAGER
from google.protobuf.pyext._message import Descriptor
from google.protobuf.pyext._message import EnumDescriptor


def transform_enum(desc):
    # type: (Any) -> astroid.ClassDef
    raise NotImplementedError()


def transform_message(desc, name):
    # type: (Any, str) -> astroid.ClassDef
    if name is None:
        name = desc.name
    cls = astroid.extract_node("""
    class {name}(object):
        __slots__ = {body}
    """.format(name=name, body=repr(tuple(desc.fields_by_name))))
    return cls


def transform_descriptor_to_class(cls, alias=None):
    # type: (Any, str) -> astroid.ClassDef
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
            cls_def = transform_descriptor_to_class(cls)
            cls_def._is_protobuf_class = True
            mod.locals[name] = [cls_def]
        except (NotImplementedError, AttributeError):
            pass

    return mod


def is_some_protobuf_module(node):
    # type: (astroid.Module) -> bool
    modname = node.name
    return modname.endswith('_pb2') and not modname.startswith('google.')
