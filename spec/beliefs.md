# GRACE BELIEF_STATE (MVP)

This document is normative for the MVP.

## Purpose

`BELIEF_STATE` makes latent assumptions explicit for complex code blocks. It is required when a block depends on heuristics, uncertain world models, non-trivial branching, or hidden operational assumptions.

## Invariants

1. Complex anchors must declare a `BELIEF_STATE`.
2. `BELIEF_STATE` is attached to an anchor, not only to a file.
3. `BELIEF_STATE` must be machine-readable.
4. Missing `BELIEF_STATE` on a complex anchor is a validation error.

## Required fields

- `anchor_id`
- `complexity`
- `assumptions`
- `risks`
- `failure_modes`

## Complexity levels

- `simple`: `BELIEF_STATE` optional
- `complex`: `BELIEF_STATE` required

## Open issues

- Complexity classification is currently author-supplied.
- Future versions may infer required belief states from control-flow or heuristic patterns.
