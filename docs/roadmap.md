# GRACE Roadmap

This document records the current canonical development plan for GRACE after the v0.2 baseline.

## Core Position

GRACE must not evolve into:

- another code generation tool
- another IDE plugin
- another generic parser framework

Its primary value is:

- stable semantic coordinates
- code-first source of truth
- deterministic patching
- machine-readable contract for agents

The architectural goal is:

GRACE is a semantic protocol for deterministic, agent-driven repository editing.

## Fixed Baseline

GRACE currently has a stable v0.2 baseline.

The baseline includes:

- inline code-first annotations as the only source of truth
- parser
- validator
- linter
- derived map
- semantic patcher by `anchor_id` with rollback
- CLI
- single-file and repo-level JSON contract for shell-driven agents
- CI, release hygiene, docs, examples, smoke tests

Further development must build on this stable core rather than reinventing it.

## Canonical Invariants

### Source Of Truth

The only canonical source of truth is inline GRACE annotations in code/files.

Derived artifacts such as:

- map
- graph
- JSON exports
- patch plans
- future sidecars

must never override inline annotations.

### Stable Semantic Identity

`anchor_id` is a stable semantic coordinate, not a decorative tag.

### Deterministic Editing Discipline

Any patch workflow must remain:

patch -> parse -> validate -> rollback on failure

Lint warnings may remain non-blocking, but parse/validate failure must remain blocking.

### Core vs Frontend Separation

GRACE Core must remain conceptually language-agnostic.

Language-specific behavior belongs in frontend layers.

### Agent Contract Stability

Once CLI commands provide machine-readable `--json`, minor versions should not break the JSON shape without strong reason.

## Main Strategy

GRACE should evolve along three axes:

### Scale

From:

- file-level operations

To:

- repo-level operations
- cross-file graph
- multi-file patch plans

### Control

From:

- single patch execution

To:

- patch plan
- dry-run
- preview
- structured results
- transactional semantics

### Agentness

From:

- human CLI

To:

- machine-readable CLI contracts
- canonical agent loop
- agent evals
- repo-level agent workflows

If a new feature does not materially improve scale, control, or agentness, it should not be prioritized.

## Canonical Agent Loop

For an existing repository:

map -> inspect -> select anchors -> patch/plan -> validate -> lint -> repeat

For future bootstrap mode:

project spec -> scaffold -> map -> patch loop -> validate -> lint

GRACE should not encourage rewriting whole files.

Its canonical mode is anchor-driven atomic editing.

## Detailed Roadmap

## v0.17 - Release Hardening + Protocol Freeze

Goal:

Treat the current GRACE surface as a near-stable agent protocol and harden it through docs, regression coverage, and self-hosted reliability work instead of adding new capability layers.

Focus:

- freeze CLI and JSON result envelopes as normative references
- stabilize repository-root discovery and export behavior
- expand repo-scale eval and regression coverage
- document curated validation scopes versus inspection/export scopes
- define derived artifact policy for committed vs local-only outputs

Explicit non-goals for this stage:

- new adapters
- new patch semantics
- heuristics or ranking layers
- UI / IDE work
- source-of-truth expansion

## v0.18 - Adapter SDK Hardening

Goal:

Make adding a new adapter a routine engineering task instead of a one-off architecture exercise.

Focus:

- adapter authoring guide
- reusable conformance/parity/eval harness patterns
- support tier policy
- fixture templates and release checklist

Explicit non-goals for this stage:

- new adapter runtime
- broader syntax coverage for existing pilots
- core semantics changes
- Tree-sitter refactors beyond current pilot needs

## v0.19 - Repo-Scale Agent Reliability

Goal:

Measure GRACE as a repository-scale agent platform rather than only as a set of isolated fixture-level commands.

Focus:

- repo-scale reliability eval suite
- curated-scope validation policy
- deterministic CLI contract checks across export/navigation commands
- release criteria and quality gates

Explicit non-goals for this stage:

- new runtime capabilities
- new adapters
- broader syntax coverage
- graph or patch semantics changes

## v0.20 - v1.0 Readiness Review

Goal:

Assess whether GRACE is actually ready to become a stable agent development platform, rather than assuming readiness from feature count.

