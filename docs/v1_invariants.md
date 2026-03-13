# GRACE v1 Invariants

## Source Of Truth

GRACE v1 is code-first.

- The only source of truth is inline GRACE annotations in supported source files.
- Semantic identity is defined by inline `@grace.module` and `@grace.anchor`.
- Sidecars are not part of the v1 source-of-truth model.

## Derived Artifacts

These are derived from parsed `GraceFileModel` objects:

- GRACE map payloads
- CLI summaries and JSON output
- Validation and lint reports
- Patch results after re-parse and re-validation
- Patch plans and apply-plan execution results
- Project maps that expose cross-file semantic graph edges

Derived artifacts must not invent new `module_id` or `anchor_id`.

## Parser Guarantees

- Parses only inline GRACE annotations.
- Binds block annotations to the nearest supported semantic entity exposed by the active language adapter.
- Produces a typed `GraceFileModel` on success.
- Produces hard parse failure with structured issues on grammar or binding violations.
- Enforces required module header fields and block annotation structure.
- Enforces `complexity` as integer `1..10`.
- Enforces `belief` when `complexity >= 6`.
- Preserves `grace.links` as parsed semantic references without requiring file-local target resolution.

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
- Supports dry-run preflight without writing patched contents to disk.
- Supports semantic block preview diffs as derived output, not as a new coordinate system.
- Re-parses, validates, and lints after applying a patch.
- Uses project-aware validation and linting against a temporary snapshot of GRACE files under the target file's containing directory.
- Rolls back to original file contents if parse or validation fails.
- Allows successful patch completion with lint warnings.

## Plan Guarantees

- `PatchPlan` is a derived artifact, never source of truth.
- `apply-plan` executes entries sequentially in plan order.
- `apply-plan --dry-run` does not write plan changes to disk.
- `apply-plan --preview` exposes entry-level semantic diffs without writing to disk.
- `apply-plan` stops on the first failing entry.
- Current baseline is not transactional across already-applied earlier entries.

## CLI Guarantees

- CLI is a thin wrapper over core APIs.
- CLI does not define new source-of-truth semantics.
- Commands included in v1:
  `parse`, `validate`, `lint`, `map`, `patch`, `apply-plan`.
- `parse`, `validate`, `lint`, and `map` accept either a file path or a directory path.
- `parse`, `validate`, `lint`, and `patch` support `--json` for machine-readable agent workflows.
- `apply-plan` supports `--json` for machine-readable multi-anchor execution results.
- `patch` also supports `--dry-run` and `--preview` for agent-safe preflight and review.
- `apply-plan` also supports `--dry-run` and `--preview` for agent-safe plan execution preflight and review.
- `map --json` emits the raw derived GRACE map payload.
- Project `map --json` is the canonical cross-file semantic graph contract in the current baseline.
- Exit code behavior is stable:
  parse/validate/map/patch/apply-plan return non-zero on hard failure;
  lint returns zero on warnings and non-zero only on parse or validation failure.
