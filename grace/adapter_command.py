# @grace.module grace.adapter_command
# @grace.purpose Expose deterministic adapter probe, gap, and evaluation commands so agents can inspect repository language coverage without mutating files.
# @grace.interfaces adapter_group, probe_command, gaps_command, eval_command
# @grace.invariant Adapter CLI commands remain read-only and report only derived language-pack and file-policy state.

from __future__ import annotations

import json
from pathlib import Path

import click

from grace.adapter_tools import collect_adapter_gaps, evaluate_adapter_surface, probe_adapter
from grace.bootstrap_safety import evaluate_bootstrap_safety


# @grace.anchor grace.adapter_command.adapter_group
# @grace.complexity 1
@click.group("adapter", help="Inspect adapter routing, file policy, and repository coverage gaps.")
def adapter_group() -> None:
    pass


# @grace.anchor grace.adapter_command.probe_command
# @grace.complexity 2
# @grace.links grace.adapter_tools.probe_adapter
@adapter_group.command("probe")
@click.argument("path", type=click.Path(exists=False, file_okay=True, dir_okay=False, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def probe_command(path: Path, as_json: bool) -> None:
    probe = probe_adapter(path)
    payload = {
        "ok": True,
        "command": "adapter",
        "action": "probe",
        **probe.model_dump(mode="json"),
    }

    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return

    click.echo(
        f"Adapter probe for {probe.path}: "
        f"language={probe.language_name or 'unregistered'}, "
        f"policy={probe.policy_verdict}, "
        f"adapter={probe.adapter_class_name or 'none'}"
    )


# @grace.anchor grace.adapter_command.gaps_command
# @grace.complexity 2
# @grace.links grace.adapter_tools.collect_adapter_gaps
@adapter_group.command("gaps")
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def gaps_command(path: Path, as_json: bool) -> None:
    gaps = collect_adapter_gaps(path)
    payload = {
        "ok": True,
        "command": "adapter",
        "action": "gaps",
        "path": str(path),
        "gap_count": len(gaps),
        "gaps": [gap.model_dump(mode="json") for gap in gaps],
    }

    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return

    click.echo(f"Adapter gaps for {path}: {len(gaps)} file(s)")
    for gap in gaps:
        click.echo(f"- {gap.path}: {gap.gap_kind} ({gap.reason})")


# @grace.anchor grace.adapter_command.eval_command
# @grace.complexity 2
# @grace.links grace.adapter_tools.evaluate_adapter_surface
@adapter_group.command("eval")
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def eval_command(path: Path, as_json: bool) -> None:
    evaluation = evaluate_adapter_surface(path)
    payload = {
        "ok": True,
        "command": "adapter",
        "action": "eval",
        **evaluation.model_dump(mode="json"),
    }

    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return

    click.echo(
        f"Adapter eval for {evaluation.requested_path}: {evaluation.file_count} file(s), "
        f"{sum(evaluation.gap_counts.values())} gap(s)"
    )


# @grace.anchor grace.adapter_command.safety_command
# @grace.complexity 2
# @grace.links grace.bootstrap_safety.evaluate_bootstrap_safety
@adapter_group.command("safety")
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Print a JSON result envelope for agent use.")
def safety_command(path: Path, as_json: bool) -> None:
    safety = evaluate_bootstrap_safety(path)
    payload = {
        "ok": True,
        "command": "adapter",
        "action": "safety",
        **safety.model_dump(mode="json"),
    }

    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return

    click.echo(
        f"Bootstrap safety for {safety.requested_path}: {safety.safe_file_count}/{safety.file_count} "
        f"file(s) safe for apply"
    )
