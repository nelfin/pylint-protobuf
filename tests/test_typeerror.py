import pytest
import astroid
import pylint.testutils

import pylint_protobuf


@pytest.fixture
def person_pb2(proto_builder):
    return proto_builder("""
        message Person {
          required string name = 1;
          required int32 code = 2;
          optional string email = 3;
        }
    """)


class TestSimpleTypeError(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_inferred_assignattr_warns(self, person_pb2):
        node = astroid.extract_node("""
            from {} import Person
            p = Person()
            code = 123
            p.name = code
        """.format(person_pb2))
        message = pylint.testutils.Message(
            'protobuf-type-error',
            node=node.targets[0], args=('Person', 'name', 'str', 123)
        )
        with self.assertAddsMessages(message):
            self.walk(node.root())

    def test_uninferable_assignattr_no_warn(self, person_pb2):
        node = astroid.extract_node("""
            from {} import Person
            p = Person()
            p.name = get_user_name()
        """.format(person_pb2))
        with self.assertNoMessages():
            self.walk(node.root())


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


#@pytest.mark.xfail(reason='unimplemented check of composite ')
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
