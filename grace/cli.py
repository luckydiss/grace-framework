# @grace.module grace.cli
# @grace.purpose Expose a thin CLI over GRACE core APIs for file-level and repo-level agent workflows.
# @grace.interfaces main(argv)->int; commands: parse(path), validate(path), lint(path), map(path), query.<modules|anchors|anchor|links|dependents|neighbors>(path), patch(path, anchor_id, replacement_file), apply-plan(plan_file)
# @grace.invariant The CLI must not introduce a new source of truth or line-based addressing semantics.
# @grace.invariant Machine-readable JSON output should mirror core API results closely enough for shell-driven agents to compose deterministic workflows.
from __future__ import annotations

import json
import os
from pathlib import Path

import click

from grace.linter import LintFailure, lint_file, lint_project
from grace.map import build_file_map, build_project_map, map_to_dict
from grace.patcher import PatchFailure, PatchStepResult, patch_block
from grace.plan import ApplyPlanFailure, ApplyPlanSuccess, apply_patch_plan, load_patch_plan
from grace.query import QueryLookupError, query_anchor, query_anchors, query_dependents, query_links, query_modules, query_neighbors
from grace.models import GraceFileModel, GraceParseFailure, GraceParseSuccess
from grace.parser import GraceParseError, parse_python_file, try_parse_python_file
from grace.validator import ValidationFailure, validate_file, validate_project

IGNORED_DISCOVERY_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".pytest-tmp",
    ".pytest-basetemp",
    ".pytest-basetemp-runs",
    ".pytest-basetemp-test",
    ".tmp_parser_tests",
    "build",
    "dist",
}


# @grace.anchor grace.cli.DiscoveryError
# @grace.complexity 1
class DiscoveryError(ValueError):
    # @grace.anchor grace.cli.DiscoveryError.__init__
    # @grace.complexity 1
    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(message)


# @grace.anchor grace.cli._path_argument
# @grace.complexity 1
def _path_argument(*, dir_okay: bool) -> click.Path:
    return click.Path(exists=True, file_okay=True, dir_okay=dir_okay, path_type=Path)


# @grace.anchor grace.cli._emit_json
# @grace.complexity 1
def _emit_json(payload: dict) -> None:
    click.echo(json.dumps(payload, indent=2))


# @grace.anchor grace.cli._serialize_file
# @grace.complexity 1
def _serialize_file(grace_file: GraceFileModel) -> dict:
    return grace_file.model_dump(mode="json")


# @grace.anchor grace.cli._serialize_parse_failure
# @grace.complexity 1
def _serialize_parse_failure(result: GraceParseFailure) -> dict:
    return {
        "path": str(result.path),
        "errors": [issue.model_dump(mode="json") for issue in result.errors],
    }


# @grace.anchor grace.cli._parse_error_payload
# @grace.complexity 2
def _parse_error_payload(command: str, error: GraceParseError) -> dict:
    return {
        "ok": False,
        "command": command,
        "scope": "file",
        "stage": "parse",
        "path": str(error.path),
        "errors": [issue.model_dump(mode="json") for issue in error.errors],
    }


# @grace.anchor grace.cli._parse_success_payload
# @grace.complexity 2
def _parse_success_payload(command: str, grace_file: GraceFileModel) -> dict:
    return {
        "ok": True,
        "command": command,
        "scope": "file",
        "path": str(grace_file.path),
        "module_id": grace_file.module.module_id,
        "block_count": len(grace_file.blocks),
        "file": _serialize_file(grace_file),
    }


# @grace.anchor grace.cli._validation_failure_payload
# @grace.complexity 2
def _validation_failure_payload(path: Path, result: ValidationFailure) -> dict:
    return {
        "ok": False,
        "command": "validate",
        "scope": result.scope,
        "stage": "validate",
        "path": str(path),
        "issues": [issue.model_dump(mode="json") for issue in result.issues],
    }


# @grace.anchor grace.cli._validation_success_payload
# @grace.complexity 2
def _validation_success_payload(grace_file: GraceFileModel) -> dict:
    return {
        "ok": True,
        "command": "validate",
        "scope": "file",
        "path": str(grace_file.path),
        "module_id": grace_file.module.module_id,
        "block_count": len(grace_file.blocks),
        "validation": {
            "ok": True,
            "scope": "file",
        },
    }


# @grace.anchor grace.cli._lint_success_payload
# @grace.complexity 2
def _lint_success_payload(grace_file: GraceFileModel) -> dict:
    return {
        "ok": True,
        "command": "lint",
        "scope": "file",
        "path": str(grace_file.path),
        "module_id": grace_file.module.module_id,
        "warning_count": 0,
        "warnings": [],
        "clean": True,
    }


# @grace.anchor grace.cli._lint_warning_payload
# @grace.complexity 2
def _lint_warning_payload(grace_file: GraceFileModel, result: LintFailure) -> dict:
    return {
        "ok": True,
        "command": "lint",
        "scope": "file",
        "path": str(grace_file.path),
        "module_id": grace_file.module.module_id,
        "warning_count": len(result.issues),
        "warnings": [issue.model_dump(mode="json") for issue in result.issues],
        "clean": False,
    }


# @grace.anchor grace.cli._patch_failure_payload
# @grace.complexity 3
def _patch_failure_payload(result: PatchFailure) -> dict:
    return {
        "ok": False,
        "command": "patch",
        "scope": "file",
        "target": {
            "path": str(result.path),
            "anchor_id": result.anchor_id,
        },
        "stage": result.stage.value,
        "path": str(result.path),
        "anchor_id": result.anchor_id,
        "dry_run": result.dry_run,
        "identity_preserved": result.identity_preserved,
        "parse": _serialize_patch_step(result.parse),
        "validate": _serialize_patch_step(result.validation),
        "lint_warnings": [],
        "warning_count": 0,
        "rollback_performed": result.rollback_performed,
        "before_hash": result.before_hash,
        "after_hash": result.after_hash,
        "preview": result.preview,
        "message": result.message,
        "parse_errors": [issue.model_dump(mode="json") for issue in result.parse_errors],
        "validation_issues": [issue.model_dump(mode="json") for issue in result.validation_issues],
    }


