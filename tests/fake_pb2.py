class _FieldDescriptor(object):
    def __init__(self, name):
        self.name = name


class _Descriptor(object):
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields


Foo = type('Foo', (object, ), {
    'DESCRIPTOR': _Descriptor(
        name='Foo',
        fields=[_FieldDescriptor(name='valid_field')],
    )})

Bar = type('Bar', (object, ), {
    'DESCRIPTOR': _Descriptor(
        name='Bar',
        fields=[_FieldDescriptor(name='valid_field')],
    )})
