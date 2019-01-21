"""
An example module with no warnings otherwise
"""

try:
    from person_pb2 import Person
except ImportError:
    with open('person.proto', 'wb') as f:
        f.write("""
message Person {
  required string name = 1;
  required int32 id = 2;
  optional string email = 3;
}""")
    import subprocess
    subprocess.check_call(['protoc', 'person.proto', '--python_out=.'])
    from person_pb2 import Person
    from google.protobuf import message as _message


def main():
    """A pedantic docstring."""
    person: _message = Person()
    person.should_warn = 123