# @grace.anchor grace.cli._patch_success_payload
# @grace.complexity 3
def _patch_success_payload(result) -> dict:
    return {
        "ok": True,
        "command": "patch",
        "scope": "file",
        "target": {
            "path": str(result.path),
            "anchor_id": result.anchor_id,
        },
        "path": str(result.path),
        "anchor_id": result.anchor_id,
        "dry_run": result.dry_run,
        "identity_preserved": result.identity_preserved,
        "parse": _serialize_patch_step(result.parse),
        "validate": _serialize_patch_step(result.validation),
        "lint_warnings": [issue.model_dump(mode="json") for issue in result.lint_issues],
        "warning_count": len(result.lint_issues),
        "rollback_performed": result.rollback_performed,
        "before_hash": result.before_hash,
        "after_hash": result.after_hash,
        "preview": result.preview,
        "file": result.file.model_dump(mode="json"),
    }


# @grace.anchor grace.cli._apply_plan_success_payload
# @grace.complexity 2
def _apply_plan_success_payload(plan_path: Path, result: ApplyPlanSuccess) -> dict:
    return {
        "ok": True,
        "command": "apply-plan",
        "scope": "project",
        "plan_path": str(plan_path),
        "dry_run": result.dry_run,
        "preview": result.preview,
        "entry_count": result.entry_count,
        "applied_count": result.applied_count,
        "entries": [_serialize_applied_patch_entry(entry) for entry in result.entries],
    }


# @grace.anchor grace.cli._apply_plan_failure_payload
# @grace.complexity 3
def _apply_plan_failure_payload(plan_path: Path, result: ApplyPlanFailure) -> dict:
    return {
        "ok": False,
        "command": "apply-plan",
        "scope": "project",
        "stage": result.stage.value,
        "plan_path": str(plan_path),
        "dry_run": result.dry_run,
        "preview": result.preview,
        "entry_count": result.entry_count,
        "applied_count": result.applied_count,
        "failed_index": result.failed_index,
        "failed_path": str(result.failed_path),
        "failed_anchor_id": result.failed_anchor_id,
        "message": result.message,
        "entries": [_serialize_applied_patch_entry(entry) for entry in result.entries],
    }


# @grace.anchor grace.cli._serialize_patch_step
# @grace.complexity 1
def _serialize_patch_step(step: PatchStepResult) -> dict:
    return {
        "status": step.status.value,
        "ok": step.status.value == "passed",
        "issue_count": step.issue_count,
    }


# @grace.anchor grace.cli._serialize_applied_patch_entry
# @grace.complexity 1
def _serialize_applied_patch_entry(entry) -> dict:
    return {
        "index": entry.index,
        "path": str(entry.path),
        "anchor_id": entry.anchor_id,
        "operation": entry.operation.value,
        "result": _serialize_patch_result(entry.result),
    }


# @grace.anchor grace.cli._serialize_patch_result
# @grace.complexity 2
def _serialize_patch_result(result) -> dict:
    if isinstance(result, PatchFailure):
        payload = _patch_failure_payload(result)
    else:
        payload = _patch_success_payload(result)
    payload.pop("command", None)
    payload.pop("scope", None)
    return payload


# @grace.anchor grace.cli._project_parse_success_payload
# @grace.complexity 2
def _project_parse_success_payload(command: str, root_path: Path, grace_files: tuple[GraceFileModel, ...]) -> dict:
    return {
        "ok": True,
        "command": command,
        "scope": "project",
        "path": str(root_path),
        "file_count": len(grace_files),
        "module_count": len(grace_files),
        "block_count": sum(len(grace_file.blocks) for grace_file in grace_files),
        "files": [_serialize_file(grace_file) for grace_file in grace_files],
    }


# @grace.anchor grace.cli._project_parse_failure_payload
# @grace.complexity 2
def _project_parse_failure_payload(
    command: str,
    root_path: Path,
    parsed_files: tuple[GraceFileModel, ...],
    parse_failures: tuple[GraceParseFailure, ...],
) -> dict:
    return {
        "ok": False,
        "command": command,
        "scope": "project",
        "stage": "parse",
        "path": str(root_path),
        "parsed_file_count": len(parsed_files),
        "failed_file_count": len(parse_failures),
        "files": [_serialize_file(grace_file) for grace_file in parsed_files],
        "errors": [_serialize_parse_failure(result) for result in parse_failures],
    }


# @grace.anchor grace.cli._discovery_failure_payload
# @grace.complexity 1
def _discovery_failure_payload(command: str, path: Path, message: str) -> dict:
    return {
        "ok": False,
        "command": command,
        "scope": "project",
        "stage": "discovery",
        "path": str(path),
        "message": message,
    }


# @grace.anchor grace.cli._project_validation_success_payload
# @grace.complexity 2
def _project_validation_success_payload(root_path: Path, grace_files: tuple[GraceFileModel, ...]) -> dict:
    return {
        "ok": True,
        "command": "validate",
        "scope": "project",
        "path": str(root_path),
        "file_count": len(grace_files),
        "module_count": len(grace_files),
        "block_count": sum(len(grace_file.blocks) for grace_file in grace_files),
        "validation": {
            "ok": True,
            "scope": "project",
        },
    }


# @grace.anchor grace.cli._project_lint_success_payload
# @grace.complexity 2
def _project_lint_success_payload(root_path: Path, grace_files: tuple[GraceFileModel, ...]) -> dict:
    return {
        "ok": True,
        "command": "lint",
        "scope": "project",
        "path": str(root_path),
        "file_count": len(grace_files),
        "module_count": len(grace_files),
        "warning_count": 0,
        "warnings": [],
        "clean": True,
    }


# @grace.anchor grace.cli._project_lint_warning_payload
# @grace.complexity 2
def _project_lint_warning_payload(root_path: Path, grace_files: tuple[GraceFileModel, ...], result: LintFailure) -> dict:
    return {
        "ok": True,
        "command": "lint",
        "scope": "project",
        "path": str(root_path),
        "file_count": len(grace_files),
        "module_count": len(grace_files),
        "warning_count": len(result.issues),
        "warnings": [issue.model_dump(mode="json") for issue in result.issues],
        "clean": False,
    }


# @grace.anchor grace.cli._query_failure_payload
# @grace.complexity 2
def _query_failure_payload(query_name: str, path: Path, scope: str, message: str, anchor_id: str | None = None) -> dict:
    payload = {
        "ok": False,
        "command": "query",
        "query": query_name,
        "scope": scope,
        "query_scope": "anchor" if anchor_id is not None else "collection",
        "stage": "query",
        "path": str(path),
        "message": message,
    }
    if anchor_id is not None:
        payload["anchor_id"] = anchor_id
    return payload


