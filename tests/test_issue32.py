import pytest

import pylint_protobuf


@pytest.fixture
def map_mod(proto_builder):
    return proto_builder("""
        message MapTest {
            map<string, string> map_test = 1;
        }
    """)


@pytest.fixture
def warnings_mod(map_mod, module_builder):
    return module_builder("""
        from {} import MapTest
        m = MapTest(map_test={{"a":"A"}})
        print("a" in m.map_test)
        print(m.map_test["a"])
    """.format(map_mod), 'warnings_mod')


def test_membership_on_map_types(warnings_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['unsupported-membership-test',
                                 'unsubscriptable-object'],
    )
    linter.check([warnings_mod])
    # expected_messages = [
    #     pylint.checkers.typecheck.MSGS['E1135'][0] % ('m.map_test',),
    #     pylint.checkers.typecheck.MSGS['E1136'][0] % ('m.map_test',),
    # ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert not actual_messages
