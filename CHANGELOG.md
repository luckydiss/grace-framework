# Changelog

## Unreleased

- Removed legacy sidecar-first implementation remnants and obsolete spec/schema files.
- Added GitHub Actions CI for editable install and test execution.
- Kept the published GRACE v1 surface aligned with the code-first baseline.
- Added machine-readable `--json` output for `parse`, `validate`, `lint`, and `patch`.
- Added `docs/agent_contract.md` for shell-driven coding agents.
- Added repo-level `parse`, `validate`, `lint`, and `map` for directory inputs.
- Added deterministic directory discovery policy for GRACE-annotated Python files.
- Added patch `--dry-run` and `--preview` for agent-safe semantic block preflight.
- Added structured patch results with identity preservation, parse/validate step status, preview, hashes, and rollback state.

## v0.1.0

Initial GRACE v1 MVP baseline.

- Added code-first inline GRACE parser for Python files.
- Added validator for hard semantic and identity consistency.
- Added linter for soft policy warnings.
- Added derived GRACE map builder.
- Added semantic block patcher with rollback on parse or validation failure.
- Added minimal CLI for `parse`, `validate`, `lint`, `map`, and `patch`.
- Added examples, release metadata, and end-to-end test coverage.
