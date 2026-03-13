# v0.7 Graph Query Layer

This document prepares the next step after the first self-hosted GRACE development cycle.

## Goal

GRACE v0.7 should add a graph query layer over the existing derived project map so that agents can query repository structure without inventing new source-of-truth semantics.

The graph query layer is not a new parser, not a graph database, and not an analytics product. It is a deterministic read layer over already-derived GRACE graph data.

## Inputs

- Parsed `GraceFileModel` values
- Derived `GraceMap`
- Existing module and anchor identities
- Existing `module_has_anchor` and `anchor_links_to_anchor` relationships

## Architectural Constraints

- Inline GRACE annotations remain the only source of truth.
- Query results must never introduce new `module_id` or `anchor_id` values.
- Query semantics must remain deterministic and machine-readable.
- The query layer must stay derived-only and read-only.
- The query layer must not mutate repositories.

## Why It Exists

The current `map --json` contract is sufficient for full graph export, but still low-level for agent loops.

Agents need simple deterministic questions such as:

- which modules exist in this scope
- which anchors exist in a module
- which anchors link to a target anchor
- which anchors are immediate neighbors of a given anchor
- which files are affected by a selected anchor set

These are query problems, not parsing problems.

## Proposed Scope

v0.7 should focus on a minimal query surface over the current graph:

- list modules
- list anchors
- get a module by `module_id`
- get an anchor by `anchor_id`
- list outgoing links for an anchor
- list incoming links for an anchor
- list immediate neighbors for an anchor

All results should be JSON-first.

## Non-Goals

Not in v0.7:

- graph visualization
- semantic ranking heuristics
- graph scoring
- graph database integration
- impact prediction by heuristics
- write operations
- query languages more complex than the minimum needed for agent workflows

## Expected CLI Direction

The most likely shape is a thin CLI layer over the derived graph, for example:

- `grace query modules <path> --json`
- `grace query anchors <path> --json`
- `grace query anchor <path> <anchor_id> --json`
- `grace query neighbors <path> <anchor_id> --json`

This should remain a machine-readable agent contract, not an interactive UI.

## Relation To Existing Layers

- parser: produces typed file models
- validator: enforces hard consistency
- linter: emits warnings
- map: exports the derived graph artifact
- graph query layer: reads and filters that graph artifact for agents

The graph query layer should build on `map`, not bypass it.

## Success Criteria

v0.7 is successful if an agent can:

1. query the repository graph deterministically
2. find a target anchor and its immediate neighborhood
3. reason about linked anchors without scanning raw map JSON manually
4. keep using the same anchor-driven patch workflow afterward

## Canonical Position

GRACE continues to evolve as:

semantic protocol for deterministic, agent-driven repository editing

The graph query layer strengthens navigation and reasoning. It must not drift into code generation or UI-centric tooling.