# @grace.anchor grace.cli._query_collection_payload
# @grace.complexity 2
def _query_collection_payload(query_name: str, path: Path, scope: str, items: tuple[dict, ...], module_id: str | None = None) -> dict:
    payload = {
        "ok": True,
        "command": "query",
        "query": query_name,
        "scope": scope,
        "query_scope": "collection",
        "path": str(path),
        "count": len(items),
    }
    if module_id is not None:
        payload["module_id"] = module_id
    payload[query_name] = list(items)
    return payload


# @grace.anchor grace.cli._query_anchor_payload
# @grace.complexity 2
def _query_anchor_payload(query_name: str, path: Path, scope: str, anchor_id: str, anchor_payload: dict) -> dict:
    return {
        "ok": True,
        "command": "query",
        "query": query_name,
        "scope": scope,
        "query_scope": "anchor",
        "path": str(path),
        "anchor_id": anchor_id,
        "anchor": anchor_payload,
    }


# @grace.anchor grace.cli._query_anchor_collection_payload
# @grace.complexity 3
def _query_anchor_collection_payload(
    query_name: str,
    path: Path,
    scope: str,
    anchor_id: str,
    anchor_payload: dict,
    items: tuple[dict, ...],
) -> dict:
    return {
        "ok": True,
        "command": "query",
        "query": query_name,
        "scope": scope,
        "query_scope": "anchor",
        "path": str(path),
        "anchor_id": anchor_id,
        "anchor": anchor_payload,
        "count": len(items),
        query_name: list(items),
    }


# @grace.anchor grace.cli._discover_grace_paths
# @grace.complexity 5
# @grace.links grace.language_adapter.get_language_adapter_for_path, grace.artifact_hygiene.is_ignored_artifact_dir_name, grace.repo_config.load_repo_config, grace.repo_config.candidate_in_repo_scope
def _discover_grace_paths(path: Path) -> tuple[str, tuple[Path, ...]]:
    from grace.artifact_hygiene import is_ignored_artifact_dir_name
    from grace.language_adapter import get_language_adapter_for_path
    from grace.repo_config import candidate_in_repo_scope, load_repo_config

    def has_grace_module_header(source_text: str) -> bool:
        for raw_line in source_text.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.startswith(("#", "//", "/*", "*", "--")):
                if "@grace.module" in stripped:
                    return True
                continue
            return False
        return False

    resolved_path = path.expanduser().resolve()
    try:
        repo_config = load_repo_config(resolved_path)
    except ValueError as exc:
        raise DiscoveryError(resolved_path, str(exc)) from exc

    if resolved_path.is_file():
        try:
            get_language_adapter_for_path(resolved_path)
        except ValueError as exc:
            raise DiscoveryError(resolved_path, str(exc)) from exc
        return "file", (resolved_path,)

    discovered_paths: list[Path] = []
    for current_root, dir_names, file_names in os.walk(resolved_path):
        dir_names[:] = [
            dir_name
            for dir_name in dir_names
            if dir_name not in IGNORED_DISCOVERY_DIR_NAMES
            and not dir_name.endswith(".egg-info")
            and not is_ignored_artifact_dir_name(dir_name)
        ]

        root_path = Path(current_root)
        for file_name in sorted(file_names):
            candidate_path = (root_path / file_name).resolve()
            if not candidate_in_repo_scope(repo_config, resolved_path, candidate_path):
                continue
            try:
                source_text = candidate_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if not has_grace_module_header(source_text):
                continue
            try:
                get_language_adapter_for_path(candidate_path)
            except ValueError:
                continue
            discovered_paths.append(candidate_path)

    discovered_paths.sort(key=lambda candidate: candidate.relative_to(resolved_path).as_posix())
    if not discovered_paths:
        raise DiscoveryError(resolved_path, f"no GRACE-annotated files supported by installed adapters found under {resolved_path}")
    return "project", tuple(discovered_paths)


# @grace.anchor grace.cli._parse_many
# @grace.complexity 3
# @grace.links grace.parser.try_parse_python_file
def _parse_many(paths: tuple[Path, ...]) -> tuple[tuple[GraceFileModel, ...], tuple[GraceParseFailure, ...]]:
    parsed_files: list[GraceFileModel] = []
    parse_failures: list[GraceParseFailure] = []
    for path in paths:
        result = try_parse_python_file(path)
        if isinstance(result, GraceParseSuccess):
            parsed_files.append(result.file)
        else:
            parse_failures.append(result)
    return tuple(parsed_files), tuple(parse_failures)


# @grace.anchor grace.cli._load_grace_map_for_query
# @grace.complexity 4
# @grace.links grace.cli._discover_grace_paths, grace.cli._parse_many, grace.parser.parse_python_file
def _load_grace_map_for_query(path: Path) -> tuple[str, object]:
    scope, discovered_paths = _discover_grace_paths(path)
    if scope == "project":
        parsed_files, parse_failures = _parse_many(discovered_paths)
        if parse_failures:
            raise GraceParseError(path, [issue for failure in parse_failures for issue in failure.errors])
        return scope, build_project_map(parsed_files)
    return scope, build_file_map(parse_python_file(path))


# @grace.anchor grace.cli._emit_project_parse_failure
# @grace.complexity 2
def _emit_project_parse_failure(path: Path, parse_failures: tuple[GraceParseFailure, ...]) -> None:
    click.echo(f"Parse failed for project {path}", err=True)
    for failure in parse_failures:
        click.echo(f"- file: {failure.path}", err=True)
        for issue in failure.errors:
            location = f" line {issue.line}" if issue.line is not None else ""
            click.echo(f"  - {issue.code.value}{location}: {issue.message}", err=True)


# @grace.anchor grace.cli._emit_discovery_failure
# @grace.complexity 1
def _emit_discovery_failure(path: Path, message: str) -> None:
    click.echo(f"Discovery failed for {path}: {message}", err=True)


# @grace.anchor grace.cli._emit_parse_errors
# @grace.complexity 2
def _emit_parse_errors(error: GraceParseError) -> None:
    click.echo(f"Parse failed for {error.path}", err=True)
    for issue in error.errors:
        location = f" line {issue.line}" if issue.line is not None else ""
        click.echo(f"- {issue.code.value}{location}: {issue.message}", err=True)


# @grace.anchor grace.cli._emit_validation_failure
# @grace.complexity 1
def _emit_validation_failure(result: ValidationFailure) -> None:
    click.echo("Validation failed", err=True)
    for issue in result.issues:
        click.echo(f"- {issue.code.value}: {issue.message}", err=True)


