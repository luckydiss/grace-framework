# @grace.module grace.file_policy
# @grace.purpose Classify repository files into deterministic bootstrap safety buckets so agents can scale GRACE onboarding without guessing whether a file is safe to annotate.
# @grace.interfaces GraceFileClass, GraceFilePolicy, GraceFilePolicyVerdict, resolve_file_policy
# @grace.invariant File policy remains deterministic metadata over paths and registered packs; it does not change parser, validator, or patch semantics.

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from grace.repo_config import GraceRepoConfig

IGNORED_DIR_NAMES = frozenset(
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

GENERATED_DIR_NAMES = frozenset(
    {
        "dist",
        "build",
        "coverage",
        ".next",
        "target",
        "out",
        "generated",
        "gen",
    }
)

PREVIEW_ONLY_CODE_SUFFIXES = frozenset(
    {
        ".tsx",
        ".jsx",
        ".js",
        ".mjs",
        ".cjs",
        ".java",
        ".rs",
        ".rb",
        ".php",
        ".cs",
        ".kt",
        ".swift",
        ".scala",
    }
)

DOCS_SUFFIXES = frozenset({".md", ".rst", ".txt", ".adoc"})
DATA_SUFFIXES = frozenset(
    {
        ".json",
        ".jsonl",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".xml",
        ".csv",
        ".tsv",
        ".env",
        ".lock",
    }
)


# @grace.anchor grace.file_policy.GraceFileClass
# @grace.complexity 1
class GraceFileClass(str, Enum):
    CODE = "code"
    DOCS = "docs"
    DATA = "data"
    GENERATED = "generated"
    IGNORE = "ignore"


# @grace.anchor grace.file_policy.GraceFilePolicyVerdict
# @grace.complexity 1
class GraceFilePolicyVerdict(str, Enum):
    SAFE_APPLY = "safe_apply"
    PREVIEW_ONLY = "preview_only"
    UNSUPPORTED = "unsupported"
    IGNORE = "ignore"


# @grace.anchor grace.file_policy.GraceFilePolicy
# @grace.complexity 2
class GraceFilePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    file_class: GraceFileClass
    verdict: GraceFilePolicyVerdict
    reason: str
    language_name: str | None = None
    matched_pattern: str | None = None


def _matches_any(relative_path: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        if Path(relative_path).match(pattern):
            return pattern
    return None


def _relative_path(path: Path, config: GraceRepoConfig | None) -> str | None:
    if config is None:
        return None
    try:
        return path.relative_to(config.root.resolve()).as_posix()
    except ValueError:
        return None


def _class_for_suffix(path: Path) -> GraceFileClass:
    suffix = path.suffix.lower()
    if suffix in DOCS_SUFFIXES:
        return GraceFileClass.DOCS
    if suffix in DATA_SUFFIXES:
        return GraceFileClass.DATA
    return GraceFileClass.CODE


def _policy_from_override(path: Path, config: GraceRepoConfig | None) -> GraceFilePolicy | None:
    relative_path = _relative_path(path, config)
    if relative_path is None or config is None:
        return None

    matched_pattern = _matches_any(relative_path, config.ignore)
    if matched_pattern is not None:
        return GraceFilePolicy(
            path=path,
            file_class=GraceFileClass.IGNORE,
            verdict=GraceFilePolicyVerdict.IGNORE,
            reason=f"repo config marks {relative_path} as ignored",
            matched_pattern=matched_pattern,
        )

    matched_pattern = _matches_any(relative_path, config.generated)
    if matched_pattern is not None:
        return GraceFilePolicy(
            path=path,
            file_class=GraceFileClass.GENERATED,
            verdict=GraceFilePolicyVerdict.IGNORE,
            reason=f"repo config marks {relative_path} as generated output",
            matched_pattern=matched_pattern,
        )

    matched_pattern = _matches_any(relative_path, config.unsupported)
    if matched_pattern is not None:
        return GraceFilePolicy(
            path=path,
            file_class=_class_for_suffix(path),
            verdict=GraceFilePolicyVerdict.UNSUPPORTED,
            reason=f"repo config marks {relative_path} as unsupported for GRACE bootstrap",
            matched_pattern=matched_pattern,
        )

    matched_pattern = _matches_any(relative_path, config.preview_only)
    if matched_pattern is not None:
        return GraceFilePolicy(
            path=path,
            file_class=_class_for_suffix(path),
            verdict=GraceFilePolicyVerdict.PREVIEW_ONLY,
            reason=f"repo config marks {relative_path} as preview-only for GRACE bootstrap",
            matched_pattern=matched_pattern,
        )

    return None


# @grace.anchor grace.file_policy.resolve_file_policy
# @grace.complexity 4
# @grace.belief Repository onboarding only scales if GRACE can deterministically say which files are safe, preview-only, or unsupported before bootstrap touches them.
# @grace.links grace.spec_registry.get_language_pack_for_path
def resolve_file_policy(path: str | Path, config: GraceRepoConfig | None = None) -> GraceFilePolicy:
    from grace.spec_registry import get_language_pack_for_path

    candidate_path = Path(path).expanduser().resolve()

    override_policy = _policy_from_override(candidate_path, config)
    if override_policy is not None:
        return override_policy

    path_parts = {part.lower() for part in candidate_path.parts}
    if path_parts & IGNORED_DIR_NAMES:
        return GraceFilePolicy(
            path=candidate_path,
            file_class=GraceFileClass.IGNORE,
            verdict=GraceFilePolicyVerdict.IGNORE,
            reason="path is under an ignored repository directory",
        )

    if path_parts & GENERATED_DIR_NAMES:
        return GraceFilePolicy(
            path=candidate_path,
            file_class=GraceFileClass.GENERATED,
            verdict=GraceFilePolicyVerdict.IGNORE,
            reason="path is under a generated-output directory",
        )

    pack = get_language_pack_for_path(candidate_path)
    if pack is not None:
        verdict = (
            GraceFilePolicyVerdict.SAFE_APPLY
            if pack.bootstrap_safe
            else GraceFilePolicyVerdict.PREVIEW_ONLY
        )
        return GraceFilePolicy(
            path=candidate_path,
            file_class=GraceFileClass.CODE,
            verdict=verdict,
            reason=f"language pack {pack.language_name!r} is registered for {candidate_path.suffix.lower() or '<no extension>'}",
            language_name=pack.language_name,
        )

    suffix = candidate_path.suffix.lower()
    if suffix in PREVIEW_ONLY_CODE_SUFFIXES:
        return GraceFilePolicy(
            path=candidate_path,
            file_class=GraceFileClass.CODE,
            verdict=GraceFilePolicyVerdict.PREVIEW_ONLY,
            reason=f"{suffix or '<no extension>'} is a code-like suffix without a registered bootstrap-safe language pack",
        )

    if suffix in DOCS_SUFFIXES:
        return GraceFilePolicy(
            path=candidate_path,
            file_class=GraceFileClass.DOCS,
            verdict=GraceFilePolicyVerdict.UNSUPPORTED,
            reason=f"{suffix} files currently have no deterministic inline comment-host policy for GRACE bootstrap",
        )

    if suffix in DATA_SUFFIXES:
        return GraceFilePolicy(
            path=candidate_path,
            file_class=GraceFileClass.DATA,
            verdict=GraceFilePolicyVerdict.UNSUPPORTED,
            reason=f"{suffix} files are treated as data and are not safe for inline GRACE bootstrap",
        )

    return GraceFilePolicy(
        path=candidate_path,
        file_class=GraceFileClass.DATA,
        verdict=GraceFilePolicyVerdict.UNSUPPORTED,
        reason="no registered language pack or deterministic file policy exists for this suffix",
    )


__all__ = [
    "GraceFileClass",
    "GraceFilePolicy",
    "GraceFilePolicyVerdict",
    "resolve_file_policy",
]
