# @grace.module grace.patcher
# @grace.purpose Replace semantic blocks by anchor_id while preserving identity and enforcing parse-validate rollback discipline.
# @grace.interfaces patch_block(path, anchor_id, replacement_source, *, dry_run=False)->PatchResult
# @grace.invariant Patching is always addressed by anchor_id, never by line numbers as a user-facing coordinate system.
# @grace.invariant Parse or validation failure after a write always rolls the file back to its original contents.
from __future__ import annotations

import difflib
import hashlib
import os
import re
import tempfile
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from grace.linter import LintFailure, LintIssue, lint_file
from grace.models import GraceFileModel, GraceParseIssue
from grace.parser import GraceParseError, parse_python_file
from grace.validator import ValidationFailure, ValidationIssue, validate_file

ANCHOR_ANNOTATION_RE = re.compile(r"^\s*#\s*@grace\.anchor\s+(?P<payload>.*\S)\s*$")


 # @grace.anchor grace.patcher.PatchFailureStage
 # @grace.complexity 1
class PatchFailureStage(str, Enum):
    TARGET_LOOKUP = "target_lookup"
    IDENTITY = "identity"
    PARSE = "parse"
    VALIDATE = "validate"


# @grace.anchor grace.patcher.PatchStepStatus
# @grace.complexity 1
class PatchStepStatus(str, Enum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"


# @grace.anchor grace.patcher.PatchStepResult
# @grace.complexity 1
class PatchStepResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: PatchStepStatus
    issue_count: int = Field(default=0, ge=0)


# @grace.anchor grace.patcher.PatchSuccess
# @grace.complexity 2
class PatchSuccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[True] = True
    path: Path
    anchor_id: str = Field(min_length=1)
    dry_run: bool = False
    identity_preserved: Literal[True] = True
    parse: PatchStepResult
    validation: PatchStepResult
    rollback_performed: bool = False
    before_hash: str = Field(min_length=1)
    after_hash: str = Field(min_length=1)
    preview: str
    file: GraceFileModel
    lint_issues: tuple[LintIssue, ...] = Field(default_factory=tuple)


# @grace.anchor grace.patcher.PatchFailure
# @grace.complexity 2
class PatchFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[False] = False
    path: Path
    anchor_id: str = Field(min_length=1)
    dry_run: bool = False
    stage: PatchFailureStage
    message: str = Field(min_length=1)
    identity_preserved: bool = False
    parse: PatchStepResult
    validation: PatchStepResult
    rollback_performed: bool = False
    before_hash: str | None = None
    after_hash: str | None = None
    preview: str | None = None
    parse_errors: tuple[GraceParseIssue, ...] = Field(default_factory=tuple)
    validation_issues: tuple[ValidationIssue, ...] = Field(default_factory=tuple)


PatchResult = PatchSuccess | PatchFailure


# @grace.anchor grace.patcher.patch_block
# @grace.complexity 7
# @grace.belief Safe semantic patching depends on preserving target identity up front, then reusing the existing parse and validation pipeline both before and after any write so rollback decisions remain deterministic.
# @grace.links grace.patcher._find_anchor_annotation_line, grace.patcher._extract_replacement_anchor_id, grace.patcher._normalize_replacement_source, grace.patcher._build_preview_diff, grace.patcher._hash_text, grace.patcher._parse_candidate_text, grace.patcher._splice_block
def patch_block(path: str | Path, anchor_id: str, replacement_source: str, *, dry_run: bool = False) -> PatchResult:
    source_path = Path(path)
    original_text = source_path.read_text(encoding="utf-8")

    try:
        original_file = parse_python_file(source_path)
    except GraceParseError as exc:
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            dry_run=dry_run,
            stage=PatchFailureStage.PARSE,
            message="existing file failed GRACE parsing before patch",
            parse=PatchStepResult(status=PatchStepStatus.FAILED, issue_count=len(exc.errors)),
            validation=PatchStepResult(status=PatchStepStatus.NOT_RUN),
            parse_errors=exc.errors,
        )

    target_block = next((block for block in original_file.blocks if block.anchor_id == anchor_id), None)
    if target_block is None:
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            dry_run=dry_run,
            stage=PatchFailureStage.TARGET_LOOKUP,
            message=f"anchor_id {anchor_id!r} does not exist in the target file",
            parse=PatchStepResult(status=PatchStepStatus.PASSED),
            validation=PatchStepResult(status=PatchStepStatus.NOT_RUN),
        )

    original_lines = original_text.splitlines(keepends=True)
    annotation_start = _find_anchor_annotation_line(original_lines, anchor_id)
    if annotation_start is None:
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            dry_run=dry_run,
            stage=PatchFailureStage.TARGET_LOOKUP,
            message=f"failed to locate the inline @grace.anchor line for {anchor_id!r}",
            parse=PatchStepResult(status=PatchStepStatus.PASSED),
            validation=PatchStepResult(status=PatchStepStatus.NOT_RUN),
        )

    original_block_source = "".join(original_lines[annotation_start : target_block.line_end])
    normalized_replacement_source = _normalize_replacement_source(replacement_source)
    preview = _build_preview_diff(source_path, anchor_id, original_block_source, normalized_replacement_source)
    before_hash = _hash_text(original_block_source)
    after_hash = _hash_text(normalized_replacement_source)

    replacement_anchor_id = _extract_replacement_anchor_id(replacement_source)
    if replacement_anchor_id is None:
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            dry_run=dry_run,
            stage=PatchFailureStage.IDENTITY,
            message="replacement_source must contain a non-empty @grace.anchor annotation",
            identity_preserved=False,
            parse=PatchStepResult(status=PatchStepStatus.NOT_RUN),
            validation=PatchStepResult(status=PatchStepStatus.NOT_RUN),
            before_hash=before_hash,
            after_hash=after_hash,
            preview=preview,
        )
    if replacement_anchor_id != anchor_id:
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            dry_run=dry_run,
            stage=PatchFailureStage.IDENTITY,
            message=(
                f"replacement_source anchor_id {replacement_anchor_id!r} does not match "
                f"target anchor_id {anchor_id!r}"
            ),
            identity_preserved=False,
            parse=PatchStepResult(status=PatchStepStatus.NOT_RUN),
            validation=PatchStepResult(status=PatchStepStatus.NOT_RUN),
            before_hash=before_hash,
            after_hash=after_hash,
            preview=preview,
        )

    patched_text = _splice_block(
        original_lines=original_lines,
        block_start_index=annotation_start,
        block_end_line=target_block.line_end,
        replacement_source=normalized_replacement_source,
    )
    try:
        candidate_file = _parse_candidate_text(source_path, patched_text)
    except GraceParseError as exc:
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            dry_run=dry_run,
            stage=PatchFailureStage.PARSE,
            message="replacement failed GRACE parsing during patch preflight",
            identity_preserved=True,
            parse=PatchStepResult(status=PatchStepStatus.FAILED, issue_count=len(exc.errors)),
            validation=PatchStepResult(status=PatchStepStatus.NOT_RUN),
            before_hash=before_hash,
            after_hash=after_hash,
            preview=preview,
            parse_errors=exc.errors,
        )

    validation_result = validate_file(candidate_file)
    if isinstance(validation_result, ValidationFailure):
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            dry_run=dry_run,
            stage=PatchFailureStage.VALIDATE,
            message="replacement failed GRACE validation during patch preflight",
            identity_preserved=True,
            parse=PatchStepResult(status=PatchStepStatus.PASSED),
            validation=PatchStepResult(status=PatchStepStatus.FAILED, issue_count=len(validation_result.issues)),
            before_hash=before_hash,
            after_hash=after_hash,
            preview=preview,
            validation_issues=validation_result.issues,
        )

    if dry_run:
        lint_result = lint_file(candidate_file)
        lint_issues = lint_result.issues if isinstance(lint_result, LintFailure) else ()
        return PatchSuccess(
            path=source_path,
            anchor_id=anchor_id,
            dry_run=True,
            parse=PatchStepResult(status=PatchStepStatus.PASSED),
            validation=PatchStepResult(status=PatchStepStatus.PASSED),
            rollback_performed=False,
            before_hash=before_hash,
            after_hash=after_hash,
            preview=preview,
            file=candidate_file.model_copy(update={"path": source_path}),
            lint_issues=tuple(lint_issues),
        )

    source_path.write_text(patched_text, encoding="utf-8")

    try:
        patched_file = parse_python_file(source_path)
    except GraceParseError as exc:
        source_path.write_text(original_text, encoding="utf-8")
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            dry_run=False,
            stage=PatchFailureStage.PARSE,
            message="patched file failed GRACE parsing and was rolled back",
            identity_preserved=True,
            parse=PatchStepResult(status=PatchStepStatus.FAILED, issue_count=len(exc.errors)),
            validation=PatchStepResult(status=PatchStepStatus.NOT_RUN),
            rollback_performed=True,
            before_hash=before_hash,
            after_hash=after_hash,
            preview=preview,
            parse_errors=exc.errors,
        )

    validation_result = validate_file(patched_file)
    if isinstance(validation_result, ValidationFailure):
        source_path.write_text(original_text, encoding="utf-8")
        return PatchFailure(
            path=source_path,
            anchor_id=anchor_id,
            dry_run=False,
            stage=PatchFailureStage.VALIDATE,
            message="patched file failed GRACE validation and was rolled back",
            identity_preserved=True,
            parse=PatchStepResult(status=PatchStepStatus.PASSED),
            validation=PatchStepResult(status=PatchStepStatus.FAILED, issue_count=len(validation_result.issues)),
            rollback_performed=True,
            before_hash=before_hash,
            after_hash=after_hash,
            preview=preview,
            validation_issues=validation_result.issues,
        )

    lint_result = lint_file(patched_file)
    lint_issues = lint_result.issues if isinstance(lint_result, LintFailure) else ()
    return PatchSuccess(
        path=source_path,
        anchor_id=anchor_id,
        dry_run=False,
        parse=PatchStepResult(status=PatchStepStatus.PASSED),
        validation=PatchStepResult(status=PatchStepStatus.PASSED),
        rollback_performed=False,
        before_hash=before_hash,
        after_hash=after_hash,
        preview=preview,
        file=patched_file,
        lint_issues=tuple(lint_issues),
    )


