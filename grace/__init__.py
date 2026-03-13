# @grace.module grace.api
# @grace.purpose Re-export the stable GRACE public API for library callers and shell-driven tooling.
# @grace.interfaces import from grace -> parser, validator, linter, map, query, impact, patch, and plan APIs
# @grace.invariant Package exports remain a thin derived layer over core modules and never become a second source of truth.
# @grace.invariant The exported symbol manifest should stay patchable through a single semantic block under current GRACE grammar limits.
from grace.impact import ImpactLookupError, ImpactSummary, impact_direct, impact_summary, impact_transitive
from grace.linter import (
    LintFailure,
    LintIssue,
    LintIssueCode,
    LintResult,
    LintSeverity,
    LintSuccess,
    lint_file,
    lint_project,
)
from grace.map import (
    GRACE_MAP_VERSION,
    GraceMap,
    GraceMapAnchor,
    GraceMapEdge,
    GraceMapModule,
    build_file_map,
    build_project_map,
    map_to_dict,
)
from grace.models import (
    BlockKind,
    GraceBlockMetadata,
    GraceFileModel,
    GraceModuleMetadata,
    GraceParseFailure,
    GraceParseIssue,
    GraceParseResult,
    GraceParseSuccess,
    ParseErrorCode,
)
from grace.patcher import (
    PatchFailure,
    PatchFailureStage,
    PatchResult,
    PatchStepResult,
    PatchStepStatus,
    PatchSuccess,
    patch_block,
)
from grace.parser import GraceParseError, parse_python_file, try_parse_python_file
from grace.plan import (
    PATCH_PLAN_VERSION,
    ApplyPlanFailure,
    ApplyPlanFailureStage,
    ApplyPlanResult,
    ApplyPlanSuccess,
    AppliedPatchEntry,
    PatchPlan,
    PatchPlanEntry,
    PatchPlanOperation,
    apply_patch_plan,
    load_patch_plan,
    plan_to_dict,
)
from grace.query import (
    QueryLookupError,
    query_anchor,
    query_anchors,
    query_dependents,
    query_links,
    query_modules,
    query_neighbors,
)
from grace.validator import (
    ValidationFailure,
    ValidationIssue,
    ValidationIssueCode,
    ValidationResult,
    ValidationSuccess,
    validate_file,
    validate_project,
)


# @grace.anchor grace.api._public_api
# @grace.complexity 3
def _public_api() -> tuple[str, ...]:
    return (
        "ApplyPlanFailure",
        "ApplyPlanFailureStage",
        "ApplyPlanResult",
        "ApplyPlanSuccess",
        "AppliedPatchEntry",
        "BlockKind",
        "GRACE_MAP_VERSION",
        "GraceBlockMetadata",
        "GraceFileModel",
        "GraceMap",
        "GraceMapAnchor",
        "GraceMapEdge",
        "GraceMapModule",
        "GraceModuleMetadata",
        "GraceParseError",
        "GraceParseFailure",
        "GraceParseIssue",
        "GraceParseResult",
        "GraceParseSuccess",
        "ImpactLookupError",
        "ImpactSummary",
        "LintFailure",
        "LintIssue",
        "LintIssueCode",
        "LintResult",
        "LintSeverity",
        "LintSuccess",
        "PATCH_PLAN_VERSION",
        "ParseErrorCode",
        "PatchFailure",
        "PatchFailureStage",
        "PatchPlan",
        "PatchPlanEntry",
        "PatchPlanOperation",
        "PatchResult",
        "PatchStepResult",
        "PatchStepStatus",
        "PatchSuccess",
        "QueryLookupError",
        "ValidationFailure",
        "ValidationIssue",
        "ValidationIssueCode",
        "ValidationResult",
        "ValidationSuccess",
        "apply_patch_plan",
        "build_file_map",
        "build_project_map",
        "impact_direct",
        "impact_summary",
        "impact_transitive",
        "lint_file",
        "lint_project",
        "load_patch_plan",
        "map_to_dict",
        "parse_python_file",
        "patch_block",
        "plan_to_dict",
        "query_anchor",
        "query_anchors",
        "query_dependents",
        "query_links",
        "query_modules",
        "query_neighbors",
        "try_parse_python_file",
        "validate_file",
        "validate_project",
    )


__all__ = list(_public_api())
