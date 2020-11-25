import os
import textwrap
from subprocess import check_call

import astroid
import pytest
import pylint.testutils
import pylint_protobuf


@pytest.fixture(autouse=False)
def error_on_missing_modules():
    oldval = pylint_protobuf._MISSING_IMPORT_IS_ERROR
    pylint_protobuf._MISSING_IMPORT_IS_ERROR = True
    yield
    pylint_protobuf._MISSING_IMPORT_IS_ERROR = oldval


def _touch(fname):
    with open(fname, 'wb'):
        pass


def _split_package_path(pkg_spec):
    """
    >>> _split_package_path('module')
    ('.', 'module')
    >>> _split_package_path('package.module')
    ('package', 'module')
    >>> _split_package_path('parent.package.module')
    ('parent/package', 'module')
    """
    parts = pkg_spec.split('.')
    if len(parts) == 1:
        return '.', parts[0]
    return os.path.join(*parts[:-1]), parts[-1]


def _parts(path):
    """
    >>> list(_parts('parent/child/'))
    ['parent', 'child']
    >>> list(_parts('parent/child'))
    ['parent']
    """
    parts = []
    head, _ = os.path.split(path)
    while head:
        head, tail = os.path.split(head)
        parts.append(tail)
    return reversed(parts)


def _prepare_package_path(path):
    if path == '.':
        return
    os.makedirs(path, exist_ok=True)
    for dirname in _parts(path):
        os.chdir(dirname)
        _touch('__init__.py')


@pytest.fixture
def proto_builder(tmpdir, monkeypatch):
    def proto(source, name='mod'):
        path, module_name = _split_package_path(name)
        proto_name = '{}.proto'.format(module_name)

        old = tmpdir.chdir()
        _prepare_package_path(path)
        p = tmpdir.join(proto_name)
        p.write(textwrap.dedent(source))

        try:
            check_call(['protoc', '--python_out={}'.format(path), proto_name])
        finally:
            old.chdir()

        monkeypatch.syspath_prepend(tmpdir)
        return '{}_pb2'.format(name)
    yield proto
    tmpdir.remove()


@pytest.fixture
def module_builder(tmpdir, monkeypatch):
    def module(source, name):
        p = tmpdir.join('{}.py'.format(name))
        p.write(textwrap.dedent(source))
        monkeypatch.syspath_prepend(tmpdir)
        return name
    return module


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
