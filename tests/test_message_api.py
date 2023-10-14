import pytest

import pylint_protobuf
from tests._testsupport import CheckerTestCase


@pytest.fixture
def proto2_example(proto_builder):
    return proto_builder("""
        message Example {
            message Inner {
                required int32 sub_count = 1;
            }
            required int32 count = 1;
            required Inner inner = 2;
            optional string tag = 3;
            repeated int32 friends = 4;
        }
    """)

class TestMessageApiProto2(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    @pytest.mark.parametrize('field,field_to_check,message_id,message_args', [
        ('example', 'count', None, None),  # unset required
        ('example', 'tag', None, None),  # unset optional
        ('example', 'inner', None, None),  # unset sub_message
        ('example', 'friends', 'protobuf-no-repeated-membership', None),  # repeated field
        ('example', 'should_warn', 'protobuf-undefined-attribute', ('should_warn', 'Example')),  # no such field
        ('example.inner', 'sub_count', None, None),  # unset sub_message required field
        ('example.inner', 'should_warn', 'protobuf-undefined-attribute', ('should_warn', 'Inner')),  # no such field
    ])
    def test_hasfield(self, field, field_to_check, message_id, message_args, proto2_example):
        s = """
            from {} import Example
            example = Example()
            {}.HasField({!r})
        """.format(proto2_example, field, field_to_check)
        node = self.extract_node(s)
        if message_id is None:
            self.assert_no_messages(node)
        else:
            msg = self.make_message(message_id, node, message_args)
            self.assert_adds_messages(node, msg)

    @pytest.mark.parametrize('field,field_to_check,message_id,message_args', [
        ('example', 'count', None, None),  # unset required
        ('example', 'tag', None, None),  # unset optional
        ('example', 'inner', None, None),  # unset sub_message
        ('example', 'friends', 'protobuf-no-repeated-membership', None),  # repeated field
        ('example', 'should_warn', 'protobuf-undefined-attribute', ('should_warn', 'Example')),  # no such field
        ('example.inner', 'sub_count', None, None),  # unset sub_message required field
        ('example.inner', 'should_warn', 'protobuf-undefined-attribute', ('should_warn', 'Inner')),  # no such field
    ])
    def test_clearfield(self, field, field_to_check, message_id, message_args, proto2_example):
        s = """
            from {} import Example
            example = Example()
            {}.ClearField({!r})
        """.format(proto2_example, field, field_to_check)
        node = self.extract_node(s)
        if message_id is None:
            self.assert_no_messages(node)
        else:
            msg = self.make_message(message_id, node, message_args)
            self.assert_adds_messages(node, msg)


@pytest.fixture
def proto3_example(proto_builder, request):
    name = request.node.name.translate({ord(c): ord('_') for c in '/.:[]-'})
    # TODO: rework proto_builder to just take a syntax argument?
    preamble = 'syntax = "proto3";\npackage {};\n'.format(name)
    return proto_builder("""
        message Example {
            message Inner {
                int32 sub_count = 1;
            }
            int32 count = 1;
            Inner inner = 2;
            // optional string tag = 3;
            // optional needs --experimental_allow_proto3_optional, equivalent to the following:
            oneof _tag {
                string tag = 3;
            }
            repeated int32 friends = 4;
        }
    """, preamble=preamble)


class TestMessageApiProto3(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    @pytest.mark.parametrize('field,field_to_check,message_id,message_args', [
        ('example', 'count', 'protobuf-no-proto3-membership', ('count',)),  # unset required
        ('example', 'tag', None, None),  # unset optional
        ('example', 'inner', None, None),  # unset sub_message
        ('example', 'friends', 'protobuf-no-repeated-membership', None),  # repeated field
        ('example', 'should_warn', 'protobuf-undefined-attribute', ('should_warn', 'Example')),  # no such field
        ('example.inner', 'sub_count', 'protobuf-no-proto3-membership', ('sub_count',)),  # unset sub_message required field
        ('example.inner', 'should_warn', 'protobuf-undefined-attribute', ('should_warn', 'Inner')),  # no such field
    ])
    def test_hasfield(self, field, field_to_check, message_id, message_args, proto3_example):
        # Traceback (most recent call last):
        #   File "proto3_hasfield.py", line 3, in <module>
        #     assert e.HasField('count')  # will raise ValueError
        # ValueError: Can't test non-optional, non-submessage field "Example.value" for presence in proto3.
        s = """
                from {} import Example
                example = Example()
                {}.HasField({!r})
            """.format(proto3_example, field, field_to_check)
        node = self.extract_node(s)
        if message_id is None:
            self.assert_no_messages(node)
        else:
            msg = self.make_message(message_id, node, message_args)
            self.assert_adds_messages(node, msg)

    @pytest.mark.parametrize('field,field_to_check,message_id,message_args', [
        ('example', 'count', 'protobuf-no-proto3-membership', ('count',)),  # unset required
        ('example', 'tag', None, None),  # unset optional
        ('example', 'inner', None, None),  # unset sub_message
        ('example', 'friends', 'protobuf-no-repeated-membership', None),  # repeated field
        ('example', 'should_warn', 'protobuf-undefined-attribute', ('should_warn', 'Example')),  # no such field
        ('example.inner', 'sub_count', 'protobuf-no-proto3-membership', ('sub_count',)),  # unset sub_message required field
        ('example.inner', 'should_warn', 'protobuf-undefined-attribute', ('should_warn', 'Inner')),  # no such field
    ])
    def test_clearfield(self, field, field_to_check, message_id, message_args, proto3_example):
        s = """
                from {} import Example
                example = Example()
                {}.ClearField({!r})
            """.format(proto3_example, field, field_to_check)
        node = self.extract_node(s)
        if message_id is None:
            self.assert_no_messages(node)
        else:
            msg = self.make_message(message_id, node, message_args)
            self.assert_adds_messages(node, msg)
