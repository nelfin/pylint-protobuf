import pytest

import pylint_protobuf
from tests._testsupport import make_message, CheckerTestCase


def test_inline_proto_compilation(proto_builder):
    mod_name = proto_builder("""
    message Foo {
      required int32 id = 1;
    }
    """)
    node = CheckerTestCase.extract_node("""
    import {} as mod
    foo = mod.Person()
    foo.missing = 123
    """.format(mod_name))
    assert node is not None


@pytest.fixture
def foo_mod(proto_builder):
    return proto_builder("""
        message Foo {
          required int32 id = 1;
        }
    """, 'foo')


class TestAutoBuilder(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_missing_field(self, foo_mod):
        node = self.extract_node("""
        import {} as mod
        foo = mod.Foo()
        foo.should_warn
        """.format(foo_mod))
        message = make_message('protobuf-undefined-attribute', node, 'Foo', 'should_warn')
        self.assert_adds_messages(node, message)
