# Adapter Authoring Guide

This guide describes how to add a new GRACE language adapter without changing GRACE Core semantics.

It is intentionally operational: the goal is to make adapter work routine.

## Purpose

An adapter exists to keep language-specific parsing separate from the GRACE semantic core.

The adapter layer is responsible for:

- detecting supported files
- discovering comment-hosted GRACE annotations
- binding annotations to supported semantic entities
- computing deterministic semantic block spans
- emitting `GraceFileModel`-compatible output

The core remains responsible for:

- validation
- linting
- map
- query
- impact
- read
- planner
- patch/apply-plan
- CLI contracts

## Authoring Workflow

For a new adapter, follow this sequence:

1. Create the adapter module.
2. Implement `GraceLanguageAdapter`.
3. Add adapter dispatch in `get_language_adapter_for_path(...)`.
4. Add a small language-specific example.
5. Add parity fixtures under `examples/parity/<language>/`.
6. Add adapter-specific tests.
7. Plug the adapter into the shared conformance and parity harness.
8. Update compatibility docs and release notes.

## Minimum Viable Adapter

A minimal adapter must support:

- module-level annotations
- function declarations
- methods if the language has a reliable method construct
- deterministic block spans
- `GraceFileModel` parity with the existing core

The adapter does not need to support the whole language.

## Required Responsibilities

Every adapter must:

1. Detect supported files
   Example: `.py`, `.ts`, `.go`

2. Discover annotations in valid comment-host syntax
   The adapter must follow the polyglot annotation policy already frozen in GRACE docs.

3. Bind annotations to supported semantic entities
   If binding is impossible, parsing must fail predictably.

4. Compute deterministic spans
   `line_start` / `line_end` must be stable for equivalent input.

5. Emit normalized GRACE models
   Output must be compatible with:
   - `GraceFileModel`
   - `GraceModuleMetadata`
   - `GraceBlockMetadata`

Where possible, implement the adapter as a `TreeSitterLanguageSpec` on top of the shared `TreeSitterAdapterBase` instead of writing a new parser loop from scratch.

## Unsupported Syntax Policy

Unsupported syntax must behave predictably:

- unsupported constructs without GRACE annotations must remain inert
- unsupported constructs targeted by GRACE annotations must fail predictably
- adapters must not invent heuristic bindings to “rescue” invalid input

## Support Tiers

GRACE adapters are classified by support tier.

### Reference

Requirements:

- normative baseline for behavior
- broadest test coverage
- parity coverage
- conformance coverage
- eval stability

Current example:

- Python

### Pilot

Requirements:

- honest narrow construct support
- conformance coverage
- parity fixtures
- eval coverage
- explicit unsupported syntax list

Current examples:

- TypeScript
- Go

### Experimental

Requirements:

- adapter boundary proof only
- may have incomplete parity/eval coverage
- not recommended as a contract baseline

There are currently no experimental adapters in-tree.

## Fixture Template Set

Every new adapter should add parity fixtures for:

- `basic`
- `async_shape`
- `service_shape`
- `links_shape`

The point is semantic parity, not syntax identity.

If a language has no native async construct, parity may be represented by a documented equivalent, as Go does.

## Reusable Test Expectations

The adapter should pass:

- adapter conformance tests
- cross-language parity tests
- adapter eval metrics
- CLI parity checks for parse / validate / map

These tests should reuse shared harness helpers where possible instead of inventing per-language one-offs.

## Release Checklist

Before merging a new adapter:

- adapter dispatch added
- basic example added
- parity fixtures added
- adapter-specific tests added
- shared conformance harness updated
- shared parity coverage updated
- shared eval coverage updated
- compatibility matrix updated
- language-specific adapter doc added
- changelog updated

## Non-Goals

This guide is not a license to:

- change inline annotations as source of truth
- add heuristics to core parsing
- broaden patch semantics
- add framework profiles prematurely
- claim broad language support before tests prove it
