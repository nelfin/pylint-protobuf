from dataclasses import dataclass
from typing import List


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
    def __init__(self, qualname, *args, **kwargs):
        super(Enum, self).__init__(*args, **kwargs)
        self.qualname = qualname


class Message(_Mapping):
    def __init__(self, qualname, *args, **kwargs):
        super(Message, self).__init__(*args, **kwargs)
        self.qualname = qualname
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

####################################################################

class Qualifier(Enum):
    required = 'required'
    optional = 'optional'
    repeated = 'repeated'

@dataclass
class Option(object):
    name: str
    value: str  # TODO

@dataclass
class Field(object):
    qualifier: Qualifier
    field_type: str
    name: str
    field_id: int
    options: List[Option]

@dataclass
class NewMessage(object):
    qualname: str
    # options: List[Option]
    fields: List[Field]

class OldModule(object):
    __slots__ = ('original_name', 'module_globals')

    def __init__(self, original_name, module_globals):
        self.original_name = original_name
        self.module_globals = module_globals

    def getattr(self, var):
        return self.module_globals.get(var)

    @property
    def fields(self):
        return self.module_globals.keys()

    @property
    def qualname(self):
        return self.original_name

    def __repr__(self):
        return "Module({}, {})".format(self.original_name, self.module_globals)


class ProtobufEnum(object):
    def __init__(self, qualname, values):
        self.qualname = qualname
        self.values = values

    @property
    def fields(self):
        return self.values.keys()
