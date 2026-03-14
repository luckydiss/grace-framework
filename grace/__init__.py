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
# @grace.complexity 2
# @grace.belief Public exports should make declarative extension layers visible to agents, otherwise new language and construct work still requires internal-module spelunking.
def _public_api() -> tuple[str, ...]:
    return (
        "AdapterEval",
        "AdapterGap",
        "AdapterProbe",
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
        "GraceConstructPack",
        "GraceFileClass",
        "GraceFileModel",
        "GraceFilePolicy",
        "GraceFilePolicyVerdict",
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
        "apply_construct_packs",
        "apply_patch_plan",
        "build_anchor_neighbors",
        "build_file_map",
        "build_plan_skeleton",
        "build_treesitter_pack",
        "build_project_map",
        "collect_adapter_gaps",
        "collect_patch_targets",
        "evaluate_adapter_surface",
        "extract_anchor_annotations",
        "extract_anchor_code",
        "filter_self_anchor",
        "get_construct_pack",
        "get_construct_packs",
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
        "probe_adapter",
        "query_anchor",
        "query_anchors",
        "query_dependents",
        "query_links",
        "query_modules",
        "query_neighbors",
        "query_path",
        "query_path_edge_types",
        "read_anchor_context",
        "register_construct_pack",
        "register_language_pack",
        "resolve_file_policy",
        "try_parse_python_file",
        "validate_file",
        "validate_project",
    )


# @grace.anchor grace.api.__getattr__
# @grace.complexity 6
# @grace.belief Lazy exports should cover both language packs and construct packs so agents can extend coverage through one consistent public surface instead of internal registry imports.
def __getattr__(name: str) -> object:
    if name in {
        "FallbackTextAdapter",
        "GoAdapter",
        "GraceConstructPack",
        "GraceFileClass",
        "GraceFilePolicy",
        "GraceFilePolicyVerdict",
        "GraceLanguageAdapter",
        "GraceLanguagePack",
        "GraceLanguagePackStatus",
        "PythonAdapter",
        "TreeSitterAdapterBase",
        "TreeSitterBlockQuerySpec",
        "TreeSitterLanguageSpec",
        "TypeScriptAdapter",
        "apply_construct_packs",
        "build_treesitter_pack",
        "get_construct_pack",
        "get_construct_packs",
        "get_language_adapter_for_path",
        "get_language_pack",
        "get_language_pack_for_path",
        "get_registered_language_packs",
        "register_construct_pack",
        "register_language_pack",
        "resolve_file_policy",
    }:
        from grace.construct_pack import GraceConstructPack, apply_construct_packs
        from grace.construct_registry import get_construct_pack, get_construct_packs, register_construct_pack
        from grace.fallback_adapter import FallbackTextAdapter
        from grace.file_policy import GraceFileClass, GraceFilePolicy, GraceFilePolicyVerdict, resolve_file_policy
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
            "GraceConstructPack": GraceConstructPack,
            "GraceFileClass": GraceFileClass,
            "GraceFilePolicy": GraceFilePolicy,
            "GraceFilePolicyVerdict": GraceFilePolicyVerdict,
            "GraceLanguageAdapter": GraceLanguageAdapter,
            "GraceLanguagePack": GraceLanguagePack,
            "GraceLanguagePackStatus": GraceLanguagePackStatus,
            "PythonAdapter": PythonAdapter,
            "TreeSitterAdapterBase": TreeSitterAdapterBase,
            "TreeSitterBlockQuerySpec": TreeSitterBlockQuerySpec,
            "TreeSitterLanguageSpec": TreeSitterLanguageSpec,
            "TypeScriptAdapter": TypeScriptAdapter,
            "apply_construct_packs": apply_construct_packs,
            "build_treesitter_pack": build_treesitter_pack,
            "get_construct_pack": get_construct_pack,
            "get_construct_packs": get_construct_packs,
            "get_language_adapter_for_path": get_language_adapter_for_path,
            "get_language_pack": get_language_pack,
            "get_language_pack_for_path": get_language_pack_for_path,
            "get_registered_language_packs": get_registered_language_packs,
            "register_construct_pack": register_construct_pack,
            "register_language_pack": register_language_pack,
            "resolve_file_policy": resolve_file_policy,
        }
        return exported[name]
    if name in {
        "AdapterEval",
        "AdapterGap",
        "AdapterProbe",
        "collect_adapter_gaps",
        "evaluate_adapter_surface",
        "probe_adapter",
    }:
        from grace.adapter_tools import (
            AdapterEval,
            AdapterGap,
            AdapterProbe,
            collect_adapter_gaps,
            evaluate_adapter_surface,
            probe_adapter,
        )

        exported = {
            "AdapterEval": AdapterEval,
            "AdapterGap": AdapterGap,
            "AdapterProbe": AdapterProbe,
            "collect_adapter_gaps": collect_adapter_gaps,
            "evaluate_adapter_surface": evaluate_adapter_surface,
            "probe_adapter": probe_adapter,
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
