# GRACE v1

GRACE stands for Graph-RAG Anchored Code Engineering.

GRACE v1 is a code-first framework/spec for LLM-oriented development where code is addressed by semantic anchors instead of line numbers. The source of truth is inline GRACE annotations in Python files.

## Source Of Truth

GRACE v1 is inline-first:

- `@grace.module`
- `@grace.purpose`
- `@grace.interfaces`
- `@grace.invariant`
- `@grace.anchor`
- `@grace.complexity`
- `@grace.belief`
- `@grace.links`

Derived artifacts such as maps are built from the parsed model. Sidecars are not part of the v1 source-of-truth model.

## Layers

- `parser`: parses inline annotations and binds them to `def`, `async def`, `class`, and methods.
- `validator`: enforces hard semantic and identity consistency on parsed GRACE objects.
- `linter`: emits soft warnings for readability, maintainability, and machine-utility quality.
- `map`: builds a derived navigation artifact from `GraceFileModel`.
- `patcher`: replaces a semantic block by `anchor_id` with rollback on parse or validation failure.
- `cli`: thin command wrapper over the existing APIs.

## Install

```bash
pip install -e .
```

This installs the `grace` console command from `grace.cli:main`.

## Minimal Example

Example file: [examples/basic/pricing.py](C:\Users\luckydiss\Documents\grace_framework\examples\basic\pricing.py)

```python
# @grace.module billing.pricing
# @grace.purpose Determine discount strategy and apply discounts.
# @grace.interfaces apply_discount(price:int, percent:int) -> int
# @grace.invariant Discount percent must never be negative.
# @grace.invariant Anchor ids remain stable unless pricing semantics change.

# @grace.anchor billing.pricing.apply_discount
# @grace.complexity 2
def apply_discount(price: int, percent: int) -> int:
    return price - ((price * percent) // 100)
```

## CLI

Parse a file:

```bash
grace parse examples/basic/pricing.py
```

Validate a file:

```bash
grace validate examples/basic/pricing.py
```

Lint a file:

```bash
grace lint examples/basic/pricing.py
```

Build a JSON map:

```bash
grace map examples/basic/pricing.py --json
```

Patch a block by anchor:

```bash
grace patch examples/basic/pricing.py billing.pricing.apply_discount examples/basic/apply_discount.replacement.pyfrag
```

## Scope

GRACE v1 release scope includes:

- code-first parsing of inline annotations;
- file and project validation;
- soft lint warnings;
- derived map generation;
- semantic block patching by `anchor_id`;
- a minimal CLI.

Deferred beyond v1:

- graph analytics;
- planning/generation flows;
- multi-file patch orchestration;
- sidecar-first workflows;
- line-based patch semantics.
