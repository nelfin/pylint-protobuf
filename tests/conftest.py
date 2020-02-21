import os
import textwrap
from subprocess import check_call

import astroid
import pytest
import pylint.testutils
import pylint_protobuf


@pytest.fixture(autouse=False)
def error_on_missing_modules():
    pylint_protobuf._MISSING_IMPORT_IS_ERROR = True


def _touch(fname):
    with open(fname, 'wb'):
        pass


def _prepare_package_path(path):
    parts = path.split('.')
    if len(parts) == 1:
        return
    os.makedirs(os.path.join(*parts[:-1]), exist_ok=True)
    for dirname in parts:
        os.chdir(dirname)
        _touch('__init__.py')


@pytest.fixture
def proto_builder(tmpdir, monkeypatch):
    def proto(source, name='mod'):
        proto_name = '{}.proto'.format(name)
        s = textwrap.dedent(source)
        p = tmpdir.join(proto_name)
        p.write(s)
        old = tmpdir.chdir()
        _prepare_package_path(name)
        try:
            check_call(['protoc', '--python_out=.', proto_name])
        finally:
            old.chdir()
        monkeypatch.syspath_prepend(tmpdir)
        return '{}_pb2'.format(name)
    return proto


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
