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


def is_some_protobuf_module(node):
    # type: (astroid.node_classes.NodeNG) -> bool
    assert isinstance(node, (astroid.Import, astroid.ImportFrom))
    if isinstance(node, astroid.ImportFrom):
        return node.modname.endswith('_pb2')
    elif isinstance(node, astroid.Import):
        return any(modname.endswith('_pb2') for modname, _ in node.names)
    return False


def transform_import(node):
    # have to transform imports into class definitions
    # or is there a way to modify the inferred value of the names when doing a function call?

    # turn an import into a series of class definitions assigned to some object, or inner class definitions?
    # a la:
    # class person_pb2:
    #     class Person:
    #          __slots__ = ('name', )
    raise NotImplementedError()


def transform_importfrom(node):
    # type: (astroid.ImportFrom) -> astroid.ClassDef

    # turn an ImportFrom into a series of class definitions, one for each imported name (aliased appropriately)
    # or all of them in the case of a *-import
    modname = node.modname
    names = node.names
    mod = node.do_import_module()  # type: astroid.Module
    if ('*', None) in names:
        names = mod.wildcard_import_names()
        raise NotImplementedError()
    for name, alias in names:
        cls = mod_node_to_class(mod, name)
        cls_def = transform_descriptor_to_class(cls, alias)
    return cls_def


def test_transform():
    MANAGER.register_transform(astroid.ImportFrom, transform_importfrom, is_some_protobuf_module)
    node = astroid.extract_node("from fixture.foo_pb2 import Message")
    pass


@astroid.inference_tip
def _importfrom_inference(node, _context=None):
    return iter([transform_importfrom(node)])


def register(_):
    pass


# MANAGER.register_transform(astroid.Import, _import_inference, is_some_protobuf_module)
MANAGER.register_transform(astroid.ImportFrom, _importfrom_inference, is_some_protobuf_module)
