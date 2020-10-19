class EnumValue(object):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'EnumValue({0})'.format(self.value)


class _Mapping(object):
    def __init__(self, *args, **kwargs):
        for key, val in args:
            setattr(self, key, val)
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self._values = dict(args)
        self._values.update(kwargs)

    def __iter__(self):
        return iter(sorted(self._values.items()))

    def __contains__(self, key):
        return key in self._values

    def __getattr__(self, key):
        return self._values.get(key)

    def __repr__(self):
        body = ', '.join('{k}={v}'.format(k=k, v=v) for k, v in self)
        return '{0}({1})'.format(type(self).__name__, body)


class Enum(_Mapping):
    pass


class Message(_Mapping):
    def __init__(self, *args, **kwargs):
        super(Message, self).__init__(*args, **kwargs)
        enum_values = {}
        for _, value in self:
            if type(value) is Enum:
                enum_values.update(tuple(value))
        self._values.update(enum_values)


class Module(_Mapping):
    def __init__(self, *args, **kwargs):
        super(Module, self).__init__(*args, **kwargs)
        enum_values = {}
        for _, value in self:
            if type(value) is Enum:
                enum_values.update(tuple(value))
        self._values.update(enum_values)
