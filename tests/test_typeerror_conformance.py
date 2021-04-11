import importlib

import pytest

import pylint_protobuf


@pytest.mark.parametrize('typenames,py_valid,py_invalid', [
    (('float', 'float'), [123.0, 123, True], ['str', b'bytes']),
    (('int32', 'int'),   [123, True], [123.0, 'str', b'bytes']),
    (('bool', 'bool'),   [123.0, 123, True], ['str', b'bytes']),
    (('string', 'str'),  ['str', b'bytes'], [123.0, 123, True]),
    (('bytes', 'bytes'), [b'bytes'], [123.0, 123, True, 'str']),
])
def test_typeerror_conformance(typenames, py_valid, py_invalid, proto_builder, module_builder, linter_factory):
    pb2_field, pytype = typenames
    pb2 = proto_builder("""
        message Test {{
            required {pb2_field} value = 1;
        }}
    """.format(pb2_field=pb2_field))
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'protobuf-type-error'],
    )

    for val in py_valid:
        # Check no warnings and check no TypeErrors
        name = pb2_field + str(type(val))
        mod = module_builder("""
            from {pb2} import Test
            t = Test()
            t.value = {val!r}
        """.format(pb2=pb2, val=val), name=name)
        linter.check([mod])
        assert not linter.reporter.messages
        importlib.import_module(name)  # Should not raise

    for val in py_invalid:
        # Check both warnings and raises TypeError
        name = pb2_field + str(type(val))
        mod = module_builder("""
            from {pb2} import Test
            t = Test()
            t.value = {val!r}
        """.format(pb2=pb2, val=val), name=name)
        linter.check([mod])
        actual_messages = [m.msg for m in linter.reporter.messages]
        expected_messages = [
            pylint_protobuf.MESSAGES['E5903'][0] % ('Test', 'value', pytype, val),
        ]
        assert sorted(actual_messages) == sorted(expected_messages)
        with pytest.raises(TypeError, match='expected one of:'):
            importlib.import_module(name)
