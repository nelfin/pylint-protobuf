import pytest
import astroid
import pylint.testutils

import pylint_protobuf

@pytest.fixture
def repeated_scalar_mod(proto_builder):
    return proto_builder("""
        message Repeated {
            repeated string values = 1;
        }
    """)

@pytest.fixture
def repeated_composite_mod(proto_builder):
    return proto_builder("""
        message Outer {
            message Inner {
                required string value = 1;
            }
            repeated Inner values = 1;
        }
    """)

@pytest.fixture
def repeated_external_composite_mod(proto_builder):
    # Pretty much the same as a map entry
    return proto_builder("""
        message Inner {
            required string value = 1;
        }
        message Outer {
            repeated Inner values = 1;
        }
    """)

# repeated scalar (append) vs repeated composite (add)

class TestProtobufRepeatedFields(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_no_warnings(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values.append("hello")  # should not raise
        """.format(repeated=repeated_scalar_mod))
        with self.assertNoMessages():
            self.walk(node.root())

    def test_repeated_attrassign(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values = ["abc", "def"]
        """.format(repeated=repeated_scalar_mod))
        message = pylint.testutils.Message(
            'protobuf-no-assignment',
            node=node.targets[0], args=('Repeated', 'values')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_repeated_attrassign_no_typeerror(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values = [123, 456]
        """.format(repeated=repeated_scalar_mod))
        message = pylint.testutils.Message(
            'protobuf-no-assignment',
            node=node.targets[0], args=('Repeated', 'values')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_repeated_scalar_assign_no_typeerror(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values = 123
        """.format(repeated=repeated_scalar_mod))
        message = pylint.testutils.Message(
            'protobuf-no-assignment',
            node=node.targets[0], args=('Repeated', 'values')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_scalar_typeerror(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values.append(123)
        """.format(repeated=repeated_scalar_mod))
        message = pylint.testutils.Message(
            'protobuf-type-error',
            node=node, args=('Repeated', 'values', 'str', 123)
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_scalar_append_bad_usage_no_error(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            msg.values.append(123, 456)
        """.format(mod=repeated_scalar_mod))
        with self.assertNoMessages():
            self.walk(node.root())

    def test_scalar_extend_warns_on_each(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            msg.values.extend([123, 456])
        """.format(mod=repeated_scalar_mod))
        m1 = pylint.testutils.Message(
            'protobuf-type-error',
            node=node, args=('Repeated', 'values', 'str', 123)
        )
        m2 = pylint.testutils.Message(
            'protobuf-type-error',
            node=node, args=('Repeated', 'values', 'str', 456)
        )
        with self.assertAddsMessages(m1, m2):
            self.walk(node.root())

    def test_scalar_extend_indirect_warns(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            vals = [123]
            msg.values.extend(vals)
        """.format(mod=repeated_scalar_mod))
        msg = pylint.testutils.Message(
            'protobuf-type-error',
            node=node, args=('Repeated', 'values', 'str', 123)
        )
        with self.assertAddsMessages(msg):
            self.walk(node.root())

    def test_scalar_extend_bad_usage_no_error(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            msg.values.extend([123], [456])
        """.format(mod=repeated_scalar_mod))
        with self.assertNoMessages():
            self.walk(node.root())

    def test_list_extend_bad_usage_no_error(self):
        node = astroid.extract_node("""
            msg = []
            msg.extend([123], [456])
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_nonscalar_append_bad_usage_no_error(self):
        node = astroid.extract_node("""
            class NonProtobuf(object):
                values = []
            msg = NonProtobuf()
            msg.values.append(123, 456)
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    def test_scalar_append_uninferable_no_error(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            msg.values.append(get_external())
        """.format(mod=repeated_scalar_mod))
        with self.assertNoMessages():
            self.walk(node.root())

    def test_scalar_extend_uninferable_no_error(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            msg.values.append([get_external()])
        """.format(mod=repeated_scalar_mod))
        with self.assertNoMessages():
            self.walk(node.root())

    def test_scalar_indirect_extend_uninferable_no_error(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            vals = [get_external()]
            msg.values.append(vals)
        """.format(mod=repeated_scalar_mod))
        with self.assertNoMessages():
            self.walk(node.root())

    def test_nonscalar_append_uninferable_no_error(self):
        node = astroid.extract_node("""
            class NonProtobuf(object):
                values = []
            msg = NonProtobuf()
            msg.values.append(get_external())
        """)
        with self.assertNoMessages():
            self.walk(node.root())

    @pytest.mark.xfail(reason='unimplemented, needs design review',
                       raises=AssertionError, match='Expected messages did not match actual')
    def test_indirect_access_no_error(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            v = msg.values
            v.append(123)
        """.format(mod=repeated_scalar_mod))
        msg = pylint.testutils.Message(
            'protobuf-type-error',
            node=node, args=('Repeated', 'values', 'str', 123)
        )
        with self.assertAddsMessages(msg):
            self.walk(node.root())

    def test_not_a_repeated_field_no_typeerror(self, repeated_scalar_mod):
        node = astroid.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            msg.other.append(123)
        """.format(mod=repeated_scalar_mod))
        msg = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.func.expr, args=('other', 'Repeated')
        )
        with self.assertAddsMessages(msg):
            self.walk(node.root())

    def test_missing_field_on_repeated_inner_warns(self, repeated_composite_mod):
        node = astroid.extract_node("""
        import {repeated}

        outer = {repeated}.Outer()
        inner = outer.values.add()
        inner.invalid_field = 123  #@
        """.format(repeated=repeated_composite_mod))
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'Inner')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_missing_field_on_repeated_warns(self, repeated_external_composite_mod):
        node = astroid.extract_node("""
        import {repeated}

        outer = {repeated}.Outer()
        inner = outer.values.add()
        inner.invalid_field = 123  #@
        """.format(repeated=repeated_external_composite_mod))
        message = pylint.testutils.Message(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'Inner')
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_repeated_composite_supports_append(self, repeated_composite_mod):
        node = astroid.extract_node("""
        import {repeated}

        outer = {repeated}.Outer()
        inner = {repeated}.Outer.Inner()
        inner.value = 'a string'
        outer.values.append(inner)
        """.format(repeated=repeated_composite_mod))
        with self.assertNoMessages():
            self.walk(node.root())


@pytest.fixture
def scalar_warnings_mod(repeated_scalar_mod, module_builder):
    return module_builder("""
        import {repeated}

        msg = {repeated}.Repeated()
        msg.values.append("hello")          # should not raise
        print(msg.values.should_raise)
    """.format(repeated=repeated_scalar_mod), 'scalar_warnings_mod')


def test_no_E1101_on_repeated_fields(scalar_warnings_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['no-member', 'protobuf-undefined-attribute'],
    )
    linter.check([scalar_warnings_mod])
    expected_messages = [
        "Instance of 'list' has no 'should_raise' member",
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert actual_messages
    assert sorted(actual_messages) == sorted(expected_messages)
