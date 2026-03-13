# @grace.module grace.linter
# @grace.purpose Emit soft policy warnings about maintainability, machine utility, and LLM-friendly block granularity for parsed GRACE models.
# @grace.interfaces lint_file(grace_file)->LintResult; lint_project(grace_files)->LintResult
# @grace.invariant Linter must not duplicate parser or validator hard failures as a second blocking layer.
# @grace.invariant Lint issues remain advisory in the execution loop and do not change source-of-truth semantics.
from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from grace.models import GraceBlockMetadata, GraceFileModel


PLACEHOLDER_RE = re.compile(r"^(?:todo|tbd|n/?a|none|placeholder|fixme|\.{3,})$", re.IGNORECASE)
SHORT_BELIEF_RE = re.compile(r"^(?:unknown|unclear|maybe|temporary|heuristic|default)$", re.IGNORECASE)

MAX_BLOCK_LINE_SPAN = 40
MAX_TEXT_LENGTH = 240
MIN_STRONG_BELIEF_LENGTH = 24
MIN_INVARIANTS_FOR_COMPLEX_MODULE = 2


# @grace.anchor grace.linter.LintSeverity
# @grace.complexity 1
class LintSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


# @grace.anchor grace.linter.LintIssueCode
# @grace.complexity 1
class LintIssueCode(str, Enum):
    LARGE_BLOCK = "large_block"
    WEAK_BELIEF = "weak_belief"
    WEAK_MODULE_TEXT = "weak_module_text"
    LONG_TEXT = "long_text"
    DUPLICATE_LINK = "duplicate_link"
    TOO_FEW_INVARIANTS = "too_few_invariants"
    UNTRACKED_ARTIFACT = "untracked_artifact"


# @grace.anchor grace.linter.LintIssue
# @grace.complexity 1
class LintIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: LintIssueCode
    severity: LintSeverity
    message: str = Field(min_length=1)
    path: Path | None = None
    module_id: str | None = None
    anchor_id: str | None = None


# @grace.anchor grace.linter.LintSuccess
# @grace.complexity 1
class LintSuccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[True] = True
    scope: Literal["file", "project"]


# @grace.anchor grace.linter.LintFailure
# @grace.complexity 1
class LintFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[False] = False
    scope: Literal["file", "project"]
    issues: tuple[LintIssue, ...] = Field(min_length=1)


LintResult = LintSuccess | LintFailure


# @grace.anchor grace.linter.lint_file
# @grace.complexity 2
# @grace.links grace.linter._lint_file
def lint_file(grace_file: GraceFileModel) -> LintResult:
    issues = _lint_file(grace_file)
    if issues:
        return LintFailure(scope="file", issues=tuple(issues))
    return LintSuccess(scope="file")


# @grace.anchor grace.linter.lint_project
# @grace.complexity 4
# @grace.links grace.linter._lint_file, grace.artifact_hygiene.discover_unignored_artifact_paths
def lint_project(grace_files: list[GraceFileModel] | tuple[GraceFileModel, ...]) -> LintResult:
    import os

    from grace.artifact_hygiene import discover_unignored_artifact_paths

    if not grace_files:
        return LintSuccess(scope="project")

    issues: list[LintIssue] = []
    for grace_file in grace_files:
        issues.extend(_lint_file(grace_file))

    scope_root = Path(os.path.commonpath([str(grace_file.path.parent) for grace_file in grace_files]))
    for artifact_path in discover_unignored_artifact_paths(scope_root):
        issues.append(
            LintIssue(
                code=LintIssueCode.UNTRACKED_ARTIFACT,
                severity=LintSeverity.WARNING,
                message=(
                    f"derived artifact {artifact_path.name!r} is present under {scope_root} and should either be cleaned "
                    "or ignored in .gitignore"
                ),
                path=artifact_path,
            )
        )

    if issues:
        return LintFailure(scope="project", issues=tuple(issues))
    return LintSuccess(scope="project")


# @grace.anchor grace.linter._lint_file
# @grace.complexity 4
# @grace.links grace.linter._lint_module_text, grace.linter._lint_block
def _lint_file(grace_file: GraceFileModel) -> list[LintIssue]:
    issues: list[LintIssue] = []
    module_id = grace_file.module.module_id

    issues.extend(_lint_module_text(grace_file))

    if any(block.complexity >= 6 for block in grace_file.blocks) and len(grace_file.module.invariants) < MIN_INVARIANTS_FOR_COMPLEX_MODULE:
        issues.append(
            LintIssue(
                code=LintIssueCode.TOO_FEW_INVARIANTS,
                severity=LintSeverity.WARNING,
                message=(
                    f"module {module_id!r} contains complex blocks but only {len(grace_file.module.invariants)} invariant(s); "
                    f"consider at least {MIN_INVARIANTS_FOR_COMPLEX_MODULE}"
                ),
                path=grace_file.path,
                module_id=module_id,
            )
        )

    for block in grace_file.blocks:
        issues.extend(_lint_block(grace_file, block))

    return issues


