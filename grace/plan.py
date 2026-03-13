from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from grace.patcher import PatchFailure, PatchResult, patch_block

PATCH_PLAN_VERSION = "v1"


class PatchPlanOperation(str, Enum):
    REPLACE_BLOCK = "replace_block"


class PatchPlanEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    anchor_id: str = Field(min_length=1)
    operation: PatchPlanOperation = PatchPlanOperation.REPLACE_BLOCK
    replacement_file: Path | None = None
    replacement_source: str | None = None

    @model_validator(mode="after")
    def _validate_replacement_locator(self) -> "PatchPlanEntry":
        provided_count = int(self.replacement_file is not None) + int(self.replacement_source is not None)
        if provided_count != 1:
            raise ValueError("exactly one of replacement_file or replacement_source must be provided")
        return self


class PatchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    grace_version: Literal[PATCH_PLAN_VERSION] = PATCH_PLAN_VERSION
    entries: tuple[PatchPlanEntry, ...] = Field(min_length=1)


class AppliedPatchEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    index: int = Field(ge=0)
    path: Path
    anchor_id: str = Field(min_length=1)
    operation: PatchPlanOperation
    result: PatchResult


class ApplyPlanFailureStage(str, Enum):
    ENTRY_FAILURE = "entry_failure"


class ApplyPlanSuccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[True] = True
    plan: PatchPlan
    dry_run: bool = False
    preview: bool = False
    applied_count: int = Field(ge=0)
    entry_count: int = Field(ge=1)
    entries: tuple[AppliedPatchEntry, ...]


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


def load_patch_plan(path: str | Path) -> PatchPlan:
    plan_path = Path(path)
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    plan = PatchPlan.model_validate(payload)
    return _resolve_plan_paths(plan, base_dir=plan_path.parent)


def apply_patch_plan(plan: PatchPlan, *, dry_run: bool = False, preview: bool = False) -> ApplyPlanResult:
    applied_entries: list[AppliedPatchEntry] = []
    applied_count = 0
    effective_dry_run = dry_run or preview

    for index, entry in enumerate(plan.entries):
        replacement_source = _load_replacement_source(entry)
        patch_result = patch_block(entry.path, entry.anchor_id, replacement_source, dry_run=effective_dry_run)
        applied_entries.append(
            AppliedPatchEntry(
                index=index,
                path=entry.path,
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
                applied_count=applied_count,
                entry_count=len(plan.entries),
                failed_index=index,
                failed_path=entry.path,
                failed_anchor_id=entry.anchor_id,
                message=f"patch plan failed at entry {index}",
                entries=tuple(applied_entries),
            )
        applied_count += 1

    return ApplyPlanSuccess(
        plan=plan.model_dump(mode="python"),
        dry_run=effective_dry_run,
        preview=preview,
        applied_count=applied_count,
        entry_count=len(plan.entries),
        entries=tuple(applied_entries),
    )


def plan_to_dict(plan: PatchPlan) -> dict:
    return plan.model_dump(mode="json")


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
