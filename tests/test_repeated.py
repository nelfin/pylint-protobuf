import pylint.checkers.typecheck
import pylint.testutils
import pytest

import pylint_protobuf
from tests._testsupport import CheckerTestCase


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

class TestProtobufRepeatedFields(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_no_warnings(self, repeated_scalar_mod):
        node = self.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values.append("hello")  # should not raise
        """.format(repeated=repeated_scalar_mod))
        self.assert_no_messages(node)

    def test_repeated_attrassign(self, repeated_scalar_mod):
        node = self.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values = ["abc", "def"]
        """.format(repeated=repeated_scalar_mod))
        message = pylint.testutils.MessageTest(
            'protobuf-no-assignment',
            node=node.targets[0], args=('Repeated', 'values')
        )
        self.assert_adds_messages(node, message)

    def test_repeated_attrassign_no_typeerror(self, repeated_scalar_mod):
        node = self.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values = [123, 456]
        """.format(repeated=repeated_scalar_mod))
        message = pylint.testutils.MessageTest(
            'protobuf-no-assignment',
            node=node.targets[0], args=('Repeated', 'values')
        )
        self.assert_adds_messages(node, message)

    def test_repeated_scalar_assign_no_typeerror(self, repeated_scalar_mod):
        node = self.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values = 123
        """.format(repeated=repeated_scalar_mod))
        message = pylint.testutils.MessageTest(
            'protobuf-no-assignment',
            node=node.targets[0], args=('Repeated', 'values')
        )
        self.assert_adds_messages(node, message)

    def test_scalar_typeerror(self, repeated_scalar_mod):
        node = self.extract_node("""
            import {repeated}

            msg = {repeated}.Repeated()
            msg.values.append(123)
        """.format(repeated=repeated_scalar_mod))
        message = pylint.testutils.MessageTest(
            'protobuf-type-error',
            node=node, args=('Repeated', 'values', 'str', 123)
        )
        self.assert_adds_messages(node, message)

    def test_scalar_append_bad_usage_no_error(self, repeated_scalar_mod):
        node = self.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            msg.values.append(123, 456)
        """.format(mod=repeated_scalar_mod))
        self.assert_no_messages(node)

    def test_scalar_extend_warns_on_each(self, repeated_scalar_mod):
        node = self.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            msg.values.extend([123, 456])
        """.format(mod=repeated_scalar_mod))
        m1 = pylint.testutils.MessageTest(
            'protobuf-type-error',
            node=node, args=('Repeated', 'values', 'str', 123)
        )
        m2 = pylint.testutils.MessageTest(
            'protobuf-type-error',
            node=node, args=('Repeated', 'values', 'str', 456)
        )
        self.assert_adds_messages(node, m1, m2)

    def test_scalar_extend_indirect_warns(self, repeated_scalar_mod):
        node = self.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            vals = [123]
            msg.values.extend(vals)
        """.format(mod=repeated_scalar_mod))
        msg = pylint.testutils.MessageTest(
            'protobuf-type-error',
            node=node, args=('Repeated', 'values', 'str', 123)
        )
        self.assert_adds_messages(node, msg)

    def test_scalar_extend_bad_usage_no_error(self, repeated_scalar_mod):
        node = self.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            msg.values.extend([123], [456])
        """.format(mod=repeated_scalar_mod))
        self.assert_no_messages(node)

    def test_list_extend_bad_usage_no_error(self):
        node = self.extract_node("""
            msg = []
            msg.extend([123], [456])
        """)
        self.assert_no_messages(node)

    def test_nonscalar_append_bad_usage_no_error(self):
        node = self.extract_node("""
            class NonProtobuf(object):
                values = []
            msg = NonProtobuf()
            msg.values.append(123, 456)
        """)
        self.assert_no_messages(node)

    def test_scalar_append_uninferable_no_error(self, repeated_scalar_mod):
        node = self.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            msg.values.append(get_external())
        """.format(mod=repeated_scalar_mod))
        self.assert_no_messages(node)

    def test_scalar_extend_uninferable_no_error(self, repeated_scalar_mod):
        node = self.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            msg.values.extend([get_external()])
        """.format(mod=repeated_scalar_mod))
        self.assert_no_messages(node)

    def test_scalar_indirect_extend_uninferable_no_error(self, repeated_scalar_mod):
        node = self.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            vals = [get_external()]
            msg.values.extend(vals)
        """.format(mod=repeated_scalar_mod))
        self.assert_no_messages(node)

    def test_nonscalar_append_uninferable_no_error(self):
        node = self.extract_node("""
            class NonProtobuf(object):
                values = []
            msg = NonProtobuf()
            msg.values.append(get_external())
        """)
        self.assert_no_messages(node)

    @pytest.mark.xfail(reason='unimplemented, needs design review',
                       raises=AssertionError, match='Expected messages did not match actual')
    def test_indirect_access_no_error(self, repeated_scalar_mod):
        node = self.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            v = msg.values
            v.append(123)
        """.format(mod=repeated_scalar_mod))
        msg = pylint.testutils.MessageTest(
            'protobuf-type-error',
            node=node, args=('Repeated', 'values', 'str', 123)
        )
        self.assert_adds_messages(node, msg)

    def test_not_a_repeated_field_no_typeerror(self, repeated_scalar_mod):
        node = self.extract_node("""
            import {mod}
            msg = {mod}.Repeated()
            msg.other.append(123)
        """.format(mod=repeated_scalar_mod))
        msg = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.func.expr, args=('other', 'Repeated')
        )
        self.assert_adds_messages(node, msg)

    def test_missing_field_on_repeated_inner_warns(self, repeated_composite_mod):
        node = self.extract_node("""
        import {repeated}

        outer = {repeated}.Outer()
        inner = outer.values.add()
        inner.invalid_field = 123  #@
        """.format(repeated=repeated_composite_mod))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'Inner')
        )
        self.assert_adds_messages(node, message)

    def test_missing_field_on_repeated_warns(self, repeated_external_composite_mod):
        node = self.extract_node("""
        import {repeated}

        outer = {repeated}.Outer()
        inner = outer.values.add()
        inner.invalid_field = 123  #@
        """.format(repeated=repeated_external_composite_mod))
        message = pylint.testutils.MessageTest(
            'protobuf-undefined-attribute',
            node=node.targets[0], args=('invalid_field', 'Inner')
        )
        self.assert_adds_messages(node, message)

    def test_repeated_composite_supports_append(self, repeated_composite_mod):
        node = self.extract_node("""
        import {repeated}

        outer = {repeated}.Outer()
        inner = {repeated}.Outer.Inner()
        inner.value = 'a string'
        outer.values.append(inner)
        """.format(repeated=repeated_composite_mod))
        self.assert_no_messages(node)

    def test_no_posargs_on_repeated_add(self, repeated_composite_mod):
        s = """
            import {mod}
            outer = {mod}.Outer()
            outer.values.add(123)
        """.format(mod=repeated_composite_mod)
        node = self.extract_node(s)
        msg = self.no_posargs_msg(node)
        self.assert_adds_messages(node, msg)

    def test_typeerror_on_repeated_kwargs(self, repeated_composite_mod):
        s = """
            import {mod}
            outer = {mod}.Outer()
            outer.values.add(value=123)
        """.format(mod=repeated_composite_mod)
        node = self.extract_node(s)
        msg = self.type_error_msg(node, 'Inner', 'value', 'str', 123)
        self.assert_adds_messages(node, msg)


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


def test_E1123_on_repeated_add(repeated_composite_mod, module_builder, linter_factory):
    warnings_mod = module_builder("""
        import {mod}
        outer = {mod}.Outer()
        outer.values.add(should_warn=123)
    """.format(mod=repeated_composite_mod), 'unexpect_kwarg_in_add')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['unexpected-keyword-arg', 'protobuf-type-error'],
    )
    linter.check([warnings_mod])
    expected_messages = [
        pylint.checkers.typecheck.MSGS['E1123'][0] % ('should_warn', 'constructor')
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert sorted(actual_messages) == sorted(expected_messages)
