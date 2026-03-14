# Universal Language Integration

GRACE now supports a data-driven adapter architecture built around a shared Tree-sitter execution engine plus a deterministic text fallback.

## Goals

- keep inline annotations as the only source of truth
- avoid rewriting GRACE Core for every new language
- make language onboarding mostly declarative
- preserve the existing `GraceFileModel` contract

## Layers

### TreeSitterAdapterBase

`grace/treesitter_base.py` provides the shared AST-driven engine:

- loads a Tree-sitter grammar
- executes declarative block queries
- computes deterministic block spans
- reuses the existing GRACE annotation state machine
- emits `GraceFileModel`

### TreeSitterLanguageSpec

Each Tree-sitter-backed language supplies:

- file extensions
- comment-host policy
- query specs for supported block kinds
- capture names for symbol, owner, and async state
- enough metadata for deterministic bootstrap discovery through the shared base

### FallbackTextAdapter

`grace/fallback_adapter.py` is the deterministic backup for files without a dedicated runtime adapter.

It is intentionally coarse:

- text-only matching
- conservative block spans
- no framework semantics
- no AST guarantees

Its role is bootstrap safety, not rich language coverage.

## Current Direction

- Python is the reference adapter on top of the shared Tree-sitter base.
- TypeScript and Go are pilot adapters on the same shared engine.
- Unsupported or not-yet-integrated languages fall back to the text adapter rather than immediately failing adapter selection.
- Bootstrap uses this same boundary: Tree-sitter-backed adapters expose unannotated block discovery through the shared base, while unsupported suffixes fall back to deterministic text-only discovery.

## Non-goals

- changing `GraceFileModel`
- changing patch semantics
- adding AI heuristics
- replacing inline annotations with external metadata
