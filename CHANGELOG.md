# Changelog

## Unreleased

- Added a shared data-driven `TreeSitterAdapterBase` and `TreeSitterLanguageSpec` so Python, TypeScript, and Go can reuse one AST-driven execution engine instead of duplicating parser loops per language.
- Added `FallbackTextAdapter` for deterministic bootstrap parsing of unsupported suffixes without changing GRACE source-of-truth semantics.
- Routed unknown file suffixes through the fallback adapter and documented the universal language integration architecture.
- Declared Tree-sitter Python and Go runtime dependencies explicitly in packaging metadata.
- Made `apply-plan` transactional by simulating all entries against a temporary project mirror before writing any repository file.
- Ensured multi-entry plan failures no longer leave partial on-disk writes from earlier successful entries.
- Added regression coverage for transactional `apply-plan` failure behavior and normalized result paths during dry-run execution.
- Added deterministic artifact hygiene helpers plus `grace clean` for removing GRACE temp artifacts without touching committed example plans or replacement fragments.
- Added `untracked_artifact` lint warnings for project scopes that contain derived artifacts not ignored by `.gitignore`.
- Taught CLI and patcher discovery to ignore `.grace_plan_*` directories so temporary mirrors do not pollute later discovery or graph export.
- Added `orphan_anchor` project-level lint warnings based on derived incoming semantic links and module interface exposure.
- Added `[tool.grace]` repository discovery config with `include` and `exclude` globs so repo-root parse, validate, lint, and map can use a stable default scope while explicit file or subdirectory targets still override filters.
- Made repo-root `validate . --json` and `lint . --json` green-by-default for this repository by scoping discovery through `[tool.grace]`.
- Added deterministic `grace query path <path> <source_anchor_id> <target_anchor_id> --json` over derived `anchor_links_to_anchor` edges.
- Added the derived `grace.path_query` layer plus CLI/test coverage for shortest directed semantic-path lookup.
- Extended the TypeScript pilot adapter to support arrow functions and object literal methods without changing GRACE core semantics.
- Shifted TypeScript unsupported-syntax coverage from arrow functions to function expressions and documented the new pilot boundary.

## v1.0.0 - 2026-03-13

- Added `docs/v1_release_notes.md` as the public framing for the first stable release.
- Updated `docs/agent_contract.md` to describe GRACE as a stable shell-driven agent protocol rather than an earlier development-phase contract.
- Added `docs/v1_release_prep.md` to freeze `v1.0` framing around stable core guarantees, pilot adapter messaging, and repository-root policy.
- Added documentation-driven release-prep coverage so adapter tiers and repo-root validation policy stay aligned across readiness docs.
- Added `docs/v1_readiness_review.md` to separate current release-ready surfaces from remaining `v1.0` blockers.
- Added review-level regression coverage for current green surfaces (`parse/map .`, `validate/lint grace`) and current documented blockers (`validate/lint .`).
- Added repo-scale reliability coverage for deterministic root export, curated validation scopes, and self-hosted dry-run patch/apply-plan behavior.
- Added `docs/release_criteria.md` to define hardening gates for protocol reliability before future releases.
- Added `docs/adapter_authoring.md` to define a repeatable workflow for future language adapters.
- Added reusable adapter harness helpers for parity, conformance, and eval tests.
- Documented support tiers (`reference`, `pilot`, `experimental`) for adapter maturity.
- Hardened repo discovery so only files with a real top-level `@grace.module` preamble become directory parse/map candidates.
- Restored successful `grace parse . --json` and `grace map . --json` on the repository root without weakening parser semantics.
- Added protocol freeze documentation for CLI/JSON envelopes, curated validation scopes, and derived artifact policy.
- Added regression coverage for self-hosted JSON envelope stability and repository-root parse/map behavior.
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
- Added `docs/agent_playbook.md` to define the canonical agent workflow for GRACE-native repositories.
- Added a small self-hosted eval suite over `grace/` with baseline metrics for anchor selection accuracy, patch/apply-plan success rate, rollback rate, and unnecessary file touch rate.
- Added a language adapter contract and reference Python adapter so parser entrypoints can stay language-agnostic without changing core GRACE semantics.
- Added `docs/language_integration.md` and compatibility coverage for adapter-backed parsing.
- Added `docs/language_adapter_contract.md` to freeze adapter responsibilities, output requirements, and core invariants before adding a second language runtime.
- Added a Tree-sitter-backed TypeScript pilot adapter with `.ts` adapter selection, deterministic block spans, and coverage for module annotations, functions, async functions, classes, and methods.
- Added `docs/typescript_adapter.md` and a small TypeScript pilot example.
- Added cross-language parity fixtures for Python and TypeScript plus adapter conformance coverage for the current adapter boundary.
- Added `docs/adapter_compatibility.md` and explicit unsupported-syntax policy guidance for adapters.
- Added a third pilot language adapter for Go with support for module annotations, function declarations, receiver methods, and simple struct type declarations.
- Added Go basic and parity fixtures plus adapter-specific tests and parity/conformance coverage.
- Expanded the adapter compatibility matrix to cover Go alongside Python and TypeScript.
- Expanded parity fixtures across Python, TypeScript, and Go with dedicated async-shape, service-shape, and links-shape scenarios.
- Added adapter evaluation coverage for semantic parity, deterministic parse output, conformance stability, and unsupported syntax behavior.
- Added CLI polyglot verification for parsing and validating language-specific parity subdirectories.

## v0.1.0

Initial GRACE v1 MVP baseline.

- Added code-first inline GRACE parser for Python files.
- Added validator for hard semantic and identity consistency.
- Added linter for soft policy warnings.
- Added derived GRACE map builder.
- Added semantic block patcher with rollback on parse or validation failure.
- Added minimal CLI for `parse`, `validate`, `lint`, `map`, and `patch`.
- Added examples, release metadata, and end-to-end test coverage.
