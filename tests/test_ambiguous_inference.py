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
