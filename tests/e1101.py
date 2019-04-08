import person_pb2

person = person_pb2.Person()
print(person.name)  # should not raise E1101
print(person.should_warn)  # should raise E5901
