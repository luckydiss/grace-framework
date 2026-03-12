from __future__ import annotations

import json
import os
from pathlib import Path

import click

from grace.linter import LintFailure, lint_file, lint_project
from grace.map import build_file_map, build_project_map, map_to_dict
from grace.patcher import PatchFailure, PatchStepResult, patch_block
from grace.plan import ApplyPlanFailure, ApplyPlanSuccess, apply_patch_plan, load_patch_plan
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


class DiscoveryError(ValueError):
    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(message)


def _path_argument(*, dir_okay: bool) -> click.Path:
    return click.Path(exists=True, file_okay=True, dir_okay=dir_okay, path_type=Path)


def _emit_json(payload: dict) -> None:
    click.echo(json.dumps(payload, indent=2))


def _serialize_file(grace_file: GraceFileModel) -> dict:
    return grace_file.model_dump(mode="json")


def _serialize_parse_failure(result: GraceParseFailure) -> dict:
    return {
        "path": str(result.path),
        "errors": [issue.model_dump(mode="json") for issue in result.errors],
    }


def _parse_error_payload(command: str, error: GraceParseError) -> dict:
    return {
        "ok": False,
        "command": command,
        "scope": "file",
        "stage": "parse",
        "path": str(error.path),
        "errors": [issue.model_dump(mode="json") for issue in error.errors],
    }


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


def _validation_failure_payload(path: Path, result: ValidationFailure) -> dict:
    return {
        "ok": False,
        "command": "validate",
        "scope": result.scope,
        "stage": "validate",
        "path": str(path),
        "issues": [issue.model_dump(mode="json") for issue in result.issues],
    }


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


def _apply_plan_success_payload(plan_path: Path, result: ApplyPlanSuccess) -> dict:
    return {
        "ok": True,
        "command": "apply-plan",
        "scope": "project",
        "plan_path": str(plan_path),
        "entry_count": result.entry_count,
        "applied_count": result.applied_count,
        "entries": [_serialize_applied_patch_entry(entry) for entry in result.entries],
    }


def _apply_plan_failure_payload(plan_path: Path, result: ApplyPlanFailure) -> dict:
    return {
        "ok": False,
        "command": "apply-plan",
        "scope": "project",
        "stage": "apply_plan",
        "plan_path": str(plan_path),
        "entry_count": result.entry_count,
        "applied_count": result.applied_count,
        "failed_index": result.failed_index,
        "message": result.message,
        "entries": [_serialize_applied_patch_entry(entry) for entry in result.entries],
    }


def _serialize_patch_step(step: PatchStepResult) -> dict:
    return {
        "status": step.status.value,
        "ok": step.status.value == "passed",
        "issue_count": step.issue_count,
    }


def _serialize_applied_patch_entry(entry) -> dict:
    return {
        "index": entry.index,
        "path": str(entry.path),
        "anchor_id": entry.anchor_id,
        "operation": entry.operation.value,
        "result": _serialize_patch_result(entry.result),
    }


def _serialize_patch_result(result) -> dict:
    if isinstance(result, PatchFailure):
        payload = _patch_failure_payload(result)
    else:
        payload = _patch_success_payload(result)
    payload.pop("command", None)
    payload.pop("scope", None)
    return payload


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


def _discovery_failure_payload(command: str, path: Path, message: str) -> dict:
    return {
        "ok": False,
        "command": command,
        "scope": "project",
        "stage": "discovery",
        "path": str(path),
        "message": message,
    }


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


def _discover_grace_paths(path: Path) -> tuple[str, tuple[Path, ...]]:
    if path.is_file():
        return "file", (path,)

    discovered_paths: list[Path] = []
    for current_root, dir_names, file_names in os.walk(path):
        dir_names[:] = [
            dir_name
            for dir_name in dir_names
            if dir_name not in IGNORED_DISCOVERY_DIR_NAMES and not dir_name.endswith(".egg-info")
        ]

        root_path = Path(current_root)
        for file_name in sorted(file_names):
            if not file_name.endswith(".py"):
                continue
            candidate_path = root_path / file_name
            try:
                source_text = candidate_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "@grace." in source_text:
                discovered_paths.append(candidate_path)

    discovered_paths.sort(key=lambda candidate: candidate.relative_to(path).as_posix())
    if not discovered_paths:
        raise DiscoveryError(path, f"no GRACE-annotated Python files found under {path}")
    return "project", tuple(discovered_paths)


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


