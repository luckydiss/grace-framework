# GRACE Graph Export (MVP)

This document is normative for the MVP.

## Purpose

The graph export makes a GRACE project consumable by external RAG agents without forcing those agents to re-parse the repository from scratch.

## Invariants

1. Graph export must include modules, anchors, contracts, and belief states.
2. Graph export must preserve explicit semantic links.
3. Graph export must not rely on line numbers as primary coordinates.
4. Graph export must be serializable as standalone JSON.

## Node types

- `module`
- `anchor`
- `contract`
- `belief`

## Edge types

- `module_has_anchor`
- `module_has_contract`
- `anchor_has_belief`

## Open issues

- Dependency and call-graph edges are out of MVP scope.
- Incremental graph updates are not yet specified.
