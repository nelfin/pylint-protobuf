import sys

import pylint.testutils
import pytest

import pylint_protobuf
from tests._testsupport import make_message, CheckerTestCase


@pytest.fixture
def enum_mod(proto_builder):
    return proto_builder("""
        enum Variable {
          CONTINUOUS = 0;
          DISCRETE = 1;
        }
    """, 'enum')


@pytest.fixture
def nested_enum_mod(proto_builder):
    return proto_builder("""
        enum Outer {
          UNDEFINED = 0;
          ONE = 1;
          TWO = 2;
        }

        message Message {
          enum Inner {
            UNDEFINED = 0;
            UNO = 1;
            DOS = 2;
          }
        }
    """)


@pytest.fixture
def package_nested_enum_mod(proto_builder):
    return proto_builder("""
        enum Outer {
          UNDEFINED = 0;
          ONE = 1;
          TWO = 2;
        }

        message Message {
          enum Inner {
            UNDEFINED = 0;
            UNO = 1;
            DOS = 2;
          }
        }
    """, 'nested_enum', package='package')


@pytest.fixture
def innerclass_dict_mod(proto_builder):
    return proto_builder("""
    message OuterClass {
      enum InnerEnum {
          ENUM_1 = 0;
          ENUM_2 = 1;
      }
      InnerEnum enum = 2;
    }
    """, preamble='syntax = "proto3";\npackage test;\n')


