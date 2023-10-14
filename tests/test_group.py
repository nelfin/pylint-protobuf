import pylint_protobuf
from tests._testsupport import CheckerTestCase


class TestGroupFields(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_nonrepeated_groups_are_like_nested_messages(self, proto_builder):
        group_pb2 = proto_builder("""
            message NonRepeatedGroup {
                required group Result = 1 {
                    required string url = 2;
                    optional string title = 3;
                }
            }
        """)
        s = """
            from {} import NonRepeatedGroup
            group = NonRepeatedGroup()
            group.result.url = 123
        """.format(group_pb2)
        node = self.extract_node(s)
        msg = self.type_error_msg(node.targets[0], 'Result', 'url', 'str', 123)
        self.assert_adds_messages(node, msg)

    def test_repeated_groups_are_like_repeated_messages(self, proto_builder):
        group_pb2 = proto_builder("""
            message RepeatedGroup {
                repeated group Result = 1 {
                    required string url = 2;
                    optional string title = 3;
                }
            }
        """)
        s = """
            from {} import RepeatedGroup
            group = RepeatedGroup()
            result = group.result.add()
            result.should_warn = 123
        """.format(group_pb2)
        node = self.extract_node(s)
        msg = self.undefined_attribute_msg(node.targets[0], 'should_warn', 'Result')
        self.assert_adds_messages(node, msg)
