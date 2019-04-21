from person_pb2 import Person

person = Person()
print(person.name)  # should not raise E1101
print(person.should_warn)  # should raise E5901

class Foo: pass
Person = Foo  # FIXME: should be renamed by class def
person = Person()
print(person.renamed_should_warn)  # should raise E1101
