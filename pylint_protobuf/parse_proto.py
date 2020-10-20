EXAMPLE = """
// single line comment

/* Multi-line
comment */

syntax = "proto2";

// top-level we can have file-level options, enums, or messages

option optimize_for = SPEED;

enum AllowAlias {
    option allow_alias = true;
    UNKNOWN = 0;
    STARTED = 1;
    RUNNING = 1;
}

message Point {
  required int32 x = 1;
  required int32 y = 2;
  optional string label = 3;
}

message Line {
  required Point start = 1;
  required Point end = 2;
  optional string label = 3;
}

message Polyline {
  repeated Point point = 1;
  optional string label = 2;
}

message LessCommonFeatures {
    repeated int32 ids = 1 [packed = true];
    optional int32 pages = 2 [default = 10];
    optional string cheese = 3 [default="gouda", deprecated=true];

    reserved 10;
    reserved "foo", "bar";

    enum NestedEnum {
        RED = 0;
        BLUE = 1;
    }
    optional NestedEnum color = 11 [default = BLUE];
}

message RemoteReference {
    optional LessCommonFeatures.NestedEnum color = 1;
}

message DeprecatedGroupFeature {
    repeated group Result = 1 {
        required string url = 2;
        optional string title = 3;
        repeated string snippets = 4;
    }
}

message Extensions {
    optional string name = 1;
    extensions 100 to 199;
}

extend Extensions {
    optional int32 count = 123;
}

message NestedExtension {
    extend Extensions {
        optional int32 favouriteNumber = 150;
    }
}

message NumbersCanAlsoBeKeywords {
    extensions 1000 to max;
}

message Unions {
    oneof test {
        string name = 1;
        int32 code = 2;
        // required optional repeated qualifiers not allowed
    }
}

// TODO:
// maps
// packages
// services
// import "other.proto";
"""

# A protobuf schema consists of a sequence of message objects
# A message object has a name, braces, and a number of fields
# A field has a qualifier, a type, a name, literal "=", an ID/number, literal ";"

from dataclasses import dataclass  # Python >= 3.7
from typing import List
from enum import Enum

from parsec import (
    generate,
    many,
    none_of,
    optional,
    regex,
    sepBy,
    spaces,
    string,
)


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
class Message(object):
    name: str
    # options: List[Option]
    fields: List[Field]

FIELD = "required int32 x = 1;"

lexeme = lambda p: p << spaces()
# TODO: check with Protobuf spec

def is_any(parsers):
    if not parsers:
        return  # ?
    result = parsers[0]
    for p in parsers[1:]:
        result |= p
    return result

def is_a(enum_cls):
    return is_any([string(m) for m in enum_cls.__members__]).parsecmap(enum_cls)

identifier = lexeme(regex(r'[^\d\W]\w*'))
number = lexeme(regex('-?(0|[1-9][0-9]*)([.][0-9]+)?([eE][+-]?[0-9]+)?'))  # eugh

@lexeme
@generate
def quoted_string():
    yield string('"')
    chars = yield many(none_of('"'))
    yield string('"')
    return ''.join(chars)

literal = number | quoted_string
value = identifier | literal
equals = lexeme(string('='))
comma = lexeme(string(','))

@generate
def option():
    n = yield identifier
    yield equals
    v = yield value  # TODO: distinguish literals and identifiers?
    return Option(n, v)

@generate
def field_options():
    yield lexeme(string('['))
    options = yield sepBy(option, comma)
    yield lexeme(string(']'))
    return options

qualifier = lexeme(is_a(Qualifier))
field_type = lexeme(regex(r'[^\d\W]\w*'))  # XXX: for now
field_id = lexeme(regex('[1-9][0-9]*')).parsecmap(int)

@generate
def field():
    q = yield qualifier
    ft = yield field_type
    ident = yield identifier
    yield equals
    fi = yield field_id
    options = yield optional(field_options, default_value=[])
    yield lexeme(string(';'))
    return Field(q, ft, ident, fi, options)

MESSAGE = """message Point {
  required int32 x = 1;
  required int32 y = 2;
  optional string label = 3;
}
"""

@generate
def message():
    yield lexeme(string('message'))
    name = yield identifier
    yield lexeme(string('{'))
    fields = yield many(field)
    yield lexeme(string('}'))
    return Message(name, fields)

ENUM = """enum State {
    UNKNOWN = 0;
    STARTED = 1;
    RUNNING = 2;
}
"""

@dataclass
class EnumValue(object):
    name: str
    value: int

integer = lexeme(regex(r'\d+'))
@generate
def enum_value():
    n = yield identifier
    yield equals
    v = yield integer  # XXX: check
    yield lexeme(string(';'))
    return EnumValue(n, v)

@dataclass
class ProtobufEnum(object):
    name: str
    members: List[EnumValue]

@generate
def enum():
    yield lexeme(string('enum'))
    name = yield identifier
    yield lexeme(string('{'))
    members = yield many(enum_value)
    yield lexeme(string('}'))
    return ProtobufEnum(name, members)
