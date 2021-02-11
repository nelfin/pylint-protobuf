# pylint-protobuf

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
