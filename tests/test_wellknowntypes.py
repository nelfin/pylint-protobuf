import pytest
import astroid
import pylint.testutils

import pylint_protobuf

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


class TestWellKnownTypes(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    @pytest.mark.parametrize("module,wkt,fields", SAMPLE_WKTS)
    def test_import_wkt_no_warnings(self, module, wkt, fields, error_on_missing_modules):
        for field in fields:
            node = astroid.extract_node("""
            from google.protobuf.{module} import {wkt}
            t = {wkt}()
            t.{field}()
            """.format(module=module, wkt=wkt, field=field))
            with self.assertNoMessages():
                self.walk(node.root())

    @pytest.mark.parametrize("module,wkt,fields", SAMPLE_WKTS)
    def test_import_wkt_as_module_no_warnings(self, module, wkt, fields, error_on_missing_modules):
        for field in fields:
            node = astroid.extract_node("""
            from google.protobuf import {module}
            t = {module}.{wkt}()
            t.{field}()
            """.format(module=module, wkt=wkt, field=field))
            with self.assertNoMessages():
                self.walk(node.root())
