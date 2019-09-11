class _FieldDescriptor(object):
    def __init__(self, name):
        self.name = name


class _Descriptor(object):
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields

_FOO = _Descriptor(
    name='Foo',
    fields=[_FieldDescriptor(name='valid_field', type=9)],
)

_BAR = _Descriptor(
    name='Bar',
    fields=[_FieldDescriptor(name='valid_field', type=9)],
)

class __FakeModule:
    pass
_reflection = __FakeModule()
_reflection.GeneratedProtocolMessageType = type

Foo = _reflection.GeneratedProtocolMessageType('Foo', (object, ), {'DESCRIPTOR': _FOO})
Bar = _reflection.GeneratedProtocolMessageType('Bar', (object, ), {'DESCRIPTOR': _BAR})
