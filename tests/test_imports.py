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


class TestImportedProtoDefinitions(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_issue9_imported_message_no_attribute_error(self, parent_mod):
        node = extract_node("""
        from {} import Parent
        """.format(parent_mod))
        self.assert_no_messages(node)

    @pytest.mark.xfail(reason='external message definitions (Child) are Uninferable')
    def test_issue10_imported_message_warns(self, parent_mod):
        # NOTE: this works if we hardcode the lookup for the initialiser as
        # self.child = child__pb2.Child(), just need to determine a way to
        # programmatically determine this
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
