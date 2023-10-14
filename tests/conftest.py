import os
import sys
import textwrap
from subprocess import check_call

import google.protobuf.descriptor_pool
import google.protobuf.pyext._message
import pytest
from pylint import checkers
from pylint.lint import PyLinter
from pylint.testutils import MinimalTestReporter

import pylint_protobuf


@pytest.fixture(autouse=True)
def error_on_missing_modules(request):
    oldval = pylint_protobuf._MISSING_IMPORT_IS_ERROR
    pylint_protobuf._MISSING_IMPORT_IS_ERROR = 'no_missing_modules_check' not in request.keywords
    yield
    pylint_protobuf._MISSING_IMPORT_IS_ERROR = oldval


def _safe_name(request):
    return request.node.name.translate({ord(c): ord('_') for c in '/.:[]-'})


@pytest.fixture
def proto_builder(tmpdir, monkeypatch, request):
    def proto(source, name=None, preamble=None, package=None):
        if name is None:
            name = _safe_name(request)
        if preamble is None:
            preamble = 'syntax = "proto2";\npackage {};\n'.format(name)
        if package is None:
            package = ''
        assert '.' not in name, "FIXME: use package arg"
        path = package.split('.')

        old = tmpdir.chdir()

        d = tmpdir.join(*path)
        # str(d) for Python 3.5 compatibility
        # exist_ok to catch the package='' case
        os.makedirs(str(d), exist_ok=True)

        proto_name = '{}.proto'.format(name)
        p = d.join(proto_name)
        p.write(preamble + textwrap.dedent(source))

        try:
            p.dirpath().chdir()
            check_call(['protoc', '--python_out=.', proto_name])
        finally:
            old.chdir()

        monkeypatch.syspath_prepend(tmpdir)

        pb2_name = '{}_pb2'.format(name)
        if package:
            pb2_name = '{}.{}'.format(package, pb2_name)
        return pb2_name
    monkeypatch.setattr(sys, 'modules', sys.modules.copy())
    # XXX: protobuf descriptor pool is a singleton breaking unit test isolation
    monkeypatch.setattr(
        google.protobuf.pyext._message, 'default_pool',
        google.protobuf.descriptor_pool.DescriptorPool()
    )
    yield proto


@pytest.fixture
def module_builder(tmpdir, monkeypatch):
    def module(source, name):
        p = tmpdir.join('{}.py'.format(name))
        p.write(textwrap.dedent(source))
        monkeypatch.syspath_prepend(tmpdir)
        return name
    monkeypatch.setattr(sys, 'modules', sys.modules.copy())
    yield module


@pytest.fixture
def linter_factory():
    def linter(register=None, enable=None, disable=None):
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