class TestEnumDefinitions(CheckerTestCase):
    CHECKER_CLASS = pylint_protobuf.ProtobufDescriptorChecker

    def test_import_enum_types_no_errors(self, enum_mod):
        self.assert_no_messages(self.extract_node("""
            from {} import Variable
            print(Variable)
        """.format(enum_mod)))

    def test_import_enum_values_no_errors(self, enum_mod):
        self.assert_no_messages(self.extract_node("""
            from {} import DISCRETE
            print(DISCRETE)
        """.format(enum_mod)))

    def test_import_enum_attributes_no_errors(self, enum_mod):
        self.assert_no_messages(self.extract_node("""
            from {} import Variable
            print(Variable.DISCRETE)
        """.format(enum_mod)))

    def test_import_enum_missing_attributes_warns(self, enum_mod):
        node = self.extract_node("""
            from {} import Variable
            print(
                Variable.should_warn  #@
            )
        """.format(enum_mod))
        msg = make_message('protobuf-undefined-attribute', node, 'Variable', 'should_warn')
        self.assert_adds_messages(node, msg)

    def test_import_enum_by_value_no_errors(self, enum_mod):
        self.assert_no_messages(self.extract_node("""
            from {} import Variable
            print(Variable.Value('DISCRETE'))
        """.format(enum_mod)))

    def test_star_import_enum_no_errors(self, enum_mod):
        self.assert_no_messages(self.extract_node("""
            from {} import *
            print(DISCRETE)
        """.format(enum_mod)))

    def test_star_import_enum_should_warn(self, enum_mod):
        node = self.extract_node("""
            from {} import *
            Variable.should_warn  #@
        """.format(enum_mod))
        msg = make_message('protobuf-undefined-attribute', node, 'Variable', 'should_warn')
        self.assert_adds_messages(node, msg)

    def test_import_enum_missing_attribute_by_value_warns(self, enum_mod):
        node = self.extract_node("""
        from {} import Variable
        Variable.Value('should_warn')  #@
        """.format(enum_mod))
        msg = pylint.testutils.MessageTest(
            'protobuf-enum-value',
            node=node, args=('should_warn', 'Variable')
        )
        self.assert_adds_messages(node, msg)

    def test_missing_value_inference_warns(self, enum_mod):
        node = self.extract_node("""
        from {} import Variable
        a = 'should_warn'
        Variable.Value(a)
        """.format(enum_mod))
        msg = pylint.testutils.MessageTest(
            'protobuf-enum-value',
            node=node, args=('should_warn', 'Variable')
        )
        self.assert_adds_messages(node, msg)

    def test_missing_value_uniferable_no_error(self, enum_mod):
        node = self.extract_node("""
        from {} import Variable
        a = get_external()
        Variable.Value(a)
        """.format(enum_mod))
        self.assert_no_messages(node)

    @pytest.mark.xfail(reason='debating whether this case should be implemented')
    def test_missing_attribute_by_value_indirect_warns(self, enum_mod):
        node = self.extract_node("""
        from {} import Variable
        func = Variable.Value
        func('should_warn')
        """.format(enum_mod))
        msg = pylint.testutils.MessageTest(
            'protobuf-enum-value',
            node=node, args=('should_warn', 'Variable')
        )
        self.assert_adds_messages(node, msg)

    def test_looks_like_enum_value_should_not_warn(self, enum_mod):
        node = self.extract_node("""
        class Variable(object):
            def Value(*args):
                pass
        Variable.Value('should_not_warn', 'even_with_extra_args')
        """.format(enum_mod))
        self.assert_no_messages(node)

    def test_missing_value_on_nested_enum_warns(self, nested_enum_mod):
        node = self.extract_node("""
        from {} import Message
        Message.Inner.Value('should_warn')
        """.format(nested_enum_mod))
        msg = pylint.testutils.MessageTest(
            'protobuf-enum-value',
            node=node, args=('should_warn', 'Inner')
        )
        self.assert_adds_messages(node, msg)

    def test_issue16_nested_enum_definition_direct_reference_no_errors(self, nested_enum_mod):
        self.assert_no_messages(self.extract_node("""
            import {mod} as sut
            {mod}.Message.Inner.UNO
        """.format(mod=nested_enum_mod)))

    def test_issue16_nested_enum_definition_no_errors(self, nested_enum_mod):
        self.assert_no_messages(self.extract_node("""
            import {mod}
            {mod}.Message.UNO
        """.format(mod=nested_enum_mod)))

    def test_fixme_issue16_nested_enum_definition_no_errors(self, nested_enum_mod):
        self.assert_no_messages(self.extract_node("""
            import {} as sut
            sut.Message.UNO
        """.format(nested_enum_mod)))

    def test_issue16_package_nested_enum_definition_warns(self, package_nested_enum_mod):
        node = self.extract_node("""
            import {mod}
            {mod}.Message.should_warn
        """.format(mod=package_nested_enum_mod))
        msg = make_message('protobuf-undefined-attribute', node, 'Message', 'should_warn')
        self.assert_adds_messages(node, msg)

    def test_issue16_nested_enum_definition_warns(self, nested_enum_mod):
        node = self.extract_node("""
            import {} as sut
            sut.Message.should_warn
        """.format(nested_enum_mod))
        msg = make_message('protobuf-undefined-attribute', node, 'Message', 'should_warn')
        self.assert_adds_messages(node, msg)

    @pytest.mark.skipif(sys.version_info < (3, 0),
                        reason='function annotations are Python 3+')
    def test_issue21_nested_enum_annassign(self, nested_enum_mod):
        self.assert_no_messages(self.extract_node("""
            import {} as sut
            def fun(type_: sut.Message.Inner):
                pass
        """.format(nested_enum_mod)))

    def test_issue21_missing_field_on_nested_enum(self, nested_enum_mod):
        node = self.extract_node("""
            import {} as sut
            sut.Message.Inner.NOPE = 123
        """.format(nested_enum_mod))
        msg = make_message('protobuf-undefined-attribute', node.targets[0], 'Inner', 'NOPE')
        self.assert_adds_messages(node, msg)

    def test_nested_enum_dict(self, innerclass_dict_mod):
        outer = self.extract_node("""
        from {} import OuterClass
        enum = OuterClass.InnerEnum.ENUM_1
        outer = OuterClass(enum=enum)
        """.format(innerclass_dict_mod))
        self.assert_no_messages(outer)

    def test_issue31_name_from_value_no_warnings(self, enum_mod):
        self.assert_no_messages(self.extract_node("""
        from {} import Variable
        print(Variable.Name(0))
        """.format(enum_mod)))

    def test_name_from_invalid_value_warns(self, enum_mod):
        node = self.extract_node("""
            from {} import Variable
            Variable.Name(123)
        """.format(enum_mod))
        msg = pylint.testutils.MessageTest(
            'protobuf-enum-value',
            node=node, args=(123, 'Variable')
        )
        self.assert_adds_messages(node, msg)

    def test_names_are_not_values(self, enum_mod):
        node = self.extract_node("""
            from {} import Variable
            Variable.Name('CONTINUOUS')
        """.format(enum_mod))
        msg = pylint.testutils.MessageTest(
            'protobuf-enum-value',
            node=node, args=('CONTINUOUS', 'Variable')
        )
        self.assert_adds_messages(node, msg)

    def test_name_from_inferable_warns(self, enum_mod):
        node = self.extract_node("""
            from {} import Variable
            b = 123
            Variable.Name(b)
        """.format(enum_mod))
        msg = pylint.testutils.MessageTest(
            'protobuf-enum-value',
            node=node, args=(123, 'Variable')
        )
        self.assert_adds_messages(node, msg)

    def test_name_from_uninferable_no_warn(self, enum_mod):
        node = self.extract_node("""
            from {} import Variable
            b = get_external_value()
            Variable.Name(b)
        """.format(enum_mod))
        self.assert_no_messages(node)

    def test_enums_do_not_have_message_fields(self, enum_mod):
        node = self.extract_node("""
            from {} import Variable
            Variable.ParseFromString("blah")
        """.format(enum_mod))
        msg = make_message('protobuf-undefined-attribute', node.func, 'Variable', 'ParseFromString')
        self.assert_adds_messages(node, msg)

    def test_messages_do_not_have_enum_fields(self, nested_enum_mod):
        node = self.extract_node("""
            from {} import Message
            Message.Value("ONE")
        """.format(nested_enum_mod))
        msg = make_message('protobuf-undefined-attribute', node.func, 'Message', 'Value')
        self.assert_adds_messages(node, msg)


def test_issue16_toplevel_enum(nested_enum_mod, module_builder, linter_factory):
    mod = module_builder("""
        import {pb2}
        {pb2}.ONE
    """.format(pb2=nested_enum_mod), 'toplevel_example1')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'no-member'],
    )
    linter.check([mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert not actual_messages


def test_issue16_missing_toplevel_enum(request, nested_enum_mod, module_builder, linter_factory):
    mod = module_builder("""
        import {pb2} as sut
        sut.UNO
    """.format(pb2=nested_enum_mod), 'toplevel_example2')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'no-member'],
    )
    linter.check([mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert len(actual_messages) == 1
    assert actual_messages[0].endswith("has no 'UNO' member")  # ignore dynamic module name


def test_issue16_package_missing_toplevel_enum(package_nested_enum_mod, module_builder, linter_factory):
    mod = module_builder("""
        import {pb2}
        {pb2}.UNO
    """.format(pb2=package_nested_enum_mod), 'toplevel_example3')
    linter = linter_factory(
        register=pylint_protobuf.register,
        disable=['all'], enable=['protobuf-undefined-attribute', 'no-member'],
    )
    linter.check([mod])
    actual_messages = [m.msg for m in linter.reporter.messages]
    assert actual_messages == ["Module 'package.nested_enum_pb2' has no 'UNO' member"]
