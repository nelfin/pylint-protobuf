import keyword

import pytest

import pylint_protobuf


@pytest.fixture
def keyword_pb2(proto_builder):
    fields = [
        '    required string {} = {};'.format(kw, idx)
        for idx, kw in enumerate(keyword.kwlist, 2)
    ]
    proto = (
        "message Example {\n" +
        "    required int32 normal = 1;\n" +
        "\n".join(fields) +
        "}"
    )
    return proto_builder(proto)


def test_issue46_field_matching_keyword_should_not_error(keyword_pb2, module_builder, linter_factory):
    mod = module_builder("""
        from {pb2} import Example
        ex = Example()
        ex.HasField('while')
        setattr(ex, 'if', 'something')
        ex.normal = 123
        ex.should_warn = 123
    """.format(pb2=keyword_pb2), 'issue46_example1')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'no-member'],
    )
    linter.check([mod])
    expected_msgs = [
        pylint_protobuf.MESSAGES['E5901'][0] % ('should_warn', 'Example'),
    ]
    actual_msgs = [message.msg for message in linter.reporter.messages]
    assert sorted(actual_msgs) == sorted(expected_msgs)

# TODO: switch up these tests to use different field types, (external) message definitions etc
#  It's making a lot of work for yourself to do:
#    message while { ... }
#  but it's technically supported through via:
#    from example_pb2 import *
#    example = globals()['while']()