# @grace.anchor grace.cli._emit_lint_warnings
# @grace.complexity 1
def _emit_lint_warnings(result: LintFailure) -> None:
    click.echo(f"Lint warnings: {len(result.issues)}")
    for issue in result.issues:
        click.echo(f"- {issue.code.value}: {issue.message}")


# @grace.anchor grace.cli._emit_patch_failure
# @grace.complexity 2
def _emit_patch_failure(result: PatchFailure) -> None:
    click.echo(f"Patch failed at stage {result.stage.value}: {result.message}", err=True)
    for issue in result.parse_errors:
        location = f" line {issue.line}" if issue.line is not None else ""
        click.echo(f"- {issue.code.value}{location}: {issue.message}", err=True)
    for issue in result.validation_issues:
        click.echo(f"- {issue.code.value}: {issue.message}", err=True)


# @grace.anchor grace.cli._emit_patch_preview
# @grace.complexity 1
def _emit_patch_preview(result) -> None:
    click.echo(f"Patch preview for {result.anchor_id} in {result.path}")
    click.echo(result.preview if result.preview else "(no diff)")


# @grace.anchor grace.cli._emit_patch_success
# @grace.complexity 2
def _emit_patch_success(result) -> None:
    if result.dry_run:
        click.echo(f"Dry-run succeeded for {result.anchor_id} in {result.path}")
    else:
        click.echo(f"Patched {result.anchor_id} in {result.path}")
    if result.lint_issues:
        click.echo(f"Lint warnings: {len(result.lint_issues)}")
        for issue in result.lint_issues:
            click.echo(f"- {issue.code.value}: {issue.message}")


# @grace.anchor grace.cli._emit_apply_plan_success
# @grace.complexity 1
def _emit_apply_plan_success(plan_path: Path, result: ApplyPlanSuccess) -> None:
    if result.dry_run:
        click.echo(f"Dry-run succeeded for patch plan {plan_path}: {result.applied_count}/{result.entry_count} entry(s)")
    else:
        click.echo(f"Applied patch plan {plan_path}: {result.applied_count}/{result.entry_count} entry(s) succeeded")


# @grace.anchor grace.cli._emit_apply_plan_failure
# @grace.complexity 2
def _emit_apply_plan_failure(plan_path: Path, result: ApplyPlanFailure) -> None:
    click.echo(
        f"Patch plan failed at stage {result.stage.value} for entry {result.failed_index} in {plan_path}: {result.message}",
        err=True,
    )
    failed_entry = result.entries[-1]
    failed_result = failed_entry.result
    if isinstance(failed_result, PatchFailure):
        _emit_patch_failure(failed_result)


# @grace.anchor grace.cli._emit_apply_plan_preview
# @grace.complexity 2
def _emit_apply_plan_preview(result: ApplyPlanSuccess | ApplyPlanFailure) -> None:
    click.echo("Patch plan preview:")
    for entry in result.entries:
        click.echo(f"Entry {entry.index}: {entry.anchor_id} in {entry.path}")
        preview = entry.result.preview if hasattr(entry.result, "preview") else None
        click.echo(preview if preview else "(no diff)")


# @grace.anchor grace.cli.app
# @grace.complexity 2
# @grace.links grace.clean_command.clean_command
@click.group(help="GRACE v1 CLI")
def app() -> None:
    pass


from grace.clean_command import clean_command

if "clean" not in app.commands:
    app.add_command(clean_command, name="clean")


# @grace.anchor grace.cli.query_group
# @grace.complexity 1
@app.group("query", help="Query the derived GRACE graph without changing repository state.")
def query_group() -> None:
    pass


# @grace.anchor grace.cli.parse_command
# @grace.complexity 6
# @grace.belief Parse command orchestration stays deterministic by running discovery first, then switching cleanly between single-file and project aggregation paths without mixing partial success into the file-level contract.
# @grace.links grace.cli._discover_grace_paths, grace.cli._parse_many, grace.parser.parse_python_file
@app.command("parse")
@click.argument("path", type=_path_argument(dir_okay=True))
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def parse_command(path: Path, as_json: bool) -> None:
    try:
        scope, discovered_paths = _discover_grace_paths(path)
    except DiscoveryError as error:
        if as_json:
            _emit_json(_discovery_failure_payload("parse", error.path, error.message))
            raise click.exceptions.Exit(code=1) from error
        _emit_discovery_failure(error.path, error.message)
        raise click.exceptions.Exit(code=1) from error

    if scope == "project":
        parsed_files, parse_failures = _parse_many(discovered_paths)
        if parse_failures:
            if as_json:
                _emit_json(_project_parse_failure_payload("parse", path, parsed_files, parse_failures))
                raise click.exceptions.Exit(code=1)
            _emit_project_parse_failure(path, parse_failures)
            raise click.exceptions.Exit(code=1)

        if as_json:
            _emit_json(_project_parse_success_payload("parse", path, parsed_files))
            return

        click.echo(
            f"Parsed project {path}: {len(parsed_files)} file(s), "
            f"{len(parsed_files)} module(s), {sum(len(grace_file.blocks) for grace_file in parsed_files)} block(s)"
        )
        return

    try:
        grace_file = parse_python_file(path)
    except GraceParseError as error:
        if as_json:
            _emit_json(_parse_error_payload("parse", error))
            raise click.exceptions.Exit(code=1) from error
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error

    if as_json:
        _emit_json(_parse_success_payload("parse", grace_file))
        return

    click.echo(f"Parsed module {grace_file.module.module_id} with {len(grace_file.blocks)} block(s)")


