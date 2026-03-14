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

## What Bootstrap Does Not Do

- It does not generate real purpose text.
- It does not generate interfaces text beyond `TODO`.
- It does not infer invariants.
- It does not generate belief or links.
- It does not change existing GRACE semantics.
