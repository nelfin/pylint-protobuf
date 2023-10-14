import pylint.testutils
import pytest

import pylint_protobuf
from tests._testsupport import CheckerTestCase


@pytest.fixture
def complexfield_pb2(proto_builder):
    return proto_builder("""
        message Inner {
          required string value = 1;
        }

        message Outer {
          required Inner inner = 1;
        }
    """, 'complexfield')

@pytest.fixture
def innerclass_pb2(proto_builder):
    return proto_builder("""
        message Person {
          message Alias {
            required string name = 1;
          }
          required Alias primary_alias = 2;
        }
    """, 'innerclass')

@pytest.fixture
def extern_pb2(proto_builder):
    return proto_builder("""
        message Book {
          message Identifier {
            required string URI = 1;
          }
          required Identifier canonical = 2;
        }

        message UserFavourite {
          required Book.Identifier favourite = 1;
        }
    """, 'extern')

@pytest.fixture
def mutual_pb2(proto_builder):
    return proto_builder("""
    message A {
      required B b_mutual = 1;
    }

    message B {
      required A a_mutual = 1;
    }
    """)

@pytest.fixture
def double_pb2(proto_builder):
    return proto_builder("""
        message Outer {
          message Inner {
            message Innermost {
              required string value = 1;
            }
          }
          required Inner.Innermost double_nested = 2;
        }
    """)

@pytest.fixture
def no_package_pb2(proto_builder):
    preamble = 'syntax = "proto2";'  # deliberately no package
    return proto_builder("""
        message GloballyUniqueExternMessage {
          message Inner {
            required string value = 1;
          }
        }

        message GloballyUniqueUsingExternMessage {
          required GloballyUniqueExternMessage.Inner inner = 1;
        }
    """, preamble=preamble)

class TestComplexMessageDefinitions(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_complex_field(self, complexfield_pb2):
        node = self.extract_node("""
        from {} import Outer
        outer = Outer()
        outer.inner.should_warn = 123  #@
        """.format(complexfield_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0],
            args=('should_warn', 'Inner')
        )
        self.assert_adds_messages(node, message)

    def test_complex_field_no_warnings(self, complexfield_pb2):
        node = self.extract_node("""
        from {} import Outer
        outer = Outer()
        outer.inner.value = 'a_string'
        """.format(complexfield_pb2))
        self.assert_no_messages(node)

    def test_issue12_field_defaults_no_errors(self, complexfield_pb2):
        node = self.extract_node("""
        from {} import Inner
        a = Inner()
        b = a.value
        """.format(complexfield_pb2))
        self.assert_no_messages(node)

    def test_inner_class_no_warnings(self, innerclass_pb2):
        node = self.extract_node("""
        from {} import Person
        p = Person()
        p.primary_alias.name = "Example Fakename"  #@
        """.format(innerclass_pb2))
        self.assert_no_messages(node)

    def test_inner_class_no_assignment(self, innerclass_pb2):
        node = self.extract_node("""
        from {} import Person
        p = Person()
        p.primary_alias = Person.Alias(name="Example Fakename")
        """.format(innerclass_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-no-assignment',
            node=node.targets[0], args=('Person', 'primary_alias')
        )
        self.assert_adds_messages(node, message)

    def test_inner_class_warns(self, innerclass_pb2):
        node = self.extract_node("""
        from {} import Person
        p = Person()
        p.primary_alias.should_warn = 123  #@
        """.format(innerclass_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0],
            args=('should_warn', 'Alias')
        )
        self.assert_adds_messages(node, message)

    def test_mutually_recursive_warns(self, mutual_pb2):
        node = self.extract_node("""
        from {} import A
        a = A()
        a.b_mutual.a_mutual.should_warn = 123  #@
        """.format(mutual_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0],
            args=('should_warn', 'A')
        )
        self.assert_adds_messages(node, message)

    def test_external_nested_class_warns(self, extern_pb2):
        node = self.extract_node("""
        from {} import UserFavourite
        pref = UserFavourite()
        pref.favourite.should_warn = 123  #@
        """.format(extern_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0],
            args=('should_warn', 'Identifier')
        )
        self.assert_adds_messages(node, message)

    def test_double_nested_class_warns(self, double_pb2):
        node = self.extract_node("""
        from {} import Outer
        o = Outer()
        o.double_nested.value = 'a_string'
        o.double_nested.should_warn = 'a_string'
        """.format(double_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0],
            args=('should_warn', 'Innermost')
        )
        self.assert_adds_messages(node, message)

    def test_no_toplevel_package_no_error(self, no_package_pb2):
        node = self.extract_node("""
        from {} import GloballyUniqueUsingExternMessage
        o = GloballyUniqueUsingExternMessage()
        o.inner.value = 'a_string'
        o.inner.should_warn = 'a_string'
        """.format(no_package_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0],
            args=('should_warn', 'Inner')
        )
        self.assert_adds_messages(node, message)
