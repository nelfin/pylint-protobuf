import pytest
import astroid
import pylint.testutils

import pylint_protobuf

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

class TestComplexMessageDefinitions(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    @pytest.mark.xfail(reason='externally defined types are Uninferable')
    def test_complex_field(self, complexfield_pb2):
        node = astroid.extract_node("""
        from {} import Outer
        outer = Outer()
        outer.inner.should_warn = 123  #@
        """.format(complexfield_pb2))
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0],
            args=('should_warn', 'Inner')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_complex_field_no_warnings(self, complexfield_pb2):
        node = astroid.extract_node("""
        from {} import Outer
        outer = Outer()
        outer.inner.value = 123  #@
        """.format(complexfield_pb2))
        with self.assertNoMessages():
            self.walk(node.root())

    def test_issue12_field_defaults_no_errors(self, complexfield_pb2):
        node = astroid.extract_node("""
        from {} import Inner
        a = Inner()
        b = a.value
        """.format(complexfield_pb2))
        with self.assertNoMessages():
            self.walk(node.root())

    def test_inner_class_no_warnings(self, innerclass_pb2):
        node = astroid.extract_node("""
        from {} import Person
        p = Person()
        p.primary_alias.name = "Example Fakename"  #@
        """.format(innerclass_pb2))
        with self.assertNoMessages():
            self.walk(node.root())

    def test_inner_class_warns(self, innerclass_pb2):
        node = astroid.extract_node("""
        from {} import Person
        p = Person()
        p.primary_alias.should_warn = 123  #@
        """.format(innerclass_pb2))
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0],
            args=('should_warn', 'Alias')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented external types inference')
    def test_mutually_recursive_warns(self, mutual_pb2):
        node = astroid.extract_node("""
        from {} import A
        a = A()
        a.b_mutual.a_mutual.should_warn = 123  #@
        """.format(mutual_pb2))
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0],
            args=('should_warn', 'fixture.mutual_pb2.A.b_mutual.a_mutual')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.xfail(reason='externally defined types are Uninferable')
    def test_external_nested_class_warns(self, extern_pb2):
        node = astroid.extract_node("""
        from {} import UserFavourite
        pref = UserFavourite()
        pref.favourite.should_warn = 123  #@
        """.format(extern_pb2))
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0],
            args=('should_warn', 'favourite')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())
