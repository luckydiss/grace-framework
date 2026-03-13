# Self-Hosting GRACE

GRACE is now developed through GRACE itself.

This document records the canonical self-hosting workflow for the `grace/` package and the practical lessons learned while dogfooding the framework on its own core.

## Canonical Workflow

1. Build the repo graph:

```bash
grace map grace --json
```

2. Discover candidate anchors:

```bash
grace query anchors grace --json
```

3. Read local anchor context:

```bash
grace read grace <anchor_id> --json
```

4. Inspect reverse dependency impact:

```bash
grace impact grace <anchor_id> --json
```

5. Generate a deterministic proposal:

```bash
grace plan impact grace <anchor_id> --json
```

6. Prepare a concrete patch plan or replacement block.

7. Preflight before writing:

```bash
grace apply-plan plan.json --dry-run --preview --json
```

8. Apply the change:

```bash
grace apply-plan plan.json --json
```

9. Re-check the self-hosted scope:

```bash
grace validate grace --json
grace lint grace --json
```

The canonical loop is therefore:

`map -> query -> read -> impact -> plan -> apply-plan -> validate -> lint`

## Scope Discipline

Self-hosting currently targets the annotated `grace/` package.

The canonical scope for development commands is:

```bash
grace map grace --json
grace validate grace --json
grace lint grace --json
```

Using the repository root as discovery scope is possible, but `grace/` remains the curated self-hosting surface.

## Dogfooding Lessons

### Annotation overhead

Inline semantic coordinates are workable on real framework code, but helper-heavy modules accumulate noticeable annotation overhead. This is acceptable because the overhead buys stable patch targets and machine-readable navigation.

### Large block warnings

The linter consistently flags orchestration-heavy anchors such as CLI commands, parser state-machine blocks, and patch pipeline blocks. This is useful pressure: it reveals where GRACE-friendly semantic granularity is weaker than ideal even when the code is still functionally correct.

### Curated discovery scope

The most reliable self-hosting scope is the annotated `grace/` package itself. Running discovery over the whole repository introduces unnecessary noise from tests, fixtures, and other files that are not part of the active dogfood surface.

### Cross-file links behavior

Cross-file `grace.links` are real in the self-hosted core. That forced patch preflight to become project-aware instead of file-only. Self-hosting surfaced this requirement before it would have been obvious from isolated examples.

### Patcher path bug

Self-hosting also exposed a path-handling execution bug: relative-path patches failed in post-write validation while absolute-path patches succeeded. This led to the `v0.10.1` canonical-path fix, and it is a concrete example of GRACE improving itself through its own workflow.

## Current Status

The self-hosted core now covers the full execution loop:

- parse
- validate
- lint
- map
- query
- impact
- read
- planner
- patcher
- apply-plan

New feature work in the annotated core should continue to prefer GRACE-native editing rather than direct manual edits.
