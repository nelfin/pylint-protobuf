import pylint_protobuf
from tests._testsupport import CheckerTestCase


class TestReservedFields(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_reserved_fields_should_appear_undefined(self, proto_builder):
        pb2 = proto_builder("""
            message ReservedMessage {
                optional string value = 1;
                reserved 2 to 5;
                reserved "unused";
            }
        """)
        s = """
            from {} import ReservedMessage
            example = ReservedMessage()
            example.value = 'should not warn'
            example.unused = 'should warn'
        """.format(pb2)
        node = self.extract_node(s)
        msg = self.undefined_attribute_msg(node.targets[0], 'unused', 'ReservedMessage')
        self.assert_adds_messages(node, msg)
