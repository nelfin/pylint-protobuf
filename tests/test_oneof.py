import pylint.testutils
import pytest

import pylint_protobuf
from tests._testsupport import CheckerTestCase


@pytest.fixture
def oneof_scalar_pb2(proto_builder):
    return proto_builder("""
        message ScalarOneof {
            oneof test {
                string name = 1;
                int32 code = 2;
            }
        }
    """)

@pytest.fixture
def oneof_composite_pb2(proto_builder):
    return proto_builder("""
        message CompositeOneof {
            message Name {
                required string name = 1;
            }
            message Email {
                required string email = 2;
            }
            oneof test {
                Name name = 10;
                Email email = 11;
            }
        }
    """)

class TestProtobufOneofFields(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_no_oneof_warnings(self, oneof_scalar_pb2):
        node = self.extract_node("""
            import {mod}
            msg = {mod}.ScalarOneof()
            msg.code = 123  # should not raise
        """.format(mod=oneof_scalar_pb2))
        self.assert_no_messages(node)

    def test_assignment_to_composite_field(self, oneof_composite_pb2):
        node = self.extract_node("""
            import {mod}
            msg = {mod}.CompositeOneof()
            msg.name = msg.Name(name="Person")
        """.format(mod=oneof_composite_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-no-assignment',
            node=node.targets[0], args=('CompositeOneof', 'name')
        )
        self.assert_adds_messages(node, message)

    def test_scalar_assignment_to_composite_field(self, oneof_composite_pb2):
        node = self.extract_node("""
            import {mod}
            msg = {mod}.CompositeOneof()
            msg.name = 'Example'
        """.format(mod=oneof_composite_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-no-assignment',
            node=node.targets[0], args=('CompositeOneof', 'name')
        )
        self.assert_adds_messages(node, message)

    def test_composite_field_warnings(self, oneof_composite_pb2):
        node = self.extract_node("""
            import {mod}
            msg = {mod}.CompositeOneof()
            msg.name.name = 'Person'                # should not warn
            msg.email.email = 'hello@example.com'   # should not warn
            msg.name.should_warn = 123
        """.format(mod=oneof_composite_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Name')
        )
        self.assert_adds_messages(node, message)


@pytest.fixture
def composite_warnings_mod(oneof_composite_pb2, module_builder):
    return module_builder("""
        import {mod}
        msg = {mod}.CompositeOneof()
        print(msg.email.should_warn)
    """.format(mod=oneof_composite_pb2), 'composite_warnings_mod')


def test_no_E1101_on_oneof_fields(composite_warnings_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['no-member', 'protobuf-undefined-attribute'],
    )
    linter.check([composite_warnings_mod])
    expected_messages = [
        pylint_protobuf.MESSAGES['E5901'][0] % ('should_warn', 'Email')
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert actual_messages
    assert sorted(actual_messages) == sorted(expected_messages)
