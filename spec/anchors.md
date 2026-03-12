# GRACE Anchor Model (MVP)

This document is normative for the MVP.

## Purpose

Anchors are the primary semantic coordinates in GRACE. Any significant code block must be addressable by a stable anchor identifier. Line numbers are not part of GRACE identity.

## Invariants

1. Every GRACE module must declare exactly one `@grace.module` identifier.
2. Every significant code block must declare exactly one `@grace.anchor` identifier.
3. Anchor identifiers must be globally unique inside the indexed project.
4. Anchor identifiers must be human-readable semantic paths.
5. Anchors remain stable across local body edits if block semantics are unchanged.
6. Tooling may inspect line locations during parsing, but line numbers must not be exported as canonical semantic coordinates.

## Inline syntax for Python MVP

The Python MVP uses line comments:

```python
# @grace.module billing.pricing
# @grace.contract examples/python_service/grace/contracts/billing.pricing.contract.json

# @grace.anchor billing.pricing.apply_discount kind=function
def apply_discount(price: int, percent: int) -> int:
    ...
```

## Anchor kinds

The MVP supports:

- `module`
- `function`
- `class`
- `method`
- `block`

## Open issues

- Exact cross-language anchor syntax is not fixed.
- Refactor-stability rules beyond semantic path continuity remain open.
