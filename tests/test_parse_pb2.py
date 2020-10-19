import pytest

from pylint_protobuf import parse_pb2
from pylint_protobuf.pb2_model import (
    Module,
    Message,
    Enum,
    EnumValue,
)
from conftest import extract_node


@pytest.fixture
def example_pb2(proto_builder):
    return proto_builder("""
        syntax = "proto2";
        package test;

        enum Outer {
          VALUE = 0;
        }

        message Message {
          enum Inner {
            INNER_VALUE = 0;
          }
        }
    """, 'example')


@pytest.mark.xfail(reason='TODO')
def test_foo(example_pb2):
    import_node = extract_node('import {0}'.format(example_pb2))
    mod_node = import_node.do_import_module(example_pb2)
    retval = parse_pb2.import_module(mod_node, example_pb2, {}, [])
    assert False