# @grace.anchor grace.cli.validate_command
# @grace.complexity 6
# @grace.belief Validate command must stop on parse failures before invoking validation so agents never receive mixed parse-and-validate success signals for the same scope.
# @grace.links grace.cli._discover_grace_paths, grace.cli._parse_many, grace.parser.parse_python_file
@app.command("validate")
@click.argument("path", type=_path_argument(dir_okay=True))
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def validate_command(path: Path, as_json: bool) -> None:
    try:
        scope, discovered_paths = _discover_grace_paths(path)
    except DiscoveryError as error:
        if as_json:
            _emit_json(_discovery_failure_payload("validate", error.path, error.message))
            raise click.exceptions.Exit(code=1) from error
        _emit_discovery_failure(error.path, error.message)
        raise click.exceptions.Exit(code=1) from error

    if scope == "project":
        parsed_files, parse_failures = _parse_many(discovered_paths)
        if parse_failures:
            if as_json:
                _emit_json(_project_parse_failure_payload("validate", path, parsed_files, parse_failures))
                raise click.exceptions.Exit(code=1)
            _emit_project_parse_failure(path, parse_failures)
            raise click.exceptions.Exit(code=1)

        result = validate_project(parsed_files)
        if isinstance(result, ValidationFailure):
            if as_json:
                _emit_json(_validation_failure_payload(path, result))
                raise click.exceptions.Exit(code=1)
            _emit_validation_failure(result)
            raise click.exceptions.Exit(code=1)

        if as_json:
            _emit_json(_project_validation_success_payload(path, parsed_files))
            return

        click.echo(f"Validated project {path} successfully ({len(parsed_files)} file(s))")
        return

    try:
        grace_file = parse_python_file(path)
    except GraceParseError as error:
        if as_json:
            _emit_json(_parse_error_payload("validate", error))
            raise click.exceptions.Exit(code=1) from error
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error

    result = validate_file(grace_file)
    if isinstance(result, ValidationFailure):
        if as_json:
            _emit_json(_validation_failure_payload(path, result))
            raise click.exceptions.Exit(code=1)
        _emit_validation_failure(result)
        raise click.exceptions.Exit(code=1)

    if as_json:
        _emit_json(_validation_success_payload(grace_file))
        return

    click.echo(f"Validated module {grace_file.module.module_id} successfully")


# @grace.anchor grace.cli.lint_command
# @grace.complexity 6
# @grace.belief Lint command preserves the core execution discipline by requiring successful parse and validation first, while still keeping lint warnings non-blocking for the exit-code contract.
# @grace.links grace.cli._discover_grace_paths, grace.cli._parse_many, grace.parser.parse_python_file
@app.command("lint")
@click.argument("path", type=_path_argument(dir_okay=True))
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def lint_command(path: Path, as_json: bool) -> None:
    try:
        scope, discovered_paths = _discover_grace_paths(path)
    except DiscoveryError as error:
        if as_json:
            _emit_json(_discovery_failure_payload("lint", error.path, error.message))
            raise click.exceptions.Exit(code=1) from error
        _emit_discovery_failure(error.path, error.message)
        raise click.exceptions.Exit(code=1) from error

    if scope == "project":
        parsed_files, parse_failures = _parse_many(discovered_paths)
        if parse_failures:
            if as_json:
                _emit_json(_project_parse_failure_payload("lint", path, parsed_files, parse_failures))
                raise click.exceptions.Exit(code=1)
            _emit_project_parse_failure(path, parse_failures)
            raise click.exceptions.Exit(code=1)

        validation_result = validate_project(parsed_files)
        if isinstance(validation_result, ValidationFailure):
            if as_json:
                payload = {
                    "ok": False,
                    "command": "lint",
                    "scope": "project",
                    "stage": "validate",
                    "path": str(path),
                    "issues": [issue.model_dump(mode="json") for issue in validation_result.issues],
                }
                _emit_json(payload)
                raise click.exceptions.Exit(code=1)
            _emit_validation_failure(validation_result)
            raise click.exceptions.Exit(code=1)

        lint_result = lint_project(parsed_files)
        if isinstance(lint_result, LintFailure):
            if as_json:
                _emit_json(_project_lint_warning_payload(path, parsed_files, lint_result))
                return
            _emit_lint_warnings(lint_result)
            return

        if as_json:
            _emit_json(_project_lint_success_payload(path, parsed_files))
            return

        click.echo(f"Lint passed for project {path}")
        return

    try:
        grace_file = parse_python_file(path)
    except GraceParseError as error:
        if as_json:
            _emit_json(_parse_error_payload("lint", error))
            raise click.exceptions.Exit(code=1) from error
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error

    validation_result = validate_file(grace_file)
    if isinstance(validation_result, ValidationFailure):
        if as_json:
            payload = {
                "ok": False,
                "command": "lint",
                "stage": "validate",
                "path": str(path),
                "issues": [issue.model_dump(mode="json") for issue in validation_result.issues],
            }
            _emit_json(payload)
            raise click.exceptions.Exit(code=1)
        _emit_validation_failure(validation_result)
        raise click.exceptions.Exit(code=1)

    lint_result = lint_file(grace_file)
    if isinstance(lint_result, LintFailure):
        if as_json:
            _emit_json(_lint_warning_payload(grace_file, lint_result))
            return
        _emit_lint_warnings(lint_result)
        return

    if as_json:
        _emit_json(_lint_success_payload(grace_file))
        return

    click.echo(f"Lint passed for module {grace_file.module.module_id}")


# @grace.anchor grace.cli.map_command
# @grace.complexity 5
# @grace.links grace.cli._discover_grace_paths, grace.cli._parse_many, grace.parser.parse_python_file
@app.command("map")
@click.argument("path", type=_path_argument(dir_okay=True))
@click.option("--json", "as_json", is_flag=True, help="Print a JSON-friendly GRACE map payload.")
def map_command(path: Path, as_json: bool) -> None:
    try:
        scope, discovered_paths = _discover_grace_paths(path)
    except DiscoveryError as error:
        if as_json:
            _emit_json(_discovery_failure_payload("map", error.path, error.message))
            raise click.exceptions.Exit(code=1) from error
        _emit_discovery_failure(error.path, error.message)
        raise click.exceptions.Exit(code=1) from error

    if scope == "project":
        parsed_files, parse_failures = _parse_many(discovered_paths)
        if parse_failures:
            if as_json:
                _emit_json(_project_parse_failure_payload("map", path, parsed_files, parse_failures))
                raise click.exceptions.Exit(code=1)
            _emit_project_parse_failure(path, parse_failures)
            raise click.exceptions.Exit(code=1)

        grace_map = build_project_map(parsed_files)
        if as_json:
            _emit_json(map_to_dict(grace_map))
            return

        click.echo(
            f"Built project map for {path}: "
            f"{len(grace_map.modules)} module(s), {len(grace_map.anchors)} anchor(s), {len(grace_map.edges)} edge(s)"
        )
        return

    try:
        grace_file = parse_python_file(path)
    except GraceParseError as error:
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error

    grace_map = build_file_map(grace_file)
    if as_json:
        click.echo(json.dumps(map_to_dict(grace_map), indent=2))
        return

    click.echo(
        f"Built map for module {grace_file.module.module_id}: "
        f"{len(grace_map.anchors)} anchor(s), {len(grace_map.edges)} edge(s)"
    )


