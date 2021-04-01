import os
import sys
import textwrap
from subprocess import check_call

import astroid
import pytest
import pylint.testutils
from pylint import checkers
from pylint.lint import PyLinter
from pylint.testutils import MinimalTestReporter

import pylint_protobuf
import google.protobuf.pyext._message, google.protobuf.descriptor_pool

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


def extract_node(source):
    return astroid.extract_node(source)


def make_message(node, target, attr, message='protobuf-undefined-attribute'):
    return pylint.testutils.Message(message, node=node, args=(attr, target))


class CheckerTestCase(pylint.testutils.CheckerTestCase):
    def assert_no_messages(self, node):
        with self.assertNoMessages():
            self.walk(node.root())

    def assert_adds_messages(self, node, *msg):
        with self.assertAddsMessages(*msg):
            self.walk(node.root())

    def extract_node(self, s):
        return astroid.extract_node(s)

    def make_message(self, msg_id, node, args):
        return pylint.testutils.Message(msg_id, node=node, args=args)

    undefined_attribute_msg = lambda self, node, *args: self.make_message('protobuf-undefined-attribute', node, args)
    enum_value_msg = lambda self, node, *args: self.make_message('protobuf-enum-value', node, args)
    type_error_msg = lambda self, node, *args: self.make_message('protobuf-type-error', node, args)
    no_posargs_msg = lambda self, node: self.make_message('protobuf-no-posargs', node, args=None)
    no_assignment_msg = lambda self, node, *args: self.make_message('protobuf-no-assignment', node, args)
    no_repeated_membership_msg = lambda self, node: self.make_message('protobuf-no-repeated-membership', node, args=None)
    no_proto3_membership_msg = lambda self, node, *args: self.make_message('protobuf-no-proto3-membership', node, args)
    wrong_extension_scope_msg = lambda self, node, *args: self.make_message('protobuf-wrong-extension-scope', node, args)


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
