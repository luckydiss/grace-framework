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
- Added derived `PatchPlan` support with sequential `apply-plan` execution.
- Added machine-readable `apply-plan --json` output for agent workflows.
- Moved `grace.links` target existence checks out of parser and into validator/project scope.
- Made repo `map --json` the canonical cross-file semantic graph contract for agents.
- Added `apply-plan --dry-run` and `apply-plan --preview`.
- Added stable execution-stage taxonomy for patch and apply-plan JSON results.
- Added `docs/polyglot_annotations.md` as the parallel spec track for future frontends.
- Made patch preflight and post-write validation project-aware for cross-file `grace.links`.
- Made patch linting run against the temporary project snapshot instead of file-only scope.
- Added `docs/patch_semantics.md` to document anchor-driven patch execution guarantees.
- Added derived impact analysis over `GraceMap` with direct, transitive, and module-level summaries.
- Added `grace impact <path> <anchor_id> --json` for deterministic reverse-dependency analysis.
- Added `docs/impact_layer.md` and impact coverage tests.
- Added derived anchor read layer over parsed files and `GraceMap`.
- Added `grace read <path> <anchor_id> --json` for deterministic anchor-local context loading.
- Added `docs/read_layer.md` and read-layer coverage tests.
- Added derived planning layer for deterministic impact-based patch proposals.
- Added `grace plan impact <path> <anchor_id> --json` for machine-readable patch target suggestions.
- Added `docs/planning_layer.md` and planning-layer coverage tests.
- Fixed patch path handling so `patch_block` and `apply-plan` canonicalize relative, absolute, and `Path` inputs consistently across dry-run, preview, and post-write validation.
- Added `docs/self_hosting.md` to document the canonical GRACE-on-GRACE development workflow.
- Verified the self-hosted loop over `grace/`: `map -> query -> read -> impact -> plan -> apply-plan -> validate -> lint`.
- Confirmed a real GRACE-native patch on `grace.map.build_file_map` as the first consolidated self-hosting baseline.

## v0.1.0

Initial GRACE v1 MVP baseline.

- Added code-first inline GRACE parser for Python files.
- Added validator for hard semantic and identity consistency.
- Added linter for soft policy warnings.
- Added derived GRACE map builder.
- Added semantic block patcher with rollback on parse or validation failure.
- Added minimal CLI for `parse`, `validate`, `lint`, `map`, and `patch`.
- Added examples, release metadata, and end-to-end test coverage.
