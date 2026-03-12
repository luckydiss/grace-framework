# GRACE v1 Invariants

## Source Of Truth

GRACE v1 is code-first.

- The only source of truth is inline GRACE annotations in Python source files.
- Semantic identity is defined by inline `@grace.module` and `@grace.anchor`.
- Sidecars are not part of the v1 source-of-truth model.

## Derived Artifacts

These are derived from parsed `GraceFileModel` objects:

- GRACE map payloads
- CLI summaries and JSON output
- Validation and lint reports
- Patch results after re-parse and re-validation

Derived artifacts must not invent new `module_id` or `anchor_id`.

## Parser Guarantees

- Parses only inline GRACE annotations.
- Binds block annotations to the nearest following `def`, `async def`, `class`, or method.
- Produces a typed `GraceFileModel` on success.
- Produces hard parse failure with structured issues on grammar or binding violations.
- Enforces required module header fields and block annotation structure.
- Enforces `complexity` as integer `1..10`.
- Enforces `belief` when `complexity >= 6`.

## Validator Guarantees

- Works on parsed GRACE models and does not reparse source.
- Enforces semantic dot-path validity for `module_id` and `anchor_id`.
- Enforces anchor prefix consistency with `module_id`.
- Enforces symbol and method namespace consistency where reliably checkable.
- Enforces link targets inside file or project scope.
- Enforces duplicate `module_id` and duplicate `anchor_id` detection at project scope.
- Enforces non-empty `purpose`, `interfaces`, and `invariants`.

## Linter Guarantees

- Works on parsed GRACE models and does not reparse source.
- Emits soft policy warnings only.
- Does not replace parser or validator hard checks.
- Warns on weak placeholder text, weak belief text, oversized block span, duplicate links, long texts, and too-few invariants for complex modules.
- Lint warnings do not invalidate an otherwise valid GRACE object.

## Patcher Guarantees

- Patches by `anchor_id`, never by line number as user-facing identity.
- Replaces the whole semantic block unit:
  annotation group plus bound `def`, `async def`, or `class`.
- Preserves target block identity:
  replacement source must contain the same `@grace.anchor` as the requested target.
- Re-parses, validates, and lints after applying a patch.
- Rolls back to original file contents if parse or validation fails.
- Allows successful patch completion with lint warnings.

## CLI Guarantees

- CLI is a thin wrapper over core APIs.
- CLI does not define new source-of-truth semantics.
- Commands included in v1:
  `parse`, `validate`, `lint`, `map`, `patch`.
- Exit code behavior is stable:
  parse/validate/map/patch return non-zero on hard failure;
  lint returns zero on warnings and non-zero only on parse or validation failure.
