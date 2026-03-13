# @grace.module grace.plan
# @grace.purpose Load derived patch plans and apply them as deterministic sequences of semantic block replacements.
# @grace.interfaces load_patch_plan(path)->PatchPlan; apply_patch_plan(plan, *, dry_run=False, preview=False)->ApplyPlanResult; plan_to_dict(plan)->dict
# @grace.invariant Patch plans remain derived artifacts; inline file annotations stay the only source of truth.
# @grace.invariant Plan execution applies entries sequentially and stops at the first patch failure.
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from grace.patcher import PatchFailure, PatchResult, patch_block

PATCH_PLAN_VERSION = "v1"


# @grace.anchor grace.plan.PatchPlanOperation
# @grace.complexity 1
class PatchPlanOperation(str, Enum):
    REPLACE_BLOCK = "replace_block"


# @grace.anchor grace.plan.PatchPlanEntry
# @grace.complexity 3
class PatchPlanEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    anchor_id: str = Field(min_length=1)
    operation: PatchPlanOperation = PatchPlanOperation.REPLACE_BLOCK
    replacement_file: Path | None = None
    replacement_source: str | None = None

    # @grace.anchor grace.plan.PatchPlanEntry._validate_replacement_locator
    # @grace.complexity 2
    @model_validator(mode="after")
    def _validate_replacement_locator(self) -> "PatchPlanEntry":
        provided_count = int(self.replacement_file is not None) + int(self.replacement_source is not None)
        if provided_count != 1:
            raise ValueError("exactly one of replacement_file or replacement_source must be provided")
        return self


# @grace.anchor grace.plan.PatchPlan
# @grace.complexity 1
class PatchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    grace_version: Literal[PATCH_PLAN_VERSION] = PATCH_PLAN_VERSION
    entries: tuple[PatchPlanEntry, ...] = Field(min_length=1)


# @grace.anchor grace.plan.AppliedPatchEntry
# @grace.complexity 1
class AppliedPatchEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    index: int = Field(ge=0)
    path: Path
    anchor_id: str = Field(min_length=1)
    operation: PatchPlanOperation
    result: PatchResult


# @grace.anchor grace.plan.ApplyPlanFailureStage
# @grace.complexity 1
class ApplyPlanFailureStage(str, Enum):
    ENTRY_FAILURE = "entry_failure"


# @grace.anchor grace.plan.ApplyPlanSuccess
# @grace.complexity 2
class ApplyPlanSuccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[True] = True
    plan: PatchPlan
    dry_run: bool = False
    preview: bool = False
    applied_count: int = Field(ge=0)
    entry_count: int = Field(ge=1)
    entries: tuple[AppliedPatchEntry, ...]


# @grace.anchor grace.plan.ApplyPlanFailure
# @grace.complexity 2
class ApplyPlanFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[False] = False
    plan: PatchPlan
    dry_run: bool = False
    preview: bool = False
    stage: ApplyPlanFailureStage
    applied_count: int = Field(ge=0)
    entry_count: int = Field(ge=1)
    failed_index: int = Field(ge=0)
    failed_path: Path
    failed_anchor_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    entries: tuple[AppliedPatchEntry, ...] = Field(min_length=1)


ApplyPlanResult = ApplyPlanSuccess | ApplyPlanFailure


# @grace.anchor grace.plan.load_patch_plan
# @grace.complexity 4
# @grace.links grace.plan._resolve_plan_paths
def load_patch_plan(path: str | Path) -> PatchPlan:
    plan_path = Path(path)
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    plan = PatchPlan.model_validate(payload)
    return _resolve_plan_paths(plan, base_dir=plan_path.parent)