Focus:

- audit invariants and protocol docs
- compare release criteria with current behavior
- separate real `v1.0` blockers from post-1.0 backlog
- define a narrow release-ready promise for the core

Explicit non-goals for this stage:

- runtime feature expansion
- new adapters
- broader adapter coverage
- semantic contract changes

## v0.21 - v1.0 Release Prep

Goal:

Freeze release framing and public promises before any `v1.0` tag is considered.

Focus:

- final release-surface audit
- stable-core versus pilot-adapter messaging
- repository-root policy clarification
- artifact policy clarification
- release-prep regression checks on docs and public framing

Explicit non-goals for this stage:

- runtime feature expansion
- new adapters
- broader adapter coverage
- semantic contract changes

## v0.3 - Strong Patch Workflow

Goal:

Make patching not merely possible, but controllable, auditable, and machine-governed.

Required work:

- `patch --dry-run`
- `patch --preview`
- structured patch result
- explicit patch invariants documentation

`patch --dry-run` should report:

- target file
- target anchor
- whether identity is preserved
- parse result
- validate result
- lint warnings
- `rollback_needed = false`

Structured patch results should include at minimum:

- `ok`
- `command`
- `target`
- `anchor_id`
- `identity_preserved`
- `parse`
- `validate`
- `lint_warnings`
- `rollback_performed`

Optional later additions:

- `before_hash`
- `after_hash`

Explicit non-goals for this stage:

- multi-file transactional patch
- `apply-plan`
- IDE integration
- AST micro-edits
- partial line-based edits

## v0.4 - Patch Plans

Goal:

Move from single patch operations to controlled sets of changes.

New derived artifact:

`PatchPlan`

Each patch entry should minimally include:

- file
- anchor
- replacement source or replacement file
- operation type

Initial operation type:

- `replace_block`

Not in the first step:

- `rename_anchor`
- `move_block`
- `delete_block`
- `insert_block`

New command:

- `grace apply-plan plan.json`

`apply-plan` should:

- load the plan
- apply patches sequentially
- run parse/validate after each step
- stop on failure

Deferred:

- all-or-nothing multi-file transaction
- AI-generated plans inside GRACE
- complex patch languages
- graph-aware planning

## v0.5 - Cross-File Graph

Goal:

Evolve from file-level map to repo-level semantic graph.

Required work:

- cross-file anchor resolution for `links`
- repo semantic graph
- stable graph schema for agents

Graph should eventually include:

- modules
- anchors
- `module -> anchor` edges
- `anchor -> anchor` edges

Potential future expansion:

- `doc -> code`
- `code -> infra`

Explicit non-goals for this stage:

- graph visualization UI
- graph database
- fancy analytics
- semantic ranking heuristics

## v0.6 - Strong Execution Contract

Goal:

Strengthen execution semantics so GRACE is reliable not just for planning, but for deterministic agent execution.

Required work:

- `patch --dry-run`
- `apply-plan --dry-run`
- patch preview
- apply-plan preview
- structured JSON results for patch and apply-plan
- stable failure taxonomy

Execution priorities:

- keep `patch -> parse -> validate -> rollback` discipline intact
- keep lint warnings non-blocking unless explicitly elevated in a future version
- make execution results maximally machine-readable for shell-driven agents

Explicit non-goals for this stage:

- multi-file all-or-nothing transaction
- graph-aware execution planning
- IDE/editor integrations
- AST micro-edit systems

## v0.6-docs - Polyglot Annotation Contract

Goal:

Prepare GRACE for multiple languages and file types at the specification level, without delaying execution semantics.

Key principle:

The annotation vocabulary is universal even if frontends are not.

Examples of acceptable comment-hosted forms to document:

- `# @grace.anchor`
- `// @grace.anchor`
- `-- @grace.anchor`
- `/* @grace.anchor */`
- `<!-- @grace.anchor -->`

Required work:

- `docs/polyglot_annotations.md`
- vocabulary invariants
- comment-host syntax policy
- whitespace and payload rules
- frontend-readiness constraints

Explicit non-goals for this stage:

- complete multi-language implementation
- HTML/CSS/Kubernetes support all at once
- sidecar expansion

