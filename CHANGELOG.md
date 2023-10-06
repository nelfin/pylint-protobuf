# pylint-protobuf

## [0.21.0] - 2023-10-06

- Fix for removal of IAstroidChecker in pylint 3.x (#57). Thanks @matejsp,
  @Cireo, and@jacobtylerwalls. Ref pylint-dev/pylint#9094

## [0.20.2] - 2021-07-27

- Remove runtime dependency on internal protobuf interface (#50). Thanks
  @dsandbrink for the report.
- Fix unhandled KeyError in pylint_protobuf.transform (#51). Thanks
  @hmc-cs-mdrissi for the report.

## [0.20.1] - 2021-04-15
- Fix type checking of bytes fields incorrectly labelled as strings (#48)
- Fix false-positive unexpected-keyword-arg when arguments are passed as
  star-expansion (#49). Thanks @gal-simhi for the reports (#48, #49)

## [0.20.0] - 2021-04-06
- Add support for checking arguments to .add() methods of repeated composite
  fields (similar to message constructors)
- Add support for checking validity of arguments to HasField()/ClearField()
  calls on message fields. This change raises "protobuf-undefined-attribute"
  when called correctly with an unknown field and adds two new warning message
  types: "protobuf-no-repeated-membership" for checking a non-singular field,
  and "protobuf-no-proto3-membership" for checking a non-optional,
  non-submessage field in proto3
- Add support for checking extension fields. Adds a new warning message
  "protobuf-wrong-extension-scope"
- Update protobuf-undefined-attribute behaviour to match pylint behaviour
  for ambiguous inference, this should reduce the incidence of false-positive
  messages for variables that could contain different protobuf messages (#44).
  Thanks @zoedberg for the report
- Update handling of messages with full names matching well-known types to
  match protobuf behaviour (#45). Thanks @zwn for the report
- Remove special-case handling of well-known types and update to match
  existing behaviour of other protobuf messages
- Remove "protobuf-undefined-attribute" on missing top-level module attributes
  since this is better handled by "no-member"
- Fix errors in module transform caused by field names matching Python
  reserved keywords (#46). Thanks @AudriusButkevicius for the report

## [0.19.0] - 2021-03-24
- Add support for imported message definitions via 'import "foo.proto";'
- Add support for field groups
- Fix false positive protobuf-type-error on assigning iterables to repeated
  fields in message constructors (#43). Thanks @pashatyl for the report

## [0.18.5] - 2021-03-17
- Fix false positive protobuf-type-error on numeric scalar fields supporting
  type elevation, e.g. int to float (#41)
- Fix false positive protobuf-type-error on keyword arguments supplied with
  default None values (#42)
- Fix false positive protobuf-type-error on partially inferred values assigned
  to scalar fields (#40). Thanks @zoedberg for the report

## [0.18.4] - 2021-03-14
- Fix IndexError raised in `_check_repeated_scalar` (#39). Thanks @zoedberg for
  the report

## [0.18.3] - 2021-03-04
- Fix AttributeError raised in `_check_repeated_scalar`

## [0.18.2] - 2021-03-04
- Fix AttributeError raised in `_check_init_kwargs` method (#38). Thanks
  @mcharlou for the report

## [0.18.1] - 2021-03-02

- Fix missing .append() (and other) methods on repeated composite containers
  causing false positive warnings

## [0.18.0] - 2021-02-28
- Add support for checking invalid enum values and names. This introduces a new
  warning message "protobuf-enum-value"
- Add support for type checking scalar fields. This introduces a new warning
  message "protobuf-type-error"
- Add warning for use of positional arguments on message constructors. This
  introduces a new warning message "protobuf-no-posargs"
- Add support for type checking message constructor arguments
- Add support for type checking repeated scalar fields
- Add support for checking assignment to read-only fields. This introduces a
  new warning message "protobuf-no-assignment"
- Fix missing warnings for non-nested composite types and external nested
  (e.g. External.Inner) composite types

## [0.17.0] - 2021-02-18
- Add support for scalar repeated fields
- Fix false-negative warnings on some implicitly defined protobuf message
  fields (e.g. ParseFromString is not defined on Enums, nor is Value defined on
  messages)
- Add partial support for composite repeated fields (only nested messages
  currently supported)
- Fix integration with default typecheck checker (E1101 no-member warnings) on
  protobuf well-known types (#37). Thanks @mabrowning for the PR.

## [0.16.0] - 2021-02-13
- Allow warnings on unknown keyword arguments in protobuf message constructors
  (originally suppressed to fix #30)
- Fix incorrect AST transform of deeply-nested message types (#33, #34)
- Add better support for map fields (#35)
- Change handling of inferred values around ambiguous cases where a name may be
  a protobuf message (#36)

Thanks to @mabrowning for the reports and PRs! (#33, #34, #35, #36)

## [0.15.0] - 2021-02-12
- Fix spurious warnings on use of keyword arguments in protobuf message
  constructors due to integration with pylint typecheck (#30)
- Fix some false-positives on protobuf enum types (#31)
- Fix spurious warnings on protobuf map fields due to integration with pylint
  typecheck (#32). Thanks to @mabrowning for these reports (#30, #31, #32).

## [0.14.1] - 2021-02-11
- Warning and suppression of ImportError for Python 3.9 and protobuf 3.14

## [0.14] - 2021-02-11
- Rewrite of the internals of the checker to compare usages against protobuf
  message and field descriptors. This change represents a significant departure
  in the design of the checker towards an AST transform of pb2 modules into
  plain class definitions and leveraging the astroid inference framework to
  track scope changes and name shadowing. This release should have feature
  parity with 0.13 (some message details have changed, though message codes
  remain the same), please raise an issue if behaviours have changed in
  unexpected ways.
- This release should address a number of outstanding issues around nested
  message and enum definitions (#16, #21, #24), renaming/aliasing (#23),
  and dynamic typing (#26). Thanks @diana-infinitus-ai, @fivepapertigers,
  @mishas, @NickeZ, @sagar-infinitus-ai, and @xSAVIKx for the reports.

## [0.13] - 2020-06-18
- Fix false positive warnings on nested enum definitions. Thanks
  @diana-infinitus-ai for the PR (#28)

## [0.12] - 2020-02-01
- Fix warnings on nested message definitions

## [0.11] - 2019-09-25
- Remove false-positive warnings on protobuf well-known types when parent
  module is from-imported from a package (#17). Thanks @Shesagiri for the
  report.
- Fix unhandled AssertionError on multiple aliases of a module imported from a
  package (#18)
- Fix missing warnings on aliased versions of single module imported multiple
  times

## [0.10] - 2019-09-16
- Fix behaviour around importing protobuf modules from packages (#13)
- Remove false-positive warnings on protobuf well-known types (#14)
  Thanks @mishas for the report on #13 and #14.
- Fix missing warnings on top-level enum values

## [0.9] - 2019-09-12
- Fix AttributeError raised on bad type inference of field defaults (#12).
  Thanks @TimKingNF.

## [0.8] - 2019-09-12
- Add support for enum values. Thanks @TimKingNF for the request.
- Fix warning behaviour around star imports

## [0.7] - 2019-08-21
- Add fix for AttributeError raised when checking files using imported message
  definitions (#9). Thanks @contrivable for the report

## [0.6] - 2019-08-19
- Add fix for non-scalar message fields not triggering warnings (#4)
- Add fix for nested message types not triggering warnings

## [0.5] - 2019-06-27
- Add fix for missing attributes defined by protobuf superclasses.
  Thanks @seanwarren for reminding me of this (and @TimKingNF for the
  initial fix!)

## [0.4] - 2019-06-17
- Add fix for unhandled InferenceError when slicing Call nodes (#5)
- Add fix for TypeError raised when attempting to import missing modules (#6)
- Add fix for IndexError raised when inferring a slice out of range (#7)
- Add fix for TypeError when inferring a lookup into a non-dict type

Big thanks to @jckegelman for the report and the test cases for the issues
fixed in this release. Truly, they've been very helpful.

## [0.3] - 2019-05-24
- Refactor of parsing internals to cover more edge cases
- Fixes for multiple aliases of the same name in "from .. import" clauses
- Fix issue #2: suppression of no-member for protobuf classes, thanks
  @endafarrel for the initial report and @zapstar for additional reporting

## [0.2] - 2019-03-03
- Fixes for use of annotated assignments, thanks @TimKingNF
- Fix for broken assumption about assignment RHS in `visit_call`, thanks
  @endafarrell for the report and help debugging
- Add support for type inference of classes via renaming through list-
  and mapping- getitem based interfaces

## [0.1] - 2018-07-17
- Initial release, support for detecting potential AttributeError
