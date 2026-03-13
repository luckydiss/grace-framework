# @grace.module grace.map
# @grace.purpose Build derived GRACE maps from parsed file models without introducing new identities or source-of-truth semantics.
# @grace.interfaces build_file_map(grace_file)->GraceMap; build_project_map(grace_files)->GraceMap; map_to_dict(grace_map)->dict
# @grace.invariant Every module_id and anchor_id in a map must come directly from the input GraceFileModel set.
# @grace.invariant Map output is a derived navigation artifact only and never overrides inline annotations.
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from grace.models import GraceFileModel

GRACE_MAP_VERSION = "v1"


# @grace.anchor grace.map.GraceMapModule
# @grace.complexity 1
class GraceMapModule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    module_id: str
    path: str
    purpose: str


# @grace.anchor grace.map.GraceMapAnchor
# @grace.complexity 1
class GraceMapAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    anchor_id: str
    module_id: str
    kind: str
    complexity: int
    links: tuple[str, ...] = Field(default_factory=tuple)


# @grace.anchor grace.map.GraceMapEdge
# @grace.complexity 1
class GraceMapEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str
    source: str
    target: str


# @grace.anchor grace.map.GraceMap
# @grace.complexity 1
class GraceMap(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    grace_version: str = GRACE_MAP_VERSION
    modules: tuple[GraceMapModule, ...]
    anchors: tuple[GraceMapAnchor, ...]
    edges: tuple[GraceMapEdge, ...]


# @grace.anchor grace.map.build_file_map
# @grace.complexity 1
# @grace.links grace.map.build_project_map
def build_file_map(grace_file: GraceFileModel) -> GraceMap:
    return build_project_map([grace_file])


# @grace.anchor grace.map.build_project_map
# @grace.complexity 5
def build_project_map(grace_files: list[GraceFileModel] | tuple[GraceFileModel, ...]) -> GraceMap:
    sorted_files = tuple(sorted(grace_files, key=lambda item: (item.module.module_id, str(item.path))))
    modules: list[GraceMapModule] = []
    anchors: list[GraceMapAnchor] = []
    edges: list[GraceMapEdge] = []

    for grace_file in sorted_files:
        modules.append(
            GraceMapModule(
                module_id=grace_file.module.module_id,
                path=str(Path(grace_file.path)),
                purpose=grace_file.module.purpose,
            )
        )

        for block in sorted(grace_file.blocks, key=lambda item: item.anchor_id):
            anchors.append(
                GraceMapAnchor(
                    anchor_id=block.anchor_id,
                    module_id=grace_file.module.module_id,
                    kind=block.kind.value,
                    complexity=block.complexity,
                    links=tuple(block.links),
                )
            )
            edges.append(
                GraceMapEdge(
                    type="module_has_anchor",
                    source=grace_file.module.module_id,
                    target=block.anchor_id,
                )
            )
            for link_target in block.links:
                edges.append(
                    GraceMapEdge(
                        type="anchor_links_to_anchor",
                        source=block.anchor_id,
                        target=link_target,
                    )
                )

    return GraceMap(
        modules=tuple(modules),
        anchors=tuple(anchors),
        edges=tuple(edges),
    )


# @grace.anchor grace.map.map_to_dict
# @grace.complexity 1
def map_to_dict(grace_map: GraceMap) -> dict:
    return grace_map.model_dump(mode="json")


__all__ = [
    "GRACE_MAP_VERSION",
    "GraceMap",
    "GraceMapAnchor",
    "GraceMapEdge",
    "GraceMapModule",
    "build_file_map",
    "build_project_map",
    "map_to_dict",
]
