import textwrap

import pylint.testutils
import pytest

import pylint_protobuf
from tests._testsupport import make_message, CheckerTestCase

SAMPLE_WKTS = [
    ('any_pb2', 'Any', ['Pack', 'Unpack', 'TypeName', 'Is']),
    ('timestamp_pb2',
     'Timestamp',
     ['ToJsonString',
      'FromJsonString',
      'GetCurrentTime',
      'ToNanoseconds',
      'ToMicroseconds',
      'ToMilliseconds',
      'ToSeconds',
      'FromNanoseconds',
      'FromMicroseconds',
      'FromMilliseconds',
      'FromSeconds',
      'ToDatetime',
      'FromDatetime']),
    ('duration_pb2',
     'Duration',
     ['ToJsonString',
      'FromJsonString',
      'ToNanoseconds',
      'ToMicroseconds',
      'ToMilliseconds',
      'ToSeconds',
      'FromNanoseconds',
      'FromMicroseconds',
      'FromMilliseconds',
      'FromSeconds',
      'ToTimedelta',
      'FromTimedelta']),
    ('field_mask_pb2',
     'FieldMask',
     ['ToJsonString',
      'FromJsonString',
      'IsValidForDescriptor',
      'AllFieldsFromDescriptor',
      'CanonicalFormFromMask',
      'Union',
      'Intersect',
      'MergeMessage']),
    ('struct_pb2',
     'Struct',
     ['keys',
      'values',
      'items',
      'get_or_create_list',
      'get_or_create_struct',
      'update']),
]


class TestWellKnownTypes(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    @pytest.mark.parametrize("module,wkt,fields", SAMPLE_WKTS)
    def test_import_wkt_no_warnings(self, module, wkt, fields, error_on_missing_modules):
        for field in fields:
            node = self.extract_node("""
            from google.protobuf.{module} import {wkt}
            t = {wkt}()
            t.{field}()
            """.format(module=module, wkt=wkt, field=field))
            self.assert_no_messages(node)

    @pytest.mark.parametrize("module,wkt,fields", SAMPLE_WKTS)
    def test_import_wkt_as_module_no_warnings(self, module, wkt, fields, error_on_missing_modules):
        for field in fields:
            node = self.extract_node("""
            from google.protobuf import {module}
            t = {module}.{wkt}()
            t.{field}()
            """.format(module=module, wkt=wkt, field=field))
            self.assert_no_messages(node)

    @pytest.mark.parametrize("module,wkt,_", SAMPLE_WKTS)
    def test_wkt_should_still_warn(self, module, wkt, _, error_on_missing_modules):
        node = self.extract_node("""
            from google.protobuf.{module} import {wkt}
            t = {wkt}()
            t.should_warn = 123
        """.format(module=module, wkt=wkt))
        msg = make_message('protobuf-undefined-attribute', node.targets[0], wkt, 'should_warn')
        self.assert_adds_messages(node, msg)

    @pytest.mark.parametrize("module,wkt,_", SAMPLE_WKTS)
    def test_wkt_kwargs_should_still_warn(self, module, wkt, _, error_on_missing_modules):
        node = self.extract_node("""
            from google.protobuf.{module} import {wkt}
            {wkt}(should_warn=123)
        """.format(module=module, wkt=wkt))
        msg = pylint.testutils.MessageTest('unexpected-keyword-arg', node=node, args=('should_warn', 'constructor'))
        self.assert_adds_messages(node, msg)


@pytest.fixture
def mod_template(module_builder):
    def template(module, wkt, fields):
        fstr = ['t.{}()'.format(f) for f in fields]
        mod_str = textwrap.dedent("""
            from google.protobuf.{module} import {wkt}
            t = {wkt}()
            {fstrs}
        """).format(
            module=module, wkt=wkt, fstrs='\n'.join(fstr)
        )
        return module_builder(mod_str, name=module+'_'+wkt)
    return template


@pytest.mark.parametrize("module,wkt,fields", SAMPLE_WKTS)
def test_issue37_wkt_no_E1101(module, wkt, fields, mod_template, linter_factory):
    mod = mod_template(module, wkt, fields)
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'no-member'],
    )
    linter.check([mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert not actual_messages


def test_issue45_nested_msg_acts_like_wkt(proto_builder, module_builder, linter_factory):
    pb2 = proto_builder("""
        message google {
            message protobuf {
                message Timestamp {
                  int64 seconds = 1;
                  int32 nanos = 2;
                }
            }
        }
    """, preamble='syntax = "proto3";')  # Deliberately no package
    mod = module_builder("""
        import {pb2}
        ts = {pb2}.google.protobuf.Timestamp()
        ts.GetCurrentTime()
    """.format(pb2=pb2), 'issue45_example1')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'no-member'],
    )
    linter.check([mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert not actual_messages


def test_issue45_forward_decl_of_wkt_acts_like_wkt(proto_builder, module_builder, linter_factory):
    pb2 = proto_builder("""
        message Timestamp {
          int64 seconds = 1;
          int32 nanos = 2;
        }
    """, preamble='syntax = "proto3";\npackage google.protobuf;\n')
    mod = module_builder("""
        from {pb2} import Timestamp
        ts = Timestamp()
        ts.GetCurrentTime()
    """.format(pb2=pb2), 'issue45_example2')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'no-member'],
    )
    linter.check([mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert not actual_messages
