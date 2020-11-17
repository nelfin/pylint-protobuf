import pytest
import astroid

from pylint_protobuf.parse_pb2 import Module, TypeClass
from pylint_protobuf.evaluation import resolve, evaluate, Scope


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

def test_scope_assign():
    scope = Scope({'x': 123})
    assert scope['x'] == 123
    scope.assign('x', 456)
    assert scope['x'] == 456

def test_scope_push():
    scope = Scope({'x': 123})
    scope.push()
    assert scope['x'] == 123

def test_scope_push_shadows():
    scope = Scope({'x': 123})
    scope.push({'x': 456})
    assert scope['x'] == 456
    scope.pop()
    assert scope['x'] == 123

def test_evaluate_name():
    scope = Scope({'x': 123})
    node = astroid.extract_node('x')
    assert evaluate(scope, node) == 123

def test_evaluate_constant():
    scope = Scope({'x': 123})
    node = astroid.extract_node('456')
    assert evaluate(scope, node) == 456

def test_evaluate_attribute():
    class Obj(object):
        attr = 'attribute'
    scope = Scope({'name': Obj()})
    node = astroid.extract_node('name.attr')
    assert evaluate(scope, node) == 'attribute'

def test_evaluate_attributeerror():
    class Obj(object):
        attr = 'attribute'
    scope = Scope({'name': Obj()})
    node = astroid.extract_node('name.missing')
    with pytest.raises(AttributeError):
        evaluate(scope, node)  # Would rather it didn't raise

def test_evaluate_recursive_attributes():
    class Inner(object):
        attr = 'recursive_attribute'
    class Outer(object):
        inner = Inner()
    scope = Scope({'outer': Outer()})
    node = astroid.extract_node('outer.inner.attr')
    assert evaluate(scope, node) == 'recursive_attribute'

def test_evaluate_recursive_attributeerror():
    class Inner(object):
        attr = 'recursive_attribute'
    class Outer(object):
        inner = Inner()
    scope = Scope({'outer': Outer()})
    node = astroid.extract_node('outer.missing.attr')
    with pytest.raises(AttributeError):
        evaluate(scope, node)  # Would rather it didn't raise

def test_evaluate_recursive_top_attributeerror():
    class Obj(object):
        attr = 'one-two-three'
    scope = Scope({'name': Obj()})
    node = astroid.extract_node('missing.attr')
    with pytest.raises(KeyError):
        evaluate(scope, node)  # Would rather it didn't raise
