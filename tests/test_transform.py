import astroid

from pylint_protobuf import transform


def test_issue51():
    mod_node = astroid.parse("""
        from . import fake_pb2 as fake__pb2
        DESCRIPTOR = '...'
        # etc.
    """)
    # assert not raises KeyError
    mod = transform.transform_module(mod_node)
    assert isinstance(mod, astroid.Module)

