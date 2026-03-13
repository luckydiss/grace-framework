# GRACE Read Layer

The GRACE read layer is a read-only derived layer for anchor-local context loading.

Its purpose is to let an agent inspect one semantic block without reading the whole file.

## Scope

The read layer:

- does not introduce a new source of truth
- does not change parser semantics
- does not write to disk
- does not mutate the graph

It only extracts context from:

- parsed `GraceFileModel` objects
- derived `GraceMap`
- existing query-layer neighbors

## API

- `read_anchor_context(grace_files, grace_map, anchor_id)`
- `extract_anchor_code(grace_file, anchor_id)`
- `extract_anchor_annotations(grace_file, anchor_id)`
- `build_anchor_neighbors(grace_map, anchor_id)`

`read_anchor_context(...)` returns:

- `anchor_id`
- `module_id`
- `file_path`
- `line_start`
- `line_end`
- `annotations`
- `code`
- `links`
- `neighbors`

All outputs are deterministic for equivalent file and map inputs.

## CLI

GRACE exposes anchor reading as:

```bash
grace read <path> <anchor_id> --json
```

Example:

```bash
grace read grace grace.parser.parse_python_file --json
```

The response is a machine-readable envelope with a `data` object containing anchor-local context.

## Returned Fields

`read_anchor_context(...)` and `grace read ... --json` expose:

- `anchor_id`
- `module_id`
- `file_path`
- `line_start`
- `line_end`
- `annotations`
- `code`
- `links`
- `neighbors`

`line_start` points to the first inline GRACE annotation for the semantic block.

`line_end` points to the final line of the bound `def`, `async def`, `class`, or method block.

`annotations` contain only block-level GRACE annotations in source order.

`code` contains the executable block body, including decorators when present.

`neighbors` are derived through the query layer and remain deterministically ordered by `anchor_id`.

## Determinism

The read layer is deterministic for equivalent:

- `GraceFileModel` inputs
- `GraceMap` inputs
- source file contents

It never mutates repository state and never introduces new identities.
