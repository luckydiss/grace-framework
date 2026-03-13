from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
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
        "grace.artifact_hygiene",
        "grace.clean_command",
        "grace.map",
        "grace.patcher",
        "grace.plan",
        "grace.query",
        "grace.cli",
    ):
        sys.modules.pop(module_name, None)

    grace_package = types.ModuleType("grace")
    grace_package.__path__ = [str(ROOT / "grace")]
    sys.modules["grace"] = grace_package

    loaded = {}
    for module_name in (
        "models",
        "parser",
        "validator",
        "linter",
        "artifact_hygiene",
        "clean_command",
        "map",
        "patcher",
        "plan",
        "query",
        "cli",
    ):
        spec = importlib.util.spec_from_file_location(f"grace.{module_name}", ROOT / "grace" / f"{module_name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"grace.{module_name}"] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module

    return loaded["cli"]


CLI = load_modules()


@pytest.fixture
def writable_repo(tmp_path: Path) -> Path:
    repo = tmp_path.parent / f"{tmp_path.name}_cli_clean_repo"
    repo.mkdir(parents=True, exist_ok=True)
    try:
        repo.chmod(0o777)
    except OSError:
        pass
    (repo / ".gitignore").write_text("", encoding="utf-8")
    try:
        yield repo
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return path


def make_grace_file() -> str:
    return (
        "# @grace.module billing.pricing\n"
        "# @grace.purpose Determine pricing behavior.\n"
        "# @grace.interfaces apply_discount(price:int, percent:int) -> int\n"
        "# @grace.invariant Discount percent must never be negative.\n\n"
        "# @grace.anchor billing.pricing.apply_discount\n"
        "# @grace.complexity 1\n"
        "def apply_discount(price: int, percent: int) -> int:\n"
        "    return price - ((price * percent) // 100)\n"
    )


def runner() -> CliRunner:
    return CliRunner()


def test_cli_clean_dry_run_json_reports_temp_artifacts_without_deleting(writable_repo: Path) -> None:
    repo = writable_repo
    artifact_path = write_text(repo / ".tmp_patch.pyfrag", "temporary")
    artifact_dir = repo / ".grace_plan_abc123"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    write_text(artifact_dir / "nested.txt", "temporary")

    result = runner().invoke(CLI.app, ["clean", str(repo), "--dry-run", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "clean"
    assert payload["dry_run"] is True
    assert payload["cleaned_count"] == 2
    assert artifact_path.exists()
    assert artifact_dir.exists()


def test_cli_clean_removes_temp_artifacts_and_keeps_non_temp_files(writable_repo: Path) -> None:
    repo = writable_repo
    temp_artifact = write_text(repo / ".tmp_patch.pyfrag", "temporary")
    kept_plan = write_text(repo / "committed.plan.json", "{}")

    result = runner().invoke(CLI.app, ["clean", str(repo), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["dry_run"] is False
    assert payload["cleaned_count"] == 1
    assert not temp_artifact.exists()
    assert kept_plan.exists()


def test_cli_lint_reports_untracked_artifact_warning_with_zero_exit_code(writable_repo: Path) -> None:
    repo = writable_repo
    write_text(repo / "pricing.py", make_grace_file())
    artifact_path = write_text(repo / "manual.plan.json", "{}")

    result = subprocess.run(
        [sys.executable, "-m", "grace.cli", "lint", str(repo), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "lint"
    assert payload["warning_count"] >= 1
    assert any(issue["code"] == "untracked_artifact" for issue in payload["warnings"])
    assert any(issue["path"] == str(artifact_path.resolve()) for issue in payload["warnings"])
