import sys

import astroid
import pylint.testutils
import pytest

import pylint_protobuf
from tests._testsupport import CheckerTestCase


@pytest.fixture
def fake_pb2(proto_builder):
    return proto_builder("""
        message Foo {
          required string valid_field = 1;
        }
    """, name='fake')


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
def child_pb2(proto_builder):
    return proto_builder("""
        message Child {}
    """, 'child')


@pytest.fixture
def pb2_package(module_builder, innerclass_pb2, child_pb2):
    return module_builder("""
    import {}
    import {}
    """.format(innerclass_pb2, child_pb2), 'test_package')


@pytest.fixture
def person_pb2(proto_builder):
    return proto_builder("""
        message Person {
          required string name = 1;
          required int32 id = 2;
          optional string email = 3;
        }
    """, 'person')


class TestProtobufDescriptorChecker(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_unaliased_module_happy_path_should_not_warn(self, person_pb2):
        node = self.extract_node("""
        import person_pb2

        foo = person_pb2.Person()
        foo.id = 123  #@
        """)
        self.assert_no_messages(node)

    def test_star_import_no_errors(self, person_pb2):
        node = self.extract_node("""
        from person_pb2 import *
        """)
        self.assert_no_messages(node)

    def test_unaliased_module_happy_path_should_warn(self, person_pb2):
        node = self.extract_node("""
        import person_pb2

        foo = person_pb2.Person()
        foo.should_warn  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node, args=('should_warn', 'Person')
        )
        self.assert_adds_messages(node, message)

    def test_star_import_should_warn(self, person_pb2):
        node = self.extract_node("""
        from person_pb2 import *
        foo = Person()
        foo.should_warn  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node, args=('should_warn', 'Person')
        )
        self.assert_adds_messages(node, message)

    @pytest.mark.skipif(sys.version_info < (3, 6),
                        reason='AnnAssign requires Python 3.6+')
    def test_annassign_happy_path_should_not_warn(self, person_pb2):
        node = self.extract_node("""
        import person_pb2

        foo: Person = person_pb2.Person()
        foo.id = 123  #@
        """)
        self.assert_no_messages(node)

    @pytest.mark.skipif(sys.version_info < (3, 6),
                        reason='AnnAssign requires Python 3.6+')
    def test_annassign_attr_happy_path_should_not_warn(self, person_pb2):
        node = self.extract_node("""
        import person_pb2

        foo: Person = person_pb2.Person()
        foo.id: int = 123  #@
        """)
        self.assert_no_messages(node)

    @pytest.mark.skipif(sys.version_info < (3, 6),
                        reason='AnnAssign requires Python 3.6+')
    def test_annassign_should_warn_if_necessary(self, person_pb2):
        node = self.extract_node("""
        import person_pb2

        foo: Person = person_pb2.Person()
        foo.should_warn: int = 123  #@
        """)  # type: astroid.AnnAssign
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.target, args=('should_warn', 'Person')
        )
        self.assert_adds_messages(node, message)

    def test_unaliased_module_import_should_warn(self, person_pb2):
        node = self.extract_node("""
        import person_pb2

        foo = person_pb2.Person()
        foo.invalid_field = 'should warn'  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'Person')
        )
        self.assert_adds_messages(node, message)

    @pytest.mark.skipif(sys.version_info < (3, 6),
                        reason='AnnAssign requires Python 3.6+')
    def test_annassign_invalid_field_should_warn(self, person_pb2):
        node = self.extract_node("""
        import person_pb2

        foo: Person = person_pb2.Person()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Person')
        )
        self.assert_adds_messages(node, message)

    @pytest.mark.skipif(sys.version_info < (3, 6),
                        reason='AnnAssign requires Python 3.6+')
    def test_annassign_attribute_invalid_field_should_warn(self, person_pb2):
        node = self.extract_node("""
        import person_pb2

        foo = person_pb2.Person()
        foo.should_warn: int = 123  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.target, args=('should_warn', 'Person')
        )
        self.assert_adds_messages(node, message)

    def test_module_import_should_warn(self, person_pb2):
        node = self.extract_node("""
        import person_pb2 as person

        foo = person.Person()
        foo.invalid_field = 'should warn'  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'Person')
        )
        self.assert_adds_messages(node, message)

    def test_module_import_as_self_should_warn(self, person_pb2):
        node = self.extract_node("""
        import person_pb2 as person_pb2

        foo = person_pb2.Person()
        foo.invalid_field = 'should warn'  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'Person')
        )
        self.assert_adds_messages(node, message)

    def test_importfrom_should_warn(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo

        foo = Foo()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        self.assert_adds_messages(node, message)

    def test_importfrom_with_aliasing_should_warn(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo as Bar

        class Foo(object):
            pass  # normal class, not fake_pb2.Foo (nor fake_pb2.Bar)

        bar = Bar()
        bar.should_warn = 123  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        self.assert_adds_messages(node, message)

    def test_importfrom_with_multiple_aliasing(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo, Foo as Bar

        bar = Foo()
        bar.should_warn = 123  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        self.assert_adds_messages(node, message)

    def test_importfrom_with_aliasing_no_warning(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo as Bar

        class Foo(object):
            pass  # normal class, not fake_pb2.Foo (nor fake_pb2.Bar)

        foo = Foo()
        foo.no_error = 123  #@
        """)
        self.assert_no_messages(node)

    def test_aliasing_via_getitem_does_not_throw(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo
        foo = [Foo][0]()  #@
        """)
        self.walk(node.root())

    def test_aliasing_via_getitem_list(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo

        bar = [Foo]

        foo = bar[0]()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        self.assert_adds_messages(node, message)

    def test_aliasing_via_getitem_dict(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo

        bar = {
            'baz': Foo,
        }

        foo = bar['baz']()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        self.assert_adds_messages(node, message)

    def test_aliasing_via_getitem_uninferable_should_not_warn(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo
        from random import randint

        types = [Foo, int]
        foo = types[randint(0, 2)]()
        foo.should_warn = 123  #@
        """)
        self.assert_no_messages(node)

    def test_aliasing_via_getitem_nested_lists(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo

        bar = [[Foo]]
        foo = bar[0][0]()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        self.assert_adds_messages(node, message)

    def test_aliasing_via_indirection_class_renaming(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo

        Indirect = Foo
        foo = Indirect()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        self.assert_adds_messages(node, message)

    def test_aliasing_via_instance_renaming(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo

        foo = Foo()
        bar = foo
        bar.should_warn = 123  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        self.assert_adds_messages(node, message)

    def test_aliasing_via_multiple_assignment(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo

        baz = bar = Foo()
        baz.should_warn = 123  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        self.assert_adds_messages(node, message)

    def test_bad_fields_in_multiple_assignment_multiple_messages(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo

        foo = Foo()
        bar = Foo()
        foo.should_warn = bar.should_also_warn = 123  #@
        """)
        messages = [
            pylint.testutils.MessageTest(
                'protobuf-undefined-attribute',
                node=node.targets[0], args=('should_warn', 'Foo')
            ),
            pylint.testutils.MessageTest(
                'protobuf-undefined-attribute',
                node=node.targets[1], args=('should_also_warn', 'Foo')
            ),
        ]
        self.assert_adds_messages(node, *messages)

    @pytest.mark.xfail(reason='wontfix')
    def test_aliasing_via_indirection_getitem(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo

        types = {}
        types[0] = Foo
        foo = types[0]()

        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        self.assert_adds_messages(node, message)

    def test_aliasing_via_getitem_list_indirection(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo

        baz = [Foo]
        bar = bar[0]
        foo = baz[0]()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        self.assert_adds_messages(node, message)

    def test_aliasing_via_tuple_unpacking(self, fake_pb2):
        node = self.extract_node("""
        from fake_pb2 import Foo

        foo, bar = Foo(), 'bar'
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Foo')
        )
        self.assert_adds_messages(node, message)

    def test_issue5_inferenceerror_should_not_propagate(self):
        node = self.extract_node("""
        foo = 'bar/baz'.split('/')[-1]
        """)
        try:
            self.walk(node.root())
        except astroid.exceptions.InferenceError:
            pytest.fail("InferenceError should not propagate")

    def test_issue6_importing_a_missing_module(self, error_on_missing_modules):
        node = self.extract_node('import missing_module_pb2')
        with pytest.raises(AssertionError, match='expected to import module "missing_module_pb2"'):
            self.walk(node.root())

    def test_issue6_importing_a_missing_module_as_alias(self, error_on_missing_modules):
        node = self.extract_node('import missing_module_pb2 as foo')
        with pytest.raises(AssertionError, match='expected to import module "missing_module_pb2"'):
            self.walk(node.root())

    def test_issue6_from_importing_a_missing_module(self, error_on_missing_modules):
        node = self.extract_node('from missing_module_pb2 import foo')
        with pytest.raises(AssertionError, match='expected to import module "missing_module_pb2"'):
            self.walk(node.root())

    def test_issue7_indexerror_on_slice_inference(self):
        node = self.extract_node("""
        foo = []
        bar = foo[0]  #@
        """)
        self.walk(node.root())

    @pytest.mark.skip(reason='wontfix: probably should be Uninferable')
    def test_issue7_indexerror_on_correct_slice_inference(self):
        # TODO: this shouldn't raise IndexError, like above, but the value of
        # bar could be correctly inferred unlike above. Should we do this, and
        # where should we draw the line on what is too complex to infer?
        node = self.extract_node("""
        foo = []
        foo.append(123)
        bar = foo[0]  #@
        """)
        self.walk(node.root())

    def test_lookup_on_nonetype_should_not_raise(self):
        node = self.extract_node('foo = None[0]')
        self.walk(node.root())

    @pytest.mark.parametrize("attr", pylint_protobuf.PROTOBUF_IMPLICIT_ATTRS)
    def test_implicit_attrs_issue8(self, attr, person_pb2):
        node = self.extract_node("""
        from person_pb2 import Person
        p = Person()
        print(p.{})
        """.format(attr))
        self.assert_no_messages(node)

    def test_issue13_importing_a_module_from_package(self, innerclass_pb2):
        node = self.extract_node("""
        import {mod}
        p = {mod}.Person()
        p.should_warn = 123
        """.format(mod=innerclass_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Person')
        )
        self.assert_adds_messages(node, message)

    def test_issue13_importing_a_module_with_alias_from_package(self, innerclass_pb2):
        node = self.extract_node("""
        import {mod} as foo
        p = foo.Person()
        p.should_warn = 123
        """.format(mod=innerclass_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Person')
        )
        self.assert_adds_messages(node, message)

    def test_issue13_importing_many_modules_from_package_no_errors(self, pb2_package):
        node = self.extract_node("""
        from {} import innerclass_pb2, child_pb2
        """.format(pb2_package))
        self.walk(node.root())

    def test_issue13_importing_many_modules_with_aliases_from_package(self, pb2_package):
        node = self.extract_node("""
        from {} import child_pb2 as bar, innerclass_pb2 as foo
        p = foo.Person()
        p.should_warn = 123
        """.format(pb2_package))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Person')
        )
        self.assert_adds_messages(node, message)

    def test_module_import_renaming_still_warns(self, person_pb2):
        node = self.extract_node("""
        import person_pb2 as person_pb2
        import person_pb2 as foobar
        p = person_pb2.Person()
        p.should_warn = 123
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'Person')
        )
        self.assert_adds_messages(node, message)

    def test_typeerror_on_attrassign(self, person_pb2):
        node = self.extract_node("""
        import person_pb2
        p = person_pb2.Person()
        p.name = 123
        """)
        message = pylint.testutils.MessageTest(
            'protobuf-type-error',
            node=node.targets[0], args=('Person', 'name', 'str', 123)
        )
        self.assert_adds_messages(node, message)
