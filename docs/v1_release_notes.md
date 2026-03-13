# v1.0.0 Release Notes

GRACE `v1.0.0` is the first stable release of the core semantic editing protocol for shell-driven coding agents.

This release establishes GRACE as:

- a code-first semantic editing system
- a deterministic patch/apply-plan execution protocol
- a machine-readable repository workflow for agents

It is not a broad claim of universal language support or framework-specific intelligence.

## Stable In This Release

The `v1.0.0` stable promise covers:

- inline annotations as the only source of truth
- `GraceFileModel` as the normalized semantic representation
- parser / validator / linter / map / query / impact / read / planner / patch / apply-plan core pipeline
- deterministic CLI `--json` contracts for shell-driven agents
- self-hosted workflow over the annotated `grace/` package
- Python as the reference adapter

## Included Pilot Adapters

This release also includes:

- TypeScript adapter as `pilot`
- Go adapter as `pilot`

These adapters are intentionally narrow and should be understood as proof that the core architecture scales across languages without changing core semantics.

They are not a promise of broad TypeScript or Go ecosystem coverage.

## Repository Scope Policy

Stable repository-root export behavior:

- `grace parse . --json`
- `grace map . --json`

Recommended curated validation scopes:

- `grace/`
- `examples/basic`
- `examples/typescript`
- `examples/go`
- `examples/parity/python`
- `examples/parity/typescript`
- `examples/parity/go`

Repository-root `validate . --json` and `lint . --json` are intentionally not release gates because parity fixtures reuse semantic identities across languages.

## What GRACE v1.0.0 Is Not

GRACE `v1.0.0` is not:

- a prompt-to-project code generator
- an IDE plugin
- a language server
- a framework profile system
- a full multi-language platform
- a heuristic planning engine

## Recommended Positioning

Recommended short description:

GRACE is a semantic protocol for deterministic, agent-driven repository editing.
