# Path Query Layer

GRACE `P1.5` adds a deterministic path query over the derived semantic graph.

The goal is narrow:

- help shell-driven agents ask how one anchor connects to another
- stay read-only and derived-only
- avoid heuristics or AI inference

## Command

```bash
grace query path <path> <source_anchor_id> <target_anchor_id> --json
```

## Semantics

- traversal is deterministic BFS
- traversal uses directed `anchor_links_to_anchor` edges only
- results are shortest-path within that directed anchor graph
- missing anchors are hard query failures
- absent paths are not failures; they return `found: false`

## JSON Shape

Success with a path:

```json
{
  "ok": true,
  "command": "query",
  "query": "path",
  "query_scope": "anchor",
  "source_anchor_id": "...",
  "target_anchor_id": "...",
  "found": true,
  "route": [],
  "edge_types": []
}
```

Success without a path:

```json
{
  "ok": true,
  "command": "query",
  "query": "path",
  "query_scope": "anchor",
  "source_anchor_id": "...",
  "target_anchor_id": "...",
  "found": false,
  "route": [],
  "edge_types": []
}
```

Failure:

```json
{
  "ok": false,
  "command": "query",
  "query": "path",
  "query_scope": "anchor",
  "stage": "query"
}
```

## Non-goals

- no graph ranking
- no heuristic path scoring
- no reverse reachability inference
- no source-of-truth changes
