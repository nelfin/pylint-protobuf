import sys
import textwrap

import pytest
import astroid
import pylint.testutils

import pylint_protobuf

from hypothesis import given, strategies as st


class TestProtobufDescriptorChecker(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_unaliased_module_happy_path_should_not_warn(self):
        node = astroid.extract_node("""
        import person_pb2

        foo = person_pb2.Person()
        foo.id = 123  #@
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_star_import_no_errors(self):
        node = astroid.extract_node("""
        from person_pb2 import *
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_unaliased_module_happy_path_should_warn(self):
        node = astroid.extract_node("""
        import person_pb2

        foo = person_pb2.Person()
        foo.should_warn  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node, args=('should_warn', 'person_pb2.Person')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_star_import_should_warn(self):
        node = astroid.extract_node("""
        from person_pb2 import *
        foo = Person()
        foo.should_warn  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node, args=('should_warn', 'person_pb2.Person')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.skipif(sys.version_info < (3, 6),
                        reason='AnnAssign requires Python 3.6+')
    def test_annassign_happy_path_should_not_warn(self):
        node = astroid.extract_node("""
        import person_pb2

        foo: Person = person_pb2.Person()
        foo.id = 123  #@
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    @pytest.mark.skipif(sys.version_info < (3, 6),
                        reason='AnnAssign requires Python 3.6+')
    def test_annassign_attr_happy_path_should_not_warn(self):
        node = astroid.extract_node("""
        import person_pb2

        foo: Person = person_pb2.Person()
        foo.id: int = 123  #@
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_unaliased_module_import_should_warn(self):
        node = astroid.extract_node("""
        import person_pb2

        foo = person_pb2.Person()
        foo.invalid_field = 'should warn'  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'person_pb2.Person')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.skipif(sys.version_info < (3, 6),
                        reason='AnnAssign requires Python 3.6+')
    def test_annassign_invalid_field_should_warn(self):
        node = astroid.extract_node("""
        import person_pb2

        foo: Person = person_pb2.Person()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'person_pb2.Person')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.skipif(sys.version_info < (3, 6),
                        reason='AnnAssign requires Python 3.6+')
    def test_annassign_attribute_invalid_field_should_warn(self):
        node = astroid.extract_node("""
        import person_pb2

        foo = person_pb2.Person()
        foo.should_warn: int = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.target, args=('should_warn', 'person_pb2.Person')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_module_import_should_warn(self):
        node = astroid.extract_node("""
        import person_pb2 as person

        foo = person.Person()
        foo.invalid_field = 'should warn'  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'person_pb2.Person')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_module_import_as_self_should_warn(self):
        node = astroid.extract_node("""
        import person_pb2 as person_pb2

        foo = person_pb2.Person()
        foo.invalid_field = 'should warn'  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'person_pb2.Person')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_importfrom_should_warn(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        foo = Foo()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'fake_pb2.Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_importfrom_with_aliasing_should_warn(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo as Bar

        class Foo(object):
            pass  # normal class, not fake_pb2.Foo (nor fake_pb2.Bar)

        bar = Bar()
        bar.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'fake_pb2.Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_importfrom_with_multiple_aliasing(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo, Foo as Bar

        bar = Foo()
        bar.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'fake_pb2.Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_importfrom_with_aliasing_no_warning(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo as Bar

        class Foo(object):
            pass  # normal class, not fake_pb2.Foo (nor fake_pb2.Bar)

        foo = Foo()
        foo.no_error = 123  #@
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_aliasing_via_getitem_does_not_throw(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo
        foo = [Foo][0]()  #@
        """)
        self.walk(node.root())

    def test_aliasing_via_getitem_list(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        bar = [Foo]

        foo = bar[0]()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'fake_pb2.Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_aliasing_via_getitem_dict(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        bar = {
            'baz': Foo,
        }

        foo = bar['baz']()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'fake_pb2.Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_aliasing_via_getitem_uninferable_should_not_warn(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo
        from random import randint

        types = [Foo, int]
        foo = types[randint(0, 2)]()
        foo.should_warn = 123  #@
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_aliasing_via_getitem_nested_lists(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        bar = [[Foo]]
        foo = bar[0][0]()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'fake_pb2.Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_aliasing_via_indirection_class_renaming(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        Indirect = Foo
        foo = Indirect()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'fake_pb2.Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_aliasing_via_instance_renaming(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        foo = Foo()
        bar = foo
        bar.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'fake_pb2.Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_aliasing_via_multiple_assignment(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        baz = bar = Foo()
        baz.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'fake_pb2.Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_bad_fields_in_multiple_assignment_multiple_messages(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        foo = Foo()
        bar = Foo()
        foo.should_warn = bar.should_also_warn = 123  #@
        """)
        messages = [
            pylint.testutils.Message(
                'protobuf-undefined-attribute',
                node=node.targets[0], args=('should_warn', 'fake_pb2.Foo')
            ),
            pylint.testutils.Message(
                'protobuf-undefined-attribute',
                node=node.targets[1], args=('should_also_warn', 'fake_pb2.Foo')
            ),
        ]
        with self.assertAddsMessages(*messages):
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented')
    def test_aliasing_via_indirection_getitem(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        types = {}
        types[0] = Foo
        foo = types[0]()

        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'fake_pb2.Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_aliasing_via_getitem_list_indirection(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        baz = [Foo]
        bar = bar[0]
        foo = baz[0]()
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'fake_pb2.Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented')
    def test_aliasing_via_tuple_unpacking(self):
        node = astroid.extract_node("""
        from fake_pb2 import Foo

        foo, bar = Foo(), 'bar'
        foo.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'fake_pb2.Foo')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_new_typeof_only(self):
        Person = object()
        scope = {'Person': Person}
        node = astroid.extract_node('Person')
        assert pylint_protobuf._typeof(scope, node) is Person

    def test_new_slice_list(self):
        Person = object()
        scope = {'Person': Person}
        node = astroid.extract_node('[Person][0]')
        assert pylint_protobuf._typeof(scope, node) is Person

    def test_new_slice_dict(self):
        Person = object()
        scope = {'Person': Person}
        node = astroid.extract_node('{"a": Person}["a"]')
        assert pylint_protobuf._typeof(scope, node) is Person

    def test_new_slice_nested_dict(self):
        Person = object()
        scope = {'Person': Person}
        node = astroid.extract_node("""
        {
            "outer": {
                "inner": Person
            }
        }["outer"]["inner"]
        """)
        assert pylint_protobuf._typeof(scope, node) is Person

    def test_new_typeof_call(self):
        Person = object()
        scope = {'Person': pylint_protobuf.TypeClass(Person)}
        node = astroid.extract_node("""
        Person()
        """)
        assert pylint_protobuf._typeof(scope, node) is Person

    def test_new_assign(self):
        Person = object()
        scope = {'Person': Person}
        assign = astroid.extract_node("a = Person")
        scope, _ = pylint_protobuf.visit_assign_node(scope, assign)
        assert 'a' in scope
        assert scope['a'] is Person

    def test_new_assignattr(self):
        Person = pylint_protobuf.ClassDef({}, '')
        scope = {'a': Person}
        assign = astroid.extract_node("a.should_warn = 123")
        _, messages = pylint_protobuf.visit_assign_node(scope, assign)
        assert len(messages) == 1
        msg, _, node = messages[0]
        assert msg == 'protobuf-undefined-attribute'
        assert node == assign.targets[0]

    def test_new_typeof_import(self):
        Person = pylint_protobuf.TypeClass(object())
        mod_globals = {'module_pb2.Person': Person}
        module_pb2 = pylint_protobuf.Module('module_pb2', mod_globals)
        scope = {'module_pb2': module_pb2}
        node = astroid.extract_node('module_pb2.Person')
        assert pylint_protobuf._typeof(scope, node) is Person

    def test_new_import(self, tmpdir, monkeypatch):
        monkeypatch.syspath_prepend(tmpdir)
        p = tmpdir.join('module_pb2.py')
        p.write(textwrap.dedent("""
        class _FieldDescriptor(object):
            def __init__(self, name): pass
        class _Descriptor(object):
            def __init__(self, name, fields): pass
        _PERSON = _Descriptor(
            name='PERSON',
            fields=[_FieldDescriptor(name='valid_field')],
        )
        class __FakeModule:
            pass
        _reflection = __FakeModule()
        _reflection.GeneratedProtocolMessageType = type
        Person = _reflection.GeneratedProtocolMessageType('Person', (object, ), {'DESCRIPTOR': _PERSON})
        """))
        scope = {}
        node = astroid.extract_node('import module_pb2')
        modname = node.names[0][0]
        scope = pylint_protobuf.import_(node, modname, scope)
        assert 'module_pb2' in scope
        mod = scope['module_pb2']
        typeclass = mod.getattr('Person')
        class_def = typeclass.t
        assert len(class_def.fields) == 1
        assert 'valid_field' in class_def.fields

    def test_issue5_inferenceerror_should_not_propagate(self):
        node = astroid.extract_node("""
        foo = 'bar/baz'.split('/')[-1]
        """)
        try:
            self.walk(node.root())
        except astroid.exceptions.InferenceError:
            pytest.fail("InferenceError should not propagate")

    def test_issue6_importing_a_missing_module(self):
        node = astroid.extract_node('import missing_module_pb2')
        self.walk(node.root())

    def test_issue6_importing_a_missing_module_as_alias(self):
        node = astroid.extract_node('import missing_module_pb2 as foo')
        self.walk(node.root())

    def test_issue7_indexerror_on_slice_inference(self):
        node = astroid.extract_node("""
        foo = []
        bar = foo[0]  #@
        """)
        self.walk(node.root())

    @pytest.mark.skip(reason='probably should be Uninferable')
    def test_issue7_indexerror_on_correct_slice_inference(self):
        # TODO: this shouldn't raise IndexError, like above, but the value of
        # bar could be correctly inferred unlike above. Should we do this, and
        # where should we draw the line on what is too complex to infer?
        node = astroid.extract_node("""
        foo = []
        foo.append(123)
        bar = foo[0]  #@
        """)
        self.walk(node.root())

    def test_lookup_on_nonetype_should_not_raise(self):
        node = astroid.extract_node('foo = None[0]')
        self.walk(node.root())

    @given(st.sampled_from(pylint_protobuf.PROTOBUF_IMPLICIT_ATTRS))
    def test_implicit_attrs_issue8(self, attr):
        node = astroid.extract_node("""
        from person_pb2 import Person
        p = Person()
        print(p.{})
        """.format(attr))
        with self.assertNoMessages():
            self.walk(node.root())

    def test_issue9_imported_message_no_attribute_error(self):
        node = astroid.extract_node("""
        from fixture.import_pb2 import Parent
        """)
        self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented')
    def test_issue10_imported_message_warns(self):
        node = astroid.extract_node("""
        from fixture.import_pb2 import Parent
        p = Parent()
        p.child.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node, args=('should_warn', 'fixture.import_pb2.Parent.child')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_issue13_importing_a_module_from_package(self):
        node = astroid.extract_node("""
        from fixture import innerclass_pb2
        p = innerclass_pb2.Person()
        p.should_warn = 123
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'innerclass_pb2.Person')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())
