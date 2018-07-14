# pylint --load-plugins=pylint_protobuf --disable=all --enable=protobuf-undefined-attribute test.py
import person_pb2 as person

foo = person.Person()
foo.name = 'fine'
foo.id = 123
foo.invalid_field = 'should warn'
