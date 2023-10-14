import pylint.testutils
import pytest

import pylint_protobuf
from tests._testsupport import CheckerTestCase


@pytest.fixture
def person_pb2(proto_builder):
    return proto_builder("""
        message Person {
          required string name = 1;
          required int32 code = 2;
          optional string email = 3;
          required float fraction = 4;
          required bool toggle = 5;
        }
    """)


class TestSimpleTypeError(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_inferred_assignattr_warns(self, person_pb2):
        node = self.extract_node("""
            from {} import Person
            p = Person()
            code = 123
            p.name = code
        """.format(person_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-type-error',
            node=node.targets[0], args=('Person', 'name', 'str', 123)
        )
        self.assert_adds_messages(node, message)

    def test_uninferable_assignattr_no_warn(self, person_pb2):
        node = self.extract_node("""
            from {} import Person
            p = Person()
            p.name = get_user_name()
        """.format(person_pb2))
        self.assert_no_messages(node)

    def test_issue40_type_constructor_warns(self, person_pb2):
        node = self.extract_node("""
            from {} import Person
            Person(code=int)
        """.format(person_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-type-error',
            node=node, args=('Person', 'code', 'int', 'int()')
        )
        self.assert_adds_messages(node, message)

    def test_issue40_float_constructor_warns(self, person_pb2):
        node = self.extract_node("""
            from {} import Person
            Person(fraction=float)
        """.format(person_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-type-error',
            node=node, args=('Person', 'fraction', 'float', 'float()')
        )
        self.assert_adds_messages(node, message)

    def test_issue40_int_constructor_no_warn(self, person_pb2):
        node = self.extract_node("""
            from {} import Person
            Person(code=int('1'))
        """.format(person_pb2))
        self.assert_no_messages(node)

    def test_issue40_int_from_float_warns(self, person_pb2):
        node = self.extract_node("""
            from {} import Person
            Person(code=123.0)
        """.format(person_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-type-error',
            node=node, args=('Person', 'code', 'int', 123.0)
        )
        self.assert_adds_messages(node, message)

    def test_issue41_float_from_float_no_warn(self, person_pb2):
        node = self.extract_node("""
            from {} import Person
            Person(fraction=123.0)
        """.format(person_pb2))
        self.assert_no_messages(node)

    def test_issue41_float_from_int_no_warn(self, person_pb2):
        node = self.extract_node("""
            from {} import Person
            Person(fraction=123)
        """.format(person_pb2))
        self.assert_no_messages(node)

    def test_issue41_float_from_int_constructor_no_warn(self, person_pb2):
        node = self.extract_node("""
            from {} import Person
            p = Person(fraction=int('123'))
        """.format(person_pb2))
        self.assert_no_messages(node)

    def test_issue42_kwargs_none_should_not_warn(self, person_pb2):
        # It's silly, but true
        node = self.extract_node("""
            from {} import Person
            Person(code=None)
        """.format(person_pb2))
        self.assert_no_messages(node)

    def test_issue42_assignattr_none_should_warn(self, person_pb2):
        node = self.extract_node("""
            from {} import Person
            p = Person()
            p.code = None
        """.format(person_pb2))
        message = pylint.testutils.MessageTest(
            'protobuf-type-error',
            node=node.targets[0], args=('Person', 'code', 'int', None)
        )
        self.assert_adds_messages(node, message)


@pytest.fixture
def typeerror_mod(person_pb2, module_builder):
    return module_builder("""
        import {mod}
        p = {mod}.Person()
        p.name = 123
    """.format(mod=person_pb2), 'typeerror_mod')


def test_E5903_on_scalar_assignment(typeerror_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'protobuf-type-error'],
    )
    linter.check([typeerror_mod])
    expected_messages = [
        pylint_protobuf.MESSAGES['E5903'][0] % ('Person', 'name', 'str', 123)
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert actual_messages
    assert sorted(actual_messages) == sorted(expected_messages)


@pytest.fixture
def typeerror_kwargs_mod(person_pb2, module_builder):
    return module_builder("""
        import {mod}
        p = {mod}.Person(name=123, code='abc', email=456)
    """.format(mod=person_pb2), 'typeerror_kwargs_mod')


def test_multiple_E5903_on_same_line(typeerror_kwargs_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'protobuf-type-error'],
    )
    linter.check([typeerror_kwargs_mod])
    expected_messages = [
        pylint_protobuf.MESSAGES['E5903'][0] % ('Person', 'name', 'str', 123),
        pylint_protobuf.MESSAGES['E5903'][0] % ('Person', 'code', 'int', 'abc'),
        pylint_protobuf.MESSAGES['E5903'][0] % ('Person', 'email', 'str', 456),
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert actual_messages
    assert sorted(actual_messages) == sorted(expected_messages)


@pytest.fixture
def composite_pb2(proto_builder):
    return proto_builder("""
        message Train {
          message Driver {
            required string name = 1;
            required int32 id = 2;
          }
          required Driver driver = 3;
          required string engine_id = 4;
        }
    """)


@pytest.fixture
def composite_kwarg_mod(composite_pb2, module_builder):
    return module_builder("""
        from {mod} import Train
        t = Train(engine_id='abc123', driver=Train.Driver(name='Example', id=456))
    """.format(mod=composite_pb2), 'composite_kwarg_mod')


def test_no_warnings_on_composite_kwarg(composite_kwarg_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'protobuf-type-error'],
    )
    linter.check([composite_kwarg_mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert not actual_messages


@pytest.fixture
def composite_bad_kwarg_mod(composite_pb2, module_builder):
    return module_builder("""
        from {mod} import Train
        t = Train(engine_id='abc123', driver='bad_type')
    """.format(mod=composite_pb2), 'composite_bad_kwarg_mod')


def test_warnings_on_composite_kwarg(composite_bad_kwarg_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'protobuf-type-error'],
    )
    linter.check([composite_bad_kwarg_mod])
    expected_messages = [
        pylint_protobuf.MESSAGES['E5903'][0] % ('Train', 'driver', 'Driver', 'bad_type'),
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert sorted(actual_messages) == sorted(expected_messages)


@pytest.fixture
def composite_kwarg_with_bad_composite_mod(composite_pb2, module_builder):
    return module_builder("""
        from {mod} import Train
        t = Train(driver=Train())
    """.format(mod=composite_pb2), 'composite_kwarg_with_bad_composite_mod')


def test_warnings_on_mismatched_composite_kwarg(composite_kwarg_with_bad_composite_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'protobuf-type-error'],
    )
    linter.check([composite_kwarg_with_bad_composite_mod])
    expected_messages = [
        pylint_protobuf.MESSAGES['E5903'][0] % ('Train', 'driver', 'Driver', 'Train()'),
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert sorted(actual_messages) == sorted(expected_messages)


@pytest.fixture
def scalar_bad_kwarg_mod(composite_pb2, module_builder):
    return module_builder("""
        from {mod} import Train
        t = Train(engine_id=Train.Driver(name='bad', id=123))
    """.format(mod=composite_pb2), 'composite_bad_kwarg_mod')


def test_warnings_of_composite_on_scalar_kwarg(scalar_bad_kwarg_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'protobuf-type-error'],
    )
    linter.check([scalar_bad_kwarg_mod])
    expected_messages = [
        pylint_protobuf.MESSAGES['E5903'][0] % ('Train', 'engine_id', 'str', 'Driver()'),
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert sorted(actual_messages) == sorted(expected_messages)


def test_issue40_no_warnings(person_pb2, module_builder, linter_factory):
    parsing_mod = module_builder("""
        from {mod} import Person
        var_to_split = 'abcdfeg:1234'
        _, var = var_to_split.split(':')
        Person(code=int(var))
    """.format(mod=person_pb2), 'parsing_mod')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'protobuf-type-error'],
    )
    linter.check([parsing_mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert not actual_messages


@pytest.mark.xfail(reason='messages should be re-worded', raises=AssertionError)
def test_issue40_with_warnings(person_pb2, module_builder, linter_factory):
    parsing_mod = module_builder("""
        from {mod} import Person
        var_to_split = 'abcdfeg:1234'
        _, var = var_to_split.split(':')
        Person(code=float(var))
    """.format(mod=person_pb2), 'parsing_mod')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'protobuf-type-error'],
    )
    linter.check([parsing_mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    expected_messages = [
        # pylint_protobuf.MESSAGES['E5903'][0] % ('Person', 'code', 'int', float),          # Current
        pylint_protobuf.MESSAGES['E5903'][0] % ('Person', 'code', 'int', 'of type float'),  # Preferred
    ]
    assert sorted(actual_messages) == sorted(expected_messages)


@pytest.fixture
def repeated_scalar_pb2(proto_builder):
    return proto_builder("""
        message RepeatedScalar {
            repeated string values = 1;
        }
    """)


@pytest.fixture
def repeated_composite_pb2(proto_builder):
    return proto_builder("""
        message RepeatedMessage {
            message Inner {
                required string value = 1;
            }
            repeated Inner values = 1;
        }
    """)


class TestRepeatedTypeError(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_issue43_no_typeerror_on_repeated_scalar_no_warn(self, repeated_scalar_pb2):
        node = self.extract_node("""
            from {} import RepeatedScalar
            RepeatedScalar(values=['abc', '123'])
        """.format(repeated_scalar_pb2))
        self.assert_no_messages(node)

    @pytest.mark.skip(reason='passes spuriously, iterators are uninferable')
    def test_issue43_no_typeerror_on_iter_no_warn(self, repeated_scalar_pb2):
        node = self.extract_node("""
            from {} import RepeatedScalar
            RepeatedScalar(values=map(str, range(3)))
        """.format(repeated_scalar_pb2))
        self.assert_no_messages(node)

    def test_issue43_typeerror_on_repeated_scalar_warns(self, repeated_scalar_pb2):
        node = self.extract_node("""
            from {} import RepeatedScalar
            RepeatedScalar(values=[123])
        """.format(repeated_scalar_pb2))
        msg = self.type_error_msg(node, 'RepeatedScalar', 'values', 'str', 123)
        self.assert_adds_messages(node, msg)

    @pytest.mark.skip(reason='iterators are uninferable')
    def test_issue43_typeerror_on_iter_repeated_scalar_warns(self, repeated_scalar_pb2):
        node = self.extract_node("""
            from {} import RepeatedScalar
            RepeatedScalar(values=iter([123]))
        """.format(repeated_scalar_pb2))
        msg = self.type_error_msg(node, 'RepeatedScalar', 'values', 'str', 123)
        self.assert_adds_messages(node, msg)

    def test_issue43_no_typeerror_on_repeated_composite_no_warn(self, repeated_composite_pb2):
        node = self.extract_node("""
            from {} import RepeatedMessage
            RepeatedMessage(values=[
                RepeatedMessage.Inner(value='abc'),
                RepeatedMessage.Inner(value='123'),
            ])
        """.format(repeated_composite_pb2))
        self.assert_no_messages(node)

    def test_issue43_typeerror_on_repeated_composite_warns(self, repeated_composite_pb2):
        node = self.extract_node("""
            from {} import RepeatedMessage
            RepeatedMessage(values=['abc'])
        """.format(repeated_composite_pb2))
        msg = self.type_error_msg(node, 'RepeatedMessage', 'values', 'Inner', 'abc')
        self.assert_adds_messages(node, msg)

    def test_issue43_typeerror_on_inner_warns(self, repeated_composite_pb2):
        node = self.extract_node("""
            from {} import RepeatedMessage
            RepeatedMessage(values=[
                RepeatedMessage.Inner(value=123),  #@
            ])
        """.format(repeated_composite_pb2))
        msg = self.type_error_msg(node, 'Inner', 'value', 'str', 123)
        self.assert_adds_messages(node, msg)


def test_issue48_bytes_field(proto_builder, module_builder, linter_factory):
    pb2 = proto_builder("""
        message Connection {
            required bytes theres_no_place_like = 1;
        }
    """)
    mod = module_builder(r"""
        from {pb2} import Connection
        Connection(theres_no_place_like=b'\x7f\x00\x00\x01')
        Connection(theres_no_place_like='127.0.0.1')
    """.format(pb2=pb2), 'issue48_example1')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'protobuf-type-error'],
    )
    linter.check([mod])
    expected_messages = [
        pylint_protobuf.MESSAGES['E5903'][0] % ('Connection', 'theres_no_place_like', 'bytes', '127.0.0.1'),
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert sorted(actual_messages) == sorted(expected_messages)


def test_issue49_star_kwargs(proto_builder, module_builder, linter_factory):
    pb2 = proto_builder("""
        message Policy {
            optional string tag = 1;
        }
    """)
    mod = module_builder(r"""
        from {pb2} import Policy
        kwargs = dict(tag='cool')
        p = Policy(**kwargs)
    """.format(pb2=pb2), 'issue49_example1')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-type-error', 'unexpected-keyword-arg'],
    )
    linter.check([mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert not actual_messages
