from __future__ import annotations

import importlib.util
import json
import sys
import textwrap
import types
from functools import lru_cache
from pathlib import Path

from click.testing import CliRunner
import pytest


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def load_cli_modules():
    for module_name in (
        "grace",
        "grace.models",
        "grace.parser",
        "grace.language_adapter",
        "grace.python_adapter",
        "grace.validator",
        "grace.linter",
        "grace.map",
        "grace.patcher",
        "grace.plan",
        "grace.query",
        "grace.impact",
        "grace.read",
        "grace.planner",
        "grace.cli",
    ):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "validator", "linter", "map", "patcher", "plan", "query", "impact", "read", "planner", "cli"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return loaded["cli"]


CLI = load_cli_modules()


@pytest.fixture(autouse=True)
def _reload_modules():
    global CLI
    load_cli_modules.cache_clear()
    CLI = load_cli_modules()


def runner() -> CliRunner:
    return CliRunner()


def write_temp_python_file(base_dir: Path, relative_path: str, content: str) -> Path:
    path = base_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def module_header(
    *,
    module_id: str,
    purpose: str = "Determine pricing behavior.",
    interfaces: str = "run() -> None",
    invariants: tuple[str, ...] = (
        "Anchor ids remain stable for unchanged semantics.",
        "Dependencies are explicit through grace.links.",
    ),
) -> str:
    invariant_lines = "\n".join(f"# @grace.invariant {value}" for value in invariants)
    return (
        f"# @grace.module {module_id}\n"
        f"# @grace.purpose {purpose}\n"
        f"# @grace.interfaces {interfaces}\n"
        f"{invariant_lines}\n"
    )


def function_block(
    *,
    anchor: str,
    complexity: str = "1",
    belief: str | None = None,
    links: str | None = None,
    signature: str,
    body: str,
) -> str:
    lines = [f"# @grace.anchor {anchor}", f"# @grace.complexity {complexity}"]
    if belief is not None:
        lines.append(f"# @grace.belief {belief}")
    if links is not None:
        lines.append(f"# @grace.links {links}")
    lines.extend([signature, body])
    return "\n".join(lines)


def make_file(header: str, *sections: str) -> str:
    body = "\n\n".join(section.strip("\n") for section in sections)
    return f"{header.rstrip()}\n\n{body}\n"


def build_repo_dir(tmp_path: Path) -> Path:
    repo_dir = tmp_path.parent / f"{tmp_path.name}_planner_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    write_temp_python_file(
        repo_dir,
        "src/pricing.py",
        make_file(
            module_header(
                module_id="billing.pricing",
                interfaces="choose_discount_strategy(customer_tier:str) -> int",
            ),
            function_block(
                anchor="billing.pricing.choose_discount_strategy",
                complexity="6",
                belief="Pricing thresholds remain deterministic for the project baseline.",
                links="billing.tax.apply_tax",
                signature="def choose_discount_strategy(customer_tier: str) -> int:",
                body="    return 0",
            ),
        ),
    )
    write_temp_python_file(
        repo_dir,
        "src/reporting.py",
        make_file(
            module_header(module_id="billing.reporting", interfaces="build_tax_report() -> int"),
            function_block(
                anchor="billing.reporting.build_tax_report",
                links="billing.tax.apply_tax",
                signature="def build_tax_report() -> int:",
                body="    return 1",
            ),
        ),
    )
    write_temp_python_file(
        repo_dir,
        "src/audit.py",
        make_file(
            module_header(module_id="billing.audit", interfaces="record_tax_trace() -> None"),
            function_block(
                anchor="billing.audit.record_tax_trace",
                links="billing.reporting.build_tax_report",
                signature="def record_tax_trace() -> None:",
                body="    return None",
            ),
        ),
    )
    write_temp_python_file(
        repo_dir,
        "src/tax.py",
        make_file(
            module_header(module_id="billing.tax", interfaces="apply_tax(amount:int) -> int"),
            function_block(
                anchor="billing.tax.apply_tax",
                signature="def apply_tax(amount: int) -> int:",
                body="    return amount",
            ),
        ),
    )
    return repo_dir


def test_cli_plan_impact_json_returns_suggested_replace_block_operations(tmp_path: Path) -> None:
    repo_dir = build_repo_dir(tmp_path)

    result = runner().invoke(CLI.app, ["plan", "impact", str(repo_dir), "billing.tax.apply_tax", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "plan"
    assert payload["mode"] == "impact"
    assert payload["target"] == "billing.tax.apply_tax"
    assert [entry["anchor_id"] for entry in payload["data"]["suggested_operations"]] == [
        "billing.pricing.choose_discount_strategy",
        "billing.reporting.build_tax_report",
    ]
    assert all(entry["operation"] == "replace_block" for entry in payload["data"]["suggested_operations"])


def test_cli_plan_impact_json_can_return_empty_plan(tmp_path: Path) -> None:
    repo_dir = build_repo_dir(tmp_path)

    result = runner().invoke(CLI.app, ["plan", "impact", str(repo_dir), "billing.audit.record_tax_trace", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["data"]["suggested_operations"] == []


def test_cli_plan_impact_unknown_anchor_returns_stable_failure(tmp_path: Path) -> None:
    repo_dir = build_repo_dir(tmp_path)

    result = runner().invoke(CLI.app, ["plan", "impact", str(repo_dir), "billing.unknown.anchor", "--json"])

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "plan"
    assert payload["mode"] == "impact"
    assert payload["stage"] == "plan"
    assert payload["target"] == "billing.unknown.anchor"
