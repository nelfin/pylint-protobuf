import pytest
import astroid
import pylint.testutils

import pylint_protobuf


class TestNestedScopes(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    @pytest.mark.xfail(reason='scope and modules overwrite so last wins')
    def test_many_imports_no_aliasing(self):
        node = astroid.extract_node("""
        import fixture.innerclass_pb2
        import fixture.import_pb2
        p = innerclass_pb2.Person()
        p.should_warn = 123
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'innerclass_pb2.Person')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    # @pytest.mark.xfail(reason='unimplemented')
    @pytest.mark.skip(reason='fake_pb2 not supported')
    def test_aliasing_by_inner_class_does_not_warn(self):
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

    # @pytest.mark.xfail(reason='unimplemented')
    @pytest.mark.skip(reason='fake_pb2 not supported')
    def test_class_scope_closure_restores_warnings(self):
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

    # @pytest.mark.xfail(reason='unimplemented')
    @pytest.mark.skip(reason='fake_pb2 not supported')
    def test_alias_by_function_scope_does_not_warn(self):
        inner = astroid.extract_node("""
        from fake_pb2 import Foo
        def func():
            class Foo: pass
            inner = Foo()
            inner.should_not_warn = 123  #@
        """)
        with self.assertNoMessages():
            self.walk(inner.root())

    # @pytest.mark.xfail(reason='unimplemented')
    @pytest.mark.skip(reason='fake_pb2 not supported')
    def test_function_scope_closure_restores_warnings(self):
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