# @grace.anchor grace.linter._lint_module_text
# @grace.complexity 4
def _lint_module_text(grace_file: GraceFileModel) -> list[LintIssue]:
    issues: list[LintIssue] = []
    module_id = grace_file.module.module_id
    module_fields = {
        "purpose": grace_file.module.purpose,
        "interfaces": grace_file.module.interfaces,
    }

    for field_name, value in module_fields.items():
        normalized = _normalize_text(value)
        if _looks_placeholder(normalized):
            issues.append(
                LintIssue(
                    code=LintIssueCode.WEAK_MODULE_TEXT,
                    severity=LintSeverity.WARNING,
                    message=f"module {field_name} looks like a placeholder and should be made more informative",
                    path=grace_file.path,
                    module_id=module_id,
                )
            )
        if len(normalized) > MAX_TEXT_LENGTH:
            issues.append(
                LintIssue(
                    code=LintIssueCode.LONG_TEXT,
                    severity=LintSeverity.WARNING,
                    message=f"module {field_name} is longer than {MAX_TEXT_LENGTH} characters and may reduce machine utility",
                    path=grace_file.path,
                    module_id=module_id,
                )
            )

    for invariant in grace_file.module.invariants:
        normalized = _normalize_text(invariant)
        if _looks_placeholder(normalized):
            issues.append(
                LintIssue(
                    code=LintIssueCode.WEAK_MODULE_TEXT,
                    severity=LintSeverity.WARNING,
                    message="module invariant looks like a placeholder and should be made more informative",
                    path=grace_file.path,
                    module_id=module_id,
                )
            )
        if len(normalized) > MAX_TEXT_LENGTH:
            issues.append(
                LintIssue(
                    code=LintIssueCode.LONG_TEXT,
                    severity=LintSeverity.WARNING,
                    message=f"module invariant is longer than {MAX_TEXT_LENGTH} characters and may reduce machine utility",
                    path=grace_file.path,
                    module_id=module_id,
                )
            )

    return issues


# @grace.anchor grace.linter._lint_block
# @grace.complexity 5
def _lint_block(grace_file: GraceFileModel, block: GraceBlockMetadata) -> list[LintIssue]:
    issues: list[LintIssue] = []
    module_id = grace_file.module.module_id
    line_span = (block.line_end - block.line_start) + 1

    if line_span > MAX_BLOCK_LINE_SPAN:
        issues.append(
            LintIssue(
                code=LintIssueCode.LARGE_BLOCK,
                severity=LintSeverity.WARNING,
                message=(
                    f"block {block.anchor_id!r} spans {line_span} lines; consider splitting for LLM-friendly granularity"
                ),
                path=grace_file.path,
                module_id=module_id,
                anchor_id=block.anchor_id,
            )
        )

    if len(block.links) != len(set(block.links)):
        issues.append(
            LintIssue(
                code=LintIssueCode.DUPLICATE_LINK,
                severity=LintSeverity.WARNING,
                message=f"block {block.anchor_id!r} contains duplicate links",
                path=grace_file.path,
                module_id=module_id,
                anchor_id=block.anchor_id,
            )
        )

    if block.belief is not None:
        normalized_belief = _normalize_text(block.belief)
        if block.complexity >= 6 and _is_weak_belief(normalized_belief):
            issues.append(
                LintIssue(
                    code=LintIssueCode.WEAK_BELIEF,
                    severity=LintSeverity.WARNING,
                    message=f"belief for block {block.anchor_id!r} is too weak for a complex block",
                    path=grace_file.path,
                    module_id=module_id,
                    anchor_id=block.anchor_id,
                )
            )
        if len(normalized_belief) > MAX_TEXT_LENGTH:
            issues.append(
                LintIssue(
                    code=LintIssueCode.LONG_TEXT,
                    severity=LintSeverity.WARNING,
                    message=f"belief for block {block.anchor_id!r} is longer than {MAX_TEXT_LENGTH} characters",
                    path=grace_file.path,
                    module_id=module_id,
                    anchor_id=block.anchor_id,
                )
            )

    return issues


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _looks_placeholder(value: str) -> bool:
    return not value or bool(PLACEHOLDER_RE.fullmatch(value))


def _is_weak_belief(value: str) -> bool:
    return (not value) or len(value) < MIN_STRONG_BELIEF_LENGTH or bool(SHORT_BELIEF_RE.fullmatch(value)) or _looks_placeholder(value)


__all__ = [
    "LintFailure",
    "LintIssue",
    "LintIssueCode",
    "LintResult",
    "LintSeverity",
    "LintSuccess",
    "lint_file",
    "lint_project",
]
