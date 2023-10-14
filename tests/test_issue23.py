import pytest

import pylint_protobuf
from tests._testsupport import make_message, CheckerTestCase


@pytest.fixture
def inner_mod(proto_builder):
    return proto_builder("""
        message Test {
            required int32 id = 1;
        }
    """)


@pytest.fixture
def outer_mod(inner_mod, module_builder):
    return module_builder(
        "from {} import Test".format(inner_mod),
        "outer"
    )


class TestReexportedNames(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_reexported_protobuf_message_definition_warns(self, outer_mod):
        node = self.extract_node("""
            import outer
            t = outer.Test()
            t.should_warn = 123  #@
        """)
        msg = make_message('protobuf-undefined-attribute', node.targets[0], 'Test', 'should_warn')
        self.assert_adds_messages(node, msg)
