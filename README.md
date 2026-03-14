# GRACE v1

GRACE stands for Graph-RAG Anchored Code Engineering.

GRACE v1 is a code-first framework/spec for LLM-oriented development where code is addressed by semantic anchors instead of line numbers. The source of truth is inline GRACE annotations in supported source files.

Canonical behavioral guarantees for the baseline live in [docs/v1_invariants.md](C:\Users\luckydiss\Documents\grace_framework\docs\v1_invariants.md).
The shell-oriented agent contract lives in [docs/agent_contract.md](C:\Users\luckydiss\Documents\grace_framework\docs\agent_contract.md).
The polyglot annotation spec track lives in [docs/polyglot_annotations.md](C:\Users\luckydiss\Documents\grace_framework\docs\polyglot_annotations.md).
The self-hosting workflow lives in [docs/self_hosting.md](C:\Users\luckydiss\Documents\grace_framework\docs\self_hosting.md).
The agent workflow playbook lives in [docs/agent_playbook.md](C:\Users\luckydiss\Documents\grace_framework\docs\agent_playbook.md).
The language integration architecture lives in [docs/language_integration.md](C:\Users\luckydiss\Documents\grace_framework\docs\language_integration.md).
The frozen adapter contract lives in [docs/language_adapter_contract.md](C:\Users\luckydiss\Documents\grace_framework\docs\language_adapter_contract.md).
The adapter authoring workflow lives in [docs/adapter_authoring.md](C:\Users\luckydiss\Documents\grace_framework\docs\adapter_authoring.md).
The near-stable CLI/protocol freeze lives in [docs/protocol_freeze.md](C:\Users\luckydiss\Documents\grace_framework\docs\protocol_freeze.md).
The current v1 readiness review lives in [docs/v1_readiness_review.md](C:\Users\luckydiss\Documents\grace_framework\docs\v1_readiness_review.md).
The v1 release-prep framing lives in [docs/v1_release_prep.md](C:\Users\luckydiss\Documents\grace_framework\docs\v1_release_prep.md).
The TypeScript pilot adapter lives in [docs/typescript_adapter.md](C:\Users\luckydiss\Documents\grace_framework\docs\typescript_adapter.md).
The Go pilot adapter lives in [docs/go_adapter.md](C:\Users\luckydiss\Documents\grace_framework\docs\go_adapter.md).
The shared data-driven adapter architecture lives in [docs/universal_language_integration.md](C:\Users\luckydiss\Documents\grace_framework\docs\universal_language_integration.md).
The declarative language-pack registry lives in [docs/language_packs.md](C:\Users\luckydiss\Documents\grace_framework\docs\language_packs.md).
The construct-pack extension layer lives in [docs/construct_packs.md](C:\Users\luckydiss\Documents\grace_framework\docs\construct_packs.md).
The deterministic file-policy layer lives in [docs/file_policy.md](C:\Users\luckydiss\Documents\grace_framework\docs\file_policy.md).
The adapter probe and gap diagnostics live in [docs/adapter_probe.md](C:\Users\luckydiss\Documents\grace_framework\docs\adapter_probe.md).
The adapter compatibility matrix lives in [docs/adapter_compatibility.md](C:\Users\luckydiss\Documents\grace_framework\docs\adapter_compatibility.md).
The release hardening gates live in [docs/release_criteria.md](C:\Users\luckydiss\Documents\grace_framework\docs\release_criteria.md).
The deterministic path-query layer lives in [docs/path_query.md](C:\Users\luckydiss\Documents\grace_framework\docs\path_query.md).
The deterministic bootstrap scaffold layer lives in [docs/bootstrap_layer.md](C:\Users\luckydiss\Documents\grace_framework\docs\bootstrap_layer.md).
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
- `language_pack`: defines declarative language-pack metadata for runtime dispatch.
- `construct_pack`: defines declarative construct-pack metadata for extending specific language shapes without forking the base adapter.
- `construct_registry`: registers built-in construct packs and returns deterministic language-scoped extension order.
- `spec_registry`: registers built-in language packs and resolves adapters by extension.
- `tree_sitter_adapter`: provides substrate helpers for non-Python pilot adapters without changing core semantics.
- `treesitter_base`: provides the shared Tree-sitter execution engine plus declarative language specs.
- `fallback_adapter`: provides deterministic text fallback for unsupported suffixes and bootstrap parsing.
- `python_adapter`: reference adapter implemented on top of the shared Tree-sitter base.
- `typescript_adapter`: pilot Tree-sitter-backed adapter for `.ts` and `.tsx` files with module annotations, function declarations, async functions, arrow functions, exported TSX function components, classes, and object literal methods.
- `go_adapter`: pilot Go adapter for `.go` files with module annotations, function declarations, receiver methods, and simple struct type declarations.
- `bootstrapper`: generates deterministic scaffold annotations for unannotated files and directories.
- `bootstrap_command`: exposes preview-first/apply bootstrap behavior through the CLI.
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

