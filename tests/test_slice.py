from hypothesis import given, note
import hypothesis.strategies as s
import astroid
import pytest

import pylint_protobuf


class Node:
    def __init__(self, *args):
        self.s = self.node_class()
        self.s.postinit(*args)

    def __getattr__(self, key):
        return getattr(self.s, key)

    def __repr__(self):
        return self.s.repr_tree()

class Subscript(Node):
    node_class = astroid.Subscript
class List(Node):
    node_class = astroid.List
class Dict(Node):
    node_class = astroid.Dict

consts = s.builds(astroid.Const, s.none() | s.integers() | s.text())

def subscripts(values, slice_):
    return s.builds(Subscript, values, slice_)

def lists(vals, max_size=3):
    return s.builds(List, s.lists(vals, max_size=max_size))

def dicts(keys, vals, max_size=3):
    return s.builds(Dict, s.lists(s.tuples(keys, vals), max_size=max_size))


NestedLists = s.deferred(lambda: consts | lists(NestedLists))
@given(subscripts(NestedLists, consts))
def test_slice_does_not_raise_nested_lists(subscript):
    pylint_protobuf._slice(subscript)


NestedDicts = s.deferred(lambda: consts | dicts(consts, NestedDicts))
@pytest.mark.skip(reason='appears to get caught in infinite loop')
@given(subscripts(NestedDicts, consts))
def test_slice_does_not_raise_nested_dicts(subscript):
    pylint_protobuf._slice(subscript)


@given(subscripts(consts, lists(consts)))
def test_slice_does_not_raise_bad_index(subscript):
    pylint_protobuf._slice(subscript)
