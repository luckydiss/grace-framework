# @grace.module grace.bootstrap_command
# @grace.purpose Expose a thin CLI surface for deterministic GRACE bootstrap scaffolding without introducing new parser or patch semantics.
# @grace.interfaces bootstrap_command(path, preview=True, as_json=False)->None
# @grace.invariant Bootstrap command must default to preview mode and must never write files unless explicitly switched to apply mode.
# @grace.invariant JSON output must remain auditable and deterministic so shell-driven agents can consume scaffold results without reading full file contents.
from __future__ import annotations

import json
from pathlib import Path

import click

from grace.bootstrapper import BootstrapFailure, bootstrap_path


# @grace.anchor grace.bootstrap_command.bootstrap_command
# @grace.complexity 4
# @grace.links grace.bootstrapper.bootstrap_path
@click.command("bootstrap")
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path))
@click.option("--preview/--apply", "preview_mode", default=True, help="Preview scaffold changes by default; use --apply to write files.")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def bootstrap_command(path: Path, preview_mode: bool, as_json: bool) -> None:
    result = bootstrap_path(path, apply=not preview_mode)
    payload = {
        "ok": result.ok,
        "command": "bootstrap",
        "apply": not preview_mode,
        "requested_path": str(result.requested_path),
        "file_count": len(result.file_changes),
        "files": [
            {
                "path": str(file_change.path),
                "module_id": file_change.module_id,
                "header_added": file_change.header_added,
                "original_hash": file_change.original_hash,
                "updated_hash": file_change.updated_hash,
                "generated_anchor_ids": [anchor.anchor_id for anchor in file_change.generated_anchors],
                "generated_anchors": [
                    {
                        "anchor_id": anchor.anchor_id,
                        "kind": anchor.kind,
                        "symbol_name": anchor.symbol_name,
                        "target_line_start": anchor.target_line_start,
                        "target_line_end": anchor.target_line_end,
                        "insertion_line_start": anchor.insertion_line_start,
                    }
                    for anchor in file_change.generated_anchors
                ],
            }
            for file_change in result.file_changes
        ],
    }

    if isinstance(result, BootstrapFailure):
        payload.update(
            {
                "stage": result.stage.value,
                "message": result.message,
                "rollback_performed": result.rollback_performed,
                "parse_failures": [str(failure.path) for failure in result.parse_failures],
                "validation_messages": list(result.validation_messages),
            }
        )

    if isinstance(result, BootstrapFailure):
        if as_json:
            click.echo(json.dumps(payload, indent=2))
        else:
            click.echo(f"Bootstrap failed at stage {result.stage.value}: {result.message}")
        raise click.exceptions.Exit(code=1)

    if as_json:
        payload["validated_file_count"] = result.validated_file_count
        click.echo(json.dumps(payload, indent=2))
        return

    if preview_mode:
        click.echo(
            f"Bootstrap preview for {path}: {len(result.file_changes)} file(s) would change"
        )
        for file_change in result.file_changes:
            click.echo(f"- {file_change.preview}")
        return

    click.echo(
        f"Bootstrapped {len(result.file_changes)} file(s) under {path} "
        f"and validated {result.validated_file_count} file(s)"
    )


__all__ = ["bootstrap_command"]
