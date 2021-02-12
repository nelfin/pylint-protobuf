import pytest
import pylint.checkers.typecheck

import pylint_protobuf


@pytest.fixture
def kwarg_mod(proto_builder):
    return proto_builder("""
        message Count {
            required int32 x = 1;
        }
    """)


@pytest.fixture
def no_warnings_mod(kwarg_mod, module_builder):
    return module_builder("""
        from {} import Count
        c = Count(x=0)
    """.format(kwarg_mod), 'no_warnings_mod')


def test_no_E1123_on_expected_kwargs(no_warnings_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['unexpected-keyword-arg'],
    )
    linter.check([no_warnings_mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert not actual_messages


@pytest.fixture
def warnings_mod(kwarg_mod, module_builder):
    return module_builder("""
        from {} import Count
        c = Count(y=0)
    """.format(kwarg_mod), 'warnings_mod')


@pytest.mark.xfail(reason='actual keyword arguments are not yet checked')
def test_E1123_on_unexpected_kwargs(warnings_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['unexpected-keyword-arg'],
    )
    linter.check([warnings_mod])
    expected_messages = [
        pylint.checkers.typecheck.MSGS['E1123'][0] % ('Count', 'y')
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert sorted(actual_messages) == sorted(expected_messages)
