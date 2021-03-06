import astroid
import pylint.testutils
import pytest

import pylint_protobuf
from conftest import make_message


def test_inline_proto_compilation(proto_builder):
    mod_name = proto_builder("""
    message Foo {
      required int32 id = 1;
    }
    """)
    node = astroid.extract_node("""
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


class TestAutoBuilder(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_missing_field(self, foo_mod):
        node = astroid.extract_node("""
        import {} as mod
        foo = mod.Foo()
        foo.should_warn
        """.format(foo_mod))
        message = make_message(node, 'Foo', 'should_warn')
        with self.assertAddsMessages(message):
            self.walk(node.root())
