import pytest

import pylint_protobuf


@pytest.fixture
def heavily_nested_mod(proto_builder):
    return proto_builder("""
        message A {
            message B {
                message C {
                    message D {
                    }
                }
            }
        }
        message Test {
            required string name = 1;
        }
    """)


@pytest.fixture
def no_warnings_mod(heavily_nested_mod, module_builder):
    return module_builder("""
        from {} import Test
        test = Test(name="hello")
        print(test.name)
    """.format(heavily_nested_mod), 'no_warnings_mod')


def test_no_E1101_on_superinner_types(no_warnings_mod, linter_factory):
    """
    Incorrect templating of inner types caused a SyntaxError to be raised
    when generating the A.B.C.D classes. This broke out of the loop for the
    module, meaning a prototype class for Test was never generated and so
    the no-member warning was not suppressed.
    """
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'no-member'],
    )
    linter.check([no_warnings_mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert not actual_messages
