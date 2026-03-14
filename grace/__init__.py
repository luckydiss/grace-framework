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
# @grace.complexity 4
def _public_api() -> tuple[str, ...]:
    return (
        "ApplyPlanFailure",
        "ApplyPlanFailureStage",
        "ApplyPlanResult",
        "ApplyPlanSuccess",
        "AppliedPatchEntry",
        "BlockKind",
        "FallbackTextAdapter",
        "GoAdapter",
        "GRACE_MAP_VERSION",
        "GraceBlockMetadata",
        "GraceFileModel",
        "GraceLanguageAdapter",
        "GraceLanguagePack",
        "GraceLanguagePackStatus",
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
        "PatchPlanProposal",
        "PatchResult",
        "PatchStepResult",
        "PatchStepStatus",
        "PatchSuccess",
        "PlannerLookupError",
        "PythonAdapter",
        "QueryLookupError",
        "ReadAnchorContext",
        "ReadLookupError",
        "SuggestedPatchOperation",
        "TreeSitterAdapterBase",
        "TreeSitterBlockQuerySpec",
        "TreeSitterLanguageSpec",
        "TypeScriptAdapter",
        "ValidationFailure",
        "ValidationIssue",
        "ValidationIssueCode",
        "ValidationResult",
        "ValidationSuccess",
        "apply_patch_plan",
        "build_anchor_neighbors",
        "build_file_map",
        "build_plan_skeleton",
        "build_treesitter_pack",
        "build_project_map",
        "collect_patch_targets",
        "extract_anchor_annotations",
        "extract_anchor_code",
        "filter_self_anchor",
        "get_language_adapter_for_path",
        "get_language_pack",
        "get_language_pack_for_path",
        "get_registered_language_packs",
        "impact_direct",
        "impact_summary",
        "impact_transitive",
        "lint_file",
        "lint_project",
        "load_patch_plan",
        "map_to_dict",
        "parse_python_file",
        "patch_block",
        "plan_from_impact",
        "plan_to_dict",
        "query_anchor",
        "query_anchors",
        "query_dependents",
        "query_links",
        "query_modules",
        "query_neighbors",
        "query_path",
        "query_path_edge_types",
        "read_anchor_context",
        "register_language_pack",
        "try_parse_python_file",
        "validate_file",
        "validate_project",
    )


# @grace.anchor grace.api.__getattr__
# @grace.complexity 6
# @grace.belief Public lazy exports should stay centralized around declarative pack and adapter APIs so downstream tooling can introspect extension surfaces without importing unrelated runtime modules eagerly.
def __getattr__(name: str) -> object:
    if name in {
        "FallbackTextAdapter",
        "GoAdapter",
        "GraceLanguageAdapter",
        "GraceLanguagePack",
        "GraceLanguagePackStatus",
        "PythonAdapter",
        "TreeSitterAdapterBase",
        "TreeSitterBlockQuerySpec",
        "TreeSitterLanguageSpec",
        "TypeScriptAdapter",
        "build_treesitter_pack",
        "get_language_adapter_for_path",
        "get_language_pack",
        "get_language_pack_for_path",
        "get_registered_language_packs",
        "register_language_pack",
    }:
        from grace.fallback_adapter import FallbackTextAdapter
        from grace.go_adapter import GoAdapter
        from grace.language_adapter import GraceLanguageAdapter, get_language_adapter_for_path
        from grace.language_pack import GraceLanguagePack, GraceLanguagePackStatus, build_treesitter_pack
        from grace.python_adapter import PythonAdapter
        from grace.spec_registry import (
            get_language_pack,
            get_language_pack_for_path,
            get_registered_language_packs,
            register_language_pack,
        )
        from grace.treesitter_base import (
            TreeSitterAdapterBase,
            TreeSitterBlockQuerySpec,
            TreeSitterLanguageSpec,
        )
        from grace.typescript_adapter import TypeScriptAdapter

        exported = {
            "FallbackTextAdapter": FallbackTextAdapter,
            "GoAdapter": GoAdapter,
            "GraceLanguageAdapter": GraceLanguageAdapter,
            "GraceLanguagePack": GraceLanguagePack,
            "GraceLanguagePackStatus": GraceLanguagePackStatus,
            "PythonAdapter": PythonAdapter,
            "TreeSitterAdapterBase": TreeSitterAdapterBase,
            "TreeSitterBlockQuerySpec": TreeSitterBlockQuerySpec,
            "TreeSitterLanguageSpec": TreeSitterLanguageSpec,
            "TypeScriptAdapter": TypeScriptAdapter,
            "build_treesitter_pack": build_treesitter_pack,
            "get_language_adapter_for_path": get_language_adapter_for_path,
            "get_language_pack": get_language_pack,
            "get_language_pack_for_path": get_language_pack_for_path,
            "get_registered_language_packs": get_registered_language_packs,
            "register_language_pack": register_language_pack,
        }
        return exported[name]
    if name in {
        "query_path",
        "query_path_edge_types",
    }:
        from grace.path_query import query_path, query_path_edge_types

        exported = {
            "query_path": query_path,
            "query_path_edge_types": query_path_edge_types,
        }
        return exported[name]
    if name in {
        "ReadAnchorContext",
        "ReadLookupError",
        "build_anchor_neighbors",
        "extract_anchor_annotations",
        "extract_anchor_code",
        "read_anchor_context",
    }:
        from grace.read import (
            ReadAnchorContext,
            ReadLookupError,
            build_anchor_neighbors,
            extract_anchor_annotations,
            extract_anchor_code,
            read_anchor_context,
        )

        exported = {
            "ReadAnchorContext": ReadAnchorContext,
            "ReadLookupError": ReadLookupError,
            "build_anchor_neighbors": build_anchor_neighbors,
            "extract_anchor_annotations": extract_anchor_annotations,
            "extract_anchor_code": extract_anchor_code,
            "read_anchor_context": read_anchor_context,
        }
        return exported[name]
    if name in {
        "PatchPlanProposal",
        "PlannerLookupError",
        "SuggestedPatchOperation",
        "build_plan_skeleton",
        "collect_patch_targets",
        "filter_self_anchor",
        "plan_from_impact",
    }:
        from grace.planner import (
            PatchPlanProposal,
            PlannerLookupError,
            SuggestedPatchOperation,
            build_plan_skeleton,
            collect_patch_targets,
            filter_self_anchor,
            plan_from_impact,
        )

        exported = {
            "PatchPlanProposal": PatchPlanProposal,
            "PlannerLookupError": PlannerLookupError,
            "SuggestedPatchOperation": SuggestedPatchOperation,
            "build_plan_skeleton": build_plan_skeleton,
            "collect_patch_targets": collect_patch_targets,
            "filter_self_anchor": filter_self_anchor,
            "plan_from_impact": plan_from_impact,
        }
        return exported[name]
    raise AttributeError(f"module 'grace' has no attribute {name!r}")


__all__ = list(_public_api())
