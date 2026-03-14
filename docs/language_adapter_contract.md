# Language Adapter Contract

This document freezes the minimum stable contract for GRACE language adapters before a second runtime language is added.

It is a normative reference for adapter responsibilities and adapter output.

## Purpose

The language adapter layer exists to keep GRACE Core language-agnostic.

An adapter isolates language-specific concerns:

- syntax parsing
- valid comment-host annotation discovery
- annotation-to-entity binding
- semantic block span computation
- emission of normalized GRACE file data

This separation allows GRACE Core to remain stable while future languages integrate through an explicit boundary rather than by changing core semantics.

## Core Invariants

The following rules are core invariants and must not be changed by adapters:

- Inline GRACE annotations remain the only source of truth.
- `GraceFileModel` remains the canonical normalized representation consumed by Core.
- `validator`, `linter`, `map`, `query`, `impact`, `read`, `planner`, `patcher`, and CLI contracts operate on normalized GRACE models, not on language-specific parser state.
- Adapters may interpret language syntax, but they may not redefine GRACE semantic vocabulary.
- Adapters may not introduce alternate identity systems in place of `module_id` and `anchor_id`.

## Required Adapter Responsibilities

Any adapter must be able to:

- detect whether a file is supported by that adapter
- discover GRACE annotations in valid comment-host syntax for the language
- bind module-level and block-level annotations to semantic entities deterministically
- compute semantic block spans for supported block kinds
- emit a `GraceFileModel`-compatible result for the file

In practice this means the adapter must bridge language syntax into GRACE Core without changing the GRACE model.

## Required Output Contract

An adapter must emit data compatible with the following normalized model structure.

### `GraceFileModel`

Required fields:

- `path`
- `module`
- `blocks`

### `GraceModuleMetadata`

Required fields:

- `module_id`
- `purpose`
- `interfaces`
- `invariants`

Adapter requirements:

- required text fields must be emitted as normalized strings
- `invariants` must be emitted as an ordered sequence
- adapter output must preserve deterministic ordering

### `GraceBlockMetadata`

Required fields:

- `anchor_id`
- `kind`
- `symbol_name`
- `qualified_name`
- `is_async`
- `complexity`
- `belief`
- `links`
- `line_start`
- `line_end`

Allowed block kinds:

- `function`
- `async_function`
- `class`
- `method`

Adapter requirements:

- `anchor_id` and `links` must be normalized string identities
- `line_start` and `line_end` must describe the semantic block span deterministically
- `line_start <= line_end`
- `links` must preserve deterministic ordering
- block ordering in `GraceFileModel.blocks` must be deterministic

## Failure Behavior

Adapters must preserve GRACE parse-failure behavior.

Rules:

- Unsupported file types may route through a deterministic fallback adapter, but they must not fabricate new source-of-truth semantics.
- Invalid GRACE markup in a supported file must surface as parse failure, not as silent degradation.
- Unsupported language syntax for the adapter is an adapter limitation or adapter bug, not a new GRACE semantic category.
- A valid source file with invalid GRACE markup is an invalid GRACE file, not an adapter bug.

In short:

- unsupported language/file => adapter selection or adapter support failure
- supported language + invalid GRACE markup => parse failure
- supported language + adapter cannot correctly bind valid constructs => adapter bug

## Minimum Viable Language Support

A new language does not need full-language coverage to become a valid GRACE integration.

Minimum viable support is:

- module-level annotations
- block-level annotations
- function and method support
- deterministic semantic spans
- output parity with `GraceFileModel`

Class support is desirable when the language has a class construct, but the core requirement is deterministic emission of the normalized GRACE model for supported block kinds.

## Non-Goals

At the adapter-contract level, a new adapter is not required to:

- support every construct or block kind in the language
- understand framework semantics
- infer project semantics
- perform heuristic semantic recovery
- rank likely targets
- perform AI reasoning
- change GRACE source-of-truth rules

Those concerns are outside the minimum adapter contract.

## Python Reference Status

`grace/python_adapter.py` is the current reference implementation.

It demonstrates:

- adapter-based parser entry
- preservation of existing Python GRACE behavior
- emission of normalized `GraceFileModel`

It is a reference adapter, not a privileged exception to core invariants.
