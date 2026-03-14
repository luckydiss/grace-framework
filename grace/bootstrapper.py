# @grace.module grace.bootstrapper
# @grace.purpose Generate deterministic GRACE annotation scaffolds for unannotated source files without inventing semantic meaning.
# @grace.interfaces bootstrap_path(path, *, apply=False)->BootstrapSuccess|BootstrapFailure; derive_bootstrap_module_id(path, root)->str; discover_bootstrap_candidates(path)->tuple[Path,...]
# @grace.invariant Bootstrap remains scaffold-only: it may create TODO placeholders and anchor skeletons but must not infer purpose, belief, links, or domain semantics.
# @grace.invariant Bootstrap previews are deterministic and auditable: the same input tree must yield the same module ids, anchor ids, insertion lines, and file ordering.
# @grace.invariant Apply mode must parse and validate the candidate scope before committing, and must restore original file contents on failure.
from __future__ import annotations

import hashlib
import os
import re
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from grace.artifact_hygiene import is_ignored_artifact_dir_name
from grace.parser import GraceParseFailure

IGNORED_BOOTSTRAP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "node_modules",
    "venv",
}

_MODULE_LINE_RE = re.compile(r"^\s*(?:#|//|/\*|\*|--)\s*@grace\.module\b")
_MODULE_ID_CAPTURE_RE = re.compile(
    r"^\s*(?:#|//|/\*|\*|--)\s*@grace\.module\s+(?P<module_id>.+?)\s*(?:\*/)?\s*$"
)
_MODULE_ID_SEGMENT_RE = re.compile(r"[^A-Za-z0-9_]+")


