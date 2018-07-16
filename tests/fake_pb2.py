class _FieldDescriptor(object):
    def __init__(self, name):
        self.name = name


class _Descriptor(object):
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields

_FOO = _Descriptor(
    name='Foo',
    fields=[_FieldDescriptor(name='valid_field')],
)

_BAR = _Descriptor(
    name='Bar',
    fields=[_FieldDescriptor(name='valid_field')],
)

Foo = type('Foo', (object, ), {'DESCRIPTOR': _FOO})
Bar = type('Bar', (object, ), {'DESCRIPTOR': _BAR})