## v0.7 - Graph Query Layer

Goal:

Add a read-only derived query layer over `GraceMap` so agents can navigate the repo graph without manually decoding raw map output.

Required work:

- deterministic query ordering
- file/repo-scoped collection queries
- anchor-scoped queries
- explicit outgoing and incoming semantics
- CLI-friendly incoming naming as `dependents`

Representative commands:

- `grace query modules <path> --json`
- `grace query anchors <path> --json`
- `grace query anchor <path> <anchor_id> --json`
- `grace query links <path> <anchor_id> --json`
- `grace query dependents <path> <anchor_id> --json`
- `grace query neighbors <path> <anchor_id> --json`

Explicit non-goals:

- graph visualization
- ranking
- parser changes
- patch semantics changes

## v0.8 - Impact Analysis

Goal:

Let agents determine the consequences of changing an anchor through deterministic graph traversal.

New derived layer:

- impact layer

New command:

- `grace impact <path> <anchor_id> --json`

Impact output should include:

- direct dependents
- transitive dependents
- affected modules

Constraints:

- no new source of truth
- no parser semantics changes
- no AI inference
- deterministic traversal only over derived graph data

## v0.9 - Anchor Context Loading

Goal:

Let agents load usable anchor context without reading whole files.

New command:

- `grace read <path> <anchor_id> --json`

Read output should include:

- block annotations
- block code
- neighboring anchors
- links
- module id
- file path
- line range

Canonical agent flow becomes:

map -> query -> read -> impact -> patch

## v0.10 - Patch Planning Layer

Goal:

Add a deterministic planning layer that turns semantic graph impact into patch-plan proposals for agents.

New derived layer:

- planner layer

New command:

- `grace plan impact <path> <anchor_id> --json`

Planning output should include:

- suggested `replace_block` operations
- deterministic ordering

Constraints:

- no AI
- no heuristics
- no parser semantics changes
- no new source of truth

This layer proposes targets only and never executes patches.

## v0.10.2 - Self-Hosting Consolidation

Goal:

Stabilize GRACE as a self-hosted development system.

Required work:

- document the canonical self-hosting loop
- capture dogfooding lessons from real GRACE-on-GRACE development
- verify that `map -> query -> read -> impact -> plan -> apply-plan -> validate -> lint` works on the annotated `grace/` scope
- confirm at least one real GRACE-native patch on the self-hosted core

This is not a new semantic layer. It is a consolidation step that makes the existing workflow explicit and repeatable.

## v0.11 - Agent Playbook

Goal:

Freeze the canonical workflow for shell-driven AI agents.

New document:

- `docs/agent_playbook.md`

The playbook should standardize:

- `map`
- `query`
- `impact`
- `plan`
- `read`
- `patch / apply-plan`
- `validate`
- `lint`

This stage also adds a small self-hosted eval suite and explicit metrics for:

- anchor selection accuracy
- patch/apply-plan success rate
- rollback rate
- unnecessary file touch rate

It should include concrete examples for:

- Codex
- Claude Code
- shell-driven agents

## v0.12 - Scalable Language Integration Architecture

Goal:

Prepare GRACE for additional languages without changing GRACE Core semantics.

Required work:

- add a language adapter contract layer
- move Python-specific parsing into a reference adapter
- keep parser entrypoints language-agnostic at the top level
- preserve the existing `GraceFileModel` contract for all core layers
- document how future adapters must emit core-compatible models

Non-goals:

- no new source of truth
- no new annotation grammar
- no Tree-sitter yet
- no new runtime language support beyond Python
- no changes to patch, map, query, impact, read, or planner contracts

Outcome:

Core stays language-agnostic while Python remains the reference implementation behind an explicit adapter boundary.

Normative reference:

- `docs/language_integration.md`
- `docs/language_adapter_contract.md`

## v0.13 - Tree-sitter Pilot Adapter (TypeScript)

Goal:

Prove that a second runtime language can integrate through the adapter boundary without changing GRACE core semantics.

Delivered scope:

- `GraceLanguageAdapter` remains the stable boundary
- Tree-sitter is used only as parsing substrate
- `.ts` files route through a dedicated `TypeScriptAdapter`
- supported constructs stay intentionally small:
  - module annotations
  - function declarations
  - async function declarations
  - class declarations
  - class methods