# @grace.anchor grace.cli.query_modules_command
# @grace.complexity 4
# @grace.links grace.cli._load_grace_map_for_query
@query_group.command("modules")
@click.argument("path", type=_path_argument(dir_okay=True))
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def query_modules_command(path: Path, as_json: bool) -> None:
    try:
        scope, grace_map = _load_grace_map_for_query(path)
    except DiscoveryError as error:
        if as_json:
            _emit_json(_discovery_failure_payload("query", error.path, error.message))
            raise click.exceptions.Exit(code=1) from error
        _emit_discovery_failure(error.path, error.message)
        raise click.exceptions.Exit(code=1) from error
    except GraceParseError as error:
        if as_json:
            _emit_json(_parse_error_payload("query", error))
            raise click.exceptions.Exit(code=1) from error
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error

    modules = tuple(module.model_dump(mode="json") for module in query_modules(grace_map))
    if as_json:
        _emit_json(_query_collection_payload("modules", path, scope, modules))
        return

    click.echo(f"Query modules for {path}: {len(modules)} module(s)")
    for module in modules:
        click.echo(f"- {module['module_id']} ({module['path']})")


# @grace.anchor grace.cli.query_anchors_command
# @grace.complexity 4
# @grace.links grace.cli._load_grace_map_for_query
@query_group.command("anchors")
@click.argument("path", type=_path_argument(dir_okay=True))
@click.option("--module", "module_id", default=None, help="Limit results to a single module_id.")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def query_anchors_command(path: Path, module_id: str | None, as_json: bool) -> None:
    try:
        scope, grace_map = _load_grace_map_for_query(path)
    except DiscoveryError as error:
        if as_json:
            _emit_json(_discovery_failure_payload("query", error.path, error.message))
            raise click.exceptions.Exit(code=1) from error
        _emit_discovery_failure(error.path, error.message)
        raise click.exceptions.Exit(code=1) from error
    except GraceParseError as error:
        if as_json:
            _emit_json(_parse_error_payload("query", error))
            raise click.exceptions.Exit(code=1) from error
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error

    anchors = tuple(anchor.model_dump(mode="json") for anchor in query_anchors(grace_map, module_id=module_id))
    if as_json:
        _emit_json(_query_collection_payload("anchors", path, scope, anchors, module_id=module_id))
        return

    label = f" in module {module_id}" if module_id else ""
    click.echo(f"Query anchors for {path}{label}: {len(anchors)} anchor(s)")
    for anchor in anchors:
        click.echo(f"- {anchor['anchor_id']}")


# @grace.anchor grace.cli.query_anchor_command
# @grace.complexity 4
# @grace.links grace.cli._load_grace_map_for_query
@query_group.command("anchor")
@click.argument("path", type=_path_argument(dir_okay=True))
@click.argument("anchor_id")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def query_anchor_command(path: Path, anchor_id: str, as_json: bool) -> None:
    try:
        scope, grace_map = _load_grace_map_for_query(path)
        anchor = query_anchor(grace_map, anchor_id)
    except DiscoveryError as error:
        if as_json:
            _emit_json(_discovery_failure_payload("query", error.path, error.message))
            raise click.exceptions.Exit(code=1) from error
        _emit_discovery_failure(error.path, error.message)
        raise click.exceptions.Exit(code=1) from error
    except GraceParseError as error:
        if as_json:
            _emit_json(_parse_error_payload("query", error))
            raise click.exceptions.Exit(code=1) from error
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error
    except QueryLookupError as error:
        if as_json:
            _emit_json(_query_failure_payload("anchor", path, scope, str(error), anchor_id=anchor_id))
            raise click.exceptions.Exit(code=1) from error
        click.echo(str(error), err=True)
        raise click.exceptions.Exit(code=1) from error

    if as_json:
        _emit_json(_query_anchor_payload("anchor", path, scope, anchor_id, anchor.model_dump(mode="json")))
        return

    click.echo(f"Anchor {anchor.anchor_id} in module {anchor.module_id}")


# @grace.anchor grace.cli.query_links_command
# @grace.complexity 4
# @grace.links grace.cli._load_grace_map_for_query, grace.query.query_links
@query_group.command("links")
@click.argument("path", type=_path_argument(dir_okay=True))
@click.argument("anchor_id")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def query_links_command(path: Path, anchor_id: str, as_json: bool) -> None:
    try:
        scope, grace_map = _load_grace_map_for_query(path)
        anchor = query_anchor(grace_map, anchor_id)
        linked_anchors = tuple(item.model_dump(mode="json") for item in query_links(grace_map, anchor_id))
    except DiscoveryError as error:
        if as_json:
            _emit_json(_discovery_failure_payload("query", error.path, error.message))
            raise click.exceptions.Exit(code=1) from error
        _emit_discovery_failure(error.path, error.message)
        raise click.exceptions.Exit(code=1) from error
    except GraceParseError as error:
        if as_json:
            _emit_json(_parse_error_payload("query", error))
            raise click.exceptions.Exit(code=1) from error
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error
    except QueryLookupError as error:
        if as_json:
            _emit_json(_query_failure_payload("links", path, scope, str(error), anchor_id=anchor_id))
            raise click.exceptions.Exit(code=1) from error
        click.echo(str(error), err=True)
        raise click.exceptions.Exit(code=1) from error

    if as_json:
        _emit_json(_query_anchor_collection_payload("links", path, scope, anchor_id, anchor.model_dump(mode="json"), linked_anchors))
        return

    click.echo(f"Outgoing links for {anchor_id}: {len(linked_anchors)}")
    for linked_anchor in linked_anchors:
        click.echo(f"- {linked_anchor['anchor_id']}")


# @grace.anchor grace.cli.query_dependents_command
# @grace.complexity 4
# @grace.links grace.cli._load_grace_map_for_query, grace.query.query_dependents
@query_group.command("dependents")
@click.argument("path", type=_path_argument(dir_okay=True))
@click.argument("anchor_id")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def query_dependents_command(path: Path, anchor_id: str, as_json: bool) -> None:
    try:
        scope, grace_map = _load_grace_map_for_query(path)
        anchor = query_anchor(grace_map, anchor_id)
        dependents = tuple(item.model_dump(mode="json") for item in query_dependents(grace_map, anchor_id))
    except DiscoveryError as error:
        if as_json:
            _emit_json(_discovery_failure_payload("query", error.path, error.message))
            raise click.exceptions.Exit(code=1) from error
        _emit_discovery_failure(error.path, error.message)
        raise click.exceptions.Exit(code=1) from error
    except GraceParseError as error:
        if as_json:
            _emit_json(_parse_error_payload("query", error))
            raise click.exceptions.Exit(code=1) from error
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error
    except QueryLookupError as error:
        if as_json:
            _emit_json(_query_failure_payload("dependents", path, scope, str(error), anchor_id=anchor_id))
            raise click.exceptions.Exit(code=1) from error
        click.echo(str(error), err=True)
        raise click.exceptions.Exit(code=1) from error

    if as_json:
        _emit_json(_query_anchor_collection_payload("dependents", path, scope, anchor_id, anchor.model_dump(mode="json"), dependents))
        return

    click.echo(f"Dependents for {anchor_id}: {len(dependents)}")
    for dependent in dependents:
        click.echo(f"- {dependent['anchor_id']}")


