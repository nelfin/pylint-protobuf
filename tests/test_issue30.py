from contextlib import contextmanager

import astroid
import pylint.checkers.typecheck
import pytest

import pylint_protobuf
from pylint_protobuf.transform import transform_module, is_some_protobuf_module


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


def test_E1123_on_unexpected_kwargs(warnings_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['unexpected-keyword-arg'],
    )
    linter.check([warnings_mod])
    expected_messages = [
        pylint.checkers.typecheck.MSGS['E1123'][0] % ('y', 'constructor')
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert sorted(actual_messages) == sorted(expected_messages)


def test_warn_typeerror_on_positional_args(kwarg_mod, module_builder, linter_factory):
    mod = module_builder("""
        from {} import Count
        c = Count(0)
    """.format(kwarg_mod), 'posargs_mod')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-no-posargs'],
    )
    linter.check([mod])
    expected_messages = [
        'Positional arguments are not allowed in message constructors and will raise TypeError'
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert actual_messages  # to make this XPASS
    assert sorted(actual_messages) == sorted(expected_messages)


def test_warn_starargs_no_posargs(kwarg_mod, module_builder, linter_factory):
    mod = module_builder("""
        from {} import Count
        args = (1, 2, 3)
        Count(*args)
    """.format(kwarg_mod), 'starargs_posargs1')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-no-posargs'],
    )
    linter.check([mod])
    expected_messages = [
        'Positional arguments are not allowed in message constructors and will raise TypeError'
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert sorted(actual_messages) == sorted(expected_messages)


@pytest.fixture
def unknown_kwarg_mod(kwarg_mod, module_builder):
    return module_builder("""
        from {mod} import Count
        c = Count(x=0, should_warn=123)
    """.format(mod=kwarg_mod), 'unknown_kwarg_mod')


@contextmanager
def no_transform():
    astroid.MANAGER.unregister_transform(astroid.Module, transform_module, is_some_protobuf_module)
    try:
        yield
    finally:
        astroid.MANAGER.register_transform(astroid.Module, transform_module, is_some_protobuf_module)


def test_without_checker_has_false_negative(unknown_kwarg_mod, linter_factory):
    with no_transform():
        linter = linter_factory(disable=['all'], enable=['unexpected-keyword-arg'])
        linter.check([unknown_kwarg_mod])
        actual_messages = [m.msg for m in linter.reporter.messages]
        assert not actual_messages


def test_with_checker_fixes_false_negative(unknown_kwarg_mod, linter_factory):
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['unexpected-keyword-arg'],
    )
    linter.check([unknown_kwarg_mod])
    expected_messages = [
        pylint.checkers.typecheck.MSGS['E1123'][0] % ('should_warn', 'constructor')
    ]
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert sorted(actual_messages) == sorted(expected_messages)
