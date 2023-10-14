import pytest

import pylint_protobuf
from tests._testsupport import CheckerTestCase


@pytest.fixture
def nested_mod(proto_builder):
    return proto_builder("""
        message Outer {
          message Inner {
            required string inner_field = 1;
          }
          required Inner field = 1;
        }
    """, 'nested')


@pytest.fixture
def nested_plus_enum_mod(proto_builder):
    return proto_builder("""
        message Outer {
          enum InnerEnum {
            VALUE = 0;
          }
          message Inner {
            required string inner_field = 1;
          }
          required Inner field = 1;
        }
    """, 'nested_plus_enum')


class TestNestedMessages(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_nested_message_definition_does_not_warn(self, nested_mod):
        self.assert_no_messages(self.extract_node("""
            from {} import Outer
            inner = Outer.Inner(inner_field='foo')  #@
        """.format(nested_mod)))

    def test_nested_message_with_unrelated_enum_does_not_warn(self, nested_plus_enum_mod):
        self.assert_no_messages(self.extract_node("""
            from {} import Outer
            inner = Outer.Inner(inner_field='foo')  #@
        """.format(nested_plus_enum_mod)))
