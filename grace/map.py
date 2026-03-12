from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from grace.models import GraceFileModel

GRACE_MAP_VERSION = "v1"


class GraceMapModule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    module_id: str
    path: str
    purpose: str


class GraceMapAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    anchor_id: str
    module_id: str
    kind: str
    complexity: int
    links: tuple[str, ...] = Field(default_factory=tuple)


class GraceMapEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str
    source: str
    target: str


class GraceMap(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    grace_version: str = GRACE_MAP_VERSION
    modules: tuple[GraceMapModule, ...]
    anchors: tuple[GraceMapAnchor, ...]
    edges: tuple[GraceMapEdge, ...]


def build_file_map(grace_file: GraceFileModel) -> GraceMap:
    return build_project_map([grace_file])


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
