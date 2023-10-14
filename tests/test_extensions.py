import pytest

import pylint_protobuf
from tests._testsupport import CheckerTestCase


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
        message Baz {
            extensions 100 to 199;
        }
    """)


class TestExtensionFields(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_extensions_no_warnings(self, extension_pb2):
        s = """
            import {} as ext
            foo = ext.FooWithExtensions()
            foo.Extensions[ext.count] = 100
        """.format(extension_pb2)
        node = self.extract_node(s)
        self.assert_no_messages(node)

    def test_extensions_are_not_attributes(self, extension_pb2):
        s = """
            from {} import FooWithExtensions
            foo = FooWithExtensions()
            foo.count = 100
        """.format(extension_pb2)
        node = self.extract_node(s)
        msg = self.undefined_attribute_msg(node.targets[0], 'count', 'FooWithExtensions')
        self.assert_adds_messages(node, msg)

    @pytest.mark.xfail(reason='unimplemented: top-level field descriptors for extensions')
    def test_extensions_are_scoped(self, extension_pb2):
        s = """
            import {} as ext
            bar = ext.BarWithExtensions()
            bar.Extensions[ext.count] = 100
        """.format(extension_pb2)
        node = self.extract_node(s)
        # >>> bar.Extensions[ext.count] = 100
        # Traceback (most recent call last):
        #   File "<stdin>", line 1, in <module>
        # KeyError: "Field 'count' does not belong to message 'BarWithExtensions'"
        msg = self.wrong_extension_scope_msg(node, 'count', 'BarWithExtensions')
        self.assert_adds_messages(node, msg)

    def test_extensions_typeerror_on_initial_field(self, extension_pb2):
        s = """
            from {} import FooWithExtensions
            FooWithExtensions(foo_val=100)
        """.format(extension_pb2)
        node = self.extract_node(s)
        msg = self.type_error_msg(node, 'FooWithExtensions', 'foo_val', 'str', 100)
        self.assert_adds_messages(node, msg)

    @pytest.mark.xfail(reason='unimplemented: type checks on extensions')
    def test_extensions_typeerror_on_extension_field(self, extension_pb2):
        s = """
            import {} as ext
            foo = ext.FooWithExtensions()
            foo.Extensions[ext.count] = 'should_warn'
        """.format(extension_pb2)
        node = self.extract_node(s)
        msg = self.type_error_msg(node, 'FooWithExtensions', 'count', 'int', 'should_warn')
        self.assert_adds_messages(node, msg)

    def test_nested_extensions_belong_to_a_scope(self, nested_extension_pb2):
        s = """
            from {} import Foo
            foo = Foo(foo_val='hello')
            foo.Extensions[
                Foo.foo_bar_ext  #@
            ] = 'world'
        """.format(nested_extension_pb2)
        node = self.extract_node(s)
        msg = self.undefined_attribute_msg(node, 'foo_bar_ext', 'Foo')
        self.assert_adds_messages(node, msg)

    def test_nested_extensions_in_scope_should_not_warn(self, nested_extension_pb2):
        s = """
            from {} import Foo, Bar
            foo = Foo(foo_val='hello')
            foo.Extensions[Bar.foo_bar_ext] = 'world'
        """.format(nested_extension_pb2)
        node = self.extract_node(s)
        self.assert_no_messages(node)

    def test_nested_extensions_out_of_scope_should_warn(self, nested_extension_pb2):
        s = """
            from {} import Bar, Baz
            baz = Baz()
            baz.Extensions[Bar.foo_bar_ext] = 'world'
        """.format(nested_extension_pb2)
        node = self.extract_node(s)
        msg = self.wrong_extension_scope_msg(node.targets[0], 'foo_bar_ext', 'Baz')
        self.assert_adds_messages(node, msg)

    @pytest.mark.skip('is this a protobuf bug or feature?')
    def test_why_are_fields_also_extensions(self, nested_extension_pb2):
        s = """
            from {} import Foo
            foo = Foo()
            foo.Extensions[foo.DESCRIPTOR.fields_by_name['foo_val']] = 'should warn?'
        """.format(nested_extension_pb2)
        node = self.extract_node(s)
        self.assert_no_messages(node)
