import pytest

import pylint_protobuf


@pytest.fixture
def person_pb2(proto_builder):
    return proto_builder("""
        message Person {
          required string name = 1;
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
