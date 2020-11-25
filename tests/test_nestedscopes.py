import pytest
import astroid
import pylint.testutils

import pylint_protobuf

@pytest.fixture
def fake_pb2(proto_builder):
    return proto_builder("""
        syntax = "proto2";
        package nestedscope;
        message Foo {
            required string something = 1;
        }
    """, 'fake')

class TestNestedScopes(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    @pytest.mark.xfail(reason='inference error?')
    def test_many_imports_no_aliasing(self):
        node = astroid.extract_node("""
        import fixture.innerclass_pb2
        import fixture.import_pb2
        p = innerclass_pb2.Person()
        p.should_warn = 123
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Person')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.xfail(reason='actually this was an incorrect assumption, Foo is in the global scope')
    def test_aliasing_by_inner_class_does_not_warn(self, fake_pb2, error_on_missing_modules):
        inner = astroid.extract_node("""
        from fake_pb2 import Foo
        class Outer:
            class Foo: pass
            def __init__(self):
                inner = Foo()
                inner.should_not_warn = 123  #@
        """)
        with self.assertNoMessages():
            self.walk(inner.root())

    def test_class_scope_closure_restores_warnings(self, fake_pb2, error_on_missing_modules):
        outer = astroid.extract_node("""
        from fake_pb2 import Foo
        class Outer:
            Foo = object
        outer = Foo()
        outer.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=outer.targets[0], args=('should_warn', 'Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(outer.root())

    def test_alias_by_function_scope_does_not_warn(self, fake_pb2, error_on_missing_modules):
        inner = astroid.extract_node("""
        from fake_pb2 import Foo
        def func():
            class Foo: pass
            inner = Foo()
            inner.should_not_warn = 123  #@
        """)
        with self.assertNoMessages():
            self.walk(inner.root())

    def test_function_scope_closure_restores_warnings(self, fake_pb2, error_on_missing_modules):
        outer = astroid.extract_node("""
        from fake_pb2 import Foo
        def func():
            Foo = object
        outer = Foo()
        outer.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=outer.targets[0], args=('should_warn', 'Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(outer.root())
