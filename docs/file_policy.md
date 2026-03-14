# File Policy Layer

GRACE `v1.2` adds a deterministic file-policy layer for repository onboarding.

## Purpose

Language packs answer:

- which adapter handles this suffix

File policy answers:

- is this file safe for bootstrap apply
- should it be preview-only
- should it be treated as unsupported
- should it be ignored as generated or repository noise

This keeps repository onboarding honest for mixed trees such as:

- Python backend code
- TypeScript frontend code
- TSX gaps
- JSON configuration
- generated build output

## File Classes

- `code`
- `docs`
- `data`
- `generated`
- `ignore`

## Policy Verdicts

- `safe_apply`
- `preview_only`
- `unsupported`
- `ignore`

## Built-In Rules

- registered language packs are `safe_apply` when `bootstrap_safe = true`
- known code-like but unsupported suffixes such as `.tsx` are `preview_only`
- data files such as `.json`, `.yaml`, `.toml`, and `.xml` are `unsupported`
- generated and repository-noise directories such as `dist/`, `build/`, `target/`, `node_modules/`, and `.git/` are `ignore`

## Repo Overrides

`[tool.grace.file_policy]` in `pyproject.toml` can override built-in rules with path globs:

```toml
[tool.grace.file_policy]
ignore = ["frontend/dist/**"]
generated = ["frontend/src/generated/**"]
preview_only = ["frontend/src/**/*.tsx"]
unsupported = ["frontend/src/i18n/**/*.json"]
```

These overrides remain deterministic.
They do not change parser semantics or source-of-truth rules.

## Bootstrap Behavior

`grace bootstrap` now only auto-applies to files with `safe_apply` policy.

Effects:

- `.py`, `.ts`, and `.go` can bootstrap normally through registered packs
- `.tsx` can be classified as code-like but not yet bootstrap-safe
- `.json` is blocked from inline bootstrap
- generated output is skipped

This prevents invalid annotation insertion into files that cannot safely host GRACE comments.

## Non-Goals

File policy does not:

- invent new annotation syntax
- infer business meaning
- change adapters or parser contracts
- make unsupported file formats magically bootstrap-safe