The normative adapter-freeze reference for future language integrations is [docs/language_adapter_contract.md](C:\Users\luckydiss\Documents\grace_framework\docs\language_adapter_contract.md).
Python remains the reference implementation; `.ts` and `.go` support are deliberately small pilot adapters. Dispatch now flows through a declarative language-pack registry, while unsupported suffixes route through a deterministic fallback adapter instead of hard-failing at adapter selection.
Cross-language parity fixtures and adapter conformance tests live under [examples/parity](C:\Users\luckydiss\Documents\grace_framework\examples\parity) and [tests/test_adapter_conformance.py](C:\Users\luckydiss\Documents\grace_framework\tests\test_adapter_conformance.py).
The parity root is intended for cross-language comparison; project-level validation should be run per language subdirectory because the mirrored fixtures intentionally reuse the same `module_id`.
Repository-root discovery can be constrained through `[tool.grace]` in [pyproject.toml](C:\Users\luckydiss\Documents\grace_framework\pyproject.toml) with `include` and `exclude` globs. These filters apply to repo-root commands such as `grace validate . --json`, while explicit file and subdirectory targets remain authoritative.

## Multi-Language Behavior Guarantees

GRACE currently supports:

- Python as the reference adapter
- TypeScript as a pilot adapter
- Go as a pilot adapter

All three adapters normalize into the same `GraceFileModel` contract, so validator, linter, map, query, impact, read, planner, and patch layers remain unchanged.
Adapter growth is now guided by a reusable authoring/test workflow, a declarative language-pack registry, and a shared Tree-sitter execution engine rather than one-off per-language parser loops.

## File Policy Layer

GRACE now classifies repository files before bootstrap:

- `safe_apply` for bootstrap-safe code handled by registered language packs
- `preview_only` for code-like suffixes that still need construct or language-pack work
- `unsupported` for data and docs formats without a deterministic inline comment-host policy
- `ignore` for generated or repository-noise paths

Repo roots can refine this with `[tool.grace.file_policy]` in `pyproject.toml`.
This lets large mixed repositories stay deterministic without forcing bootstrap into `.json`, `.md`, `dist/`, or `generated/` trees.

## Adapter Diagnostics

GRACE now includes deterministic adapter diagnostics for unfamiliar repositories:

- `grace adapter probe <file>` reports language-pack routing, selected adapter class, file class, and policy verdict
- `grace adapter gaps <path>` produces a deterministic backlog of `preview_only`, `unsupported`, `ignored`, or fallback-routed files
- `grace adapter eval <path>` summarizes repository coverage so an agent can decide whether bootstrap can start immediately or framework extension work is required first

This makes repository onboarding explicit: an agent can inspect coverage gaps before attempting bootstrap, add a construct pack for a missing frontend shape, and only then proceed to mutation.

## Bootstrap Layer

GRACE now includes a deterministic scaffold layer for unannotated code:

- `grace bootstrap <path>` previews scaffold changes by default
- `grace bootstrap <path> --apply` writes annotations and validates before keeping them
- scaffold placeholders always use `TODO` rather than guessed semantics
- `lint` reports scaffold placeholders through `todo_placeholder` warnings so agents can turn them into a deterministic backlog