# @grace.anchor grace.bootstrapper.BootstrapAnchorScaffold
# @grace.complexity 2
class BootstrapAnchorScaffold(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    anchor_id: str
    kind: str
    symbol_name: str
    target_line_start: int
    target_line_end: int
    insertion_line_start: int | None = None


# @grace.anchor grace.bootstrapper.BootstrapDiscoveredBlock
# @grace.complexity 2
class BootstrapDiscoveredBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: object
    symbol_name: str
    qualified_name: str
    line_start: int
    line_end: int
    indent: str = ""


# @grace.anchor grace.bootstrapper.BootstrapFileChange
# @grace.complexity 3
class BootstrapFileChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    module_id: str
    comment_prefix: str
    header_added: bool
    original_hash: str
    updated_hash: str
    generated_anchors: tuple[BootstrapAnchorScaffold, ...]
    preview: str
    updated_source: str


# @grace.anchor grace.bootstrapper.BootstrapFailureStage
# @grace.complexity 1
class BootstrapFailureStage(str, Enum):
    DISCOVERY = "discovery"
    WRITE = "write"
    PARSE = "parse"
    VALIDATE = "validate"


# @grace.anchor grace.bootstrapper.BootstrapFailure
# @grace.complexity 2
class BootstrapFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: bool = False
    stage: BootstrapFailureStage
    requested_path: Path
    message: str
    file_changes: tuple[BootstrapFileChange, ...] = ()
    parse_failures: tuple[GraceParseFailure, ...] = ()
    validation_messages: tuple[str, ...] = ()
    rollback_performed: bool = False


# @grace.anchor grace.bootstrapper.BootstrapSuccess
# @grace.complexity 2
class BootstrapSuccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: bool = True
    requested_path: Path
    apply: bool
    file_changes: tuple[BootstrapFileChange, ...]
    validated_file_count: int = 0


BootstrapResult = BootstrapSuccess | BootstrapFailure


# @grace.anchor grace.bootstrapper.discover_bootstrap_candidates
# @grace.complexity 5
# @grace.belief Bootstrap only stays repo-safe if candidate discovery consults deterministic file policy before asking adapters to scaffold annotations into mixed code, docs, data, and generated trees.
# @grace.links grace.file_policy.resolve_file_policy
def discover_bootstrap_candidates(path: str | Path) -> tuple[Path, ...]:
    from grace.file_policy import GraceFilePolicyVerdict, resolve_file_policy

    resolved_path = Path(path).expanduser().resolve()
    try:
        repo_config = _load_repo_config(resolved_path)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    if resolved_path.is_file():
        policy = resolve_file_policy(resolved_path, repo_config)
        if policy.verdict is not GraceFilePolicyVerdict.SAFE_APPLY:
            raise ValueError(
                f"{resolved_path} is not safe for GRACE bootstrap: "
                f"{policy.verdict.value} ({policy.reason})"
            )
        _get_language_adapter_for_path(resolved_path)
        return (resolved_path,)

    discovered_paths: list[Path] = []
    for current_root, dir_names, file_names in os.walk(resolved_path):
        dir_names[:] = [
            dir_name
            for dir_name in dir_names
            if dir_name not in IGNORED_BOOTSTRAP_DIR_NAMES
            and not dir_name.endswith(".egg-info")
            and not is_ignored_artifact_dir_name(dir_name)
        ]

        root_path = Path(current_root)
        for file_name in sorted(file_names):
            candidate_path = (root_path / file_name).resolve()
            if not _candidate_in_repo_scope(repo_config, resolved_path, candidate_path):
                continue
            try:
                candidate_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            policy = resolve_file_policy(candidate_path, repo_config)
            if policy.verdict is not GraceFilePolicyVerdict.SAFE_APPLY:
                continue

            try:
                _get_language_adapter_for_path(candidate_path)
            except ValueError:
                continue
            discovered_paths.append(candidate_path)

    discovered_paths.sort(key=lambda candidate: candidate.relative_to(resolved_path).as_posix())
    return tuple(discovered_paths)


# @grace.anchor grace.bootstrapper.derive_bootstrap_module_id
# @grace.complexity 3
def derive_bootstrap_module_id(file_path: str | Path, root: str | Path | None = None) -> str:
    resolved_file = Path(file_path).expanduser().resolve()
    resolved_root = Path(root).expanduser().resolve() if root is not None else Path.cwd().resolve()

    try:
        relative_path = resolved_file.relative_to(resolved_root)
    except ValueError:
        relative_path = resolved_file.relative_to(resolved_file.anchor)

    without_suffix = relative_path.with_suffix("")
    parts = [part for part in without_suffix.parts if part and part != "__init__"]
    normalized_parts = [
        _normalize_module_segment(part)
        for part in parts
    ]
    if len(normalized_parts) == 1:
        root_name = _normalize_module_segment(resolved_root.name)
        if root_name and root_name != normalized_parts[0]:
            normalized_parts.insert(0, root_name)
    return ".".join(part for part in normalized_parts if part)


# @grace.anchor grace.bootstrapper.bootstrap_path
# @grace.complexity 8
# @grace.belief Bootstrap must stay mechanical and reversible, so the implementation first synthesizes deterministic scaffold changes, then writes only after a parse-and-validate pass over the candidate scope succeeds.
# @grace.links grace.bootstrapper.discover_bootstrap_candidates, grace.bootstrapper.derive_bootstrap_module_id
def bootstrap_path(path: str | Path, *, apply: bool = False) -> BootstrapResult:
    requested_path = Path(path).expanduser().resolve()
    try:
        candidate_paths = discover_bootstrap_candidates(requested_path)
    except ValueError as exc:
        return BootstrapFailure(
            stage=BootstrapFailureStage.DISCOVERY,
            requested_path=requested_path,
            message=str(exc),
        )

    file_changes: list[BootstrapFileChange] = []
    for candidate_path in candidate_paths:
        file_change = _build_bootstrap_change(candidate_path, requested_path)
        if file_change is not None:
            file_changes.append(file_change)

    frozen_changes = tuple(file_changes)
    if not apply:
        return BootstrapSuccess(
            requested_path=requested_path,
            apply=False,
            file_changes=frozen_changes,
        )

    if not frozen_changes:
        validated_count = _validated_file_count(requested_path)
        return BootstrapSuccess(
            requested_path=requested_path,
            apply=True,
            file_changes=(),
            validated_file_count=validated_count,
        )

    original_texts = {
        file_change.path: file_change.path.read_text(encoding="utf-8")
        for file_change in frozen_changes
    }

    try:
        for file_change in frozen_changes:
            file_change.path.write_text(file_change.updated_source, encoding="utf-8")
    except OSError as exc:
        _restore_bootstrap_files(original_texts)
        return BootstrapFailure(
            stage=BootstrapFailureStage.WRITE,
            requested_path=requested_path,
            message=str(exc),
            file_changes=frozen_changes,
            rollback_performed=True,
        )

    parse_failures, validation_messages, validated_count = _validate_bootstrap_scope(requested_path)
    if parse_failures:
        _restore_bootstrap_files(original_texts)
        return BootstrapFailure(
            stage=BootstrapFailureStage.PARSE,
            requested_path=requested_path,
            message="bootstrap candidate scope failed GRACE parsing",
            file_changes=frozen_changes,
            parse_failures=parse_failures,
            rollback_performed=True,
        )

    if validation_messages:
        _restore_bootstrap_files(original_texts)
        return BootstrapFailure(
            stage=BootstrapFailureStage.VALIDATE,
            requested_path=requested_path,
            message="bootstrap candidate scope failed GRACE validation",
            file_changes=frozen_changes,
            validation_messages=tuple(validation_messages),
            rollback_performed=True,
        )

    return BootstrapSuccess(
        requested_path=requested_path,
        apply=True,
        file_changes=frozen_changes,
        validated_file_count=validated_count,
    )


def _build_bootstrap_change(candidate_path: Path, requested_path: Path) -> BootstrapFileChange | None:
    adapter = _get_language_adapter_for_path(candidate_path)
    source_text = candidate_path.read_text(encoding="utf-8")
    module_header_present = _has_module_header(source_text)
    module_root = _module_root_for_path(candidate_path, requested_path)
    module_id = _extract_existing_module_id(source_text) or derive_bootstrap_module_id(candidate_path, module_root)
    comment_prefix = _adapter_comment_prefix(adapter)
    discovered_blocks = _adapter_unannotated_blocks(adapter, candidate_path)

    if module_header_present and not discovered_blocks:
        return None

    generated_anchors = [
        BootstrapAnchorScaffold(
            anchor_id=f"{module_id}.{block.qualified_name}",
            kind=block.kind.value,
            symbol_name=block.symbol_name,
            target_line_start=block.line_start,
            target_line_end=block.line_end,
        )
        for block in discovered_blocks
    ]

    updated_source, anchored_scaffolds = _render_bootstrap_source(
        source_text,
        comment_prefix=comment_prefix,
        module_id=module_id,
        header_added=not module_header_present,
        anchors=tuple(generated_anchors),
        indent_by_line={block.line_start: block.indent for block in discovered_blocks},
    )

    if updated_source == source_text:
        return None

    return BootstrapFileChange(
        path=candidate_path,
        module_id=module_id,
        comment_prefix=comment_prefix,
        header_added=not module_header_present,
        original_hash=_hash_text(source_text),
        updated_hash=_hash_text(updated_source),
        generated_anchors=anchored_scaffolds,
        preview=_preview_summary(candidate_path, module_id, not module_header_present, anchored_scaffolds),
        updated_source=updated_source,
    )


def _validate_bootstrap_scope(requested_path: Path) -> tuple[tuple[GraceParseFailure, ...], tuple[str, ...], int]:
    validation_paths = _discover_validated_paths(requested_path)
    parse_failures: list[GraceParseFailure] = []
    parsed_files = []

    for candidate_path in validation_paths:
        parsed = _try_parse_python_file(candidate_path)
        if getattr(parsed, "ok", False) is not True:
            parse_failures.append(parsed)
            continue
        parsed_files.append(parsed.file)

    if parse_failures:
        return (tuple(parse_failures), (), len(parsed_files))

    validation_result = _validate_project(parsed_files)
    if getattr(validation_result, "ok", False) is not True:
        messages = tuple(issue.message for issue in validation_result.issues)
        return ((), messages, len(parsed_files))

    return ((), (), len(parsed_files))


def _validated_file_count(requested_path: Path) -> int:
    return len(_discover_validated_paths(requested_path))


def _discover_validated_paths(requested_path: Path) -> tuple[Path, ...]:
    resolved_path = requested_path.expanduser().resolve()
    if resolved_path.is_file():
        return (resolved_path,)
    repo_config = _load_repo_config(resolved_path)
    scope_root = resolved_path

    discovered_paths: list[Path] = []
    for current_root, dir_names, file_names in os.walk(scope_root):
        dir_names[:] = [
            dir_name
            for dir_name in dir_names
            if dir_name not in IGNORED_BOOTSTRAP_DIR_NAMES
            and not dir_name.endswith(".egg-info")
            and not is_ignored_artifact_dir_name(dir_name)
        ]

        root_path = Path(current_root)
        for file_name in sorted(file_names):
            candidate_path = (root_path / file_name).resolve()
            if not _candidate_in_repo_scope(repo_config, scope_root, candidate_path):
                continue
            try:
                source_text = candidate_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if not _has_module_header(source_text):
                continue
            try:
                get_language_adapter_for_path(candidate_path)
            except ValueError:
                continue
            discovered_paths.append(candidate_path)

    discovered_paths.sort(key=lambda candidate: candidate.relative_to(scope_root).as_posix())
    return tuple(discovered_paths)


def _render_bootstrap_source(
    source_text: str,
    *,
    comment_prefix: str,
    module_id: str,
    header_added: bool,
    anchors: tuple[BootstrapAnchorScaffold, ...],
    indent_by_line: dict[int, str],
) -> tuple[str, tuple[BootstrapAnchorScaffold, ...]]:
    lines = source_text.splitlines()
    insertions: dict[int, list[str]] = {}
    cumulative_inserted_lines = 0
    anchored_scaffolds: list[BootstrapAnchorScaffold] = []

    if header_added:
        insertions.setdefault(1, []).extend(
            [
                f"{comment_prefix} @grace.module {module_id}",
                f"{comment_prefix} @grace.purpose TODO",
                f"{comment_prefix} @grace.interfaces TODO",
                f"{comment_prefix} @grace.invariant TODO",
                "",
            ]
        )

    sorted_anchors = sorted(anchors, key=lambda candidate: (candidate.target_line_start, candidate.anchor_id))
    inserted_before_line: dict[int, int] = {}
    for anchor in sorted_anchors:
        indent = indent_by_line.get(anchor.target_line_start, "")
        scaffold_lines = [
            f"{indent}{comment_prefix} @grace.anchor {anchor.anchor_id}",
            f"{indent}{comment_prefix} @grace.complexity 1",
            "",
        ]
        insertions.setdefault(anchor.target_line_start, []).extend(scaffold_lines)
        inserted_before_line[anchor.target_line_start] = inserted_before_line.get(anchor.target_line_start, 0) + len(scaffold_lines)

    offset = 0
    for line_number in sorted(set(insertions)):
        offset += len(insertions[line_number])
        cumulative_inserted_lines = offset

    running_offset = 0
    for anchor in sorted_anchors:
        insertion_line = anchor.target_line_start + running_offset
        running_offset += inserted_before_line.get(anchor.target_line_start, 0)
        anchored_scaffolds.append(anchor.model_copy(update={"insertion_line_start": insertion_line}))

    new_lines: list[str] = []
    if not lines:
        for insertion_lines in insertions.values():
            new_lines.extend(insertion_lines)
    else:
        for line_number, line in enumerate(lines, start=1):
            if line_number in insertions:
                new_lines.extend(insertions[line_number])
            new_lines.append(line)

    updated_source = "\n".join(new_lines)
    if source_text.endswith("\n") or not source_text:
        updated_source += "\n"
    return (updated_source, tuple(anchored_scaffolds))


def _preview_summary(
    file_path: Path,
    module_id: str,
    header_added: bool,
    anchors: tuple[BootstrapAnchorScaffold, ...],
) -> str:
    parts = [f"{file_path}: module={module_id}"]
    if header_added:
        parts.append("header=added")
    if anchors:
        parts.append(
            "anchors="
            + ",".join(
                f"{anchor.anchor_id}@{anchor.insertion_line_start}"
                for anchor in anchors
            )
        )
    else:
        parts.append("anchors=none")
    return " ".join(parts)


def _restore_bootstrap_files(original_texts: dict[Path, str]) -> None:
    for file_path, original_text in original_texts.items():
        file_path.write_text(original_text, encoding="utf-8")


def _has_module_header(source_text: str) -> bool:
    return any(_MODULE_LINE_RE.match(raw_line) for raw_line in source_text.splitlines())


def _extract_existing_module_id(source_text: str) -> str | None:
    for raw_line in source_text.splitlines():
        match = _MODULE_ID_CAPTURE_RE.match(raw_line)
        if match is not None:
            return match.group("module_id").strip()
    return None


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_module_segment(value: str) -> str:
    normalized = _MODULE_ID_SEGMENT_RE.sub("_", value).strip("_").lower()
    return normalized or "module"


def _module_root_for_path(candidate_path: Path, requested_path: Path) -> Path:
    if requested_path.is_dir():
        return requested_path
    return requested_path.parent


def _adapter_comment_prefix(adapter: object) -> str:
    base = getattr(adapter, "_base", None)
    adapter_prefix = getattr(adapter, "annotation_comment_prefix", None)
    base_prefix = getattr(base, "annotation_comment_prefix", None) if base is not None else None
    if base_prefix and (adapter_prefix is None or (adapter_prefix == "#" and base_prefix != "#")):
        return base_prefix
    if adapter_prefix:
        return adapter_prefix
    return base_prefix or "#"


def _adapter_unannotated_blocks(adapter: object, file_path: Path) -> tuple[object, ...]:
    base = getattr(adapter, "_base", None)
    if hasattr(adapter, "discover_unannotated_blocks"):
        try:
            return tuple(getattr(adapter, "discover_unannotated_blocks")(file_path))
        except NotImplementedError:
            pass
    if base is not None and hasattr(base, "discover_unannotated_blocks"):
        return tuple(getattr(base, "discover_unannotated_blocks")(file_path))
    return ()


def _get_language_adapter_for_path(path: Path) -> object:
    from grace.language_adapter import get_language_adapter_for_path

    return get_language_adapter_for_path(path)


def _try_parse_python_file(path: Path) -> object:
    from grace.parser import try_parse_python_file

    return try_parse_python_file(path)


def _validate_project(grace_files: list[object]) -> object:
    from grace.validator import validate_project

    return validate_project(grace_files)


def _load_repo_config(path: Path) -> object:
    from grace.repo_config import load_repo_config

    return load_repo_config(path)


def _candidate_in_repo_scope(repo_config: object, scope_root: Path, candidate_path: Path) -> bool:
    from grace.repo_config import candidate_in_repo_scope

    return candidate_in_repo_scope(repo_config, scope_root, candidate_path)


__all__ = [
    "BootstrapAnchorScaffold",
    "BootstrapDiscoveredBlock",
    "BootstrapFailure",
    "BootstrapFailureStage",
    "BootstrapFileChange",
    "BootstrapResult",
    "BootstrapSuccess",
    "bootstrap_path",
    "derive_bootstrap_module_id",
    "discover_bootstrap_candidates",
]