# @grace.anchor grace.cli.query_neighbors_command
# @grace.complexity 4
# @grace.links grace.cli._load_grace_map_for_query, grace.query.query_neighbors
@query_group.command("neighbors")
@click.argument("path", type=_path_argument(dir_okay=True))
@click.argument("anchor_id")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def query_neighbors_command(path: Path, anchor_id: str, as_json: bool) -> None:
    try:
        scope, grace_map = _load_grace_map_for_query(path)
        anchor = query_anchor(grace_map, anchor_id)
        neighbors = tuple(item.model_dump(mode="json") for item in query_neighbors(grace_map, anchor_id))
    except DiscoveryError as error:
        if as_json:
            _emit_json(_discovery_failure_payload("query", error.path, error.message))
            raise click.exceptions.Exit(code=1) from error
        _emit_discovery_failure(error.path, error.message)
        raise click.exceptions.Exit(code=1) from error
    except GraceParseError as error:
        if as_json:
            _emit_json(_parse_error_payload("query", error))
            raise click.exceptions.Exit(code=1) from error
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error
    except QueryLookupError as error:
        if as_json:
            _emit_json(_query_failure_payload("neighbors", path, scope, str(error), anchor_id=anchor_id))
            raise click.exceptions.Exit(code=1) from error
        click.echo(str(error), err=True)
        raise click.exceptions.Exit(code=1) from error

    if as_json:
        _emit_json(_query_anchor_collection_payload("neighbors", path, scope, anchor_id, anchor.model_dump(mode="json"), neighbors))
        return

    click.echo(f"Neighbors for {anchor_id}: {len(neighbors)}")
    for neighbor in neighbors:
        click.echo(f"- {neighbor['anchor_id']}")


# @grace.anchor grace.cli.impact_command
# @grace.complexity 6
# @grace.belief Impact CLI should stay thin and deterministic by reusing the existing map-loading path and delegating all reverse-dependency traversal to the derived impact layer.
# @grace.links grace.cli._load_grace_map_for_query, grace.impact.impact_summary
@app.command("impact")
@click.argument("path", type=_path_argument(dir_okay=True))
@click.argument("anchor_id")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def impact_command(path: Path, anchor_id: str, as_json: bool) -> None:
    from grace.impact import ImpactLookupError, impact_summary

    try:
        scope, grace_map = _load_grace_map_for_query(path)
        summary = impact_summary(grace_map, anchor_id)
    except DiscoveryError as error:
        if as_json:
            _emit_json(_discovery_failure_payload("impact", error.path, error.message))
            raise click.exceptions.Exit(code=1) from error
        _emit_discovery_failure(error.path, error.message)
        raise click.exceptions.Exit(code=1) from error
    except GraceParseError as error:
        if as_json:
            _emit_json(_parse_error_payload("impact", error))
            raise click.exceptions.Exit(code=1) from error
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error
    except ImpactLookupError as error:
        if as_json:
            _emit_json(
                {
                    "ok": False,
                    "command": "impact",
                    "scope": scope,
                    "stage": "impact",
                    "path": str(path),
                    "target": anchor_id,
                    "message": str(error),
                }
            )
            raise click.exceptions.Exit(code=1) from error
        click.echo(str(error), err=True)
        raise click.exceptions.Exit(code=1) from error

    if as_json:
        _emit_json(
            {
                "ok": True,
                "command": "impact",
                "scope": scope,
                "path": str(path),
                "target": anchor_id,
                "data": summary.model_dump(mode="json"),
            }
        )
        return

    click.echo(
        f"Impact for {anchor_id}: "
        f"{len(summary.direct_dependents)} direct dependent(s), "
        f"{len(summary.transitive_dependents)} transitive dependent(s), "
        f"{len(summary.affected_modules)} affected module(s)"
    )
    for dependent in summary.transitive_dependents:
        click.echo(f"- {dependent.anchor_id}")


# @grace.anchor grace.cli.read_command
# @grace.complexity 6
# @grace.belief Read CLI should stay deterministic by reusing existing discovery and parse aggregation, then delegating anchor-local extraction to the derived read layer instead of inventing a second source-of-truth path.
# @grace.links grace.cli._discover_grace_paths, grace.cli._parse_many, grace.read.read_anchor_context, grace.map.build_file_map, grace.map.build_project_map
@app.command("read")
@click.argument("path", type=_path_argument(dir_okay=True))
@click.argument("anchor_id")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def read_command(path: Path, anchor_id: str, as_json: bool) -> None:
    from grace.read import ReadLookupError, read_anchor_context

    try:
        scope, discovered_paths = _discover_grace_paths(path)
    except DiscoveryError as error:
        if as_json:
            _emit_json(_discovery_failure_payload("read", error.path, error.message))
            raise click.exceptions.Exit(code=1) from error
        _emit_discovery_failure(error.path, error.message)
        raise click.exceptions.Exit(code=1) from error

    if scope == "project":
        parsed_files, parse_failures = _parse_many(discovered_paths)
        if parse_failures:
            if as_json:
                _emit_json(_project_parse_failure_payload("read", path, parsed_files, parse_failures))
                raise click.exceptions.Exit(code=1)
            _emit_project_parse_failure(path, parse_failures)
            raise click.exceptions.Exit(code=1)
        grace_files = parsed_files
        grace_map = build_project_map(parsed_files)
    else:
        try:
            grace_file = parse_python_file(path)
        except GraceParseError as error:
            if as_json:
                _emit_json(_parse_error_payload("read", error))
                raise click.exceptions.Exit(code=1) from error
            _emit_parse_errors(error)
            raise click.exceptions.Exit(code=1) from error
        grace_files = (grace_file,)
        grace_map = build_file_map(grace_file)

    try:
        context = read_anchor_context(grace_files, grace_map, anchor_id)
    except ReadLookupError as error:
        if as_json:
            _emit_json(
                {
                    "ok": False,
                    "command": "read",
                    "scope": scope,
                    "stage": "read",
                    "path": str(path),
                    "target": anchor_id,
                    "message": str(error),
                }
            )
            raise click.exceptions.Exit(code=1) from error
        click.echo(str(error), err=True)
        raise click.exceptions.Exit(code=1) from error

    if as_json:
        _emit_json(
            {
                "ok": True,
                "command": "read",
                "scope": scope,
                "path": str(path),
                "target": anchor_id,
                "data": context.model_dump(mode="json"),
            }
        )
        return

    click.echo(f"Read {anchor_id} from {context.file_path}:{context.line_start}-{context.line_end}")
    click.echo(context.code.rstrip())


