import pytest

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
