import pytest

from conftest import CheckerTestCase, extract_node, make_message

import pylint_protobuf


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
        node = extract_node("""
        from {} import Parent
        """.format(parent_mod))
        self.assert_no_messages(node)

    def test_issue10_imported_message_warns(self, parent_mod):
        node = extract_node("""
        from {} import Parent
        p = Parent()
        p.child.should_warn = 123  #@
        """.format(parent_mod))
        msg = make_message(node.targets[0], 'Child', 'should_warn')
        self.assert_adds_messages(node, msg)

    def test_issue18_renamed_from_import_no_assertion_error(self, parent_mod):
        node = extract_node("""
        import {0}
        import {0} as foo
        p = {0}.Parent()
        p.should_warn = 123
        """.format(parent_mod))
        msg = make_message(node.targets[0], 'Parent', 'should_warn')
        self.assert_adds_messages(node, msg)

    def test_imports_of_wellknown_types(self, wkt_mod):
        node = extract_node("""
            from {} import UsesTimestamp
            msg = UsesTimestamp()
            msg.ts.GetCurrentTime()
        """.format(wkt_mod))
        self.assert_no_messages(node)
