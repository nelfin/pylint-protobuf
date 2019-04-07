# pylint-protobuf

## [Unreleased]
- Refactor of parsing internals to cover more edge cases
- Fixes for nested scoping rules
- Fixes for multiple aliases of the same name in "from .. import" clauses
- Add support for repeated fields
- Fixes for support for inner classes in protobuf definitions

## [0.2] - 2019-03-03
- Fixes for use of annotated assignments, thanks @TimKingNF
- Fix for broken assumption about assignment RHS in `visit_call`, thanks
  @endafarrell for the report and help debugging
- Add support for type inference of classes via renaming through list-
  and mapping- getitem based interfaces

## [0.1] - 2018-07-17
- Initial release, support for detecting potential AttributeError
