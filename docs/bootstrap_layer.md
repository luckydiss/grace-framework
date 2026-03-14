# Bootstrap Layer

`grace bootstrap` is a deterministic scaffold layer for unannotated code.

It does not infer semantics.

It only inserts:

- `@grace.module`
- `@grace.purpose TODO`
- `@grace.interfaces TODO`
- `@grace.invariant TODO`
- `@grace.anchor`
- `@grace.complexity 1`

## Invariants

- Inline annotations remain the only source of truth.
- Bootstrap is preview-first by default.
- Bootstrap never uses LLM inference or heuristics to invent meaning.
- Apply mode parses and validates the candidate scope before committing.
- Validation failure restores original file contents.

## Workflow

Preview:

```bash
grace bootstrap src --preview
```

Apply:

```bash
grace bootstrap src --apply
grace validate src
grace lint src
```

For a single file, bootstrap derives the scaffold identity from the file scope.
If the relative path would produce only one segment, bootstrap prefixes the scope directory name so the generated `module_id` remains a valid dotted semantic path.

Example:

```bash
grace bootstrap services/pricing.py --apply --json
```

Possible scaffold result:

- module id: `services.pricing`
- anchor id: `services.pricing.run`

## Audit Surface

`bootstrap --json` returns an audit-friendly result:

- file path
- generated `module_id`
- whether a header was added
- generated anchor ids
- validated file count for apply mode

This keeps bootstrap reversible and machine-readable in the same spirit as patch/apply-plan.

## Follow-up Workflow

After bootstrap, the normal next step is:

1. `grace lint <path> --json`
2. inspect `todo_placeholder` warnings
3. use `read -> impact -> plan -> apply-plan` to replace placeholders with real semantics

## What Bootstrap Does Not Do

- It does not generate real purpose text.
- It does not generate interfaces text beyond `TODO`.
- It does not infer invariants.
- It does not generate belief or links.
- It does not change existing GRACE semantics.
