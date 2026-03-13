from __future__ import annotations

import importlib.util
import sys
import textwrap
import types
from functools import lru_cache
from pathlib import Path

from click.testing import CliRunner
import pytest


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def load_modules():
    for module_name in (
        "grace",
        "grace.models",
        "grace.parser",
        "grace.language_adapter",
        "grace.python_adapter",
        "grace.validator",
        "grace.linter",
        "grace.patcher",
        "grace.plan",
        "grace.cli",
    ):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in ("models", "parser", "validator", "linter", "patcher", "plan", "cli"):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return (
        loaded["models"],
        loaded["parser"],
        loaded["validator"],
        loaded["linter"],
        loaded["patcher"],
        loaded["plan"],
        loaded["cli"],
    )


MODELS, PARSER, VALIDATOR, LINTER, PATCHER, PLAN, CLI = load_modules()


@pytest.fixture(autouse=True)
def _reload_modules():
    global MODELS, PARSER, VALIDATOR, LINTER, PATCHER, PLAN, CLI
    load_modules.cache_clear()
    MODELS, PARSER, VALIDATOR, LINTER, PATCHER, PLAN, CLI = load_modules()


def write_temp_file(tmp_path: Path, content: str, name: str) -> Path:
    writable_dir = tmp_path.parent / f"{tmp_path.name}_patcher_path_files"
    writable_dir.mkdir(parents=True, exist_ok=True)
    try:
        writable_dir.chmod(0o777)
    except OSError:
        pass
    path = writable_dir / name
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def module_header(
    *,
    module_id: str = "billing.pricing",
    purpose: str = "Determine pricing behavior.",
    interfaces: str = "apply_discount(price:int, percent:int) -> int",
    invariants: tuple[str, ...] = (
        "Discount percent must never be negative.",
        "Anchor ids remain stable for unchanged semantics.",
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
    anchor: str = "billing.pricing.apply_discount",
    complexity: str = "1",
    belief: str | None = None,
    links: str | None = None,
    signature: str = "def apply_discount(price: int, percent: int) -> int:",
    body: str = "    return price - ((price * percent) // 100)",
) -> str:
    lines = [
        f"# @grace.anchor {anchor}",
        f"# @grace.complexity {complexity}",
    ]
    if belief is not None:
        lines.append(f"# @grace.belief {belief}")
    if links is not None:
        lines.append(f"# @grace.links {links}")
    lines.extend([signature, body])
    return "\n".join(lines)


def make_file(*sections: str, header: str | None = None) -> str:
    active_header = header if header is not None else module_header()
    body = "\n\n".join(section.strip("\n") for section in sections)
    return f"{active_header.rstrip()}\n\n{body}\n"


def replacement_block(return_value: int) -> str:
    return (
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 2\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        f"    return {return_value}\n"
    )


def runner() -> CliRunner:
    return CliRunner()


def test_patch_block_accepts_relative_path_and_returns_canonical_path(tmp_path: Path, monkeypatch) -> None:
    pricing_path = write_temp_file(tmp_path, make_file(function_block()), "pricing.py")
    monkeypatch.chdir(pricing_path.parent)

    result = PATCHER.patch_block(Path("pricing.py"), "billing.pricing.apply_discount", replacement_block(42))

    assert isinstance(result, PATCHER.PatchSuccess)
    assert result.path == pricing_path.resolve()
    assert result.file.path == pricing_path.resolve()
    assert "return 42" in pricing_path.read_text(encoding="utf-8")


def test_patch_block_accepts_absolute_path_and_returns_canonical_path(tmp_path: Path) -> None:
    pricing_path = write_temp_file(tmp_path, make_file(function_block()), "pricing.py")

    result = PATCHER.patch_block(pricing_path.resolve(), "billing.pricing.apply_discount", replacement_block(43))

    assert isinstance(result, PATCHER.PatchSuccess)
    assert result.path == pricing_path.resolve()
    assert result.file.path == pricing_path.resolve()
    assert "return 43" in pricing_path.read_text(encoding="utf-8")


def test_apply_patch_plan_uses_canonical_paths_for_relative_entries(tmp_path: Path, monkeypatch) -> None:
    pricing_path = write_temp_file(tmp_path, make_file(function_block()), "pricing.py")
    monkeypatch.chdir(pricing_path.parent)
    plan = PLAN.PatchPlan(
        entries=(
            PLAN.PatchPlanEntry(
                path=Path("pricing.py"),
                anchor_id="billing.pricing.apply_discount",
                replacement_source=replacement_block(44),
            ),
        )
    )

    dry_run_result = PLAN.apply_patch_plan(plan, dry_run=True, preview=True)
    assert isinstance(dry_run_result, PLAN.ApplyPlanSuccess)
    assert dry_run_result.entries[0].path == pricing_path.resolve()
    assert dry_run_result.entries[0].result.path == pricing_path.resolve()
    assert "return 44" not in pricing_path.read_text(encoding="utf-8")

    result = PLAN.apply_patch_plan(plan)
    assert isinstance(result, PLAN.ApplyPlanSuccess)
    assert result.entries[0].path == pricing_path.resolve()
    assert result.entries[0].result.path == pricing_path.resolve()
    assert "return 44" in pricing_path.read_text(encoding="utf-8")


def test_patch_block_dry_run_and_preview_are_consistent_for_relative_and_absolute_paths(
    tmp_path: Path, monkeypatch
) -> None:
    pricing_path = write_temp_file(tmp_path, make_file(function_block()), "pricing.py")
    monkeypatch.chdir(pricing_path.parent)
    replacement = replacement_block(45)

    relative_result = PATCHER.patch_block(Path("pricing.py"), "billing.pricing.apply_discount", replacement, dry_run=True)
    absolute_result = PATCHER.patch_block(pricing_path.resolve(), "billing.pricing.apply_discount", replacement, dry_run=True)

    assert isinstance(relative_result, PATCHER.PatchSuccess)
    assert isinstance(absolute_result, PATCHER.PatchSuccess)
    assert relative_result.path == absolute_result.path == pricing_path.resolve()
    assert relative_result.preview == absolute_result.preview
    assert relative_result.before_hash == absolute_result.before_hash
    assert relative_result.after_hash == absolute_result.after_hash
    assert pricing_path.read_text(encoding="utf-8").count("return 45") == 0


def test_cli_patch_smoke_supports_relative_and_absolute_paths(tmp_path: Path, monkeypatch) -> None:
    pricing_path = write_temp_file(tmp_path, make_file(function_block()), "pricing.py")
    relative_replacement = write_temp_file(tmp_path, replacement_block(46), "replacement.relative.pyfrag")
    absolute_replacement = write_temp_file(tmp_path, replacement_block(47), "replacement.absolute.pyfrag")
    monkeypatch.chdir(pricing_path.parent)

    relative_result = runner().invoke(
        CLI.app,
        ["patch", "pricing.py", "billing.pricing.apply_discount", relative_replacement.name, "--json"],
    )

    assert relative_result.exit_code == 0
    assert "return 46" in pricing_path.read_text(encoding="utf-8")

    absolute_result = runner().invoke(
        CLI.app,
        [
            "patch",
            str(pricing_path.resolve()),
            "billing.pricing.apply_discount",
            str(absolute_replacement.resolve()),
            "--json",
        ],
    )

    assert absolute_result.exit_code == 0
    assert "return 47" in pricing_path.read_text(encoding="utf-8")