# @grace.anchor grace.patcher._find_anchor_annotation_line
# @grace.complexity 2
def _find_anchor_annotation_line(lines: list[str], anchor_id: str) -> int | None:
    for index, line in enumerate(lines):
        match = ANCHOR_ANNOTATION_RE.match(line)
        if match and match.group("payload").strip() == anchor_id:
            return index
    return None


# @grace.anchor grace.patcher._extract_replacement_anchor_id
# @grace.complexity 2
def _extract_replacement_anchor_id(replacement_source: str) -> str | None:
    for line in replacement_source.splitlines():
        match = ANCHOR_ANNOTATION_RE.match(line)
        if match:
            return match.group("payload").strip()
    return None


# @grace.anchor grace.patcher._normalize_replacement_source
# @grace.complexity 1
def _normalize_replacement_source(replacement_source: str) -> str:
    normalized_replacement = replacement_source
    if normalized_replacement and not normalized_replacement.endswith("\n"):
        normalized_replacement += "\n"
    return normalized_replacement


# @grace.anchor grace.patcher._build_preview_diff
# @grace.complexity 3
def _build_preview_diff(path: Path, anchor_id: str, original_block_source: str, replacement_source: str) -> str:
    before_lines = original_block_source.splitlines()
    after_lines = replacement_source.splitlines()
    return "\n".join(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"{path}:{anchor_id}:before",
            tofile=f"{path}:{anchor_id}:after",
            lineterm="",
        )
    )


