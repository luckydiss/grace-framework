# TypeScript Pilot Adapter

This document describes the first non-Python GRACE language adapter.

## Scope

The TypeScript adapter is a pilot. It proves that GRACE can add a new language through the adapter boundary without changing core semantics.

The adapter uses Tree-sitter only as parsing substrate. GRACE core layers still operate on `GraceFileModel`.

## Supported Constructs

- module-level GRACE annotations
- `function` declarations
- `async function` declarations
- arrow functions assigned to variable declarators
- exported TSX function components
- exported TSX arrow components assigned to variable declarators
- `class` declarations
- class methods
- object literal methods inside top-level object declarators

## Supported Comment Hosts

- `// @grace.*`
- `/* @grace.* */`

The pilot supports single-line block comments for GRACE annotations. It does not try to infer annotations from arbitrary multi-line comment prose.

## Unsupported Constructs

- function expressions
- non-exported JSX / TSX shapes that still lack a matching declarative query
- namespaces
- overload-heavy TypeScript patterns
- framework-specific semantics

## Why This Is A Pilot

The goal is adapter-boundary proof, not full TypeScript coverage.

This pilot shows:

- adapter selection can stay outside core semantics
- Tree-sitter can compute deterministic block spans
- GRACE annotations can bind to non-Python entities
- validator, linter, map, query, impact, read, planner, and patch orchestration still consume normalized `GraceFileModel`

## Current Limitations

- `.ts` and `.tsx` now route through the same pilot via a built-in construct pack
- discovery is still annotation-driven, not project-config aware
- supported object methods are limited to method definitions inside object literals assigned to variable declarators
- unsupported TypeScript constructs fail by leaving annotations unbound instead of attempting heuristic recovery