# @grace.anchor grace.plan.apply_patch_plan
# @grace.complexity 8
# @grace.belief Transactional plan execution should simulate patches against a temporary project mirror first, so entry-level validation still reuses patch_block semantics while real repository writes happen only after every step has already passed parse and validation in the staged snapshot. The mirror itself must live under the writable project root so dry-run and real execution behave identically across relative, absolute, and Path-based plan entries without depending on host temp-directory permissions.
# @grace.links grace.patcher.patch_block, grace.plan._load_replacement_source
def apply_patch_plan(plan: PatchPlan, *, dry_run: bool = False, preview: bool = False) -> ApplyPlanResult:
    import os
    import shutil
    import uuid

    from grace.patcher import _discover_project_paths

    applied_entries: list[AppliedPatchEntry] = []
    effective_dry_run = dry_run or preview
    resolved_entry_paths = tuple(Path(entry.path).expanduser().resolve() for entry in plan.entries)
    touched_paths = tuple(dict.fromkeys(resolved_entry_paths))
    original_texts = {path: path.read_text(encoding="utf-8") for path in touched_paths}

    discovered_project_paths: set[Path] = set()
    for touched_path in touched_paths:
        for discovered_path in _discover_project_paths(touched_path.parent):
            discovered_project_paths.add(discovered_path.resolve())
    for touched_path in touched_paths:
        discovered_project_paths.add(touched_path)

    common_root = Path(os.path.commonpath([str(path.parent) for path in discovered_project_paths]))

    def normalize_patch_result(result: PatchResult, *, original_path: Path) -> PatchResult:
        if isinstance(result, PatchFailure):
            return result.model_copy(update={"path": original_path, "dry_run": effective_dry_run})
        return result.model_copy(
            update={
                "path": original_path,
                "dry_run": effective_dry_run,
                "file": result.file.model_copy(update={"path": original_path}),
            }
        )

    temp_root = common_root / f".grace_plan_{uuid.uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=False)
    temp_path_map: dict[Path, Path] = {}

    try:
        for discovered_path in sorted(discovered_project_paths, key=lambda item: str(item)):
            relative_path = discovered_path.relative_to(common_root)
            temp_path = temp_root / relative_path
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(discovered_path, temp_path)
            temp_path_map[discovered_path] = temp_path

        for index, entry in enumerate(plan.entries):
            replacement_source = _load_replacement_source(entry)
            original_path = resolved_entry_paths[index]
            temp_path = temp_path_map[original_path]
            patch_result = normalize_patch_result(
                patch_block(temp_path, entry.anchor_id, replacement_source, dry_run=False),
                original_path=original_path,
            )
            applied_entries.append(
                AppliedPatchEntry(
                    index=index,
                    path=original_path,
                    anchor_id=entry.anchor_id,
                    operation=entry.operation,
                    result=patch_result,
                )
            )
            if isinstance(patch_result, PatchFailure):
                return ApplyPlanFailure(
                    plan=plan.model_dump(mode="python"),
                    dry_run=effective_dry_run,
                    preview=preview,
                    stage=ApplyPlanFailureStage.ENTRY_FAILURE,
                    applied_count=index,
                    entry_count=len(plan.entries),
                    failed_index=index,
                    failed_path=original_path,
                    failed_anchor_id=entry.anchor_id,
                    message=f"patch plan failed at entry {index}",
                    entries=tuple(applied_entries),
                )

        if effective_dry_run:
            return ApplyPlanSuccess(
                plan=plan.model_dump(mode="python"),
                dry_run=True,
                preview=preview,
                applied_count=len(plan.entries),
                entry_count=len(plan.entries),
                entries=tuple(applied_entries),
            )

        written_paths: list[Path] = []
        try:
            for original_path in touched_paths:
                original_path.write_text(temp_path_map[original_path].read_text(encoding="utf-8"), encoding="utf-8")
                written_paths.append(original_path)
        except OSError as exc:
            for rollback_path in reversed(written_paths):
                rollback_path.write_text(original_texts[rollback_path], encoding="utf-8")
            failed_path = original_path
            failed_index = max(
                index for index, candidate_path in enumerate(resolved_entry_paths) if candidate_path == failed_path
            )
            failed_anchor_id = plan.entries[failed_index].anchor_id
            return ApplyPlanFailure(
                plan=plan.model_dump(mode="python"),
                dry_run=False,
                preview=preview,
                stage=ApplyPlanFailureStage.ENTRY_FAILURE,
                applied_count=0,
                entry_count=len(plan.entries),
                failed_index=failed_index,
                failed_path=failed_path,
                failed_anchor_id=failed_anchor_id,
                message=f"transactional commit failed for {failed_path}: {exc}",
                entries=tuple(applied_entries),
            )

        return ApplyPlanSuccess(
            plan=plan.model_dump(mode="python"),
            dry_run=False,
            preview=preview,
            applied_count=len(plan.entries),
            entry_count=len(plan.entries),
            entries=tuple(applied_entries),
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


# @grace.anchor grace.plan.plan_to_dict
# @grace.complexity 1
def plan_to_dict(plan: PatchPlan) -> dict:
    return plan.model_dump(mode="json")


# @grace.anchor grace.plan._resolve_plan_paths
# @grace.complexity 3
def _resolve_plan_paths(plan: PatchPlan, *, base_dir: Path) -> PatchPlan:
    resolved_entries = []
    for entry in plan.entries:
        resolved_entries.append(
            entry.model_copy(
                update={
                    "path": _resolve_path(entry.path, base_dir),
                    "replacement_file": _resolve_path(entry.replacement_file, base_dir)
                    if entry.replacement_file is not None
                    else None,
                }
            )
        )
    return plan.model_copy(update={"entries": tuple(resolved_entries)})


def _resolve_path(path: Path, base_dir: Path) -> Path:
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


# @grace.anchor grace.plan._load_replacement_source
# @grace.complexity 2
def _load_replacement_source(entry: PatchPlanEntry) -> str:
    if entry.replacement_source is not None:
        return entry.replacement_source
    assert entry.replacement_file is not None
    return entry.replacement_file.read_text(encoding="utf-8")


__all__ = [
    "ApplyPlanFailure",
    "ApplyPlanFailureStage",
    "ApplyPlanResult",
    "ApplyPlanSuccess",
    "AppliedPatchEntry",
    "PATCH_PLAN_VERSION",
    "PatchPlan",
    "PatchPlanEntry",
    "PatchPlanOperation",
    "apply_patch_plan",
    "load_patch_plan",
    "plan_to_dict",
]
