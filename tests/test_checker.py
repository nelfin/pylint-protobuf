import pytest
import astroid
import pylint.testutils

import pylint_protobuf


class TestProtobufDescriptorChecker(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_module_import(self):
        node = astroid.extract_node("""
        import person_pb2 as person

        foo = person.Person()
        foo.name = 'fine'
        foo.id = 123
        foo.invalid_field = 'should warn'  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'Person')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_importfrom(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        foo = Foo()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented')
    def test_complex_field(self):
        node = astroid.extract_node("""
        from complexfield_pb2 import Outer
        outer = complexfield_pb2.Outer()
        outer.inner.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Outer')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_importfrom_with_aliasing(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo as Bar

        class Foo(object):
            pass  # normal class, not fake_pb2.Foo (nor fake_pb2.Bar)

        bar = Bar()
        bar.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Bar')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_importfrom_with_aliasing_no_warning(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo as Bar

        class Foo(object):
            pass  # normal class, not fake_pb2.Foo (nor fake_pb2.Bar)

        foo = Foo()
        foo.no_error = 123  #@
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_aliasing_via_getitem_does_not_throw(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo
        foo = [Foo][0]()  #@
        """)
        self.walk(node.root())

    def test_aliasing_via_getitem_list(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        bar = [Foo]

        foo = bar[0]()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_aliasing_via_getitem_dict(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        bar = {
            'baz': Foo,
        }

        foo = bar['baz']()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_aliasing_via_getitem_uninferable_should_not_warn(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo
        from random import randint

        types = [Foo, int]
        foo = types[randint(0, 2)]()
        foo.should_warn = 123  #@
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_aliasing_via_getitem_nested_lists(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        bar = [[Foo]]
        foo = bar[0][0]()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def xtest_aliasing_via_indirection(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        Indirect = Foo
        foo = Indirect()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def xtest_aliasing_via_instance_renaming(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        foo = Foo()
        bar = foo
        bar.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def xtest_aliasing_via_indirection_getitem(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        types = {}
        types[0] = Foo
        foo = types[0]()

        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def xtest_aliasing_via_getitem_list_indirection(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        baz = [Foo]
        bar = bar[0]
        foo = baz[0]()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())
