import pytest

import pylint_protobuf


@pytest.fixture
def simple_mod(proto_builder):
    return proto_builder("""
        message Test {
            required string name = 1;
        }
    """)


@pytest.fixture
def inference_mod(simple_mod, module_builder):
    return module_builder("""
        from {} import Test
        class C:
            def __init__(self):
                self.value = None
            def parse(self):
                self.value = Test()
                self.value.ParseFromString("blahblahblah")
    """.format(simple_mod), 'inference_mod')


def test_no_E1101_on_node_inference(inference_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'no-member'],
    )
    linter.check([inference_mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert not actual_messages


@pytest.fixture
def issue44_pb2(proto_builder):
    return proto_builder("""
        message Example {
            required int32 value = 1;
        }
        message DifferentExample {
            required int32 different_value = 1;
        }
    """)


def test_issue44_no_warnings_if_any_matches(issue44_pb2, module_builder, linter_factory):
    mod = module_builder("""
        from {pb2} import Example, DifferentExample
        request = Example(value=123)
        if 1 + 1 == 2:
            request = DifferentExample()
            if 2 + 2 == 4:
                request.different_value = 456
    """.format(pb2=issue44_pb2), 'issue44_example1')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute']
    )
    linter.check([mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert not actual_messages


def test_issue44_package_no_warnings_if_any_matches(issue44_pb2, module_builder, linter_factory):
    # Previous behaviour (up to 2c09cf3) only passes in astroid-2.5 due to changes in
    # context.path (works with astroid cc3bfc5, reverted by 03d15b0)
    mod = module_builder("""
        import {pb2} as pb
        request = pb.Example(value=123)
        if 1 + 1 == 2:
            request = pb.DifferentExample()
            if 2 + 2 == 4:
                request.different_value = 456
    """.format(pb2=issue44_pb2), 'issue44_example2')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute']
    )
    linter.check([mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert not actual_messages
