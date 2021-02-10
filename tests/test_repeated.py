import pytest
import astroid
import pylint.testutils

import pylint_protobuf

@pytest.fixture
def repeated_scalar_mod(proto_builder):
    return proto_builder("""
        message Repeated {
            required string values = 1;
        }
    """)

@pytest.fixture
def repeated_composite_mod(proto_builder):
    return proto_builder("""
        message Outer {
            message Inner {
                required string value = 1;
            }
            repeated Inner values = 1;
        }
    """)

# repeated scalar (append) vs repeated composite (add)

class TestProtobufRepeatedFields(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    @pytest.mark.skip(reason='not tested')
    def test_missing_method(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values.append("hello")
        """.format(repeated=repeated_scalar_mod))
        self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented')
    def test_repeated_attrassign(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values = ["abc", "def"]
        """.format(repeated=repeated_scalar_mod))
        message = pylint.testutils.Message(
            'protobuf-repeated-assignment',  # TODO
            node=node.targets[0], args=('values', 'Repeated')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented')
    def test_scalar_typeerror(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values.append(123)
        """.format(repeated=repeated_scalar_mod))
        message = pylint.testutils.Message(
            'protobuf-type-error',  # TODO
            node=node.targets[0], args=('values', 'Repeated')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented')
    def test_missing_field_on_repeated_warns(self):
        node = astroid.extract_node("""
        import {repeated}

        outer = {repeated}.Outer()
        inner = outer.items.add()
        inner.invalid_field = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'Inner')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())
