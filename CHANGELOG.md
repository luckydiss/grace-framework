# Changelog

## Unreleased

- Removed legacy sidecar-first implementation remnants and obsolete spec/schema files.
- Added GitHub Actions CI for editable install and test execution.
- Kept the published GRACE v1 surface aligned with the code-first baseline.

## v0.1.0

Initial GRACE v1 MVP baseline.

- Added code-first inline GRACE parser for Python files.
- Added validator for hard semantic and identity consistency.
- Added linter for soft policy warnings.
- Added derived GRACE map builder.
- Added semantic block patcher with rollback on parse or validation failure.
- Added minimal CLI for `parse`, `validate`, `lint`, `map`, and `patch`.
- Added examples, release metadata, and end-to-end test coverage.
