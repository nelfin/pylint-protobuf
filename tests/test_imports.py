import pytest

import pylint_protobuf
from tests._testsupport import make_message, CheckerTestCase


@pytest.fixture
def child_mod(proto_builder, request):
    return proto_builder("""
        message Child {}
    """, 'child', preamble='syntax = "proto2";\npackage parent;\n')

@pytest.fixture
def parent_mod(proto_builder, child_mod):
    return proto_builder("""
        import "child.proto";

        message Parent {
            required Child child = 1;
        }
    """, 'parent')


@pytest.fixture
def wkt_mod(proto_builder):
    return proto_builder("""
        import "google/protobuf/timestamp.proto";
        message Sibling {
            required string value = 1;
        }
        message UsesTimestamp {
            required google.protobuf.Timestamp ts = 1;
            required Sibling a_composite = 2;
        }
    """)


class TestImportedProtoDefinitions(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_issue9_imported_message_no_attribute_error(self, parent_mod):
        node = self.extract_node("""
        from {} import Parent
        """.format(parent_mod))
        self.assert_no_messages(node)

    def test_issue10_imported_message_warns(self, parent_mod):
        node = self.extract_node("""
        from {} import Parent
        p = Parent()
        p.child.should_warn = 123  #@
        """.format(parent_mod))
        msg = make_message('protobuf-undefined-attribute', node.targets[0], 'Child', 'should_warn')
        self.assert_adds_messages(node, msg)

    def test_issue18_renamed_from_import_no_assertion_error(self, parent_mod):
        node = self.extract_node("""
        import {0}
        import {0} as foo
        p = {0}.Parent()
        p.should_warn = 123
        """.format(parent_mod))
        msg = make_message('protobuf-undefined-attribute', node.targets[0], 'Parent', 'should_warn')
        self.assert_adds_messages(node, msg)

    def test_imports_of_wellknown_types(self, wkt_mod):
        node = self.extract_node("""
            from {} import UsesTimestamp
            msg = UsesTimestamp()
            msg.ts.GetCurrentTime()
        """.format(wkt_mod))
        self.assert_no_messages(node)


def test_missing_member_on_module_should_only_raise_nomember(child_mod, module_builder, linter_factory):
    mod = module_builder("""
        import {pb2}
        {pb2}.should_warn
    """.format(pb2=child_mod), 'missing_example1')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'no-member'],
    )
    linter.check([mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert actual_messages == ["Module 'child_pb2' has no 'should_warn' member"]
