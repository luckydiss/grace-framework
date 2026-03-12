# GRACE v1

GRACE stands for Graph-RAG Anchored Code Engineering.

GRACE v1 is a code-first framework/spec for LLM-oriented development where code is addressed by semantic anchors instead of line numbers. The source of truth is inline GRACE annotations in Python files.

Canonical behavioral guarantees for the baseline live in [docs/v1_invariants.md](C:\Users\luckydiss\Documents\grace_framework\docs\v1_invariants.md).
The shell-oriented agent contract lives in [docs/agent_contract.md](C:\Users\luckydiss\Documents\grace_framework\docs\agent_contract.md).
The longer-term development plan lives in [docs/roadmap.md](C:\Users\luckydiss\Documents\grace_framework\docs\roadmap.md).

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
- `patcher`: replaces a semantic block by `anchor_id`, supports dry-run and preview, and rolls back on parse or validation failure.
- `plan`: loads a derived `PatchPlan` artifact and applies `replace_block` entries sequentially.
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

Parse a file for an agent:

```bash
grace parse examples/basic/pricing.py --json
```

Parse a directory for an agent:

```bash
grace parse repo/ --json
```

Validate a file:

```bash
grace validate examples/basic/pricing.py
```

Validate a file for an agent:

```bash
grace validate examples/basic/pricing.py --json
```

Validate a directory for an agent:

```bash
grace validate repo/ --json
```

Lint a file:

```bash
grace lint examples/basic/pricing.py
```

Lint a file for an agent:

```bash
grace lint examples/basic/pricing.py --json
```

Lint a directory for an agent:

```bash
grace lint repo/ --json
```

Build a JSON map:

```bash
grace map examples/basic/pricing.py --json
```

Build a project JSON map:

```bash
grace map repo/ --json
```

Patch a block by anchor:

```bash
grace patch examples/basic/pricing.py billing.pricing.apply_discount examples/basic/apply_discount.replacement.pyfrag
```

Dry-run a patch without writing to disk:

```bash
grace patch examples/basic/pricing.py billing.pricing.apply_discount examples/basic/apply_discount.replacement.pyfrag --dry-run
```

Preview a semantic block diff without writing to disk:

```bash
grace patch examples/basic/pricing.py billing.pricing.apply_discount examples/basic/apply_discount.replacement.pyfrag --preview
```

Patch a block for an agent:

```bash
grace patch examples/basic/pricing.py billing.pricing.apply_discount examples/basic/apply_discount.replacement.pyfrag --json
```

Apply a patch plan:

```bash
grace apply-plan examples/basic/apply_discount.plan.json
```

Apply a patch plan for an agent:

```bash
grace apply-plan examples/basic/apply_discount.plan.json --json
```

## Scope

GRACE v1 release scope includes:

- code-first parsing of inline annotations;
- file and project validation;
- soft lint warnings;
- derived map generation;
- semantic block patching by `anchor_id`;
- patch dry-run, preview, and structured JSON patch results;
- derived patch plans with sequential `apply-plan` execution;
- a minimal CLI.

Deferred beyond v1:

- graph analytics;
- planning/generation flows;
- multi-file transactional patch orchestration;
- sidecar-first workflows;
- line-based patch semantics.
