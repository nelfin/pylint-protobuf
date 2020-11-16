from collections import defaultdict

import astroid

from .pb2_model import (
    OldModule as Module,
    NewMessage as Message,
)


class ClassDef(object):  # XXX
    def __init__(self, fields, qualname):
        self.fields = fields
        self.qualname = qualname

    def getattr(self, key):
        return self.fields.get(key)


class TypeClass(object):
    __slots__ = ('t',)

    def __init__(self, t):
        self.t = t

    @property
    def fields(self):
        return self.t.fields

    @property
    def qualname(self):
        return self.t.qualname

    def instance(self):
        # TODO: clarify/unify this and ClassDef
        return self.t


###

class DangerModule(object):
    pass

def danger_import_module(mod):
    mod_globals, mod_locals = {}, {}
    exec(mod.as_string(), mod_globals, mod_locals)  # XXX!!!
    new_mod = DangerModule()
    for key in mod_locals:
        setattr(new_mod, key, mod_locals[key])
    return new_mod

def qualname2(cls):
    return '{}.{}'.format(cls.__module__, cls.__qualname__)

def build_descriptor_proxy(cls):
    desc = cls.DESCRIPTOR
    fields = Message(qualname2(cls), dict(desc.fields_by_name))
    return fields

def load_descriptors(pymod, names):
    fields = {}
    for clsname in names:
        fields[clsname] = build_descriptor_proxy(getattr(pymod, clsname))
    return fields

def likely_name(n):
    return not n.startswith('_') and n not in ('sys', 'DESCRIPTOR') and not n.endswith('_pb2')

def import_module(mod, module_name, scope, imported_names):
    new_scope = scope.copy()
    del scope
    # TODO: check *-import
    names = [n for n in mod.globals.keys() if likely_name(n)]
    try:
        mod2 = danger_import_module(mod)
        desc = load_descriptors(mod2, names=names)  # XXX: had hardcoded ['Person'] before
    except:
        return new_scope  # FIXME

    new_names = desc  # {}
    new_scope[module_name] = Module(module_name, new_names)

    for name, alias in imported_names:  # check aliasing for ImportFrom
        if name == '*':
            for qualname in new_names:
                new_scope[qualname] = new_names[qualname]
            # TODO: del new_scope[module_name]
            break  # it's a SyntaxError to have other clauses with a *-import
        if alias is None:
            alias = name
        new_scope[alias] = new_names[name]  # qualified_name(name)]
    return new_scope
