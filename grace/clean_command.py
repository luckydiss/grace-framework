# @grace.module grace.clean_command
# @grace.purpose Expose a thin CLI command that removes deterministic GRACE temp artifacts without touching annotated source files.
# @grace.interfaces clean_command(path, *, dry_run=False, as_json=False)->None
# @grace.invariant Clean command must operate only on derived temp artifacts and must not delete GRACE source files or committed examples.
# @grace.invariant JSON output should stay deterministic so shell-driven agents can compose cleanup into existing workflows.
from __future__ import annotations

from pathlib import Path

import click

from grace.artifact_hygiene import clean_artifacts


# @grace.anchor grace.clean_command.clean_command
# @grace.complexity 4
# @grace.links grace.artifact_hygiene.clean_artifacts
@click.command("clean")
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path))
@click.option("--dry-run", is_flag=True, help="Preview which deterministic GRACE temp artifacts would be removed.")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def clean_command(path: Path, dry_run: bool, as_json: bool) -> None:
    result = clean_artifacts(path, dry_run=dry_run)
    payload = {
        "ok": len(result.failed_paths) == 0,
        "command": "clean",
        "path": str(path),
        "scope_root": str(result.root_path),
        "dry_run": result.dry_run,
        "cleaned_count": len(result.cleaned_paths),
        "failed_count": len(result.failed_paths),
        "cleaned_paths": [str(candidate) for candidate in result.cleaned_paths],
        "failed_paths": [str(candidate) for candidate in result.failed_paths],
    }

    if as_json:
        click.echo(__import__("json").dumps(payload, indent=2))
        if result.failed_paths:
            raise click.exceptions.Exit(code=1)
        return

    if result.dry_run:
        click.echo(f"Dry-run cleanup for {result.root_path}: {len(result.cleaned_paths)} artifact(s)")
    else:
        click.echo(f"Cleaned {len(result.cleaned_paths)} artifact(s) under {result.root_path}")

    for candidate in result.cleaned_paths:
        click.echo(f"- {candidate}")

    if result.failed_paths:
        for candidate in result.failed_paths:
            click.echo(f"! failed: {candidate}", err=True)
        raise click.exceptions.Exit(code=1)


__all__ = ["clean_command"]
