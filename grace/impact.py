# @grace.module grace.impact
# @grace.purpose Compute deterministic reverse-dependency impact sets over a derived GraceMap.
# @grace.interfaces impact_direct(grace_map, anchor_id)->tuple[GraceMapAnchor,...]; impact_transitive(grace_map, anchor_id)->tuple[GraceMapAnchor,...]; impact_summary(grace_map, anchor_id)->ImpactSummary
# @grace.invariant Impact analysis remains a read-only derived layer over GraceMap and never introduces new identities.
# @grace.invariant Impact traversal follows only anchor_links_to_anchor edges in reverse dependency direction.
from __future__ import annotations

from collections import deque

from pydantic import BaseModel, ConfigDict, Field

from grace.map import GraceMap, GraceMapAnchor, GraceMapModule


# @grace.anchor grace.impact.ImpactLookupError
# @grace.complexity 1
class ImpactLookupError(ValueError):
    # @grace.anchor grace.impact.ImpactLookupError.__init__
    # @grace.complexity 1
    def __init__(self, anchor_id: str) -> None:
        self.anchor_id = anchor_id
        super().__init__(f"anchor_id {anchor_id!r} does not exist in impact scope")


# @grace.anchor grace.impact.ImpactSummary
# @grace.complexity 1
class ImpactSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    direct_dependents: tuple[GraceMapAnchor, ...] = Field(default_factory=tuple)
    transitive_dependents: tuple[GraceMapAnchor, ...] = Field(default_factory=tuple)
    affected_modules: tuple[GraceMapModule, ...] = Field(default_factory=tuple)


# @grace.anchor grace.impact.impact_direct
# @grace.complexity 3
# @grace.links grace.impact._require_anchor, grace.impact._anchor_index, grace.impact._reverse_dependents_index
def impact_direct(grace_map: GraceMap, anchor_id: str) -> tuple[GraceMapAnchor, ...]:
    _require_anchor(grace_map, anchor_id)
    anchor_index = _anchor_index(grace_map)
    reverse_dependents = _reverse_dependents_index(grace_map)
    return tuple(anchor_index[dependent_id] for dependent_id in reverse_dependents.get(anchor_id, ()))


# @grace.anchor grace.impact.impact_transitive
# @grace.complexity 6
# @grace.belief Transitive impact should stay deterministic by traversing only reverse anchor-links and sorting both frontier expansion and final output rather than inferring semantic reachability.
# @grace.links grace.impact._require_anchor, grace.impact._anchor_index, grace.impact._reverse_dependents_index
def impact_transitive(grace_map: GraceMap, anchor_id: str) -> tuple[GraceMapAnchor, ...]:
    _require_anchor(grace_map, anchor_id)
    anchor_index = _anchor_index(grace_map)
    reverse_dependents = _reverse_dependents_index(grace_map)
    visited: set[str] = set()
    frontier: deque[str] = deque(reverse_dependents.get(anchor_id, ()))

    while frontier:
        current_anchor_id = frontier.popleft()
        if current_anchor_id in visited:
            continue
        visited.add(current_anchor_id)
        for dependent_id in reverse_dependents.get(current_anchor_id, ()):
            if dependent_id not in visited:
                frontier.append(dependent_id)

    return tuple(anchor_index[dependent_id] for dependent_id in sorted(visited))


# @grace.anchor grace.impact.impact_summary
# @grace.complexity 4
# @grace.links grace.impact.impact_direct, grace.impact.impact_transitive, grace.impact._module_index
def impact_summary(grace_map: GraceMap, anchor_id: str) -> ImpactSummary:
    direct_dependents = impact_direct(grace_map, anchor_id)
    transitive_dependents = impact_transitive(grace_map, anchor_id)
    module_index = _module_index(grace_map)
    affected_modules = tuple(
        module_index[module_id]
        for module_id in sorted({anchor.module_id for anchor in transitive_dependents})
        if module_id in module_index
    )
    return ImpactSummary(
        direct_dependents=direct_dependents,
        transitive_dependents=transitive_dependents,
        affected_modules=affected_modules,
    )


# @grace.anchor grace.impact._require_anchor
# @grace.complexity 2
def _require_anchor(grace_map: GraceMap, anchor_id: str) -> GraceMapAnchor:
    anchor = _anchor_index(grace_map).get(anchor_id)
    if anchor is None:
        raise ImpactLookupError(anchor_id)
    return anchor


# @grace.anchor grace.impact._anchor_index
# @grace.complexity 2
def _anchor_index(grace_map: GraceMap) -> dict[str, GraceMapAnchor]:
    return {anchor.anchor_id: anchor for anchor in grace_map.anchors}


# @grace.anchor grace.impact._module_index
# @grace.complexity 2
def _module_index(grace_map: GraceMap) -> dict[str, GraceMapModule]:
    return {module.module_id: module for module in grace_map.modules}


# @grace.anchor grace.impact._reverse_dependents_index
# @grace.complexity 4
def _reverse_dependents_index(grace_map: GraceMap) -> dict[str, tuple[str, ...]]:
    reverse_dependents: dict[str, set[str]] = {}
    for edge in grace_map.edges:
        if edge.type != "anchor_links_to_anchor":
            continue
        reverse_dependents.setdefault(edge.target, set()).add(edge.source)
    return {
        target_anchor_id: tuple(sorted(dependent_anchor_ids))
        for target_anchor_id, dependent_anchor_ids in reverse_dependents.items()
    }


__all__ = [
    "ImpactLookupError",
    "ImpactSummary",
    "impact_direct",
    "impact_summary",
    "impact_transitive",
]