def _emit_project_parse_failure(path: Path, parse_failures: tuple[GraceParseFailure, ...]) -> None:
    click.echo(f"Parse failed for project {path}", err=True)
    for failure in parse_failures:
        click.echo(f"- file: {failure.path}", err=True)
        for issue in failure.errors:
            location = f" line {issue.line}" if issue.line is not None else ""
            click.echo(f"  - {issue.code.value}{location}: {issue.message}", err=True)


def _emit_discovery_failure(path: Path, message: str) -> None:
    click.echo(f"Discovery failed for {path}: {message}", err=True)


def _emit_parse_errors(error: GraceParseError) -> None:
    click.echo(f"Parse failed for {error.path}", err=True)
    for issue in error.errors:
        location = f" line {issue.line}" if issue.line is not None else ""
        click.echo(f"- {issue.code.value}{location}: {issue.message}", err=True)


def _emit_validation_failure(result: ValidationFailure) -> None:
    click.echo("Validation failed", err=True)
    for issue in result.issues:
        click.echo(f"- {issue.code.value}: {issue.message}", err=True)


def _emit_lint_warnings(result: LintFailure) -> None:
    click.echo(f"Lint warnings: {len(result.issues)}")
    for issue in result.issues:
        click.echo(f"- {issue.code.value}: {issue.message}")


def _emit_patch_failure(result: PatchFailure) -> None:
    click.echo(f"Patch failed at stage {result.stage.value}: {result.message}", err=True)
    for issue in result.parse_errors:
        location = f" line {issue.line}" if issue.line is not None else ""
        click.echo(f"- {issue.code.value}{location}: {issue.message}", err=True)
    for issue in result.validation_issues:
        click.echo(f"- {issue.code.value}: {issue.message}", err=True)


def _emit_patch_preview(result) -> None:
    click.echo(f"Patch preview for {result.anchor_id} in {result.path}")
    click.echo(result.preview if result.preview else "(no diff)")


def _emit_patch_success(result) -> None:
    if result.dry_run:
        click.echo(f"Dry-run succeeded for {result.anchor_id} in {result.path}")
    else:
        click.echo(f"Patched {result.anchor_id} in {result.path}")
    if result.lint_issues:
        click.echo(f"Lint warnings: {len(result.lint_issues)}")
        for issue in result.lint_issues:
            click.echo(f"- {issue.code.value}: {issue.message}")


def _emit_apply_plan_success(plan_path: Path, result: ApplyPlanSuccess) -> None:
    click.echo(f"Applied patch plan {plan_path}: {result.applied_count}/{result.entry_count} entry(s) succeeded")


def _emit_apply_plan_failure(plan_path: Path, result: ApplyPlanFailure) -> None:
    click.echo(
        f"Patch plan failed at entry {result.failed_index} in {plan_path}: {result.message}",
        err=True,
    )
    failed_entry = result.entries[-1]
    failed_result = failed_entry.result
    if isinstance(failed_result, PatchFailure):
        _emit_patch_failure(failed_result)


@click.group(help="GRACE v1 CLI")
def app() -> None:
    pass


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


@app.command("apply-plan")
@click.argument("plan_file", type=_path_argument(dir_okay=False))
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def apply_plan_command(plan_file: Path, as_json: bool) -> None:
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
                    "plan_path": str(plan_file),
                    "message": str(error),
                }
            )
            raise click.exceptions.Exit(code=1) from error
        click.echo(f"Failed to load patch plan {plan_file}: {error}", err=True)
        raise click.exceptions.Exit(code=1) from error

    result = apply_patch_plan(plan)
    if isinstance(result, ApplyPlanFailure):
        if as_json:
            _emit_json(_apply_plan_failure_payload(plan_file, result))
            raise click.exceptions.Exit(code=1)
        _emit_apply_plan_failure(plan_file, result)
        raise click.exceptions.Exit(code=1)

    if as_json:
        _emit_json(_apply_plan_success_payload(plan_file, result))
        return

    _emit_apply_plan_success(plan_file, result)


def main(argv: list[str] | None = None) -> int:
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
