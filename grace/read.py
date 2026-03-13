# @grace.module grace.read
# @grace.purpose Extract deterministic anchor-local context from parsed GRACE files and derived maps without reading whole modules at the agent layer.
# @grace.interfaces read_anchor_context(grace_files, grace_map, anchor_id)->ReadAnchorContext; extract_anchor_code(grace_file, anchor_id)->str; extract_anchor_annotations(grace_file, anchor_id)->tuple[str,...]; build_anchor_neighbors(grace_map, anchor_id)->tuple[GraceMapAnchor,...]
# @grace.invariant Read results are derived-only views over inline annotations and never replace code-first source-of-truth semantics.
# @grace.invariant Anchor context extraction must remain deterministic for equivalent file contents and map inputs.
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from grace.map import GraceMap, GraceMapAnchor
from grace.models import GraceBlockMetadata, GraceFileModel
from grace.query import QueryLookupError, query_anchor, query_neighbors


# @grace.anchor grace.read.ReadLookupError
# @grace.complexity 1
class ReadLookupError(ValueError):
    # @grace.anchor grace.read.ReadLookupError.__init__
    # @grace.complexity 1
    def __init__(self, anchor_id: str) -> None:
        self.anchor_id = anchor_id
        super().__init__(f"anchor_id {anchor_id!r} does not exist in read scope")


# @grace.anchor grace.read.ReadAnchorContext
# @grace.complexity 1
class ReadAnchorContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    anchor_id: str = Field(min_length=1)
    module_id: str = Field(min_length=1)
    file_path: str = Field(min_length=1)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    annotations: tuple[str, ...] = Field(default_factory=tuple)
    code: str = Field(min_length=1)
    links: tuple[str, ...] = Field(default_factory=tuple)
    neighbors: tuple[GraceMapAnchor, ...] = Field(default_factory=tuple)


# @grace.anchor grace.read.read_anchor_context
# @grace.complexity 5
# @grace.links grace.read._find_grace_file_for_anchor, grace.read._find_block, grace.read.extract_anchor_annotations, grace.read.extract_anchor_code, grace.read.build_anchor_neighbors, grace.read._find_anchor_annotation_start
def read_anchor_context(
    grace_files: list[GraceFileModel] | tuple[GraceFileModel, ...],
    grace_map: GraceMap,
    anchor_id: str,
) -> ReadAnchorContext:
    anchor = _require_anchor(grace_map, anchor_id)
    grace_file = _find_grace_file_for_anchor(grace_files, anchor_id)
    block = _find_block(grace_file, anchor_id)
    annotation_start = _find_anchor_annotation_start(grace_file.path, anchor_id)
    return ReadAnchorContext(
        anchor_id=anchor.anchor_id,
        module_id=anchor.module_id,
        file_path=str(grace_file.path),
        line_start=annotation_start + 1,
        line_end=block.line_end,
        annotations=extract_anchor_annotations(grace_file, anchor_id),
        code=extract_anchor_code(grace_file, anchor_id),
        links=tuple(anchor.links),
        neighbors=tuple(neighbor.model_dump(mode="python") for neighbor in build_anchor_neighbors(grace_map, anchor_id)),
    )


# @grace.anchor grace.read.extract_anchor_code
# @grace.complexity 4
# @grace.links grace.read._find_block, grace.read._find_anchor_annotation_start, grace.read._find_code_start
def extract_anchor_code(grace_file: GraceFileModel, anchor_id: str) -> str:
    block = _find_block(grace_file, anchor_id)
    source_lines = _read_source_lines(grace_file.path)
    annotation_start = _find_anchor_annotation_start(grace_file.path, anchor_id)
    code_start = _find_code_start(source_lines, annotation_start)
    return "".join(source_lines[code_start:block.line_end])


# @grace.anchor grace.read.extract_anchor_annotations
# @grace.complexity 4
# @grace.links grace.read._find_anchor_annotation_start, grace.read._collect_annotation_lines
def extract_anchor_annotations(grace_file: GraceFileModel, anchor_id: str) -> tuple[str, ...]:
    source_lines = _read_source_lines(grace_file.path)
    annotation_start = _find_anchor_annotation_start(grace_file.path, anchor_id)
    return tuple(line.rstrip("\n") for line in _collect_annotation_lines(source_lines, annotation_start))


# @grace.anchor grace.read.build_anchor_neighbors
# @grace.complexity 2
# @grace.links grace.query.query_neighbors
def build_anchor_neighbors(grace_map: GraceMap, anchor_id: str) -> tuple[GraceMapAnchor, ...]:
    return query_neighbors(grace_map, anchor_id)


# @grace.anchor grace.read._require_anchor
# @grace.complexity 2
def _require_anchor(grace_map: GraceMap, anchor_id: str) -> GraceMapAnchor:
    try:
        return query_anchor(grace_map, anchor_id)
    except QueryLookupError as error:
        raise ReadLookupError(anchor_id) from error


# @grace.anchor grace.read._find_grace_file_for_anchor
# @grace.complexity 3
def _find_grace_file_for_anchor(
    grace_files: list[GraceFileModel] | tuple[GraceFileModel, ...],
    anchor_id: str,
) -> GraceFileModel:
    for grace_file in grace_files:
        if any(block.anchor_id == anchor_id for block in grace_file.blocks):
            return grace_file
    raise ReadLookupError(anchor_id)


# @grace.anchor grace.read._find_block
# @grace.complexity 2
def _find_block(grace_file: GraceFileModel, anchor_id: str) -> GraceBlockMetadata:
    for block in grace_file.blocks:
        if block.anchor_id == anchor_id:
            return block
    raise ReadLookupError(anchor_id)


# @grace.anchor grace.read._find_anchor_annotation_start
# @grace.complexity 3
def _find_anchor_annotation_start(file_path: str | Path, anchor_id: str) -> int:
    source_lines = _read_source_lines(file_path)
    expected_line = f"# @grace.anchor {anchor_id}"
    for index, line in enumerate(source_lines):
        if line.rstrip("\n") == expected_line:
            return index
    raise ReadLookupError(anchor_id)


# @grace.anchor grace.read._read_source_lines
# @grace.complexity 1
def _read_source_lines(file_path: str | Path) -> list[str]:
    return Path(file_path).read_text(encoding="utf-8").splitlines(keepends=True)


# @grace.anchor grace.read._collect_annotation_lines
# @grace.complexity 3
def _collect_annotation_lines(source_lines: list[str], annotation_start: int) -> tuple[str, ...]:
    annotation_lines: list[str] = []
    for line in source_lines[annotation_start:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# @grace."):
            annotation_lines.append(line)
            continue
        break
    return tuple(annotation_lines)


# @grace.anchor grace.read._find_code_start
# @grace.complexity 3
def _find_code_start(source_lines: list[str], annotation_start: int) -> int:
    code_start = annotation_start
    for index in range(annotation_start, len(source_lines)):
        stripped = source_lines[index].strip()
        if not stripped:
            code_start = index + 1
            continue
        if stripped.startswith("# @grace."):
            code_start = index + 1
            continue
        return index
    return code_start


__all__ = [
    "ReadAnchorContext",
    "ReadLookupError",
    "build_anchor_neighbors",
    "extract_anchor_annotations",
    "extract_anchor_code",
    "read_anchor_context",
]
