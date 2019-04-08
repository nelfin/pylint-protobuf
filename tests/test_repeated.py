import astroid
import pylint.testutils

import pylint_protobuf


class TestProtobufRepeatedFields(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_missing_field_on_repeated_warns(self):
        node = astroid.extract_node("""
        import repeated_pb2

        outer = repeated_pb2.Outer()
        inner = outer.items.add()
        inner.invalid_field = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'Inner')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())