# @grace.anchor grace.cli.plan_group
# @grace.complexity 1
@app.group("plan", help="Build derived patch-planning proposals without changing repository state.")
def plan_group() -> None:
    pass


# @grace.anchor grace.cli.plan_impact_command
# @grace.complexity 5
# @grace.links grace.cli._load_grace_map_for_query, grace.planner.plan_from_impact
@plan_group.command("impact")
@click.argument("path", type=_path_argument(dir_okay=True))
@click.argument("anchor_id")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def plan_impact_command(path: Path, anchor_id: str, as_json: bool) -> None:
    from grace.planner import PlannerLookupError, plan_from_impact

    try:
        scope, grace_map = _load_grace_map_for_query(path)
        proposal = plan_from_impact(grace_map, anchor_id)
    except DiscoveryError as error:
        if as_json:
            _emit_json(_discovery_failure_payload("plan", error.path, error.message))
            raise click.exceptions.Exit(code=1) from error
        _emit_discovery_failure(error.path, error.message)
        raise click.exceptions.Exit(code=1) from error
    except GraceParseError as error:
        if as_json:
            _emit_json(_parse_error_payload("plan", error))
            raise click.exceptions.Exit(code=1) from error
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error
    except PlannerLookupError as error:
        if as_json:
            _emit_json(
                {
                    "ok": False,
                    "command": "plan",
                    "mode": "impact",
                    "scope": scope,
                    "stage": "plan",
                    "path": str(path),
                    "target": anchor_id,
                    "message": str(error),
                }
            )
            raise click.exceptions.Exit(code=1) from error
        click.echo(str(error), err=True)
        raise click.exceptions.Exit(code=1) from error

    payload = {"suggested_operations": [operation.model_dump(mode="json") for operation in proposal.suggested_operations]}
    if as_json:
        _emit_json(
            {
                "ok": True,
                "command": "plan",
                "mode": "impact",
                "scope": scope,
                "path": str(path),
                "target": anchor_id,
                "data": payload,
            }
        )
        return

    click.echo(f"Plan proposal for {anchor_id}: {len(proposal.suggested_operations)} suggested operation(s)")
    for operation in proposal.suggested_operations:
        click.echo(f"- {operation.operation}: {operation.anchor_id}")


# @grace.anchor grace.cli.patch_command
# @grace.complexity 4
# @grace.links grace.patcher.patch_block
@app.command("patch")
@click.argument("path", type=_path_argument(dir_okay=False))
@click.argument("anchor_id")
@click.argument("replacement_file", type=_path_argument(dir_okay=False))
@click.option("--dry-run", is_flag=True, help="Simulate the patch without writing to disk.")
@click.option("--preview", is_flag=True, help="Show a semantic block diff preview without writing to disk.")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def patch_command(path: Path, anchor_id: str, replacement_file: Path, dry_run: bool, preview: bool, as_json: bool) -> None:
    replacement_source = replacement_file.read_text(encoding="utf-8")
    result = patch_block(path, anchor_id, replacement_source, dry_run=(dry_run or preview))
    if isinstance(result, PatchFailure):
        if as_json:
            _emit_json(_patch_failure_payload(result))
            raise click.exceptions.Exit(code=1)
        _emit_patch_failure(result)
        raise click.exceptions.Exit(code=1)

    if as_json:
        _emit_json(_patch_success_payload(result))
        return

    if preview:
        _emit_patch_preview(result)
    _emit_patch_success(result)


# @grace.anchor grace.cli.apply_plan_command
# @grace.complexity 5
@app.command("apply-plan")
@click.argument("plan_file", type=_path_argument(dir_okay=False))
@click.option("--dry-run", is_flag=True, help="Simulate the full patch plan without writing to disk.")
@click.option("--preview", is_flag=True, help="Show semantic block diff previews for all plan entries without writing to disk.")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def apply_plan_command(plan_file: Path, dry_run: bool, preview: bool, as_json: bool) -> None:
    try:
        plan = load_patch_plan(plan_file)
    except (json.JSONDecodeError, ValueError) as error:
        if as_json:
            _emit_json(
                {
                    "ok": False,
                    "command": "apply-plan",
                    "scope": "project",
                    "stage": "plan_load",
                    "dry_run": dry_run or preview,
                    "preview": preview,
                    "plan_path": str(plan_file),
                    "message": str(error),
                }
            )
            raise click.exceptions.Exit(code=1) from error
        click.echo(f"Failed to load patch plan {plan_file}: {error}", err=True)
        raise click.exceptions.Exit(code=1) from error

    result = apply_patch_plan(plan, dry_run=dry_run, preview=preview)
    if isinstance(result, ApplyPlanFailure):
        if as_json:
            _emit_json(_apply_plan_failure_payload(plan_file, result))
            raise click.exceptions.Exit(code=1)
        if preview:
            _emit_apply_plan_preview(result)
        _emit_apply_plan_failure(plan_file, result)
        raise click.exceptions.Exit(code=1)

    if as_json:
        _emit_json(_apply_plan_success_payload(plan_file, result))
        return

    if preview:
        _emit_apply_plan_preview(result)
    _emit_apply_plan_success(plan_file, result)


# @grace.anchor grace.cli.main
# @grace.complexity 3
# @grace.links grace.clean_command.clean_command
def main(argv: list[str] | None = None) -> int:
    from grace.clean_command import clean_command

    if "clean" not in app.commands:
        app.add_command(clean_command, name="clean")
    try:
        app.main(args=argv, prog_name="grace", standalone_mode=False)
    except click.ClickException as error:
        error.show()
        return error.exit_code
    except click.exceptions.Exit as error:
        return error.exit_code
    return 0


__all__ = ["app", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
