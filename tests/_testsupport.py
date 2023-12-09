import astroid
import pylint.testutils


def make_message(message, node, target, attr):
    return pylint.testutils.MessageTest(message, node=node, args=(attr, target))


class CheckerTestCase(pylint.testutils.CheckerTestCase):
    def assert_no_messages(self, node):
        with self.assertNoMessages():
            self.walk(node.root())

    def assert_adds_messages(self, node, *msg, ignore_position=True):
        try:
            with self.assertAddsMessages(*msg, ignore_position=ignore_position):
                self.walk(node.root())
        except TypeError:  # pre ignore_position
            with self.assertAddsMessages(*msg):
                self.walk(node.root())

    @staticmethod
    def extract_node(source):
        return astroid.extract_node(source)

    def make_message(self, msg_id, node, args):
        return pylint.testutils.MessageTest(msg_id, node=node, args=args)

    undefined_attribute_msg = lambda self, node, *args: self.make_message('protobuf-undefined-attribute', node, args)
    enum_value_msg = lambda self, node, *args: self.make_message('protobuf-enum-value', node, args)
    type_error_msg = lambda self, node, *args: self.make_message('protobuf-type-error', node, args)
    no_posargs_msg = lambda self, node: self.make_message('protobuf-no-posargs', node, args=None)
    no_assignment_msg = lambda self, node, *args: self.make_message('protobuf-no-assignment', node, args)
    no_repeated_membership_msg = lambda self, node: self.make_message('protobuf-no-repeated-membership', node, args=None)
    no_proto3_membership_msg = lambda self, node, *args: self.make_message('protobuf-no-proto3-membership', node, args)
    wrong_extension_scope_msg = lambda self, node, *args: self.make_message('protobuf-wrong-extension-scope', node, args)
