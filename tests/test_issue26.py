import pytest

import pylint_protobuf


@pytest.fixture
def motorcycle_mod(proto_builder):
    preamble = """
        syntax = "proto3";
        package bikes;
    """

    return proto_builder("""
        message Engine {
            int32 displacement = 2;
        }

        message Motorcycle {
            string brand = 1;
            string name = 2;
            Engine engine = 3;
        }
    """, 'motorcycles_pb2', preamble=preamble)


@pytest.fixture
def issue26_mod(motorcycle_mod, module_builder):
    return module_builder("""
        from {} import Motorcycle

        def get_motorcycle() -> Motorcycle:
            return Motorcycle()

        def something():
            m = get_motorcycle()
            engine = m.engine
            should_warn = m.should_warn
    """.format(motorcycle_mod), 'issue26_mod')


EXPECTED_MSGS = [
    pylint_protobuf.MESSAGES['E5901'][0] % ('should_warn', 'Motorcycle'),
    # "Instance of 'Motorcycle' has no 'should_warn' member",  # no E1101
]


def test_no_E1101_on_returned_values(issue26_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'no-member'],
    )
    linter.check([issue26_mod])
    actual_msgs = [message.msg for message in linter.reporter.messages]
    assert sorted(EXPECTED_MSGS) == sorted(actual_msgs)
