import pytest

import pylint_protobuf


@pytest.fixture
def package_mod(proto_builder):
    return proto_builder("""
        message Person {
            required string name = 1;
        }
    """, 'issue19_test', package='pkg')


@pytest.fixture
def issue19_mod(package_mod, module_builder):
    return module_builder("""
        import pkg.issue19_test_pb2
        p = pkg.issue19_test_pb2.Person()
        p.name = 'Test'         # Should not raise E1101
        p.should_warn = 'Test'  # Should raise E5901
    """.format(package_mod), 'issue19_mod')


def test_no_E1101_on_modules_within_packages(issue19_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'no-member'],
    )
    linter.check([issue19_mod])
    expected_msgs = [
        pylint_protobuf.MESSAGES['E5901'][0] % ('should_warn', 'Person'),
    ]
    actual_msgs = [message.msg for message in linter.reporter.messages]
    assert sorted(actual_msgs) == sorted(expected_msgs)