# @grace.anchor grace.patcher._hash_text
# @grace.complexity 1
def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# @grace.anchor grace.patcher._parse_candidate_text
# @grace.complexity 5
# @grace.belief Candidate parsing should happen against a temporary sibling file so the parser sees a real file path and the patcher can reuse existing file-based contracts without mutating the target during preflight.
def _parse_candidate_text(source_path: Path, patched_text: str) -> GraceFileModel:
    fd, temp_name = tempfile.mkstemp(prefix=".grace_patch_", suffix=source_path.suffix, dir=source_path.parent)
    temp_path = Path(temp_name)
    os.close(fd)
    try:
        temp_path.write_text(patched_text, encoding="utf-8")
        parsed_file = parse_python_file(temp_path)
        return parsed_file.model_copy(update={"path": source_path})
    finally:
        try:
            temp_path.unlink()
        except OSError:
            pass


# @grace.anchor grace.patcher._splice_block
# @grace.complexity 2
def _splice_block(
    *,
    original_lines: list[str],
    block_start_index: int,
    block_end_line: int,
    replacement_source: str,
) -> str:
    replacement_lines = replacement_source.splitlines(keepends=True)
    return "".join(original_lines[:block_start_index] + replacement_lines + original_lines[block_end_line:])


__all__ = [
    "PatchFailure",
    "PatchFailureStage",
    "PatchResult",
    "PatchStepResult",
    "PatchStepStatus",
    "PatchSuccess",
    "patch_block",
]
