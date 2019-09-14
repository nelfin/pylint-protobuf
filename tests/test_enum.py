import pytest
import astroid
import pylint.testutils

import pylint_protobuf


class TestEnumDefinitions(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_import_enum_types_no_errors(self):
        node = astroid.extract_node("""
        from fixture.enum_pb2 import Variable
        print(Variable)
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_import_enum_values_no_errors(self):
        node = astroid.extract_node("""
        from fixture.enum_pb2 import DISCRETE
        print(DISCRETE)
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_import_enum_attributes_no_errors(self):
        node = astroid.extract_node("""
        from fixture.enum_pb2 import Variable
        print(Variable.DISCRETE)
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_import_enum_missing_attributes_warns(self):
        node = astroid.extract_node("""
        from fixture.enum_pb2 import Variable
        print(
            Variable.should_warn  #@
        )
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node,
            args=('should_warn', 'fixture.enum_pb2.Variable')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_import_enum_by_value_no_errors(self):
        node = astroid.extract_node("""
        from fixture.enum_pb2 import Variable
        print(Variable.Value('DISCRETE'))
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_star_import_enum_no_errors(self):
        node = astroid.extract_node("""
        from fixture.enum_pb2 import *
        print(DISCRETE)
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_star_import_enum_should_warn(self):
        node = astroid.extract_node("""
        from fixture.enum_pb2 import *
        Variable.should_warn  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node,
            args=('should_warn', 'fixture.enum_pb2.Variable')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented')
    def test_import_enum_missing_attribute_by_value_warns(self):
        node = astroid.extract_node("""
        from fixture.enum_pb2 import Variable
        print(
            Variable.Value('should_warn')  #@
        )
        """)
        message = pylint.testutils.Message(
            'protobuf-enum-value',
            node=node,
            args=('should_warn', 'fixture.enum_pb2.Variable')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_issue16_toplevel_enum(self):
        node = astroid.extract_node("""
        import fixture.nested_enum_pb2
        fixture.nested_enum_pb2.ONE
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_issue16_nested_enum_definition_no_errors(self):
        node = astroid.extract_node("""
        import fixture.nested_enum_pb2
        fixture.nested_enum_pb2.Message.UNO
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    @pytest.mark.xfail(reason='nested namespaces unimplemented')
    def test_fixme_issue16_nested_enum_definition_no_errors(self):
        node = astroid.extract_node("""
        import fixture.nested_enum_pb2 as sut
        sut.Message.UNO
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    @pytest.mark.xfail(reason='nested namespaces unimplemented')
    def test_issue16_package_nested_enum_definition_warns(self):
        node = astroid.extract_node("""
        import fixture.nested_enum_pb2
        fixture.nested_enum_pb2.Message.should_warn
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node,
            args=('should_warn', 'fixture.nested_enum_pb2.Message')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_issue16_nested_enum_definition_warns(self):
        node = astroid.extract_node("""
        import fixture.nested_enum_pb2 as sut
        sut.Message.should_warn
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node,
            args=('should_warn', 'fixture.nested_enum_pb2.Message')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_issue16_missing_toplevel_enum(self):
        node = astroid.extract_node("""
        import fixture.nested_enum_pb2 as sut
        sut.UNO
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node,
            args=('UNO', 'fixture.nested_enum_pb2')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.xfail(reason='nested namespaces unimplemented')
    def test_issue16_package_missing_toplevel_enum(self):
        node = astroid.extract_node("""
        import fixture.nested_enum_pb2
        fixture.nested_enum_pb2.UNO
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node,
            args=('UNO', 'fixture.nested_enum_pb2')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())
