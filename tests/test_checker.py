import sys
import textwrap

import pytest
import astroid
import pylint.testutils

import pylint_protobuf


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

    @pytest.mark.xfail(reason='unimplemented')
    def test_complex_field(self):
        node = astroid.extract_node("""
        from complexfield_pb2 import Outer
        outer = complexfield_pb2.Outer()
        outer.inner.should_warn = 123  #@
        """)
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('should_warn', 'complexfield_pb2.Outer')
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

    @pytest.mark.xfail(reason='unimplemented')
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
        scope, _ = pylint_protobuf.visit_assign_node(scope, {}, assign)
        assert 'a' in scope
        assert scope['a'] is Person

    def test_new_assignattr(self):
        Person = object()
        type_fields = {Person: ['foo', 'bar']}
        scope = {'a': Person}
        assign = astroid.extract_node("a.should_warn = 123")
        _, messages = pylint_protobuf.visit_assign_node(scope, type_fields, assign)
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

    @pytest.mark.skip(reason='API change')
    def test_new_typeof_wacky_import(self):
        Person = pylint_protobuf.TypeClass(object())
        Rando = pylint_protobuf.TypeClass(object())
        scope = {
            'mod': pylint_protobuf.Module,
            'other': pylint_protobuf.Module,
            'mod.child': pylint_protobuf.Module,
            'mod.child.Person': Person,
            'other.child': pylint_protobuf.Module,
            'other.child.Person': Rando,
        }
        node = astroid.extract_node('mod.child.Person')
        assert pylint_protobuf._typeof(scope, node) is Person

    @pytest.mark.skip(reason='API change')
    def test_new_typeof_module_factory_import(self):
        Factory = object()
        Person = object()
        scope = {
            'factory': Factory,
            'factory.mod': pylint_protobuf.Module,
            'factory.mod.Person': Person,
        }
        node = astroid.extract_node('factory.mod.Person')
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
        Person = type('Person', (object, ), {'DESCRIPTOR': _PERSON})
        """))
        scope, fields = {}, {}
        node = astroid.extract_node('import module_pb2')
        modname = node.names[0][0]
        scope, fields = pylint_protobuf.import_(node, modname, scope, fields)
        assert 'module_pb2' in scope
        # assert 'module_pb2.Person' in scope
        # Person = scope['module_pb2.Person']
        # assert fields[Person] == ['foo', 'bar']
        assert 'module_pb2.Person' in fields
        assert fields['module_pb2.Person'] == ['valid_field']
