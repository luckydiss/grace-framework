# Language Integration

GRACE Core remains language-agnostic.

Language-specific syntax handling is delegated to a language adapter layer.

## Core Responsibilities

The GRACE Core remains responsible for:

- semantic model
- validator
- linter
- map
- query
- impact
- read
- planner
- patch orchestration
- CLI contracts

Core layers consume `GraceFileModel` and do not need to know which language adapter produced it.

## Adapter Responsibilities

A language adapter is responsible for:

- parsing language syntax
- finding comment-hosted GRACE annotations
- binding annotations to semantic entities
- computing block spans
- emitting a `GraceFileModel`-compatible structure

## Adapter Contract

`grace/language_adapter.py` defines the base contract:

- `discover_annotations(source_text)`
- `extract_module_metadata(parsed_file)`
- `extract_blocks(parsed_file)`
- `compute_block_span(block)`
- `build_grace_file_model(file_path)`

The output must be compatible with `GraceFileModel`.

## Current Runtime Implementations

- `grace/python_adapter.py` is the reference adapter.
- `grace/typescript_adapter.py` is the first non-Python pilot adapter.

Python remains the normative reference implementation. The TypeScript adapter proves the boundary with intentionally narrow construct coverage.

## Adding A New Language

To add a new language later:

1. implement `GraceLanguageAdapter`
2. parse the target language syntax
3. discover GRACE annotations in supported comment hosts
4. bind annotations to semantic entities
5. compute block spans
6. emit `GraceFileModel`
7. register the adapter in language dispatch

Current runtime support includes Python plus a limited `.ts` pilot.

## Important Non-Goals

This layer does not:

- change inline annotations as source of truth
- change patch semantics
- change map/query/impact/read/planner contracts
- claim broad multi-language runtime support
- promise full framework-aware language coverage
