# Language Packs

GRACE `v1.1` introduces declarative language packs as the next step after the shared Tree-sitter adapter base.

## Purpose

Language packs make adapter selection spec-driven instead of branch-driven.

They are intended to reduce the work needed to onboard new languages or refine existing ones without changing GRACE core semantics.
When the base language already exists and only specific shapes are missing, GRACE now prefers a construct pack layered on top of the language pack instead of a new adapter.

## What A Pack Defines

A language pack declares:

- language name
- supported file extensions
- support status
- adapter family
- adapter factory
- bootstrap safety

For Tree-sitter-backed languages, a pack typically wraps a `TreeSitterLanguageSpec`.

## Current Built-In Packs

- Python = reference
- TypeScript = pilot
- Go = pilot

Unknown suffixes still route through the deterministic fallback adapter.

## Why Packs Matter

Before language packs, adapter selection lived in bespoke hard-coded dispatch.

With packs:

- language metadata is centralized
- dispatch can stay generic
- wrapper adapters can reuse the same shared pack definition
- construct packs can extend the language surface without forking the base adapter
- future CLI tooling such as `adapter probe` and `adapter gaps` can report coverage directly from registry data

## Non-Goals

Language packs do not:

- change `GraceFileModel`
- change parser, validator, or patch semantics
- invent AI heuristics
- replace inline annotations as the source of truth
