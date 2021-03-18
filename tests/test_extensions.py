import pytest

import pylint_protobuf
from conftest import CheckerTestCase


@pytest.fixture
def extension_pb2(proto_builder):
    return proto_builder("""
        message FooWithExtensions {
            optional string foo_val = 1;
            extensions 100 to 199;
        }
        message BarWithExtensions {
            optional string bar_val = 1;
            extensions 100 to 199;
        }
        extend FooWithExtensions {
            optional int32 count = 123;
        }
    """)


@pytest.fixture
def nested_extension_pb2(proto_builder):
    return proto_builder("""
        message Foo {
            optional string foo_val = 1;
            extensions 100 to 199;
        }
        message Bar {
            extend Foo {
                optional string foo_bar_ext = 123;
            }
        }
    """)


class TestExtensionFields(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    @pytest.mark.xfail(reason='unimplemented: extensions')
    def test_extensions_no_warnings(self, extension_pb2):
        node = self.extract_node("""
            import {} as ext
            foo = ext.FooWithExtensions()
            foo.Extensions[ext.count] = 100
        """.format(extension_pb2))
        self.assert_no_messages(node)

    def test_extensions_are_not_attributes(self, extension_pb2):
        node = self.extract_node("""
            from {} import FooWithExtensions
            foo = FooWithExtensions()
            foo.count = 100
        """.format(extension_pb2))
        msg = self.undefined_attribute_msg(node.targets[0], 'count', 'FooWithExtensions')
        self.assert_adds_messages(node, msg)

    @pytest.mark.xfail(reason='unimplemented: extensions')
    def test_extensions_are_scoped(self, extension_pb2):
        node = self.extract_node("""
            import {} as ext
            bar = ext.BarWithExtensions()
            bar.Extensions[ext.count] = 100
        """.format(extension_pb2))
        pytest.fail('TODO: some new warning type for bad extensions')
        # >>> bar.Extensions[ext.count] = 100
        # Traceback (most recent call last):
        #   File "<stdin>", line 1, in <module>
        # KeyError: "Field 'count' does not belong to message 'BarWithExtensions'"

    def test_extensions_typeerror_on_initial_field(self, extension_pb2):
        node = self.extract_node("""
            from {} import FooWithExtensions
            FooWithExtensions(foo_val=100)
        """.format(extension_pb2))
        msg = self.type_error_msg(node, 'FooWithExtensions', 'foo_val', 'str', 100)
        self.assert_adds_messages(node, msg)

    @pytest.mark.xfail(reason='unimplemented: extensions')
    def test_extensions_typeerror_on_extension_field(self, extension_pb2):
        node = self.extract_node("""
            import {} as ext
            foo = ext.FooWithExtensions()
            foo.Extensions[ext.count] = 'should_warn'
        """.format(extension_pb2))
        msg = self.type_error_msg(node, 'FooWithExtensions', 'count', 'int', 'should_warn')
        self.assert_adds_messages(node, msg)

    @pytest.mark.xfail(reason='unimplemented: extensions')
    def test_nested_extensions_are_scoped(self, nested_extension_pb2):
        node = self.extract_node("""
            from {} import Foo, Bar
            foo = Foo(foo_val='hello')
            foo.Extensions[Foo.foo_bar_ext] = 'world'
        """.format(nested_extension_pb2))
        msg = self.undefined_attribute_msg(node, 'foo_bar_ext', 'Foo')
        self.assert_adds_messages(node, msg)

    @pytest.mark.xfail(reason='unimplemented: extensions')
    def test_nested_extensions_in_scope_should_not_warn(self, nested_extension_pb2):
        node = self.extract_node("""
            from {} import Foo, Bar
            foo = Foo(foo_val='hello')
            foo.Extensions[Bar.foo_bar_ext] = 'world'
        """.format(nested_extension_pb2))
        self.assert_no_messages(node)
