# @grace.module grace.grammar_command
# @grace.purpose Expose explicit grammar installation and build commands so repo-local external specs can resolve Tree-sitter grammars without editing GRACE package code.
# @grace.interfaces grammar_group, list_command, install_command, build_command
# @grace.invariant Grammar CLI remains explicit and auditable; it may write cache manifests and compiled libraries, but it must not run implicitly during normal parse or bootstrap commands.

from __future__ import annotations

import json
from pathlib import Path

import click

from grace.grammar_manager import (
    GrammarInstallRecord,
    build_grammar_from_source,
    install_grammar_record,
    list_installed_grammars,
    resolve_grammar_cache_dir,
)


# @grace.anchor grace.grammar_command.grammar_group
# @grace.complexity 1
@click.group("grammar", help="Manage external Tree-sitter grammar cache records.")
def grammar_group() -> None:
    pass


# @grace.anchor grace.grammar_command.list_command
# @grace.complexity 2
@grammar_group.command("list")
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path), default=".", required=False)
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def list_command(path: Path, as_json: bool) -> None:
    records = list_installed_grammars(path)
    payload = {
        "ok": True,
        "command": "grammar",
        "action": "list",
        "path": str(path),
        "cache_dir": str(resolve_grammar_cache_dir(path)),
        "count": len(records),
        "records": [record.model_dump(mode="json") for record in records],
    }
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    click.echo(f"Installed grammars for {path}: {len(records)}")
    for record in records:
        click.echo(f"- {record.language_name}: {record.provider}")


# @grace.anchor grace.grammar_command.install_command
# @grace.complexity 3
@grammar_group.command("install")
@click.argument("language_name")
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path), default=".", required=False)
@click.option("--callable-target", help="Python callable target in module:attribute form.")
@click.option("--library-path", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path), help="Compiled grammar library to register.")
@click.option("--symbol", help="Tree-sitter exported symbol name for compiled libraries.")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def install_command(
    language_name: str,
    path: Path,
    callable_target: str | None,
    library_path: Path | None,
    symbol: str | None,
    as_json: bool,
) -> None:
    if bool(callable_target) == bool(library_path):
        raise click.ClickException("provide exactly one of --callable-target or --library-path")

    if callable_target is not None:
        record = GrammarInstallRecord(
            language_name=language_name,
            provider="python_callable",
            target=callable_target,
        )
    else:
        record = GrammarInstallRecord(
            language_name=language_name,
            provider="compiled_library",
            library_path=str(library_path),
            symbol=symbol or f"tree_sitter_{language_name.replace('-', '_')}",
        )

    record_path = install_grammar_record(record, path)
    payload = {
        "ok": True,
        "command": "grammar",
        "action": "install",
        "language_name": language_name,
        "record_path": str(record_path),
        "record": record.model_dump(mode="json"),
    }
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    click.echo(f"Installed grammar record for {language_name}: {record_path}")


# @grace.anchor grace.grammar_command.build_command
# @grace.complexity 3
@grammar_group.command("build")
@click.argument("language_name")
@click.argument("source_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path), default=".", required=False)
@click.option("--symbol", help="Override the exported Tree-sitter symbol name.")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def build_command(language_name: str, source_dir: Path, path: Path, symbol: str | None, as_json: bool) -> None:
    output_path = build_grammar_from_source(language_name, source_dir, path, symbol=symbol)
    payload = {
        "ok": True,
        "command": "grammar",
        "action": "build",
        "language_name": language_name,
        "source_dir": str(source_dir),
        "output_path": str(output_path),
        "cache_dir": str(resolve_grammar_cache_dir(path)),
    }
    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return
    click.echo(f"Built grammar for {language_name}: {output_path}")
