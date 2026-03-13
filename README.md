# GRACE v1

GRACE stands for Graph-RAG Anchored Code Engineering.

GRACE v1 is a code-first framework/spec for LLM-oriented development where code is addressed by semantic anchors instead of line numbers. The source of truth is inline GRACE annotations in Python files.

Canonical behavioral guarantees for the baseline live in [docs/v1_invariants.md](C:\Users\luckydiss\Documents\grace_framework\docs\v1_invariants.md).
The shell-oriented agent contract lives in [docs/agent_contract.md](C:\Users\luckydiss\Documents\grace_framework\docs\agent_contract.md).
The polyglot annotation spec track lives in [docs/polyglot_annotations.md](C:\Users\luckydiss\Documents\grace_framework\docs\polyglot_annotations.md).
The self-hosting workflow lives in [docs/self_hosting.md](C:\Users\luckydiss\Documents\grace_framework\docs\self_hosting.md).
The agent workflow playbook lives in [docs/agent_playbook.md](C:\Users\luckydiss\Documents\grace_framework\docs\agent_playbook.md).
The language integration architecture lives in [docs/language_integration.md](C:\Users\luckydiss\Documents\grace_framework\docs\language_integration.md).
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
- `language_adapter`: defines the language integration contract that feeds `GraceFileModel` into the core.
- `python_adapter`: reference adapter that preserves the existing Python parsing behavior behind the language adapter layer.
- `validator`: enforces hard semantic and identity consistency on parsed GRACE objects.
- `linter`: emits soft warnings for readability, maintainability, and machine-utility quality.
- `map`: builds a derived semantic graph artifact from `GraceFileModel`, including repo-level cross-file anchor edges.
- `query`: provides deterministic read-only graph navigation over derived maps.
- `impact`: computes deterministic reverse-dependency impact sets over derived maps.
- `read`: loads anchor-local context without reading whole files at the agent layer.
- `planner`: builds deterministic patch-plan proposals from semantic graph impact without executing changes.
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

Query project anchors:

```bash
grace query anchors repo/ --json
```

Inspect reverse-dependency impact:

```bash
grace impact repo/ billing.tax.apply_tax --json
```

Read anchor-local context:

```bash
grace read repo/ billing.tax.apply_tax --json
```

Build a deterministic impact-based patch proposal:

```bash
grace plan impact repo/ billing.tax.apply_tax --json
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

Dry-run a patch plan without writing to disk:

```bash
grace apply-plan examples/basic/apply_discount.plan.json --dry-run --json
```

Preview all patch plan entries without writing to disk:

```bash
grace apply-plan examples/basic/apply_discount.plan.json --preview --json
```

## Dogfood

PowerShell:

```powershell
./scripts/dogfood.ps1 -SkipInstall
```

POSIX shell:

```bash
./scripts/dogfood.sh --skip-install
```

Both scripts run the same safe loop against the repository:

## Self-Hosted Development

The canonical GRACE dogfood scope is the annotated `grace/` package itself.

Typical self-hosting loop:

```bash
grace map grace --json
grace query anchors grace --json
grace read grace grace.map.build_file_map --json
grace impact grace grace.map.build_file_map --json
grace plan impact grace grace.map.build_file_map --json
grace apply-plan plan.json --dry-run --preview --json
grace apply-plan plan.json --json
grace validate grace --json
grace lint grace --json
```

The longer workflow notes and dogfooding lessons are documented in [docs/self_hosting.md](C:\Users\luckydiss\Documents\grace_framework\docs\self_hosting.md).
The agent workflow and baseline eval guidance are documented in [docs/agent_playbook.md](C:\Users\luckydiss\Documents\grace_framework\docs\agent_playbook.md).

- `pytest`
- `parse`
- `validate`
- `lint`
- `map`
- `patch --dry-run`
- `apply-plan --dry-run`

To target your own annotated subtree instead of the built-in example, change `Scope`, `File`, `Anchor`, `Replacement`, and `Plan`.

## Scope

GRACE v1 release scope includes:

- code-first parsing of inline annotations;
- file and project validation;
- soft lint warnings;
- derived map generation;
- repo-level cross-file semantic graph edges in project maps;
- read-only graph queries and reverse-dependency impact analysis;
- anchor-local context loading through the read layer;
- deterministic patch-plan proposal generation from impact data;
- semantic block patching by `anchor_id`;
- patch dry-run, preview, and structured JSON patch results;
- derived patch plans with sequential `apply-plan` execution, dry-run, preview, and stable failure taxonomy;
- a minimal CLI.

Deferred beyond v1:

- graph analytics;
- planning/generation flows;
- multi-file transactional patch orchestration;
- sidecar-first workflows;
- line-based patch semantics.
