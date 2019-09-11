import pytest
import astroid
import pylint.testutils

import pylint_protobuf


class TestEnumDefinitions(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    @pytest.mark.xfail(reason='unimplemented')
    def test_import_enum_types_no_errors(self):
        node = astroid.extract_node("""
        from fixture.enum_pb2 import Variable
        print(Variable)
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented')
    def test_import_enum_values_no_errors(self):
        node = astroid.extract_node("""
        from fixture.enum_pb2 import DISCRETE
        print(DISCRETE)
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented')
    def test_import_enum_attributes_no_errors(self):
        node = astroid.extract_node("""
        from fixture.enum_pb2 import Variable
        print(Variable.DISCRETE)
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented')
    def test_import_enum_missing_attributes_warns(self):
        node = astroid.extract_node("""
        from fixture.enum_pb2 import Variable
        print(Variable.MISSING)  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0],  # FIXME: what's the target?
            args=('should_warn', 'fixture.enum_pb2.MISSING')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented')
    def test_import_enum_by_value_no_errors(self):
        node = astroid.extract_node("""
        from fixture.enum_pb2 import Variable
        print(Variable.Value('DISCRETE'))
        """)
        with self.assertNoMessages():
            self.walk(node.root())