Bootstrap is structural only. Meaningful `purpose`, `interfaces`, `invariant`, `belief`, and `links` still belong to a later read/plan/patch pass.

## Protocol Status

GRACE is now in a hardening phase where the preferred work is:

- deterministic behavior fixes
- contract clarification
- regression coverage
- self-hosted workflow stabilization

Repository-root behavior is now configuration-aware:

- `grace parse . --json`, `grace map . --json`, `grace validate . --json`, and `grace lint . --json` use the configured repo-root scope from `[tool.grace]`
- explicit subdirectory targets such as `examples/parity/python` still override repo filters for deliberate parity inspection

For agent workflows, the default root scope is stable, while curated subdirectories remain useful for language-specific verification.

## Reliability Status

GRACE now maintains explicit repo-scale reliability gates:

- deterministic repo-root `parse` and `map`
- curated-scope validation success
- deterministic self-hosted `query/read/impact/plan`
- dry-run patch/apply-plan reliability without unnecessary file touches

These gates are described in [docs/release_criteria.md](C:\Users\luckydiss\Documents\grace_framework\docs\release_criteria.md).

Current readiness review:

- the core and CLI protocol are close to a stable platform baseline
- Python is the stable reference adapter
- TypeScript and Go remain pilot adapters
- repository-root export and validation are stable for the configured repository scope

The release-prep framing for this phase is:

- stable core and CLI protocol
- Python as the reference adapter
- TypeScript and Go as pilot adapters
- a narrower `v1.0` promise than the full internal implementation surface

Final release framing for `v1.0.0` lives in [docs/v1_release_notes.md](C:\Users\luckydiss\Documents\grace_framework\docs\v1_release_notes.md).

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

Pilot TypeScript support:

```bash
grace parse examples/typescript/basic.ts --json
grace validate examples/typescript --json
```

Pilot Go support:

```bash
grace parse examples/go/basic.go --json
grace validate examples/go --json
```

Polyglot parity verification:

```bash
grace parse examples/parity --json
grace validate examples/parity/python --json
grace validate examples/parity/typescript --json
grace validate examples/parity/go --json
```

Query project anchors:

```bash
grace query anchors repo/ --json
```

Find the shortest deterministic semantic path between two anchors:

```bash
grace query path repo/ billing.pricing.choose_discount_strategy billing.audit.record_tax --json
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

Clean deterministic GRACE temp artifacts:

```bash
grace clean repo/ --dry-run --json
grace clean repo/ --json
```

Bootstrap an unannotated subtree:

```bash
grace bootstrap legacy_src/ --preview
grace bootstrap legacy_src/ --apply --json
grace lint legacy_src/ --json
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
grace query path grace grace.cli.query_path_command grace.path_query.query_path --json
grace impact grace grace.map.build_file_map --json
grace plan impact grace grace.map.build_file_map --json
grace apply-plan plan.json --dry-run --preview --json
grace apply-plan plan.json --json
grace validate grace --json
grace lint grace --json
grace clean grace --dry-run --json
```

The longer workflow notes and dogfooding lessons are documented in [docs/self_hosting.md](C:\Users\luckydiss\Documents\grace_framework\docs\self_hosting.md).
The agent workflow and baseline eval guidance are documented in [docs/agent_playbook.md](C:\Users\luckydiss\Documents\grace_framework\docs\agent_playbook.md).

For an unannotated or partially annotated repository, start with:

```bash
grace bootstrap legacy_repo/ --apply --json
grace lint legacy_repo/ --json
```

After bootstrap, the standard semantic loop resumes:

```bash
grace map legacy_repo/ --json
grace query anchors legacy_repo/ --json
grace read legacy_repo/ <anchor_id> --json
grace impact legacy_repo/ <anchor_id> --json
grace plan impact legacy_repo/ <anchor_id> --json
grace apply-plan plan.json --dry-run --json
grace apply-plan plan.json --json
grace validate legacy_repo/ --json
grace lint legacy_repo/ --json
```

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
