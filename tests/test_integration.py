import pytest

import pylint_protobuf

try:
    import google.protobuf
except ImportError:
    pytest.fail('behaviour of E1101 differs if protobuf is not installed')


@pytest.fixture
def person_pb2(proto_builder):
    return proto_builder("""
        message Person {
          required string name = 1;
          required int32 id = 2;
          optional string email = 3;
        }
    """, 'person')


@pytest.fixture
def e1101_mod(module_builder, person_pb2):
    return module_builder("""
        from person_pb2 import Person

        person = Person()
        print(person.name)  # should not raise E1101
        print(person.should_warn)  # should raise E5901

        class Foo: pass
        Person = Foo  # FIXME: should be renamed by class def
        person = Person()
        print(person.renamed_should_warn)  # should raise E1101
    """, 'e1101')


EXPECTED_MSGS = [
    pylint_protobuf.MESSAGES['E5901'][0] % ('should_warn', 'Person'),
    "Instance of 'Foo' has no 'renamed_should_warn' member",
]


def test_no_E1101_on_protobuf_classes(e1101_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-descriptor-checker', 'no-member'],
    )
    linter.check([e1101_mod])
    actual_msgs = [message.msg for message in linter.reporter.messages]
    assert sorted(actual_msgs) == sorted(EXPECTED_MSGS)


@pytest.fixture
def variable_pb2(proto_builder):
    preamble = """\
        syntax = "proto3";
        package variable;
    """
    return proto_builder("""\
        enum Variable {
          CONTINUOUS = 0;
          DISCRETE = 1;
        }
    """, 'variable', preamble=preamble)


@pytest.fixture
def e1101_enum(module_builder, variable_pb2):
    return module_builder("""\
        from variable_pb2 import Variable

        Variable.Name(123)  # no E1101, raise E5902
        Variable.Value('missing')  # no E1101, raise E5902
    """, 'e1101_enum')


def test_no_E1101_on_protobuf_enums(e1101_enum, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-descriptor-checker', 'no-member'],
    )
    linter.check([e1101_enum])
    actual_msgs = [message.msg for message in linter.reporter.messages]
    expected_msgs = [
        pylint_protobuf.MESSAGES['E5902'][0] % (123, 'Variable'),
        pylint_protobuf.MESSAGES['E5902'][0] % ("missing", 'Variable'),
    ]
    assert sorted(actual_msgs) == sorted(expected_msgs)
