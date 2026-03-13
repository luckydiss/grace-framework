# @grace.module grace.path_query
# @grace.purpose Compute deterministic shortest semantic paths between anchors over the derived anchor-to-anchor graph.
# @grace.interfaces query_path(grace_map, source_anchor_id, target_anchor_id)->tuple[GraceMapAnchor,...]; query_path_edge_types(anchor_path)->tuple[str,...]
# @grace.invariant Path queries are derived-only traversals over existing anchor_links_to_anchor edges and never introduce new identities.
# @grace.invariant Path traversal ordering must remain deterministic across equivalent GraceMap inputs.
from __future__ import annotations

from collections import deque

from grace.map import GraceMap, GraceMapAnchor
from grace.query import query_anchor


# @grace.anchor grace.path_query.query_path
# @grace.complexity 5
# @grace.links grace.query.query_anchor
def query_path(grace_map: GraceMap, source_anchor_id: str, target_anchor_id: str) -> tuple[GraceMapAnchor, ...]:
    source_anchor = query_anchor(grace_map, source_anchor_id)
    query_anchor(grace_map, target_anchor_id)
    if source_anchor_id == target_anchor_id:
        return (source_anchor,)

    anchor_index = {anchor.anchor_id: anchor for anchor in grace_map.anchors}
    visited = {source_anchor_id}
    frontier: deque[tuple[str, tuple[str, ...]]] = deque([(source_anchor_id, (source_anchor_id,))])

    while frontier:
        current_anchor_id, current_path = frontier.popleft()
        current_anchor = anchor_index[current_anchor_id]
        for next_anchor_id in sorted(link for link in current_anchor.links if link in anchor_index):
            if next_anchor_id in visited:
                continue
            next_path = (*current_path, next_anchor_id)
            if next_anchor_id == target_anchor_id:
                return tuple(anchor_index[anchor_id] for anchor_id in next_path)
            visited.add(next_anchor_id)
            frontier.append((next_anchor_id, next_path))

    return ()


# @grace.anchor grace.path_query.query_path_edge_types
# @grace.complexity 1
def query_path_edge_types(anchor_path: tuple[GraceMapAnchor, ...]) -> tuple[str, ...]:
    if len(anchor_path) <= 1:
        return ()
    return tuple("anchor_links_to_anchor" for _ in range(len(anchor_path) - 1))


__all__ = [
    "query_path",
    "query_path_edge_types",
]
