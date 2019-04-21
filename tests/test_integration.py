import os.path

import pytest

from pylint import checkers
from pylint.lint import PyLinter
from pylint.testutils import MinimalTestReporter

import pylint_protobuf

try:
    import google.protobuf
except ImportError:
    pytest.fail('behaviour of E1101 differs if protobuf is not installed')


@pytest.fixture
def linter_factory():
    def linter(register, enable, disable):
        _linter = PyLinter()
        _linter.set_reporter(MinimalTestReporter())
        checkers.initialize(_linter)
        if register:
            register(_linter)
        if disable:
            for msg in disable:
                _linter.disable(msg)
        if enable:
            for msg in enable:
                _linter.enable(msg)
        return _linter
    return linter


HERE = os.path.dirname(os.path.abspath(__file__))
EXPECTED_MSGS = [
    pylint_protobuf.MESSAGES['E5901'][0] % ('should_warn', 'person_pb2.Person'),
    "Instance of 'Foo' has no 'renamed_should_warn' member",
]


def test_no_E1101_on_protobuf_classes(linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'no-member'],
    )
    linter.check([os.path.join(HERE, 'e1101.py')])
    actual_msgs = [message.msg for message in linter.reporter.messages]
    assert sorted(EXPECTED_MSGS) == sorted(actual_msgs)