Explicit non-goals:

- full TypeScript coverage
- JSX / TSX support
- framework semantics
- changing validator, linter, map, query, impact, read, planner, or patch contracts

Normative references:

- `docs/language_adapter_contract.md`
- `docs/typescript_adapter.md`

## v0.14 - Adapter Hardening + Cross-Language Parity

Goal:

Harden the adapter boundary after the TypeScript pilot without changing GRACE core semantics.

Delivered hardening scope:

- cross-language parity fixtures for Python and TypeScript
- adapter conformance tests
- compatibility matrix for supported and unsupported constructs
- explicit unsupported-syntax policy

Outcome:

Python remains the reference adapter, TypeScript remains the pilot adapter, and the adapter boundary now has parity and conformance coverage before any additional language is considered.

## v0.15 - Third Language Adapter (Go)

Goal:

Prove that the language adapter architecture scales past Python and TypeScript to a third language without changing GRACE core semantics.

Delivered scope:

- `.go` files route through a dedicated `GoAdapter`
- supported constructs stay intentionally small:
  - module annotations
  - function declarations
  - receiver methods
  - simple struct type declarations

Explicit non-goals:

- full Go coverage
- interface declarations as semantic blocks
- framework-specific semantics
- changing validator, linter, map, query, impact, read, planner, or patch contracts

Possible later candidates after Go hardening:

- Rust
- SQL
- YAML

Explicit non-goals:

- rewriting the architecture around Tree-sitter
- claiming universal language support prematurely
- supporting every language at once

## v0.16 - Adapter Evals + Multi-Language Parity Hardening

Goal:

Harden the polyglot adapter architecture after Python, TypeScript, and Go without changing GRACE core semantics.

Delivered scope:

- adapter eval suite with stable metrics
- expanded cross-language parity fixtures
- unsupported-syntax behavior verification
- CLI polyglot verification over parity fixtures
- adapter quality matrix and explicit multi-language behavior guarantees

Explicit non-goals:

- no new language runtime
- no broader TypeScript or Go syntax coverage
- no changes to parser, patch, map, query, impact, read, planner, or CLI contracts

## v1.0 - Stable Agent Development Platform

Goal:

Stabilize GRACE as an agent-driven development platform.

At this point GRACE should include:

- deterministic semantic graph
- graph queries
- impact analysis
- anchor context loading
- patch orchestration
- agent workflows
- multi-language frontends

## Parallel Tracks

These may progress alongside multiple phases:

### Agent Docs

Maintain:

- `docs/agent_contract.md`
- `docs/agent_playbook.md`

### Agent Evals

Gradually build benchmark tasks for:

- selecting the correct anchor
- patching successfully
- surviving validation
- minimizing rollback rate

### Release Discipline

Maintain:

- changelog
- invariant docs
- test matrix
- CLI smoke tests

## Explicit Non-Goals For The Near Term

Do not prioritize:

- VS Code extension
- GUI or web UI
- IDE-specific integrations
- language server
- graph visualization
- "generate full project from prompt" as a magic button
- sidecar-first architecture
- universal parser for everything immediately
- support for many languages at once

## Universal Architecture Formula

GRACE should aim for:

Universal Semantic Core + Incremental Frontends + Domain Profiles

Universal Core includes:

- annotation vocabulary
- models
- validator semantics
- linter policy
- map
- graph
- patch plans
- agent contract

Incremental Frontends handle:

- parsing substrate
- annotation binding
- block kind detection
- block span extraction
- patch unit extraction

Domain Profiles define:

- what counts as a meaningful block
- scaffold patterns
- common invariants

## Near-Term Priority Order

First:

- graph query stability
- impact analysis
- anchor context loading

Then:

- agent playbook
- self-hosting completion

Then:

- frontend abstraction
- Tree-sitter-backed language expansion

Then:

- broader agent platform stabilization

## Summary Formula

GRACE develops not as:

- an AI code generation tool
- an editor plugin
- a generic parser framework

but as:

a semantic protocol for deterministic, agent-driven repository editing
