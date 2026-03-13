# GRACE Impact Layer

The GRACE impact layer is a read-only derived layer over `GraceMap`.

Its purpose is to answer the question:

What is affected if this anchor changes?

## Scope

The impact layer:

- does not introduce a new source of truth
- does not modify parser semantics
- does not perform write operations
- does not use heuristics or AI inference

Impact is computed as deterministic graph traversal over `anchor_links_to_anchor` edges.

If:

- `A -> B`

then:

- `impact(B)` contains `A`

because `A` depends on `B`.

## API

- `impact_direct(grace_map, anchor_id)`
- `impact_transitive(grace_map, anchor_id)`
- `impact_summary(grace_map, anchor_id)`

`impact_direct` returns immediate reverse dependents.

`impact_transitive` returns the transitive reverse-dependent closure.

`impact_summary` returns:

- `direct_dependents`
- `transitive_dependents`
- `affected_modules`

All outputs are deterministically ordered.

## CLI

GRACE exposes impact analysis as:

```bash
grace impact <path> <anchor_id> --json
```

Example:

```bash
grace impact grace grace.parser.parse_python_file --json
```

The JSON result is machine-readable and stable enough for shell-driven agents.
