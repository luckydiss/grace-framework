# GRACE Patch Semantics

GRACE patching is semantic and anchor-driven.

## Patch Unit

`patch_block(...)` replaces one whole semantic block:

- the block annotation group
- the bound `def`, `async def`, or `class`

It does not patch by line number as a user-facing coordinate system.

## Identity

Replacement source must preserve target identity.

The replacement block must contain the same `@grace.anchor` as the requested target.

Identity mismatch is a hard patch failure.

## Execution Discipline

GRACE patch execution remains:

patch -> parse -> validate -> lint

If parse or validation fails after a write, the file is rolled back.

Lint warnings remain non-blocking.

## Project-Aware Validation

Current GRACE baseline supports cross-file `grace.links`.

Because of that, patch preflight and post-write validation are project-aware.

`patch_block(...)` now builds a temporary project snapshot from:

- the target file's containing directory
- all GRACE-annotated Python files discovered under that directory
- the patched candidate state for the target file

That snapshot is then checked with:

- `validate_project(...)`
- `lint_project(...)`

This keeps patch execution compatible with cross-file semantic links without introducing new parser or source-of-truth semantics.
