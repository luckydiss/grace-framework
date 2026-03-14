# @grace.module grace.adapter_tools
# @grace.purpose Provide deterministic adapter diagnostics so agents can inspect coverage gaps in unfamiliar repositories before attempting bootstrap or framework extension work.
# @grace.interfaces probe_adapter, collect_adapter_gaps, evaluate_adapter_surface, AdapterProbe, AdapterGap, AdapterEval
# @grace.invariant Adapter diagnostics must remain derived-only and deterministic; they may classify files and registry coverage, but they do not change parser, bootstrap, or patch semantics.

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from grace.artifact_hygiene import is_ignored_artifact_dir_name
from grace.file_policy import GraceFilePolicyVerdict, resolve_file_policy
from grace.repo_config import candidate_in_repo_scope, load_repo_config
from grace.spec_registry import get_language_pack_for_path, get_registered_language_packs

IGNORED_ADAPTER_DIR_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        ".tox",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".idea",
        ".vscode",
        "node_modules",
    }
)


# @grace.anchor grace.adapter_tools.AdapterProbe
# @grace.complexity 2
class AdapterProbe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    exists: bool
    is_file: bool
    language_name: str | None = None
    pack_status: str | None = None
    adapter_family: str | None = None
    adapter_class_name: str | None = None
    bootstrap_safe: bool = False
    file_class: str
    policy_verdict: str
    reason: str
    matched_pattern: str | None = None


# @grace.anchor grace.adapter_tools.AdapterGap
# @grace.complexity 2
class AdapterGap(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    gap_kind: str
    language_name: str | None = None
    policy_verdict: str
    reason: str
    matched_pattern: str | None = None


# @grace.anchor grace.adapter_tools.AdapterEval
# @grace.complexity 2
class AdapterEval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requested_path: Path
    file_count: int
    file_class_counts: dict[str, int]
    verdict_counts: dict[str, int]
    language_counts: dict[str, int]
    gap_counts: dict[str, int]
    gaps: tuple[AdapterGap, ...] = Field(default_factory=tuple)


def _supported_class_name(path: Path) -> str | None:
    from grace.language_adapter import get_language_adapter_for_path

    try:
        adapter = get_language_adapter_for_path(path)
    except ValueError:
        return None
    return type(adapter).__name__


def _walk_policy_candidates(path: Path) -> tuple[Path, ...]:
    resolved_path = path.expanduser().resolve()
    repo_config = load_repo_config(resolved_path)

    if resolved_path.is_file():
        return (resolved_path,)

    discovered_paths: list[Path] = []
    for current_root, dir_names, file_names in os.walk(resolved_path):
        dir_names[:] = [
            dir_name
            for dir_name in dir_names
            if dir_name not in IGNORED_ADAPTER_DIR_NAMES
            and not dir_name.endswith(".egg-info")
            and not is_ignored_artifact_dir_name(dir_name)
        ]

        root_path = Path(current_root)
        for file_name in sorted(file_names):
            candidate_path = (root_path / file_name).resolve()
            if not candidate_in_repo_scope(repo_config, resolved_path, candidate_path):
                continue
            try:
                candidate_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            discovered_paths.append(candidate_path)

    discovered_paths.sort(key=lambda candidate: candidate.relative_to(resolved_path).as_posix())
    return tuple(discovered_paths)


def _gap_kind_for_probe(probe: AdapterProbe) -> str | None:
    if probe.policy_verdict == GraceFilePolicyVerdict.PREVIEW_ONLY.value:
        return "preview_only"
    if probe.policy_verdict == GraceFilePolicyVerdict.UNSUPPORTED.value:
        return "unsupported"
    if probe.policy_verdict == GraceFilePolicyVerdict.IGNORE.value:
        return "ignored"
    if probe.adapter_class_name == "FallbackTextAdapter":
        return "fallback"
    return None


# @grace.anchor grace.adapter_tools.probe_adapter
# @grace.complexity 4
# @grace.belief Repository onboarding only scales if the agent can ask one deterministic question about any file and get both adapter-selection and file-policy answers back without reading the whole tree.
# @grace.links grace.file_policy.resolve_file_policy
def probe_adapter(path: str | Path) -> AdapterProbe:
    candidate_path = Path(path).expanduser().resolve()
    exists = candidate_path.exists()
    repo_config = load_repo_config(candidate_path)
    policy = resolve_file_policy(candidate_path, repo_config)
    pack = get_language_pack_for_path(candidate_path)

    adapter_class_name: str | None = None
    if exists and candidate_path.is_file() and pack is not None:
        adapter_class_name = _supported_class_name(candidate_path)

    return AdapterProbe(
        path=candidate_path,
        exists=exists,
        is_file=candidate_path.is_file(),
        language_name=pack.language_name if pack is not None else None,
        pack_status=pack.status.value if pack is not None else None,
        adapter_family=pack.adapter_family if pack is not None else None,
        adapter_class_name=adapter_class_name,
        bootstrap_safe=bool(pack.bootstrap_safe) if pack is not None else False,
        file_class=policy.file_class.value,
        policy_verdict=policy.verdict.value,
        reason=policy.reason,
        matched_pattern=policy.matched_pattern,
    )


# @grace.anchor grace.adapter_tools.collect_adapter_gaps
# @grace.complexity 5
# @grace.belief Agents need a deterministic gap backlog over repository files, otherwise new-repo onboarding degenerates back into manual extension discovery and wasted context.
# @grace.links grace.adapter_tools.probe_adapter
def collect_adapter_gaps(path: str | Path) -> tuple[AdapterGap, ...]:
    candidate_paths = _walk_policy_candidates(Path(path))
    gaps: list[AdapterGap] = []
    for candidate_path in candidate_paths:
        probe = probe_adapter(candidate_path)
        gap_kind = _gap_kind_for_probe(probe)
        if gap_kind is None:
            continue
        gaps.append(
            AdapterGap(
                path=probe.path,
                gap_kind=gap_kind,
                language_name=probe.language_name,
                policy_verdict=probe.policy_verdict,
                reason=probe.reason,
                matched_pattern=probe.matched_pattern,
            )
        )

    gaps.sort(key=lambda gap: gap.path.as_posix())
    return tuple(gaps)


# @grace.anchor grace.adapter_tools.evaluate_adapter_surface
# @grace.complexity 4
# @grace.belief Repository-level evaluation must summarize policy and adapter coverage without adding heuristics, so agents can decide whether to bootstrap or extend language support next.
def evaluate_adapter_surface(path: str | Path) -> AdapterEval:
    requested_path = Path(path).expanduser().resolve()
    candidate_paths = _walk_policy_candidates(requested_path)
    probes = tuple(probe_adapter(candidate_path) for candidate_path in candidate_paths)
    gaps = collect_adapter_gaps(requested_path)

    file_class_counts = Counter(probe.file_class for probe in probes)
    verdict_counts = Counter(probe.policy_verdict for probe in probes)
    language_counts = Counter(probe.language_name or "unregistered" for probe in probes)
    gap_counts = Counter(gap.gap_kind for gap in gaps)

    return AdapterEval(
        requested_path=requested_path,
        file_count=len(probes),
        file_class_counts=dict(sorted(file_class_counts.items())),
        verdict_counts=dict(sorted(verdict_counts.items())),
        language_counts=dict(sorted(language_counts.items())),
        gap_counts=dict(sorted(gap_counts.items())),
        gaps=gaps,
    )


__all__ = [
    "AdapterEval",
    "AdapterGap",
    "AdapterProbe",
    "collect_adapter_gaps",
    "evaluate_adapter_surface",
    "probe_adapter",
]
