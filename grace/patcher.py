from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from grace.linter import LintFailure, LintIssue, lint_file
from grace.models import GraceFileModel, GraceParseIssue
from grace.parser import GraceParseError, parse_python_file
from grace.validator import ValidationFailure, ValidationIssue, validate_file

ANCHOR_ANNOTATION_RE = re.compile(r"^\s*#\s*@grace\.anchor\s+(?P<payload>.*\S)\s*$")


class PatchFailureStage(str, Enum):
    TARGET_LOOKUP = "target_lookup"
    IDENTITY = "identity"
    PARSE = "parse"
    VALIDATE = "validate"


class PatchSuccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[True] = True
    path: Path
    anchor_id: str = Field(min_length=1)
    file: GraceFileModel
    lint_issues: tuple[LintIssue, ...] = Field(default_factory=tuple)


class PatchFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[False] = False
    path: Path
    anchor_id: str = Field(min_length=1)
    stage: PatchFailureStage
    message: str = Field(min_length=1)
    parse_errors: tuple[GraceParseIssue, ...] = Field(default_factory=tuple)
    validation_issues: tuple[ValidationIssue, ...] = Field(default_factory=tuple)


PatchResult = PatchSuccess | PatchFailure


def patch_block(path: str | Path, anchor_id: str, replacement_source: str) -> PatchResult:
    source_path = Path(path)
    original_text = source_path.read_text(encoding="utf-8")

    try:
        original_file = parse_python_file(source_path)
    except GraceParseError as exc:
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            stage=PatchFailureStage.PARSE,
            message="existing file failed GRACE parsing before patch",
            parse_errors=exc.errors,
        )

    target_block = next((block for block in original_file.blocks if block.anchor_id == anchor_id), None)
    if target_block is None:
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            stage=PatchFailureStage.TARGET_LOOKUP,
            message=f"anchor_id {anchor_id!r} does not exist in the target file",
        )

    replacement_anchor_id = _extract_replacement_anchor_id(replacement_source)
    if replacement_anchor_id is None:
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            stage=PatchFailureStage.IDENTITY,
            message="replacement_source must contain a non-empty @grace.anchor annotation",
        )
    if replacement_anchor_id != anchor_id:
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            stage=PatchFailureStage.IDENTITY,
            message=(
                f"replacement_source anchor_id {replacement_anchor_id!r} does not match "
                f"target anchor_id {anchor_id!r}"
            ),
        )

    original_lines = original_text.splitlines(keepends=True)
    annotation_start = _find_anchor_annotation_line(original_lines, anchor_id)
    if annotation_start is None:
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            stage=PatchFailureStage.TARGET_LOOKUP,
            message=f"failed to locate the inline @grace.anchor line for {anchor_id!r}",
        )

    patched_text = _splice_block(
        original_lines=original_lines,
        block_start_index=annotation_start,
        block_end_line=target_block.line_end,
        replacement_source=replacement_source,
    )
    source_path.write_text(patched_text, encoding="utf-8")

    try:
        patched_file = parse_python_file(source_path)
    except GraceParseError as exc:
        source_path.write_text(original_text, encoding="utf-8")
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            stage=PatchFailureStage.PARSE,
            message="patched file failed GRACE parsing and was rolled back",
            parse_errors=exc.errors,
        )

    validation_result = validate_file(patched_file)
    if isinstance(validation_result, ValidationFailure):
        source_path.write_text(original_text, encoding="utf-8")
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            stage=PatchFailureStage.VALIDATE,
            message="patched file failed GRACE validation and was rolled back",
            validation_issues=validation_result.issues,
        )

    lint_result = lint_file(patched_file)
    lint_issues = lint_result.issues if isinstance(lint_result, LintFailure) else ()
    return PatchSuccess(
        path=source_path,
        anchor_id=anchor_id,
        file=patched_file,
        lint_issues=tuple(lint_issues),
    )


def _find_anchor_annotation_line(lines: list[str], anchor_id: str) -> int | None:
    for index, line in enumerate(lines):
        match = ANCHOR_ANNOTATION_RE.match(line)
        if match and match.group("payload").strip() == anchor_id:
            return index
    return None


def _extract_replacement_anchor_id(replacement_source: str) -> str | None:
    for line in replacement_source.splitlines():
        match = ANCHOR_ANNOTATION_RE.match(line)
        if match:
            return match.group("payload").strip()
    return None


def _splice_block(
    *,
    original_lines: list[str],
    block_start_index: int,
    block_end_line: int,
    replacement_source: str,
) -> str:
    normalized_replacement = replacement_source
    if normalized_replacement and not normalized_replacement.endswith("\n"):
        normalized_replacement += "\n"
    replacement_lines = normalized_replacement.splitlines(keepends=True)
    return "".join(original_lines[:block_start_index] + replacement_lines + original_lines[block_end_line:])


__all__ = [
    "PatchFailure",
    "PatchFailureStage",
    "PatchResult",
    "PatchSuccess",
    "patch_block",
]
