import pylint.testutils
import pytest

import pylint_protobuf
from tests._testsupport import CheckerTestCase


@pytest.fixture
def fake_pb2(proto_builder):
    return proto_builder("""
        message Foo {
            required string something = 1;
        }
    """)

@pytest.fixture
def first_alias(proto_builder):
    return proto_builder("""
        message Person {
            required string name = 1;
        }
    """)

@pytest.fixture
def second_alias(proto_builder):
    return proto_builder("""
        message Person {
            required string preferred_name = 1;
        }
    """)

class TestNestedScopes(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_many_imports_no_aliasing(self, first_alias, second_alias):
        node = self.extract_node("""
        import {first}
        import {second}
        p = {first}.Person()
        p.should_warn = 123
        """.format(first=first_alias, second=second_alias))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Person')
        )
        self.assert_adds_messages(node, message)

    def test_many_imports_with_aliasing(self, first_alias, second_alias):
        node = self.extract_node("""
        from {first} import Person
        from {second} import Person
        p = Person()
        p.should_warn = 123
        """.format(first=first_alias, second=second_alias))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Person')
        )
        self.assert_adds_messages(node, message)

    @pytest.mark.xfail(reason='actually this was an incorrect assumption, Foo is in the global scope')
    def test_aliasing_by_inner_class_does_not_warn(self, fake_pb2, error_on_missing_modules):
        inner = self.extract_node("""
        from {fake_pb2} import Foo
        class Outer:
            class Foo: pass
            def __init__(self):
                inner = Foo()
                inner.should_not_warn = 123  #@
        """.format(fake_pb2=fake_pb2))
        self.assert_no_messages(inner)

    def test_class_scope_closure_restores_warnings(self, fake_pb2, error_on_missing_modules):
        outer = self.extract_node("""
        from {fake_pb2} import Foo
        class Outer:
            Foo = object
        outer = Foo()
        outer.should_warn = 123  #@
        """.format(fake_pb2=fake_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=outer.targets[0], args=('should_warn', 'Foo')
        )
        self.assert_adds_messages(outer, message)

    def test_alias_by_function_scope_does_not_warn(self, fake_pb2, error_on_missing_modules):
        inner = self.extract_node("""
        from {fake_pb2} import Foo
        def func():
            class Foo: pass
            inner = Foo()
            inner.should_not_warn = 123  #@
        """.format(fake_pb2=fake_pb2))
        self.assert_no_messages(inner)

    def test_function_scope_closure_restores_warnings(self, fake_pb2, error_on_missing_modules):
        outer = self.extract_node("""
        from {fake_pb2} import Foo
        def func():
            Foo = object
        outer = Foo()
        outer.should_warn = 123  #@
        """.format(fake_pb2=fake_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=outer.targets[0], args=('should_warn', 'Foo')
        )
        self.assert_adds_messages(outer, message)
