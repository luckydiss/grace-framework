# v1.0 Release Prep

This document records the final preparation scope before GRACE can be tagged as a `v1.0` stable agent development platform.

It does not introduce new runtime semantics.

Its role is to freeze the public promise around:

- stable core semantics
- stable shell-driven agent protocol
- adapter maturity messaging
- release framing and non-goals

## Release Position

GRACE is preparing for `v1.0` as a semantic protocol for deterministic, agent-driven repository editing.

The stable promise is centered on:

- inline annotations as the only source of truth
- `GraceFileModel` as the normalized semantic model
- deterministic CLI `--json` contracts
- anchor-driven patch/apply-plan execution
- self-hosted agent workflows over repository graphs

The stable promise is not:

- full multi-language coverage
- framework-specific semantics
- heuristic planning
- code generation from prompts
- IDE-specific integration

## Stable Core

The following areas are considered release-grade core behavior:

- parser routing through the adapter boundary
- validator and linter semantics
- map / query / impact / read / planner derived layers
- patch / apply-plan execution discipline
- CLI JSON contract for shell-driven agents
- self-hosted workflow over the annotated `grace/` package

## Adapter Messaging

Adapter maturity must be stated explicitly in release messaging.

Current adapter tiers:

- Python: `reference`
- TypeScript: `pilot`
- Go: `pilot`

`v1.0` should promise a stable core protocol and a stable reference adapter.

It should not imply that pilot adapters provide broad language coverage or full ecosystem support.

## Repository Scope Messaging

Repository-root behavior must remain explicit.

Stable repository-root guarantees:

- `grace parse . --json`
- `grace map . --json`
- `grace validate . --json`
- `grace lint . --json`

Curated validation scopes remain the recommended validation/lint contract:

- `.`
- `grace/`
- `examples/basic`
- `examples/typescript`
- `examples/go`
- `examples/parity/python`
- `examples/parity/typescript`
- `examples/parity/go`

The parity fixtures still intentionally mirror semantic identities across languages; they remain useful inspect-only subscopes even when excluded from the default repo-root configuration.

## Artifact Policy

Release messaging must keep the distinction clear:

- inline annotations are the only source of truth
- maps, plans, previews, and exports are derived artifacts
- temporary artifacts remain local-only unless explicitly committed as reference outputs

## v1.0 Blockers vs Non-Blockers

Current blockers:

- final release framing must clearly separate stable core from pilot adapters
- public docs must stay aligned on repository-root validation policy
- artifact policy must remain explicit in release-facing docs

Current non-blockers:

- broader TypeScript coverage
- broader Go coverage
- additional language adapters
- framework profiles
- IDE or GUI integration

## Release Checklist

Before cutting `v1.0`, confirm:

1. `python -m pytest -q` passes
2. `grace validate grace --json` passes
3. `grace lint grace --json` passes
4. `grace parse . --json` passes
5. `grace map . --json` passes
6. adapter tiers are stated consistently as `reference / pilot / pilot`
7. repo-root validation policy is documented consistently as configured-scope green behavior
8. release notes describe GRACE as a semantic editing protocol, not a code generator
