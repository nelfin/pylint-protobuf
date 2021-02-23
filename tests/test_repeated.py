import pytest
import astroid
import pylint.testutils

import pylint_protobuf

@pytest.fixture
def repeated_scalar_mod(proto_builder):
    return proto_builder("""
        message Repeated {
            repeated string values = 1;
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

@pytest.fixture
def repeated_external_composite_mod(proto_builder):
    # Pretty much the same as a map entry
    return proto_builder("""
        message Inner {
            required string value = 1;
        }
        message Outer {
            repeated Inner values = 1;
        }
    """)

# repeated scalar (append) vs repeated composite (add)

class TestProtobufRepeatedFields(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_no_warnings(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values.append("hello")  # should not raise
        """.format(repeated=repeated_scalar_mod))
        with self.assertNoMessages():
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented protobuf-no-assignment')
    def test_repeated_attrassign(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values = ["abc", "def"]
        """.format(repeated=repeated_scalar_mod))
        message = pylint.testutils.Message(
            'protobuf-no-assignment',
            node=node.targets[0], args=('values', 'Repeated')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented protobuf-type-error')
    def test_scalar_typeerror(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values.append(123)
        """.format(repeated=repeated_scalar_mod))
        message = pylint.testutils.Message(
            'protobuf-type-error',
            node=node, args=('values', 'Repeated')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_missing_field_on_repeated_inner_warns(self, repeated_composite_mod):
        node = astroid.extract_node("""
        import {repeated}

        outer = {repeated}.Outer()
        inner = outer.values.add()
        inner.invalid_field = 123  #@
        """.format(repeated=repeated_composite_mod))
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'Inner')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented external types inference')
    def test_missing_field_on_repeated_warns(self, repeated_external_composite_mod):
        node = astroid.extract_node("""
        import {repeated}

        outer = {repeated}.Outer()
        inner = outer.values.add()
        inner.invalid_field = 123  #@
        """.format(repeated=repeated_external_composite_mod))
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'Inner')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

@pytest.fixture
def scalar_warnings_mod(repeated_scalar_mod, module_builder):
    return module_builder("""
        import {repeated}

        msg = {repeated}.Repeated()
        msg.values.append("hello")          # should not raise
        print(msg.values.should_raise)
    """.format(repeated=repeated_scalar_mod), 'scalar_warnings_mod')


def test_no_E1101_on_repeated_fields(scalar_warnings_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['no-member', 'protobuf-undefined-attribute'],
    )
    linter.check([scalar_warnings_mod])
    expected_messages = [
        "Instance of 'list' has no 'should_raise' member",
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert actual_messages
    assert sorted(actual_messages) == sorted(expected_messages)
