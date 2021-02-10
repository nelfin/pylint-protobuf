pylint-protobuf
===============

`pylint-protobuf` is a Pylint plugin for making Pylint aware of generated
fields from Protobuf types.

## Usage

    $ cat <<EOF >person.proto
    message Person {
      required string name = 1;
      required int32 id = 2;
      optional string email = 3;
    }
    EOF
    $ cat <<EOF >example.py
    from person_pb2 import Person
    a = Person()
    a.invalid_field = 123
    EOF
    $ protoc person.proto --python_out=.
    $ pip install pylint-protobuf
    $ pylint --load-plugins=pylint_protobuf example.py
    ************* Module example
    E:  4, 0: Field 'invalid_field' does not appear in the declared fields of
    protobuf-generated class 'Person' and will raise AttributeError on access
    (protobuf-undefined-attribute)

    ------------------------------------
    Your code has been rated at -6.67/10

## Supported Python Versions

`pylint-protobuf` supports Python 3.5 at a minimum.

## Known Issues

`pylint-protobuf` does not currently support the following concepts from the protobuf specification:
 * `oneof` fields
 * repeated fields
 * TypeError on field assignment

Externally defined message types are currently uninferable and so checking fields on message types may fail.
