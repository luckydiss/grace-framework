# Protocol Freeze

GRACE v0.17 is a hardening step, not a capability expansion.

This document freezes the intended near-stable protocol surface for shell-driven agents and repository workflows.

## Purpose

The protocol freeze exists to keep GRACE usable as a deterministic agent platform while adapters, evals, and self-hosted workflows mature.

The frozen surface is:

- inline annotations as the only source of truth
- `GraceFileModel` as the canonical normalized semantic model
- stable CLI `--json` envelopes
- deterministic derived artifacts
- deterministic patch/apply-plan execution discipline

## Frozen Surface

The following layers are treated as near-stable protocol surfaces:

- parser entry contract
- validator / linter result contracts
- map / query / impact / read / planner result contracts
- patch / apply-plan execution contracts
- language adapter boundary and adapter output contract

Minor releases may harden implementation details, but they should not casually reshape these contracts.

## Discovery Contract

Directory discovery is frozen around these rules:

- only files supported by installed adapters are considered
- common non-source directories are skipped
- a file is a discovery candidate only if its top-level comment preamble contains `@grace.module`
- files that merely contain fixture strings with `@grace.*` are not discovery candidates
- ordering is deterministic by relative path

This distinction is important for repository roots that contain tests with embedded invalid GRACE examples.

## Scope Policy

Different repository scopes have different intended meanings:

- `grace/`
  canonical self-hosted development scope
- `examples/`
  runnable examples and parity fixtures
- `.`
  repository export / inspection scope

Current repo-root behavior is intentionally split:

- `parse . --json`
  expected to succeed
- `map . --json`
  expected to succeed
- `validate . --json`
  may fail because parity fixtures intentionally reuse semantic identities across languages
- `lint . --json`
  may fail at validation stage for the same reason

Agents should use curated validation scopes when parity fixtures are present.

## JSON Envelope Stability

The following commands are part of the frozen machine-readable surface:

- `parse --json`
- `validate --json`
- `lint --json`
- `map --json`
- `query ... --json`
- `impact --json`
- `read --json`
- `plan impact --json`
- `patch --json`
- `apply-plan --json`

The freeze applies to:

- top-level success/failure discrimination through `ok`
- command identity through `command`
- explicit file/project scope where applicable
- stable semantic targets such as `path`, `module_id`, and `anchor_id`
- deterministic ordering in collections

## Patch Discipline Freeze

Patch and apply-plan remain frozen around these guarantees:

- anchor-driven addressing only
- whole semantic block replacement only
- dry-run and preview are derived execution views, not new coordinate systems
- parse + validate remain blocking
- lint warnings remain non-blocking
- rollback remains mandatory on parse or validation failure

## Artifact Policy

Derived artifacts are allowed, but they must remain secondary to inline annotations.

Recommended distinction:

- committed canonical artifacts:
  stable examples or baseline repo exports used as documentation or debugging references
- local-only artifacts:
  temporary dry-run results, previews, local eval outputs, or failed export attempts

Derived artifacts must never be treated as a replacement for inline annotations.

## Release Hardening Focus

While this freeze is in effect, preferred work is:

- regression coverage
- eval coverage
- contract clarification
- deterministic behavior fixes
- self-hosting workflow stabilization

Avoid during this phase:

- new language semantics
- new patch semantics
- heuristic planning features
- UI / IDE work
- source-of-truth expansion

## Reliability Gates

Protocol freeze is reinforced by repo-scale reliability gates defined in `docs/release_criteria.md`.

Those gates intentionally distinguish:

- repository-root export behavior
- curated validation scopes
- self-hosted agent workflow stability
