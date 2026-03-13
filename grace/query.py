# @grace.module grace.query
# @grace.purpose Provide deterministic read-only graph queries over derived GRACE maps for agent navigation.
# @grace.interfaces query_modules(grace_map)->tuple[GraceMapModule,...]; query_anchors(grace_map, module_id=None)->tuple[GraceMapAnchor,...]; query_anchor(grace_map, anchor_id)->GraceMapAnchor; query_links(grace_map, anchor_id)->tuple[GraceMapAnchor,...]; query_dependents(grace_map, anchor_id)->tuple[GraceMapAnchor,...]; query_neighbors(grace_map, anchor_id)->tuple[GraceMapAnchor,...]
# @grace.invariant Query results are derived-only views over GraceMap and never introduce new identities.
# @grace.invariant Query ordering must be deterministic across repeated runs on equivalent map inputs.
from __future__ import annotations

from grace.map import GraceMap, GraceMapAnchor, GraceMapModule


# @grace.anchor grace.query.QueryLookupError
# @grace.complexity 1
class QueryLookupError(ValueError):
    # @grace.anchor grace.query.QueryLookupError.__init__
    # @grace.complexity 1
    def __init__(self, anchor_id: str) -> None:
        self.anchor_id = anchor_id
        super().__init__(f"anchor_id {anchor_id!r} does not exist in query scope")


# @grace.anchor grace.query.query_modules
# @grace.complexity 2
def query_modules(grace_map: GraceMap) -> tuple[GraceMapModule, ...]:
    return tuple(sorted(grace_map.modules, key=lambda module: (module.module_id, module.path)))


# @grace.anchor grace.query.query_anchors
# @grace.complexity 3
def query_anchors(grace_map: GraceMap, module_id: str | None = None) -> tuple[GraceMapAnchor, ...]:
    anchors = grace_map.anchors
    if module_id is not None:
        anchors = tuple(anchor for anchor in anchors if anchor.module_id == module_id)
    return tuple(sorted(anchors, key=lambda anchor: anchor.anchor_id))


# @grace.anchor grace.query.query_anchor
# @grace.complexity 2
def query_anchor(grace_map: GraceMap, anchor_id: str) -> GraceMapAnchor:
    anchor = _anchor_index(grace_map).get(anchor_id)
    if anchor is None:
        raise QueryLookupError(anchor_id)
    return anchor


# @grace.anchor grace.query.query_links
# @grace.complexity 3
# @grace.links grace.query.query_anchor
def query_links(grace_map: GraceMap, anchor_id: str) -> tuple[GraceMapAnchor, ...]:
    anchor = query_anchor(grace_map, anchor_id)
    anchor_index = _anchor_index(grace_map)
    linked_anchors = [anchor_index[target_id] for target_id in anchor.links if target_id in anchor_index]
    return tuple(sorted(linked_anchors, key=lambda item: item.anchor_id))


# @grace.anchor grace.query.query_dependents
# @grace.complexity 4
# @grace.belief Incoming-link queries should be exposed as dependents because that name is clearer for shell-driven agents reasoning about impact from a target anchor outward.
def query_dependents(grace_map: GraceMap, anchor_id: str) -> tuple[GraceMapAnchor, ...]:
    query_anchor(grace_map, anchor_id)
    dependents = [anchor for anchor in grace_map.anchors if anchor_id in anchor.links]
    return tuple(sorted(dependents, key=lambda item: item.anchor_id))


# @grace.anchor grace.query.query_neighbors
# @grace.complexity 4
# @grace.links grace.query.query_links, grace.query.query_dependents
def query_neighbors(grace_map: GraceMap, anchor_id: str) -> tuple[GraceMapAnchor, ...]:
    outgoing = query_links(grace_map, anchor_id)
    dependents = query_dependents(grace_map, anchor_id)
    combined = {anchor.anchor_id: anchor for anchor in (*outgoing, *dependents)}
    return tuple(sorted(combined.values(), key=lambda item: item.anchor_id))


# @grace.anchor grace.query._anchor_index
# @grace.complexity 2
def _anchor_index(grace_map: GraceMap) -> dict[str, GraceMapAnchor]:
    return {anchor.anchor_id: anchor for anchor in grace_map.anchors}

__all__ = [
    "QueryLookupError",
    "query_anchor",
    "query_anchors",
    "query_dependents",
    "query_links",
    "query_modules",
    "query_neighbors",
]
