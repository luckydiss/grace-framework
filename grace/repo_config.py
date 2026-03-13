# @grace.module grace.repo_config
# @grace.purpose Load minimal repository-scoped GRACE discovery configuration from pyproject.toml without changing core source-of-truth semantics.
# @grace.interfaces load_repo_config(path)->GraceRepoConfig|None; candidate_in_repo_scope(config, requested_path, candidate_path)->bool
# @grace.invariant Repository configuration filters discovery scope only and never overrides inline GRACE annotations.
# @grace.invariant Explicit file or subdirectory targets remain authoritative even when repository-level include or exclude rules exist.
from __future__ import annotations

import fnmatch
import tomllib
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, field_validator


# @grace.anchor grace.repo_config.GraceRepoConfig
# @grace.complexity 1
class GraceRepoConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    root: Path
    include: tuple[str, ...] = Field(default_factory=tuple)
    exclude: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("include", "exclude", mode="before")
    @classmethod
    def _coerce_patterns(cls, value: object) -> object:
        if value is None:
            return ()
        if isinstance(value, list):
            return tuple(item.strip() if isinstance(item, str) else item for item in value)
        return value


# @grace.anchor grace.repo_config.load_repo_config
# @grace.complexity 4
def load_repo_config(path: str | Path) -> GraceRepoConfig | None:
    candidate = Path(path).expanduser().resolve()
    search_root = candidate if candidate.is_dir() else candidate.parent

    for current_dir in (search_root, *search_root.parents):
        pyproject_path = current_dir / "pyproject.toml"
        if not pyproject_path.is_file():
            continue

        payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        grace_section = payload.get("tool", {}).get("grace")
        if grace_section is None:
            continue
        return GraceRepoConfig(
            root=current_dir,
            include=_normalize_patterns(grace_section.get("include")),
            exclude=_normalize_patterns(grace_section.get("exclude")),
        )

    return None


# @grace.anchor grace.repo_config.candidate_in_repo_scope
# @grace.complexity 3
def candidate_in_repo_scope(
    config: GraceRepoConfig | None,
    requested_path: str | Path,
    candidate_path: str | Path,
) -> bool:
    if config is None:
        return True

    requested = Path(requested_path).expanduser().resolve()
    candidate = Path(candidate_path).expanduser().resolve()
    root = config.root.resolve()

    if requested.is_file():
        return True

    if requested != root:
        return True

    try:
        relative_path = candidate.relative_to(root).as_posix()
    except ValueError:
        return False

    if config.include and not _matches_any(relative_path, config.include):
        return False
    if config.exclude and _matches_any(relative_path, config.exclude):
        return False
    return True


def _normalize_patterns(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("tool.grace include/exclude must be arrays of glob patterns")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("tool.grace include/exclude entries must be strings")
        stripped = item.strip()
        if not stripped:
            raise ValueError("tool.grace include/exclude patterns must be non-empty")
        normalized.append(stripped)
    return tuple(normalized)


def _matches_any(relative_path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(relative_path, pattern) for pattern in patterns)


__all__ = [
    "GraceRepoConfig",
    "candidate_in_repo_scope",
    "load_repo_config",
]
