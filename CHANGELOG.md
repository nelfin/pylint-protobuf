# pylint-protobuf

## [Unreleased]
- Add fix for nested messages not triggering warnings (#4)

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
