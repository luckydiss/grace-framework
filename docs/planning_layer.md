# GRACE Planning Layer

The planning layer is a read-only derived layer for building deterministic patch proposals from the existing semantic graph.

Its purpose is to help an agent answer:

- which anchors are directly affected by a target anchor
- which anchors are reasonable first candidates for `replace_block`

## Scope

The planning layer:

- does not introduce a new source of truth
- does not change parser semantics
- does not execute patches
- does not use AI or heuristics

It only transforms existing graph information into a machine-readable proposal.

## API

- `plan_from_impact(grace_map, anchor_id)`
- `collect_patch_targets(grace_map, anchor_id)`
- `filter_self_anchor(anchors, anchor_id)`
- `build_plan_skeleton(anchors)`

`plan_from_impact(...)` returns a `PatchPlanProposal` with:

- `target_anchor_id`
- `suggested_operations`

Each suggested operation currently contains:

- `operation = "replace_block"`
- `anchor_id`

## Determinism

Planning remains deterministic for equivalent:

- `GraceMap` inputs
- target anchors

Suggested operations are ordered by `anchor_id`.

## CLI

GRACE exposes planning as:

```bash
grace plan impact <path> <anchor_id> --json
```

Example:

```bash
grace plan impact grace grace.parser.parse_python_file --json
```

This returns a proposal envelope with `suggested_operations`.

The output is intentionally not an executable `PatchPlan`.

It is a proposal for the agent to inspect before creating or applying a real plan.
