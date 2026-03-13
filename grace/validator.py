# @grace.module grace.validator
# @grace.purpose Enforce hard structural and semantic consistency rules over parsed GRACE file models.
# @grace.interfaces validate_file(grace_file)->ValidationResult; validate_project(grace_files)->ValidationResult
# @grace.invariant Validation operates only on parsed GRACE models and never reparses source files.
# @grace.invariant Broken identity, namespace, and link consistency are validator failures rather than linter warnings.
from __future__ import annotations

import re
from collections import Counter
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from grace.models import BlockKind, GraceBlockMetadata, GraceFileModel


SEMANTIC_DOT_PATH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
ALLOWED_KIND_VALUES = {kind.value for kind in BlockKind}


# @grace.anchor grace.validator.ValidationIssueCode
# @grace.complexity 1
class ValidationIssueCode(str, Enum):
    INVALID_MODULE_ID = "invalid_module_id"
    INVALID_ANCHOR_ID = "invalid_anchor_id"
    ANCHOR_MODULE_PREFIX_MISMATCH = "anchor_module_prefix_mismatch"
    SYMBOL_ANCHOR_MISMATCH = "symbol_anchor_mismatch"
    INVALID_METHOD_NAMESPACE = "invalid_method_namespace"
    BROKEN_LINK = "broken_link"
    DUPLICATE_MODULE_ID = "duplicate_module_id"
    DUPLICATE_ANCHOR_ID = "duplicate_anchor_id"
    INVALID_BLOCK_KIND = "invalid_block_kind"
    MISSING_BELIEF = "missing_belief"
    EMPTY_MODULE_FIELD = "empty_module_field"
    EMPTY_INVARIANT = "empty_invariant"


# @grace.anchor grace.validator.ValidationIssue
# @grace.complexity 1
class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ValidationIssueCode
    message: str = Field(min_length=1)
    path: Path | None = None
    module_id: str | None = None
    anchor_id: str | None = None


# @grace.anchor grace.validator.ValidationSuccess
# @grace.complexity 1
class ValidationSuccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[True] = True
    scope: Literal["file", "project"]


# @grace.anchor grace.validator.ValidationFailure
# @grace.complexity 1
class ValidationFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[False] = False
    scope: Literal["file", "project"]
    issues: tuple[ValidationIssue, ...] = Field(min_length=1)


ValidationResult = ValidationSuccess | ValidationFailure


# @grace.anchor grace.validator.validate_file
# @grace.complexity 3
# @grace.links grace.validator._validate_file_semantics
def validate_file(grace_file: GraceFileModel) -> ValidationResult:
    issues = _validate_file_semantics(grace_file, available_anchor_ids={block.anchor_id for block in grace_file.blocks})
    if issues:
        return ValidationFailure(scope="file", issues=tuple(issues))
    return ValidationSuccess(scope="file")


# @grace.anchor grace.validator.validate_project
# @grace.complexity 6
# @grace.belief Project validation must aggregate duplicate identities and cross-file link scope before delegating per-file semantic checks so repo-level consistency errors are reported without reparsing or graph-specific infrastructure.
# @grace.links grace.validator._validate_file_semantics
def validate_project(grace_files: list[GraceFileModel] | tuple[GraceFileModel, ...]) -> ValidationResult:
    issues: list[ValidationIssue] = []
    module_counter = Counter(file.module.module_id for file in grace_files)
    anchor_counter = Counter(block.anchor_id for file in grace_files for block in file.blocks)
    available_anchor_ids = set(anchor_counter)

    for module_id, count in module_counter.items():
        if count > 1:
            for grace_file in grace_files:
                if grace_file.module.module_id == module_id:
                    issues.append(
                        ValidationIssue(
                            code=ValidationIssueCode.DUPLICATE_MODULE_ID,
                            message=f"duplicate module_id {module_id!r} in project",
                            path=grace_file.path,
                            module_id=module_id,
                        )
                    )

    for anchor_id, count in anchor_counter.items():
        if count > 1:
            for grace_file in grace_files:
                for block in grace_file.blocks:
                    if block.anchor_id == anchor_id:
                        issues.append(
                            ValidationIssue(
                                code=ValidationIssueCode.DUPLICATE_ANCHOR_ID,
                                message=f"duplicate anchor_id {anchor_id!r} in project",
                                path=grace_file.path,
                                module_id=grace_file.module.module_id,
                                anchor_id=anchor_id,
                            )
                        )

    for grace_file in grace_files:
        issues.extend(_validate_file_semantics(grace_file, available_anchor_ids=available_anchor_ids))

    if issues:
        return ValidationFailure(scope="project", issues=tuple(issues))
    return ValidationSuccess(scope="project")


