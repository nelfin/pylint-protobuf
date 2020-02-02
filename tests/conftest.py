import textwrap
from subprocess import check_call

import astroid
import pytest
import pylint.testutils


@pytest.fixture
def proto_builder(tmpdir, monkeypatch):
    def proto(source, name='mod'):
        proto_name = '{}.proto'.format(name)
        s = textwrap.dedent(source)
        p = tmpdir.join(proto_name)
        p.write(s)
        old = tmpdir.chdir()
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
