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

## v0.7 - Frontend Abstraction

Goal:

Separate Core from Python-specific assumptions.

Introduce:

- `GraceFrontend`

Frontend responsibilities:

- find annotations
- bind annotations to semantic entities
- determine block kind
- compute block span
- produce `GraceFileModel`-compatible output

Core remains responsible for:

- validator
- linter
- map
- patch plans
- agent contract
- project graph
- CLI JSON contract

Deferred:

- rewriting everything into a universal parser immediately
- deleting the Python frontend before a second stable frontend exists

## v0.8 - Tree-sitter Frontends

Goal:

Use Tree-sitter as a parsing substrate for additional frontends.

Tree-sitter is:

- a parser substrate
- a CST provider
- a block/span detector

Tree-sitter is not:

- a replacement for GRACE architecture

Recommended first new frontend:

- TypeScript

Possible later frontends:

- Go
- Java
- Rust
- YAML/Kubernetes
- Markdown/docs

Explicit non-goals:

- supporting every language at once
- rewriting the Python frontend before abstraction is stable
- promising universal support prematurely

## v0.9 - Domain Profiles

Goal:

Go beyond "code only" into docs, infra, and configs.

Key idea:

A GRACE block is an atomically and deterministically editable unit of meaning.

Examples:

- Python: function / class / method
- TypeScript: function / class / method
- YAML/Kubernetes: resource
- Markdown: section
- HTML: subtree
- SQL: query block / migration unit

Introduce:

- frontend + domain profile

Examples:

- python + fastapi
- typescript + react
- yaml + kubernetes
- markdown + docs

At this stage sidecars may be introduced cautiously only as projection:

inline annotations -> sidecar

and only for:

- read-only artifacts
- external artifacts
- generated artifacts
- non-editable artifacts

## v1.0 - Cross-Repo Semantic Layer

Goal:

Turn GRACE into a semantic coordination layer over repositories.

At this point GRACE should support:

- repo-wide graph
- cross-artifact links
- patch plans
- stable agent contract
- multi-frontend architecture
- semantic navigation across docs/code/infra

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

- repo-level reliability
- project JSON contracts
- stronger patch workflow

Then:

- patch plans
- graph
- cross-file semantics

Then:

- polyglot annotations
- frontends
- Tree-sitter
- domain profiles

Then:

- bootstrap / project generation
- cross-repo semantic layer

## Summary Formula

GRACE develops not as:

- an AI code generation tool
- an editor plugin
- a generic parser framework

but as:

a semantic protocol for deterministic, agent-driven repository editing
