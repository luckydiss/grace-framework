# Go Adapter

`grace/go_adapter.py` is the third language adapter milestone for GRACE.

It exists to prove that the adapter boundary scales past Python and TypeScript without changing GRACE Core semantics.

## Scope

Supported Go constructs in this pilot:

- module-level annotations
- function declarations
- receiver methods
- simple `type ... struct` declarations as `class`-kind semantic blocks

## Comment Host Syntax

This pilot supports:

- `// @grace.*`

Block comments are intentionally out of scope for the minimal viable Go adapter.

## Supported Bindings

The Go adapter binds:

- `@grace.anchor` + `@grace.complexity` to the next supported `func`
- method annotations to the next receiver method
- optional type-level annotations to the next `type ... struct`

Receiver methods use the normalized namespace:

- `<module_id>.<TypeName>.<method_name>`

## Unsupported Constructs

This pilot does not support:

- interface declarations as semantic blocks
- embedded or anonymous field semantics
- function expressions
- framework conventions
- complex generics-specific binding cases
- build tags semantics

Unsupported constructs without GRACE annotations should remain inert.

If GRACE annotations target an unsupported construct and no supported semantic entity can bind them, parsing fails predictably.

## Why This Is A Pilot

This milestone is not full Go support.

It exists only to verify:

- adapter routing for a third language
- `GraceFileModel` parity at the semantic layer
- conformance of core layers without changing core contracts
