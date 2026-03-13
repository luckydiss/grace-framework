# @grace.module grace.planner
# @grace.purpose Build deterministic patch-plan proposals from existing semantic graph data without executing changes or inferring edits.
# @grace.interfaces plan_from_impact(grace_map, anchor_id)->PatchPlanProposal; collect_patch_targets(grace_map, anchor_id)->tuple[GraceMapAnchor,...]; filter_self_anchor(anchors, anchor_id)->tuple[GraceMapAnchor,...]; build_plan_skeleton(anchors)->tuple[SuggestedPatchOperation,...]
# @grace.invariant Planning proposals are derived-only artifacts and never override inline annotations or execute patches.
# @grace.invariant Planner ordering must remain deterministic for equivalent GraceMap inputs and target anchors.
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from grace.impact import ImpactLookupError, impact_direct
from grace.map import GraceMap, GraceMapAnchor


# @grace.anchor grace.planner.PlannerLookupError
# @grace.complexity 1
class PlannerLookupError(ValueError):
    # @grace.anchor grace.planner.PlannerLookupError.__init__
    # @grace.complexity 1
    def __init__(self, anchor_id: str) -> None:
        self.anchor_id = anchor_id
        super().__init__(f"anchor_id {anchor_id!r} does not exist in planning scope")


# @grace.anchor grace.planner.SuggestedPatchOperation
# @grace.complexity 1
class SuggestedPatchOperation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["replace_block"] = "replace_block"
    anchor_id: str = Field(min_length=1)


# @grace.anchor grace.planner.PatchPlanProposal
# @grace.complexity 1
class PatchPlanProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_anchor_id: str = Field(min_length=1)
    suggested_operations: tuple[SuggestedPatchOperation, ...] = Field(default_factory=tuple)


# @grace.anchor grace.planner.plan_from_impact
# @grace.complexity 4
# @grace.links grace.planner.collect_patch_targets, grace.planner.filter_self_anchor, grace.planner.build_plan_skeleton
def plan_from_impact(grace_map: GraceMap, anchor_id: str) -> PatchPlanProposal:
    direct_targets = collect_patch_targets(grace_map, anchor_id)
    filtered_targets = filter_self_anchor(direct_targets, anchor_id)
    return PatchPlanProposal(
        target_anchor_id=anchor_id,
        suggested_operations=build_plan_skeleton(filtered_targets),
    )


# @grace.anchor grace.planner.collect_patch_targets
# @grace.complexity 3
# @grace.links grace.impact.impact_direct
def collect_patch_targets(grace_map: GraceMap, anchor_id: str) -> tuple[GraceMapAnchor, ...]:
    try:
        return tuple(sorted(impact_direct(grace_map, anchor_id), key=lambda anchor: anchor.anchor_id))
    except ImpactLookupError as error:
        raise PlannerLookupError(anchor_id) from error


# @grace.anchor grace.planner.filter_self_anchor
# @grace.complexity 2
def filter_self_anchor(anchors: tuple[GraceMapAnchor, ...], anchor_id: str) -> tuple[GraceMapAnchor, ...]:
    return tuple(anchor for anchor in anchors if anchor.anchor_id != anchor_id)


# @grace.anchor grace.planner.build_plan_skeleton
# @grace.complexity 2
def build_plan_skeleton(anchors: tuple[GraceMapAnchor, ...]) -> tuple[SuggestedPatchOperation, ...]:
    return tuple(
        SuggestedPatchOperation(anchor_id=anchor.anchor_id)
        for anchor in sorted(anchors, key=lambda item: item.anchor_id)
    )


__all__ = [
    "PatchPlanProposal",
    "PlannerLookupError",
    "SuggestedPatchOperation",
    "build_plan_skeleton",
    "collect_patch_targets",
    "filter_self_anchor",
    "plan_from_impact",
]
