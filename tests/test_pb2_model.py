import pytest

from pylint_protobuf.pb2_model import (
    Module,
    Message,
    Enum,
    EnumValue,
)


@pytest.fixture
def example_enum():
    return Enum('Example', ONE=EnumValue(1), TWO=EnumValue(2))


@pytest.fixture
def example_message():
    return Message('Outer',
        Inner=Enum('Inner', INNER_VALUE=EnumValue(0)),
        INNER_VALUE=EnumValue(0)
    )


def test_model_repr(example_enum, example_message):
    assert str(example_enum) == 'Enum(ONE=EnumValue(1), TWO=EnumValue(2))'
    assert str(example_message) == (  # noqa
        'Message('
            'INNER_VALUE=EnumValue(0), '
            'Inner=Enum(INNER_VALUE=EnumValue(0))'
        ')'
    )


def test_mapping_store(example_message):
    values = tuple(example_message)
    assert len(values) == 2
    keys = [k for k, _ in values]
    assert keys == ['INNER_VALUE', 'Inner']


def test_mapping_attributes(example_enum, example_message):
    assert 'ONE' in example_enum
    assert 'TWO' in example_enum
    assert 'Inner' in example_message
    assert 'INNER_VALUE' in example_message
    assert example_message.Inner is not None


def test_message_enum_uplift(example_enum):
    message = Message('Outer', Inner=example_enum)
    assert 'ONE' in message
    assert 'TWO' in message
    assert message.ONE == example_enum.ONE
    assert message.TWO == example_enum.TWO


def test_module_enum_uplift(example_enum):
    module = Module(Inner=example_enum)
    assert 'ONE' in module
    assert 'TWO' in module
    assert module.ONE == example_enum.ONE
    assert module.TWO == example_enum.TWO