# @grace.anchor grace.validator._validate_file_semantics
# @grace.complexity 5
# @grace.links grace.validator._validate_block
def _validate_file_semantics(grace_file: GraceFileModel, available_anchor_ids: set[str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    module_id = grace_file.module.module_id
    local_anchor_counter = Counter(block.anchor_id for block in grace_file.blocks)

    if not _is_non_empty_text(module_id) or not _is_semantic_dot_path(module_id):
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.INVALID_MODULE_ID,
                message=f"module_id must be a non-empty semantic dot-path, got {module_id!r}",
                path=grace_file.path,
                module_id=module_id,
            )
        )

    if not _is_non_empty_text(grace_file.module.purpose):
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.EMPTY_MODULE_FIELD,
                message="module purpose must be non-empty and not whitespace-only",
                path=grace_file.path,
                module_id=module_id,
            )
        )

    if not _is_non_empty_text(grace_file.module.interfaces):
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.EMPTY_MODULE_FIELD,
                message="module interfaces must be non-empty and not whitespace-only",
                path=grace_file.path,
                module_id=module_id,
            )
        )

    for invariant in grace_file.module.invariants:
        if not _is_non_empty_text(invariant):
            issues.append(
                ValidationIssue(
                    code=ValidationIssueCode.EMPTY_INVARIANT,
                    message="module invariants must be non-empty and not whitespace-only",
                    path=grace_file.path,
                    module_id=module_id,
                )
            )

    for anchor_id, count in local_anchor_counter.items():
        if count > 1:
            issues.append(
                ValidationIssue(
                    code=ValidationIssueCode.DUPLICATE_ANCHOR_ID,
                    message=f"duplicate anchor_id {anchor_id!r} in file",
                    path=grace_file.path,
                    module_id=module_id,
                    anchor_id=anchor_id,
                )
            )

    for block in grace_file.blocks:
        issues.extend(_validate_block(grace_file, block, available_anchor_ids))

    return issues


# @grace.anchor grace.validator._validate_block
# @grace.complexity 6
# @grace.belief Block validation centralizes namespace, symbol-tail, belief-threshold, and link checks so file-level and project-level validation share the same hard consistency rules across scopes.
def _validate_block(
    grace_file: GraceFileModel,
    block: GraceBlockMetadata,
    available_anchor_ids: set[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    module_id = grace_file.module.module_id
    kind_value = block.kind.value if isinstance(block.kind, BlockKind) else str(block.kind)

    if kind_value not in ALLOWED_KIND_VALUES:
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.INVALID_BLOCK_KIND,
                message=f"block kind must be one of {sorted(ALLOWED_KIND_VALUES)}, got {kind_value!r}",
                path=grace_file.path,
                module_id=module_id,
                anchor_id=block.anchor_id,
            )
        )

    if not _is_non_empty_text(block.anchor_id) or not _is_semantic_dot_path(block.anchor_id):
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.INVALID_ANCHOR_ID,
                message=f"anchor_id must be a non-empty semantic dot-path, got {block.anchor_id!r}",
                path=grace_file.path,
                module_id=module_id,
                anchor_id=block.anchor_id,
            )
        )

    if _is_non_empty_text(module_id) and _is_non_empty_text(block.anchor_id):
        expected_prefix = f"{module_id}."
        if not block.anchor_id.startswith(expected_prefix):
            issues.append(
                ValidationIssue(
                    code=ValidationIssueCode.ANCHOR_MODULE_PREFIX_MISMATCH,
                    message=f"anchor_id {block.anchor_id!r} must start with module_id {module_id!r}",
                    path=grace_file.path,
                    module_id=module_id,
                    anchor_id=block.anchor_id,
                )
            )

    if not _tail_matches_symbol_name(block):
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.SYMBOL_ANCHOR_MISMATCH,
                message=f"anchor tail for {block.anchor_id!r} must match symbol_name {block.symbol_name!r}",
                path=grace_file.path,
                module_id=module_id,
                anchor_id=block.anchor_id,
            )
        )

    if block.kind == BlockKind.METHOD:
        expected_method_anchor = f"{module_id}.{block.qualified_name}"
        if block.anchor_id != expected_method_anchor:
            # This is reliable with current parser output because qualified_name already captures Class.method.
            issues.append(
                ValidationIssue(
                    code=ValidationIssueCode.INVALID_METHOD_NAMESPACE,
                    message=(
                        f"method anchor_id {block.anchor_id!r} must equal "
                        f"{expected_method_anchor!r} for qualified_name {block.qualified_name!r}"
                    ),
                    path=grace_file.path,
                    module_id=module_id,
                    anchor_id=block.anchor_id,
                )
            )

    if block.complexity >= 6 and not _is_non_empty_text(block.belief):
        issues.append(
            ValidationIssue(
                code=ValidationIssueCode.MISSING_BELIEF,
                message="belief must be non-empty and not whitespace-only when complexity >= 6",
                path=grace_file.path,
                module_id=module_id,
                anchor_id=block.anchor_id,
            )
        )

    for link_target in block.links:
        if link_target not in available_anchor_ids:
            issues.append(
                ValidationIssue(
                    code=ValidationIssueCode.BROKEN_LINK,
                    message=f"link target {link_target!r} does not exist in validation scope",
                    path=grace_file.path,
                    module_id=module_id,
                    anchor_id=block.anchor_id,
                )
            )

    return issues


def _is_non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_semantic_dot_path(value: str) -> bool:
    return bool(SEMANTIC_DOT_PATH_RE.fullmatch(value))


def _tail_matches_symbol_name(block: GraceBlockMetadata) -> bool:
    if not _is_non_empty_text(block.anchor_id) or not _is_non_empty_text(block.symbol_name):
        return False
    tail = block.anchor_id.rsplit(".", 1)[-1]
    return tail == block.symbol_name


__all__ = [
    "ValidationFailure",
    "ValidationIssue",
    "ValidationIssueCode",
    "ValidationResult",
    "ValidationSuccess",
    "validate_file",
    "validate_project",
]
