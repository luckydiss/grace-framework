from __future__ import annotations

import json
from pathlib import Path

import click

from grace.linter import LintFailure, lint_file
from grace.map import build_file_map, map_to_dict
from grace.patcher import PatchFailure, patch_block
from grace.parser import GraceParseError, parse_python_file
from grace.validator import ValidationFailure, validate_file


def _path_argument() -> click.Path:
    return click.Path(exists=True, dir_okay=False, path_type=Path)


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


@click.group(help="GRACE v1 CLI")
def app() -> None:
    pass


@app.command("parse")
@click.argument("path", type=_path_argument())
def parse_command(path: Path) -> None:
    try:
        grace_file = parse_python_file(path)
    except GraceParseError as error:
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error

    click.echo(f"Parsed module {grace_file.module.module_id} with {len(grace_file.blocks)} block(s)")


@app.command("validate")
@click.argument("path", type=_path_argument())
def validate_command(path: Path) -> None:
    try:
        grace_file = parse_python_file(path)
    except GraceParseError as error:
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error

    result = validate_file(grace_file)
    if isinstance(result, ValidationFailure):
        _emit_validation_failure(result)
        raise click.exceptions.Exit(code=1)

    click.echo(f"Validated module {grace_file.module.module_id} successfully")


@app.command("lint")
@click.argument("path", type=_path_argument())
def lint_command(path: Path) -> None:
    try:
        grace_file = parse_python_file(path)
    except GraceParseError as error:
        _emit_parse_errors(error)
        raise click.exceptions.Exit(code=1) from error

    validation_result = validate_file(grace_file)
    if isinstance(validation_result, ValidationFailure):
        _emit_validation_failure(validation_result)
        raise click.exceptions.Exit(code=1)

    lint_result = lint_file(grace_file)
    if isinstance(lint_result, LintFailure):
        _emit_lint_warnings(lint_result)
        return

    click.echo(f"Lint passed for module {grace_file.module.module_id}")


@app.command("map")
@click.argument("path", type=_path_argument())
@click.option("--json", "as_json", is_flag=True, help="Print a JSON-friendly GRACE map payload.")
def map_command(path: Path, as_json: bool) -> None:
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
@click.argument("path", type=_path_argument())
@click.argument("anchor_id")
@click.argument("replacement_file", type=_path_argument())
def patch_command(path: Path, anchor_id: str, replacement_file: Path) -> None:
    replacement_source = replacement_file.read_text(encoding="utf-8")
    result = patch_block(path, anchor_id, replacement_source)
    if isinstance(result, PatchFailure):
        _emit_patch_failure(result)
        raise click.exceptions.Exit(code=1)

    click.echo(f"Patched {result.anchor_id} in {result.path}")
    if result.lint_issues:
        click.echo(f"Lint warnings: {len(result.lint_issues)}")
        for issue in result.lint_issues:
            click.echo(f"- {issue.code.value}: {issue.message}")


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
