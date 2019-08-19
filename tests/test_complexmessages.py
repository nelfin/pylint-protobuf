import astroid
import pylint.testutils

import pylint_protobuf


class TestComplexMessageDefinitions(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_complex_field(self):
        node = astroid.extract_node("""
        from fixture.complexfield_pb2 import Outer
        outer = Outer()
        outer.inner.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0],
            args=('should_warn', 'fixture.complexfield_pb2.Outer.inner')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_complex_field_no_warnings(self):
        node = astroid.extract_node("""
        from fixture.complexfield_pb2 import Outer
        outer = Outer()
        outer.inner.value = 123  #@
        """)
        with self.assertNoMessages():
            self.walk(node.root())
