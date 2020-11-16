import pytest
import astroid

from pylint_protobuf.parse_pb2 import Module, TypeClass
from pylint_protobuf.evaluation import resolve


def test_resolve_name():
    Person = object()
    scope = {'Person': Person}
    node = astroid.extract_node('Person')
    assert resolve(scope, node) is Person

def test_resolve_constant_slice():
    Person = object()
    scope = {'Person': Person}
    node = astroid.extract_node('[Person][0]')
    assert resolve(scope, node) is Person

def test_resolve_constant_dict():
    Person = object()
    scope = {'Person': Person}
    node = astroid.extract_node('{"a": Person}["a"]')
    assert resolve(scope, node) is Person

def test_resolve_nested_dict():
    Person = object()
    scope = {'Person': Person}
    node = astroid.extract_node("""
    {
        "outer": {
            "inner": Person
        }
    }["outer"]["inner"]
    """)
    assert resolve(scope, node) is Person

@pytest.mark.skip(reason='changes in typeof')
def test_resolve_call():
    Person = object()
    scope = {'Person': TypeClass(Person)}
    node = astroid.extract_node('Person()')
    assert resolve(scope, node) is Person

@pytest.mark.skip(reason='changes in typeof')
def test_resolve_import():
    Person = TypeClass(object())
    mod_globals = {'module_pb2.Person': Person}
    module_pb2 = Module('module_pb2', mod_globals)
    scope = {'module_pb2': module_pb2}
    node = astroid.extract_node('module_pb2.Person')
    assert resolve(scope, node) is Person
